# -*- coding: utf-8 -*-
"""
BCI 注意力训练 EEG 分析 - 配置文件
"""

# 数据路径
DATA_ROOT = r"d:\code\CrazyMilkTeaCup\bci训练日志"
OUTPUT_DIR = r"d:\code\CrazyMilkTeaCup\bci_analysis\outputs"

# EEG 参数
FS = 250                # 采样率 (Hz)
CHANNEL_NAME = "Fp2"    # 电极位置

# 频带定义 (Hz)
BANDS = {
    "Delta (1-4)":   (1, 4),
    "Theta (4-8)":   (4, 8),
    "Alpha (8-13)":  (8, 13),
    "Beta (13-30)":  (13, 30),
    "Gamma (30-45)": (30, 45),
}

BAND_COLORS = {
    "Delta (1-4)":   "#1f77b4",
    "Theta (4-8)":   "#ff7f0e",
    "Alpha (8-13)":  "#2ca02c",
    "Beta (13-30)":  "#d62728",
    "Gamma (30-45)": "#9467bd",
}

BAND_ALPHA = 0.3

# 预处理
LOWCUT = 1.0
HIGHCUT = 45.0
NOTCH_FREQ = 50.0      # 50Hz 工频 (中国)

# PSD 计算
NFFT = 512             # FFT 窗口大小 (2秒)
NOVERLAP = 256         # 50% 重叠

# 图表参数
FIGSIZE_WIDE = (14, 8)
FIGSIZE_SQUARE = (10, 8)
DPI = 150
