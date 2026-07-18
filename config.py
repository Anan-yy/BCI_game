"""
疯狂奶茶杯 - 游戏配置文件
所有游戏参数、资源路径、颜色、尺寸等集中在此管理
修改游戏数值时，优先在此文件中查找对应参数
"""

import os
import sys

import pygame


def _get_base_path():
    """获取资源基础路径，支持 PyInstaller 打包"""
    if getattr(sys, "frozen", False):
        return sys._MEIPASS
    return os.path.abspath(".")


# ============================================================
# 屏幕配置
# ============================================================
SCREEN_WIDTH = 1280  # 游戏窗口宽度（像素），修改此项可改变窗口宽度
SCREEN_HEIGHT = 720  # 游戏窗口高度（像素），修改此项可改变窗口高度
TITLE = "疯狂奶茶杯"  # 游戏窗口标题栏文字

# ============================================================
# 六等分车道配置 (保留向后兼容)
# ============================================================
NUM_LANES = 6
LANE_WIDTH = SCREEN_WIDTH // NUM_LANES
MIDDLE_LANE_INDICES = [NUM_LANES // 2 - 1, NUM_LANES // 2]
INGREDIENT_LANE_INDICES = [0, 1, 4, 5]
LANE_LINE_COLOR = (100, 100, 100, 40)

# ============================================================
# 出料口位置 (基于游戏背景图1920x1078映射到1280x720)
# ============================================================
OUTLET_POSITIONS = [
    (114, 182),
    (345, 183),
    (904, 184),
    (1141, 181),
]
OUTLET_BLOCK_RADIUS = 60  # 出料口堵塞检测半径
# ============================================================
# ============================================================
# 资源路径配置
# ============================================================
ASSETS_DIR = os.path.join(_get_base_path(), "assets")  # 资源文件夹根目录
IMAGES_DIR = os.path.join(ASSETS_DIR, "images")  # 图片资源目录
SOUNDS_DIR = os.path.join(ASSETS_DIR, "sounds")  # 音效资源目录

# ============================================================
# 图片资源路径
# 新增图片时只需将文件放入 images 目录，然后在此处添加路径即可
# ============================================================
BACKGROUND_IMG = os.path.join(IMAGES_DIR, "backgrounds", "游戏背景.jpg")  # 游戏背景图
CUP_IMGS = [  # 杯子阶段图片：0接→1, 1接→2, 2+接→3
    os.path.join(IMAGES_DIR, "cups", "奶茶杯1.png"),
    os.path.join(IMAGES_DIR, "cups", "奶茶杯2.png"),
    os.path.join(IMAGES_DIR, "cups", "奶茶杯3.png"),
]
INGREDIENT_IMGS = {  # 食材图片字典
    "红茶": os.path.join(IMAGES_DIR, "ingredients", "红茶.png"),
    "绿茶": os.path.join(IMAGES_DIR, "ingredients", "绿茶.png"),
    "牛奶": os.path.join(IMAGES_DIR, "ingredients", "牛奶.png"),
    "珍珠": os.path.join(IMAGES_DIR, "ingredients", "珍珠.png"),
    "椰果": os.path.join(IMAGES_DIR, "ingredients", "椰果.png"),
    "芋圆": os.path.join(IMAGES_DIR, "ingredients", "芋圆.png"),
    "脆啵啵": os.path.join(IMAGES_DIR, "ingredients", "脆啵啵.png"),
    "芒果": os.path.join(IMAGES_DIR, "ingredients", "芒果.png"),
    "椰奶": os.path.join(IMAGES_DIR, "ingredients", "椰奶.png"),
    "草莓": os.path.join(IMAGES_DIR, "ingredients", "草莓.png"),
    "芋泥": os.path.join(IMAGES_DIR, "ingredients", "芋泥.png"),
    "燕麦奶": os.path.join(IMAGES_DIR, "ingredients", "燕麦奶.png"),
    "咖啡": os.path.join(IMAGES_DIR, "ingredients", "咖啡.png"),
    "特调稀奶油顶": os.path.join(IMAGES_DIR, "ingredients", "特调稀奶油顶.png"),
    "抹茶奶盖": os.path.join(IMAGES_DIR, "ingredients", "抹茶奶盖.png"),
    "米酿": os.path.join(IMAGES_DIR, "ingredients", "米酿.png"),
    "咸芝士奶盖": os.path.join(IMAGES_DIR, "ingredients", "咸芝士奶盖.png"),
    "茉莉花茶": os.path.join(IMAGES_DIR, "ingredients", "茉莉花茶.png"),
    "秘方": os.path.join(IMAGES_DIR, "ingredients", "秘方.png"),
    "冰块": os.path.join(IMAGES_DIR, "ingredients", "冰块.png"),
}
BADGE_IMGS = [  # 徽章图片列表，按等级排列
    os.path.join(IMAGES_DIR, "badges", "badge1.png"),
    os.path.join(IMAGES_DIR, "badges", "badge2.png"),
    os.path.join(IMAGES_DIR, "badges", "badge3.png"),
    os.path.join(IMAGES_DIR, "badges", "badge4.png"),
]
PATIENCE_BAR_IMG = os.path.join(IMAGES_DIR, "other", "耐心条.png")
TOP_BAR_IMG = os.path.join(IMAGES_DIR, "other", "横.png")  # 游戏顶部背景板（已弃用，保留向后兼容）
INFO_BAR_IMG = os.path.join(IMAGES_DIR, "other", "信息栏.png")  # 游戏顶部信息栏
INFO_BAR_HEIGHT = 123  # 信息栏缩放后高度 (184 * 1280/1919)
# 信息标签中心坐标 (基于背景图1920x1078映射到1280x720)
INFO_REGIONS = [
    (169, 64),  # 等级 (182,67)-(326,125)
    (354, 63),  # 模式 (435,67)-(628,123)
    (870, 62),  # 杯数 (1217,62)-(1395,123)
    (1080, 61),  # 收益 (1538,62)-(1705,121)
]
INFO_FONT_SIZE = 26
# 等级徽章位置 (基于背景图1920x1078映射到1280x720, 区域(19,15)-(170,162))
INFO_BADGE_POS = (63, 59)  # 徽章中心点
INFO_BADGE_SIZE = (100, 100)
PATIENCE_BAR_SIZE = (350, 35)
PATIENCE_BAR_TIMEOUT = 90.0  # 接住小料的超时时间（秒）

# ============================================================
# 专注力球 - 游戏内显示实时注意力值
# 原始背景图1920x1078上的位置(831,639)-(1109,873) 映射到1280x720
# ============================================================
FOCUS_BALL_IMG = os.path.join(IMAGES_DIR, "other", "专注力球.png")
FOCUS_BALL_POS = (640, 360)  # 球中心点 (屏幕居中)
FOCUS_BALL_SIZE = (198, 163)  # 球显示尺寸 (保持原图 1065x877 宽高比，缩小10%)
NUM_IMG_DIR = os.path.join(IMAGES_DIR, "nums")
DIGIT_WIDTH = 35
DIGIT_HEIGHT = 45
DIGIT_SPACING = 3

# 出料口区域 (遮罩镂空) - 基于背景图1920x1078映射到1280x720
OVERLAY_CLEAR_REGIONS = [
    (47, 124, 133, 75),
    (281, 127, 127, 75),
    (838, 126, 131, 77),
    (1072, 118, 138, 81),
]
BACKGROUND_OVERLAY_ALPHA = 90  # 游戏背景遮罩不透明度（0=不遮, 255=全黑），可在设置中调节
SHOW_HUD_INFO = True  # 是否显示顶部信息栏（等级、模式、杯数、收益）
SHOW_FOCUS_BALL = True  # 是否显示专注力球

# ============================================================
# 结算面板 - 游戏结束/退出时显示
# ============================================================
SUMMARY_PANEL_IMG = os.path.join(IMAGES_DIR, "other", "结算面板.png")
SETTINGS_PANEL_IMG = os.path.join(IMAGES_DIR, "other", "设置面板.png")
TRAINING_PANEL_IMG = os.path.join(IMAGES_DIR, "other", "训练计划面板.png")
SUMMARY_PANEL_SIZE = (1024, 658)
SUMMARY_PANEL_POS = (128, 31)  # centered on 1280x720
SUMMARY_BTN_W = 200
SUMMARY_BTN_H = 50
SUMMARY_BTN_GAP = 60  # 两按钮间距

# ============================================================
# 颜色定义（RGB 三元组，范围 0-255）
# ============================================================
WHITE = (255, 255, 255)  # 白色
BLACK = (0, 0, 0)  # 黑色
BROWN = (139, 69, 19)  # 棕色
RED = (255, 0, 0)  # 红色
GREEN = (0, 255, 0)  # 绿色

# ============================================================
# 杯子配置
# ============================================================
CUP_WIDTH = 80  # 杯子宽度（像素），修改此项可改变杯子大小
CUP_HEIGHT = 100  # 杯子高度（像素），修改此项可改变杯子大小
CUP_SPEED = 9  # 杯子左右移动速度（像素/帧），值越大移动越快 (8 ≈ 480px/s)
CUP_COLOR = BROWN  # 杯子默认颜色（无图片时使用）

# ============================================================
# 食材配置
# ============================================================
INGREDIENT_SIZE = 80  # 食材图片尺寸（像素），修改此项可同时改变所有食材大小
INGREDIENT_SPEED = 3.5  # 食材下落速度（像素/帧），值越大下落越快，游戏难度越高
INGREDIENT_TYPES = [  # 所有食材种类
    "珍珠",
    "椰果",
    "牛奶",
    "红茶",
    "绿茶",
    "芋圆",
    "脆啵啵",
    "芒果",
    "椰奶",
    "草莓",
    "芋泥",
    "燕麦奶",
    "咖啡",
    "特调稀奶油顶",
    "抹茶奶盖",
    "米酿",
    "咸芝士奶盖",
    "茉莉花茶",
    "秘方",
]

INGREDIENT_COLORS = {  # 食材默认颜色（无图片时使用，RGB 格式）
    "珍珠": (60, 50, 40),
    "椰果": (240, 230, 140),
    "牛奶": (255, 250, 240),
    "红茶": (160, 82, 45),
    "绿茶": (120, 180, 80),
    "芋圆": (180, 140, 100),
    "脆啵啵": (200, 180, 220),
    "芒果": (140, 100, 60),
    "椰奶": (255, 245, 230),
    "草莓": (220, 50, 80),
    "芋泥": (170, 120, 160),
    "燕麦奶": (230, 210, 170),
    "咖啡": (90, 60, 40),
    "特调稀奶油顶": (255, 245, 200),
    "抹茶奶盖": (255, 245, 200),
    "米酿": (240, 220, 160),
    "咸芝士奶盖": (250, 240, 180),
    "茉莉花茶": (180, 210, 100),
    "冰块": (180, 210, 240),
}

INGREDIENT_POINTS = {  # 食材分值/金钱值，接到对应食材时获得的价格（元）
    "珍珠": 1,
    "椰果": 1,
    "牛奶": 2,
    "红茶": 2,
    "绿茶": 3,
    "芋圆": 2,
    "脆啵啵": 2,
    "芒果": 2,
    "椰奶": 3,
    "草莓": 3,
    "芋泥": 3,
    "燕麦奶": 4,
    "咖啡": 4,
    "特调稀奶油顶": 5,
    "抹茶奶盖": 5,
    "米酿": 5,
    "咸芝士奶盖": 6,
    "茉莉花茶": 6,
    "秘方": 0,
    "冰块": 0,
}

TRAINING_INGREDIENT_POINTS = {
    "牛奶": 3, "红茶": 3, "绿茶": 3, "芒果": 3, "椰奶": 3,
    "燕麦奶": 3, "咖啡": 3, "茉莉花茶": 3,
    "珍珠": 2, "椰果": 2, "芋圆": 2, "脆啵啵": 2,
    "草莓": 2, "芋泥": 2, "特调稀奶油顶": 2,
    "抹茶奶盖": 2, "米酿": 2, "咸芝士奶盖": 2,
    "秘方": 0, "冰块": 0,
}

INGREDIENT_TIERS = {  # 等级系统：每个等级的可用食材和必接食材（含之前等级所有食材）
    1: {
        "available": ["珍珠", "椰果", "牛奶", "红茶", "绿茶"],
        "required": ["牛奶", "红茶", "绿茶"],
    },
    2: {
        "available": [
            "珍珠",
            "椰果",
            "牛奶",
            "红茶",
            "绿茶",
            "芋圆",
            "脆啵啵",
            "芒果",
            "椰奶",
        ],
        "required": ["牛奶", "红茶", "绿茶", "芒果", "椰奶"],
    },
    3: {
        "available": [
            "珍珠",
            "椰果",
            "牛奶",
            "红茶",
            "绿茶",
            "芋圆",
            "脆啵啵",
            "芒果",
            "椰奶",
            "草莓",
            "芋泥",
            "燕麦奶",
            "咖啡",
        ],
        "required": ["牛奶", "红茶", "绿茶", "芒果", "椰奶", "燕麦奶", "咖啡"],
    },
    4: {
        "available": [
            "珍珠",
            "椰果",
            "牛奶",
            "红茶",
            "绿茶",
            "芋圆",
            "脆啵啵",
            "芒果",
            "椰奶",
            "草莓",
            "芋泥",
            "燕麦奶",
            "咖啡",
            "抹茶奶盖",
            "米酿",
            "咸芝士奶盖",
            "茉莉花茶",
        ],
        "required": [
            "牛奶",
            "红茶",
            "绿茶",
            "芒果",
            "椰奶",
            "燕麦奶",
            "咖啡",
            "茉莉花茶",
        ],
    },
}

# ============================================================
# 脑电（BCI）数据配置
# 注意：BCI服务器IP和端口请在游戏中点击"BCI设置"按钮进行配置
# 配置文件保存在 bci_config.json
# ============================================================
DEFAULT_ATTENTION = 50  # 默认专注力值（0-100）
BCI_CONNECTION_TIMEOUT = 5  # 连接超时时间（秒）

# ============================================================
# 一杯制配置
# ============================================================
CUP_DURATION = 20  # 每杯时间上限 T（秒），超时则结算
TOTAL_CUPS = 45  # 本局共需制作的奶茶杯数，游戏最大时长 = TOTAL_CUPS × CUP_DURATION（15分钟=900秒）
SECRET_RECIPE_SUSTAIN = 8  # 秘方触发所需持续专注秒数
DIFFICULTY_BASELINE = 60  # 难度基线初始值（0-100），自适应调节
DIFFICULTY_ADAPT_WINDOW = 30  # 难度自适应窗口（秒），取此窗口内平均专注力更新基线
CUP_SPEED_MIN = 2.0  # 专注力高时的最低食材速度（px/frame），约可接住 ≥8 个/杯
CUP_SPEED_MAX = 5.0  # 专注力低时的最高食材速度（px/frame），约可接住 ≤6 个/杯
DIFFICULTY_BASELINE_MIN = 40  # 基线调节下限
DIFFICULTY_BASELINE_MAX = 80  # 基线调节上限

# ============================================================
# 热身阶段配置
# 进入正式游戏前进行 3 分钟热身，收集注意力数据用于归一化
# ============================================================
WARMUP_DURATION = 180  # 热身阶段时长（秒），修改此项可改变热身时间
WARMUP_LOW_THRESHOLD = 10  # 低注意力阈值，注意力低于此值时开始计时冻结（与正式游戏一致）
WARMUP_FREEZE_TIME = 5.0  # 低注意力持续多久冻结画面（秒），与正式游戏一致

# ============================================================
# 防伪迹仲裁配置
# 正常专注时头部有微小自然抖动（1-2度），若头部完全静止
# 超过阈值且专注力异常高，判定为刻意咬牙/僵直等伪迹行为
# ============================================================
ARTIFACT_STILL_THRESHOLD = 0.5  # 陀螺仪变化阈值（度），低于此值视为头部静止
ARTIFACT_STILL_DURATION = 10.0   # 头部静止持续时间（秒），超时触发检测
ARTIFACT_ATTENTION_THRESHOLD = 80  # 专注力阈值，高于此值+静止=判定伪迹
ARTIFACT_PENALTY_DURATION = 5.0  # 惩罚冻结时长（秒），自动恢复

# ============================================================
# 专注力-收益系数（专注意义化）
# 防止低专注力下食材速度快反而接到更多、收益更高
# 高专注力 → 全额收益，低专注力 → 收益打折
# ============================================================


def get_attention_coefficient(normalized_attn: float) -> float:
    if normalized_attn > 50:
        return 1.0
    elif normalized_attn >= 20:
        return 0.5 + 0.5 * (normalized_attn - 20) / 30
    else:
        return 0.5


WARMUP_RESUME_TIME = 3.0  # 注意力恢复后持续多久解冻（秒）
WARMUP_RESUME_THRESHOLD = 15  # 低专注恢复阈值（注意力 > 15 才计时恢复）
WARMUP_SMOOTH_WINDOW = 3.0  # 注意力平滑窗口（秒），用于速度计算

# ============================================================
# 正式游戏速度配置（热身结束后使用）
# 速度变化范围比热身阶段窄，减轻感知
# ============================================================
FORMAL_SPEED_MIN = 2.0  # 正式游戏最低速度（归一化值=100时，pixels/frame）
FORMAL_SPEED_MAX = 4.5  # 正式游戏最高速度（归一化值=1时，pixels/frame）
RAW_SPEED_MIN = 1.5  # 原萃模式最低速度（高专注时，pixels/frame）
RAW_SPEED_MAX = 6.0  # 原萃模式最高速度（低专注时，pixels/frame）

# ============================================================
# 忆调模式配置
# ============================================================
MEMORY_SPEED_MIN = 2.5  # 忆调模式最低速度（高专注时，pixels/frame）
MEMORY_SPEED_MAX = 6.5  # 忆调模式最高速度（低专注时，pixels/frame）
MEMORY_SPEED_DEFAULT = 5.5  # 忆调模式默认速度（无BCI时，pixels/frame）
MEMORY_SPAWN_MULTIPLIER = 3  # 每轮投放倍数：总食材数 = recipe_length × 此值
MEMORY_SESSION_DURATION = 900  # 忆调模式一局总时长（秒），默认15分钟

# ============================================================
# 游戏模式配置
# ============================================================
GAME_MODES = {
    "regular": {
        "name": "特调模式",
        "description": "接住必接食材，完成标准配方",
        "has_required": True,
        "free_combine": False,
        "bci_mode": False,
        "ingredient_speed": 3,
        "spawn_interval": 1000,
        "ui_color": (60, 160, 100),
        "total_cups": 45,
        "secret_recipe_cup_interval": 1,
    },
    "bci": {
        "name": "脑机接口模式",
        "description": "使用BCI设备读取专注力和头动数据",
        "has_required": False,
        "free_combine": True,
        "bci_mode": True,
        "ingredient_speed": 3,
        "spawn_interval": 1200,
        "ui_color": (0, 150, 200),
        "total_cups": 45,
        "secret_recipe_cup_interval": 3,
    },
    "infinite": {
        "name": "原萃模式",
        "description": "原始注意力驱动，专注力直接控制食材速度",
        "has_required": False,
        "free_combine": True,
        "bci_mode": True,
        "ingredient_speed": 3,
        "spawn_interval": 1000,
        "ui_color": (200, 100, 50),
        "secret_recipe_cup_interval": 3,
        "raw_attention": True,
    },
}

# ============================================================
# 控制模式配置（主菜单模式选择器使用）
# 特调模式使用 bci 游戏底层配置
# ============================================================
CONTROL_MODES = [
    {
        "key": "bci_normal",
        "name": "特调模式",
        "desc": "BCI头环控制杯子，未连接时键盘控制",
        "enabled": True,
        "color": (0, 150, 200),
        "glow": (100, 200, 255),
    },
    {
        "key": "memory",
        "name": "忆调模式",
        "desc": "记忆食材序列",
        "enabled": True,
        "color": (100, 100, 100),
        "glow": (150, 150, 150),
    },
    {
        "key": "infinite",
        "name": "原萃模式",
        "desc": "专注力直驱食材速度，不进行归一化",
        "enabled": True,
        "color": (200, 100, 50),
        "glow": (255, 150, 100),
    },
    {
        "key": "training",
        "name": "训练模式",
        "desc": "分阶段训练，配置原萃/特调/忆调时长",
        "enabled": True,
        "color": (160, 40, 40),
        "glow": (220, 80, 80),
    },
]

# ============================================================
# 生成间隔（毫秒）
# 注：实际间隔由 GAME_MODES 中对应模式的 spawn_interval 决定
# ============================================================
INGREDIENT_SPAWN_INTERVAL = 1000  # 兼容旧代码的默认值
