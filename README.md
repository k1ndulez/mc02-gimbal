# mc02-gimbal — 达妙 MC02 + 3×ZDT X42 三轴云台

用 STM32H723 主控 + 三个闭环步进做一台"指哪停哪"的三轴云台：方位轴 / 俯仰轴 / 横滚轴。

> 不是航拍增稳云台（那种要用无刷 + FOC + IMU），这是**定位型转台**：
> 停得准、停得稳、能读回位置，代价是高速段力矩小、有噪音。

## 当前状态

| 阶段 | 状态 |
|---|---|
| 硬件方案（选型 / 电源 / 接线） | ✅ 已定稿，有机器校验 |
| 固件（脉冲生成 / 三轴联动） | ⬜ 未开始 |
| CAN 总线控制 | ⬜ 预留 |
| 视觉接入（MaixCAM Pro / K230） | ⬜ 选型未定 |
| 整机联调 | ⬜ 未开始 |

## 硬件

| 部件 | 型号 / 参数 |
|---|---|
| 主控 | 达妙 DM-MC02（STM32H723VGT6，Cortex-M7 550MHz，3× CANFD） |
| 执行器 | 3× ZDT X42S 闭环步进（1.8°，16 细分，3200 脉冲/圈） |
| 电源 | 24V 10A + 自制 24V 分电板（1 入 5 出，主保险 10A） |
| 控制方式 | 脉冲 + 方向为主，CAN3 备用汇流 |
| 视觉 | MaixCAM Pro 或 K230（串口接 USART1） |

## 引脚速查

| 轴 | STEP | DIR | 定时器 |
|---|---|---|---|
| 方位轴（文档中 `base`） | `PE13` | `PD10` | TIM1_CH3 |
| 俯仰轴（`joint1`） | `PE8` | `PE14` | TIM1_CH4 |
| 横滚轴（`joint2`） | `PA0` | `PD14` | TIM2_CH1 |
| 三轴 | `COM`/`En` 并接扩展口 #8 的 **3.3V** | — | 共阳光耦 |

> 为什么 STEP 要分在 TIM1 和 TIM2：`PA0`(TIM2_CH1) 与 `PA2`(TIM2_CH3) 同源，
> 共享 ARR 只能跑同一频率；分开才能三轴独立调速。

## 三条硬约束

1. **X42 的 `COM` 只能接 3.3V**。接 5V/24V 会经光耦把高压灌进 MCU，直接烧板。
2. **`V+`/`Gnd` 禁止杜邦线**。电源走 2P 端子（或 XH2.54 / 焊接），杜邦只走信号。
3. **24V 只在分电板熔断**。主保险 10A，X42 三路各 3A，MC02 1.5A，备用 2A。

## 目录

```text
docs/hardware/
  MC02+3xX42+24V分电板-接线表.md    完整接线表（电源树 / 端子 / 信号 / 自检 / BOM）
  MC02+3xX42+24V分电板-接线图.png   一页速查图
  wiring-mc02-x42.json              机器可校验的引脚注册表
  check_wiring.py                   自检脚本（0 FAIL 才算接线表自洽）
  make_wiring_diagram.py            重新生成速查图
```

## 怎么用

在仓库根目录运行：

```bash
# 校验接线表（引脚冲突 / 电源 / 保险丝 / 自检覆盖度）
python -X utf8 docs/hardware/check_wiring.py
# 期望：结果 0 FAIL

# 重新生成接线速查图（需要 Pillow + 微软雅黑）
python -X utf8 docs/hardware/make_wiring_diagram.py
```

## 资料

- 达妙科技《DM-MC-Board02 电机开发板使用说明书 V1.1》2025.07.23
- 张大头《ZDT_X42S 第二代闭环步进电机用户手册 V1.0.5》2026.05.27

## 相关仓库

- `C:\Users\liangshanyou\Documents\stm32f103-diff-car` — 上一代项目，F103 差速小车（航向闭环 + 体感遥控）
- `C:\Users\liangshanyou\Documents\gimbal` — 更早的 ESP32 二轴云台骨架（未写代码）
