#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MC02 + 3xX42 + 24V 分电板 接线表自检脚本。

用法:
    python docs/hardware/check_wiring.py

退出码:
    0 = 全部检查通过
    1 = 存在 FAIL

设计意图: 让接线表"可被机器验证"。引脚、端子、电源、保险丝、上电自检
这些最容易抄错的地方，由脚本兜底，而不是靠肉眼。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HW = ROOT / "docs" / "hardware"
PINMAP = HW / "wiring-mc02-x42.json"
DOC = HW / "MC02+3xX42+24V分电板-接线表.md"

# ---------------------------------------------------------------------------
# MC02 侧允许引用的引脚清单（来源：DM-MC-Board02 说明书 V1.1 附录一 管脚配置图
# + 第 17 节 用户扩展 IO 表 + 第 3/6/7/8 节接口表）。
# 只收"能当 GPIO/PWM/UART/CAN 用"的引脚；纯电源脚（GND/5V/3V3/2V8/1V5）不放这里。
# ---------------------------------------------------------------------------
MC02_PINS = {
    # PWM 排口（PWMx4）: PA00 PA02 PE09 PE13
    "PA0": "PWM1 / TIM2_CH1",
    "PA2": "PWM2 / TIM2_CH3",
    "PE9": "PWM3 (TIM1_CH4，以原理图复核)",
    "PE13": "PWM4 / TIM1_CH3",
    # 24Pin 扩展口
    "PD15": "扩展 UART9_TX",
    "PD14": "扩展 UART9_RX",
    "PE14": "扩展 GPIO",
    "PE0": "扩展 UART8_RX",
    "PE1": "扩展 UART8_TX",
    "PC12": "扩展 SPI3_MOSI",
    "PC11": "扩展 SPI3_MISO",
    "PC10": "扩展 SPI3_CLK",
    "PB8": "扩展 IIC_SCL（与 DCMI SCL 共用）",
    "PB9": "扩展 IIC_SDA（与 DCMI SDA 共用）",
    # USB / 串口
    "PA9": "USART1_TX",
    "PA10": "USART1_RX",
    "PE8": "UART7_TX",
    "PE7": "UART7_RX",
    "PE3": "UART10_TX",
    "PE2": "UART10_RX",
    # SWD
    "PA13": "SWDIO",
    "PA14": "SWCLK",
    # 板载用户按键（复用需放弃按键）
    "PA5": "LCD KEY / 用户可用",
    # LCD 扩展口
    "PD10": "LCD GPIO",
    # CAN 收发器引脚（只走 CAN 端子，不推荐当 GPIO）
    "PB12": "CAN3_RX",
    "PB13": "CAN3_TX",
    "PD0": "CAN1_RX",
    "PD1": "CAN1_TX",
    "PB5": "CAN2_RX",
    "PB6": "CAN2_TX",
    # 用户按键 / 指示灯（不推荐占用）
    "PA15": "User Key",
    "PA7": "WS2812",
    "PB15": "蜂鸣器 TIM12_CH2",
    # 直接由 X42/扩展口供电的电源脚，允许作为"电源类"引用
    "3V3": "扩展 3V3 电源",
    "5V": "PWM/串口 5V 可控电源",
    "VCC_IN": "扩展口 24V 输入直通",
    "GND": "地",
}

# 这些引脚属于板载必需外设，接线表里不允许被占用（SWD 口本身除外，见下方豁免）
RESERVED = {
    "PA7": "WS2812 状态灯",
    "PB15": "蜂鸣器",
    "PA15": "用户按键",
    "PA13": "SWDIO",
    "PA14": "SWCLK",
}

# 电源/地是可以合法并联共享的，不参与"唯一占用"检查（但每路仍要有自己的回线，见 GND 检查）
SHARED_POWER = {"GND", "3V3", "5V", "VCC_IN"}

# 允许 SWD 调试口占用这两个引脚（其它区块不得再占）
SWD_OWNER = "swd"

X42_SIGNALS = {"V+", "GND", "COM", "En", "Stp", "Dir", "R/A/H", "T/B/L"}
AXES = {"base", "joint1", "joint2"}
REQUIRED_BLOCKS = ("mc02_input", "distribution_board", "x42_axes", "can_backup", "vision", "swd", "self_test")

results: list[tuple[bool, str]] = []


def check(ok: bool, msg: str) -> bool:
    results.append((ok, msg))
    print(("PASS  " if ok else "FAIL  ") + msg)
    return ok


def load_json(path: Path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"FAIL  {path.name} JSON 解析失败: {exc}")
        return None


def iter_mc02_refs(data):
    """收集 JSON 里所有 mc02_pin 字段。"""
    axes = data.get("x42_axes", {})
    if isinstance(axes, dict):
        for axis in axes.values():
            for sig in axis.get("signals", []):
                ref = sig.get("mc02_pin")
                if ref:
                    yield axis.get("name", "?"), sig.get("signal", "?"), ref
    can = data.get("can_backup", {})
    for net in can.get("nets", []):
        ref = net.get("mc02_pin")
        if ref:
            yield "can_backup", net.get("signal", "?"), ref
    vision = data.get("vision", {})
    for net in vision.get("nets", []):
        ref = net.get("mc02_pin")
        if ref:
            yield "vision", net.get("signal", "?"), ref
    swd = data.get("swd", {})
    for net in swd.get("nets", []):
        ref = net.get("mc02_pin")
        if ref:
            yield "swd", net.get("signal", "?"), ref


def main() -> int:
    print("== MC02 + 3xX42 + 24V 分电板 接线表自检 ==\n")

    check(PINMAP.exists(), f"引脚注册表存在: {PINMAP.relative_to(ROOT)}")
    check(DOC.exists(), f"接线表正文存在: {DOC.relative_to(ROOT)}")

    data = load_json(PINMAP) if PINMAP.exists() else None
    if not data:
        check(False, "引脚注册表可解析为 JSON")
        return summarize()

    check(all(k in data for k in REQUIRED_BLOCKS),
          f"注册表包含全部必需区块 {list(REQUIRED_BLOCKS)}")

    # 1) 引脚白名单
    used: dict[str, list[str]] = {}
    for owner, sig, pin in iter_mc02_refs(data):
        ok = pin in MC02_PINS
        check(ok, f"MC02 引脚已知: {owner}.{sig} -> {pin}" + ("" if ok else "（不在引脚清单里）"))
        if ok:
            used.setdefault(pin, []).append(f"{owner}.{sig}")

    # 2) 重复占用（电源/地允许并联）
    for pin, owners in sorted(used.items()):
        if pin in SHARED_POWER:
            check(True, f"电源/地并联: {pin} <- {len(owners)} 处")
            continue
        check(len(owners) == 1, f"引脚唯一占用: {pin} <- {', '.join(owners)}")

    # 3) 保留引脚（SWD 允许被 swd 区块占用）
    for pin, owners in sorted(used.items()):
        if pin not in RESERVED:
            continue
        allowed = all(o.startswith(SWD_OWNER + ".") for o in owners)
        check(allowed, f"保留引脚 {pin}（{RESERVED[pin]}）" + ("允许被 SWD 占用" if allowed else "被非 SWD 占用"))
    check(not any(p in RESERVED for p, o in used.items() if not all(x.startswith(SWD_OWNER + ".") for x in o)),
          "未占用板载必需外设引脚（WS2812/蜂鸣器/按键；SWD 除外）")

    # 4) 三轴完整性
    axes = data.get("x42_axes", {})
    check(isinstance(axes, dict) and set(axes) == AXES,
          f"三轴齐全且命名正确: {sorted(AXES)}")
    if isinstance(axes, dict):
        for key in sorted(AXES & set(axes)):
            ax = axes[key]
            sigs = {s.get("signal") for s in ax.get("signals", [])}
            for need in ("Stp", "Dir"):
                check(need in sigs, f"{ax.get('name', key)} 有 {need} 信号")
            check("En" in sigs or ax.get("en_tied_to") == "COM/3V3",
                  f"{ax.get('name', key)} 的 En 有明确去处（GPIO 或共接 COM/3V3）")
            for s in ax.get("signals", []):
                if s.get("signal") in X42_SIGNALS:
                    continue
                check(False, f"{ax.get('name', key)} 出现未知 X42 端子: {s.get('signal')}")

    # 4b) 电源入口：禁止杜邦
    if isinstance(axes, dict):
        for key in sorted(AXES & set(axes)):
            ax = axes[key]
            vplus = next((s for s in ax.get("signals", []) if s.get("signal") == "V+"), None)
            conn = (vplus or {}).get("connector", "")
            check(bool(conn), f"{ax.get('name', key)} 的 V+ 写明了电源连接器")
            check("杜邦" not in conn,
                  f"{ax.get('name', key)} 的 V+ 未用杜邦（实为 {conn!r}）")

    # 5) 共阳电平硬约束
    com_levels = data.get("x42_common", {}).get("com_level")
    check(com_levels == "3V3", f"X42 COM 电平 = 3V3（实为 {com_levels}）")
    forbidden = data.get("x42_common", {}).get("forbidden_com_levels", [])
    check(set(forbidden) >= {"5V", "24V"}, "登记了 COM 禁止接 5V/24V")

    # 6) 电源树与保险丝
    dist = data.get("distribution_board", {})
    fuse = dist.get("main_fuse_a")
    check(isinstance(fuse, (int, float)) and fuse > 0, f"主保险丝额定有效: {fuse}A")
    branches = dist.get("branches", [])
    check(len(branches) >= 4, f"分电板至少 1 入 4 出（实为 {len(branches)} 路输出）")
    branch_sum = sum(b.get("fuse_a", 0) for b in branches)
    # 分支之和可以大于主保险（保护对象不同：分支保护线束，主保险保护电源/母线），
    # 但必须把选择依据写清楚，否则等于没做选型。
    if branch_sum <= fuse:
        check(True, f"分支保险之和 {branch_sum}A <= 主保险 {fuse}A")
    else:
        check(bool(dist.get("fuse_coordination")),
              f"分支保险之和 {branch_sum}A > 主保险 {fuse}A，但已写明熔断配合依据")
    budget = data.get("power_budget", {})
    total = budget.get("total_avg_a")
    supply = budget.get("supply_a")
    check(isinstance(total, (int, float)) and isinstance(supply, (int, float)) and total <= supply,
          f"平均电流预算闭合: {total}A <= 电源 {supply}A")

    # 7) 每个负载都有 GND 回线
    for key, ax in (axes.items() if isinstance(axes, dict) else []):
        sigs = {s.get("signal") for s in ax.get("signals", [])}
        check("GND" in sigs, f"{ax.get('name', key)} 有 GND 回线")
    for key in ("can_backup", "vision", "swd"):
        blk = data.get(key, {})
        nets = {n.get("signal") for n in blk.get("nets", [])}
        check("GND" in nets, f"{key} 有 GND 回线")

    # 8) CAN 备用汇流
    can = data.get("can_backup", {})
    check(can.get("p_serial") == "CAN1_MAP", "X42 P_Serial 设为 CAN1_MAP")
    terms = can.get("termination", [])
    check(sum(1 for t in terms if t.get("fitted")) == 2,
          f"CAN 终端电阻恰好 2 处（实为 {sum(1 for t in terms if t.get('fitted'))}）")

    # 9) 文档覆盖度
    if DOC.exists():
        text = DOC.read_text(encoding="utf-8")
        must = {
            "COM 3.3V 约束": r"COM\s*(接|→)\s*3\.3V",
            "禁止 COM 接 5V/24V": r"(禁止|严禁|不得)[^\n]{0,20}(5V|24V)",
            "主保险 10A": r"10\s*A",
            "上电自检": r"自检",
            "X42 参数": r"P_Pul",
            "CAN 复用": r"CAN1_MAP",
            "电源口禁杜邦": r"禁止[^\n]{0,12}杜邦",
            "电源端子替代方案": r"XH2\.54|KF128|焊接",
            "MC02 电源输入": r"XT30|24V\s*输入|VCC_IN",
            "SWD": r"SWD",
        }
        for label, pat in must.items():
            check(re.search(pat, text) is not None, f"正文包含: {label}")
        for term in ("V+", "GND", "COM", "En", "Stp", "Dir", "R/A/H", "T/B/L"):
            check(term in text, f"正文覆盖 X42 端子: {term}")

    return summarize()


def summarize() -> int:
    fails = [m for ok, m in results if not ok]
    print(f"\n== 结果: {len(results) - len(fails)} PASS / {len(fails)} FAIL ==")
    if fails:
        for m in fails:
            print("  - " + m)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
