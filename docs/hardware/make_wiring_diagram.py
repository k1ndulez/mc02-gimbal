# -*- coding: utf-8 -*-
"""生成 MC02 + 3xX42 + 24V 分电板 接线速查图（PNG）。"""
import os
from PIL import Image, ImageDraw, ImageFont

FONT = r"C:\Windows\Fonts\msyh.ttc"
FONTB = r"C:\Windows\Fonts\msyhbd.ttc"
W, H = 1760, 2360
BG = (250, 250, 252)
INK = (30, 34, 40)
GRAY = (110, 116, 124)
RED = (200, 40, 40)
BLACK = (25, 25, 25)
PURPLE = (130, 60, 170)
WHITE_Y = (190, 150, 20)
YELLOW = (235, 190, 30)
BLUE = (40, 90, 190)
GREEN = (30, 140, 70)

img = Image.new("RGB", (W, H), BG)
d = ImageDraw.Draw(img)

f_title = ImageFont.truetype(FONTB, 46)
f_h = ImageFont.truetype(FONTB, 32)
f = ImageFont.truetype(FONT, 25)
f_s = ImageFont.truetype(FONT, 21)
f_xs = ImageFont.truetype(FONT, 18)


def box(xy, title, lines, fill=(255, 255, 255), outline=(180, 186, 194), title_fill=None, lw=2):
    x1, y1, x2, y2 = xy
    d.rounded_rectangle(xy, radius=12, fill=fill, outline=outline, width=lw)
    if title:
        d.text((x1 + 14, y1 + 10), title, font=f_h, fill=title_fill or INK)
        yy = y1 + 52
    else:
        yy = y1 + 12
    for ln, color in lines:
        d.text((x1 + 16, yy), ln, font=f_s, fill=color)
        yy += 30


def wire(pts, color, width=4):
    d.line(pts, fill=color, width=width, joint="curve")


def label(xy, text, font=None, fill=INK):
    d.text(xy, text, font=font or f_xs, fill=fill)


# ---------------- 标题 ----------------
d.text((60, 40), "MC02 + 3×X42 + 24V 分电板 · 接线速查", font=f_title, fill=INK)
d.text((60, 105), "机械臂版：底座旋转 / 关节1 / 关节2　·　脉冲+方向主控，CAN 备用　·　COM 共阳接 3.3V",
       font=f_s, fill=GRAY)

# ---------------- 第一层：电源树 ----------------
d.text((60, 160), "① 电源树（24V 分电板 1 入 5 出）", font=f_h, fill=INK)

box((60, 215, 330, 330), "24V 电源", [("24V 10A（4A 不够）", GRAY), ("220V 转 24V 开关电源", GRAY)])
box((390, 215, 640, 330), "J1 主输入", [("2P 5.08 / XT60", GRAY), ("红+ 黑− 16AWG", GRAY)], outline=RED)
box((700, 215, 1010, 340), "F0 主保险 10A\nD1 防反接 P-MOS", [], outline=RED)
box((1050, 180, 1700, 390), "24V 母线（TP24 / TPGND）", [
    ("OUT1  F1 1.5A → MC02（XT30）", INK),
    ("OUT2  F2 3A  → X42 base", INK),
    ("OUT3  F3 3A  → X42 joint1", INK),
    ("OUT4  F4 3A  → X42 joint2", INK),
    ("OUT5  F5 2A  → 24V 备用（视觉降压/夹爪）", INK),
    ("CAN 汇流：J2 入 / J3~J5 出 / JP1 120Ω", GREEN),
])

wire([(330, 272), (390, 272)], RED)
wire([(640, 272), (700, 272)], RED)
wire([(1010, 272), (1050, 272)], RED)

# ---------------- 第二层：MC02 ----------------
d.text((60, 430), "② MC02 侧（引出的关键端子）", font=f_h, fill=INK)

box((60, 490, 830, 1030), "MC02  DM-MC-Board02 / STM32H723VGT6", [
    ("主电源 XT30：24V ← OUT1", RED),
    ("板载：5V 可控 2A(PC15) / 5V 0.6A / 3.3V 1A", GRAY),
    ("", INK),
    ("PWM 排口（4 组 3P：5V / 信号 / GND）", INK),
    ("  PA0=TIM2_CH1   PE13=TIM1_CH3", BLUE),
    ("  PE8/PE9=TIM1_CH4 以丝印+万用表复核", GRAY),
    ("", INK),
    ("24Pin 扩展口（SGDGBF-08-024P-H35）", INK),
    ("  #2 VCC_IN   #4/#6 5V可控   #8 VCC_3V3", INK),
    ("  #9 PD15   #11 PD14   #13 PE14", BLUE),
    ("  #10 CAN3_H   #12 CAN3_L", GREEN),
    ("", INK),
    ("LCD 口 #9 PD10（GPIO）　#10 PA05(KEY)", INK),
    ("USART1：GND / PA9 TX / PA10 RX", INK),
    ("UART7：GND / PE8 TX / PE7 RX", INK),
    ("SWD 4P：3V3 / PA13 / PA14 / GND", INK),
])

# ---------------- 第三层：三轴 ----------------
d.text((860, 430), "③ 三个 X42S（每轴同一套接法）", font=f_h, fill=INK)

axes = [
    ("M1 base 底座旋转", 490, "PE13  TIM1_CH3", "PD10  LCD#9 GPIO", 1),
    ("M2 joint1 关节1", 700, "PE8   TIM1_CH4", "PE14  扩展#13", 2),
    ("M3 joint2 关节2", 910, "PA0   TIM2_CH1", "PD14  扩展#11", 3),
]
for name, y, step, direction, fuse_idx in axes:
    box((860, y, 1700, y + 180), name, [
        (f"V+ ← OUT{fuse_idx+1} 24V 红20AWG    Gnd ← OUT{fuse_idx+1} GND 黑20AWG（共地）", RED),
        (f"Com ← 扩展口#8 3.3V 紫    En ← 与 Com 同点 → 参数设 Hold", PURPLE),
        (f"Stp ← {step}   白", BLUE),
        (f"Dir ← {direction}   黄", YELLOW),
        (f"R/A/H、T/B/L：CAN 备用时 = H/L；不用则悬空", GRAY),
    ], outline=(120, 130, 145))

# ---------------- 第四层：三条红线警告 ----------------
d.text((60, 1080), "④ 三条硬约束（错一条就报废）", font=f_h, fill=RED)
warns = [
    "1. 三个 X42 的 COM 只能并接 【3.3V】。接 5V 或 24V → 光耦把高压灌进 H723 的 Stp/Dir，MCU 报废。",
    "2. 上电前必量：COM 对 GND = 3.3V；三路 24V 分支保险各自在位；GND 三轴与 MC02 同一点汇合。",
    "3. 三轴不要一次全上：先只接 base，1 kHz 试转 → 反转 → 再逐轴加。",
]
yy = 1135
for w in warns:
    d.text((80, yy), w, font=f_s, fill=RED)
    yy += 38

# ---------------- 第五层：视觉 / CAN / 自检 ----------------
d.text((60, 1270), "⑤ 视觉模块（MaixCAM Pro / K230）", font=f_h, fill=INK)
box((60, 1325, 830, 1500), None, [
    ("5V  ← PWM 排口 5V（PC15 使能，≤2A）   橙22AWG", YELLOW),
    ("GND ← PWM 排口 GND                    黑22AWG", BLACK),
    ("TX  → MC02 USART1 #3 RX = PA10         绿", GREEN),
    ("RX  → MC02 USART1 #2 TX = PA9          蓝", BLUE),
    ("备选：UART7 PE8/PE7；超大电流改 OUT5 独立降压", GRAY),
])

d.text((870, 1270), "⑥ CAN 备用（先留端子）", font=f_h, fill=INK)
box((870, 1325, 1700, 1500), None, [
    ("MC02 CAN3 H/L（Pb12/Pb13）→ J2 → J3~J5 → 三轴 R/A/H=H、T/B/L=L", GREEN),
    ("终端 120Ω 只在两端：MC02 板载 + 分电板 JP1（只接通一次）", GREEN),
    ("X42：P_Serial = CAN1_MAP，地址 1/2/3，1 Mbps", GREEN),
    ("SBUS口(PC02) 是 SBUS 输入，不是串口，别拿它接视觉", RED),
])

d.text((60, 1540), "⑦ 上电自检（顺序执行）", font=f_h, fill=INK)
checks = [
    ("1", "断电蜂鸣档量 J1 正负", "不响"),
    ("2", "量 TP24 对 TPGND", "24V ±5%"),
    ("3", "量 OUT1~5 各对 GND", "24V ±5%"),
    ("4", "量扩展口 #8 对 GND", "3.3V ±3%"),
    ("5", "拉高 PC15 量 PWM 排口 5V", "5V ±5%"),
    ("6", "量三个 X42 COM 对 GND", "3.3V，绝不是 5V/24V"),
    ("7", "只接 base，发 1 kHz", "正转不丢步"),
    ("8", "翻转 Dir 再发 1 kHz", "反转"),
    ("9", "立即停止 / 断 24V", "1 秒内停"),
    ("10", "STLink 连 PA13/PA14", "识别 H723"),
]
yy = 1600
for no, act, exp in checks:
    d.text((80, yy), f"{no:>2}.", font=f_s, fill=GRAY)
    d.text((130, yy), act, font=f_s, fill=INK)
    d.text((760, yy), "→ 期望：" + exp, font=f_s, fill=GREEN)
    yy += 36

d.text((60, 2005), "⑧ 线色约定", font=f_h, fill=INK)
legend = [
    ("24V 主/分支", RED, "16AWG / 20AWG"),
    ("GND", BLACK, "16/20/22AWG"),
    ("3.3V COM/En", PURPLE, "24AWG"),
    ("STEP 脉冲", BLUE, "24AWG"),
    ("DIR 方向", YELLOW, "24AWG"),
    ("CAN H/L", GREEN, "24AWG 双绞"),
    ("5V 视觉", WHITE_Y, "22AWG"),
]
x = 80
for name, color, spec in legend:
    d.rectangle((x, 2065, x + 46, 2077), fill=color)
    d.text((x, 2087), name, font=f_xs, fill=INK)
    d.text((x, 2113), spec, font=f_xs, fill=GRAY)
    x += 220

d.text((60, 2190), "机器校验：python -X utf8 docs/hardware/check_wiring.py（0 FAIL 才算接线表自洽）",
       font=f_xs, fill=GRAY)

out = os.path.join("docs", "hardware", "MC02+3xX42+24V分电板-接线图.png")
img.save(out, "PNG")
print(out, img.size)


