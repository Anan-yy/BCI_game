"""
疯狂奶茶杯 - 游戏配置文件
所有游戏参数、资源路径、颜色、尺寸等集中在此管理
修改游戏数值时，优先在此文件中查找对应参数
"""

import os

import pygame

# ============================================================
# 屏幕配置
# ============================================================
SCREEN_WIDTH = 1280  # 游戏窗口宽度（像素），修改此项可改变窗口宽度
SCREEN_HEIGHT = 720  # 游戏窗口高度（像素），修改此项可改变窗口高度
FPS = 60  # 游戏帧率，值越高画面越流畅，但会增加 CPU/GPU 负担
TITLE = "疯狂奶茶杯 - 第1周"  # 游戏窗口标题栏文字

# ============================================================
# 资源路径配置
# ============================================================
ASSETS_DIR = "assets"  # 资源文件夹根目录
IMAGES_DIR = os.path.join(ASSETS_DIR, "images")  # 图片资源目录
SOUNDS_DIR = os.path.join(ASSETS_DIR, "sounds")  # 音效资源目录

# ============================================================
# 图片资源路径
# 新增图片时只需将文件放入 images 目录，然后在此处添加路径即可
# ============================================================
BACKGROUND_IMG = os.path.join(IMAGES_DIR, "backgrounds", "奶茶店2.png")  # 背景图
CUP_LEVEL_IMGS = [  # 不同等级的杯子图片列表
    os.path.join(IMAGES_DIR, "cups", "cup1.png"),
    os.path.join(IMAGES_DIR, "cups", "cup2.png"),
    os.path.join(IMAGES_DIR, "cups", "cup3.png"),
]
FOCUS_TEAPOT_IMG = os.path.join(
    IMAGES_DIR, "other", "focus_teapot.png"
)  # 专注力茶壶 UI 图片
INGREDIENT_IMGS = {  # 食材图片字典
    "红茶": os.path.join(IMAGES_DIR, "ingredients", "tea.png"),
    "牛奶": os.path.join(IMAGES_DIR, "ingredients", "milk.png"),
    "珍珠": os.path.join(IMAGES_DIR, "ingredients", "pearl.png"),
    "椰果": os.path.join(IMAGES_DIR, "ingredients", "coconut.png"),
    "布丁": os.path.join(IMAGES_DIR, "ingredients", "pudding.png"),
    "仙草": os.path.join(IMAGES_DIR, "ingredients", "grass_jelly.png"),
    "秘方": os.path.join(IMAGES_DIR, "ingredients", "secret_recipe.png"),
}
BADGE_IMGS = [  # 徽章图片列表，按等级排列
    os.path.join(IMAGES_DIR, "badges", "badge1.png"),
    os.path.join(IMAGES_DIR, "badges", "badge2.png"),
    os.path.join(IMAGES_DIR, "badges", "badge3.png"),
]
PATIENCE_BAR_IMG = os.path.join(IMAGES_DIR, "other", "耐心条.png")
PATIENCE_BAR_SIZE = (350, 35)
PATIENCE_BAR_TIMEOUT = 90.0  # 接住小料的超时时间（秒）

# ============================================================
# 中文字体配置（按加载优先级排列）
# 系统会依次尝试加载，直到成功为止
# ============================================================
CHINESE_FONTS = [
    os.path.join(
        ASSETS_DIR, "fonts", "ZCOOLKuaiLe-Regular.ttf"
    ),  # 站酷快乐体（项目内置卡通字体，优先使用）
    "simhei.ttf",  # 黑体（Windows 系统字体）
    "simkai.ttf",  # 楷体（Windows 系统字体）
    "msyh.ttf",  # 微软雅黑（Windows 系统字体）
    "msyhbd.ttf",  # 微软雅黑粗体（Windows 系统字体）
    os.path.join(ASSETS_DIR, "fonts", "simhei.ttf"),  # 项目内置黑体（备用）
]

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
CUP_SPEED = 5  # 杯子左右移动速度（像素/帧），值越大移动越快
CUP_COLOR = BROWN  # 杯子默认颜色（无图片时使用）

# ============================================================
# 食材配置
# ============================================================
INGREDIENT_SIZE = 40  # 食材图片尺寸（像素），修改此项可同时改变所有食材大小
INGREDIENT_SPEED = 3  # 食材下落速度（像素/帧），值越大下落越快，游戏难度越高
INGREDIENT_TYPES = [
    "红茶",
    "牛奶",
    "珍珠",
    "椰果",
    "布丁",
    "仙草",
]  # 当前关卡可掉落的食材种类列表

INGREDIENT_COLORS = {  # 食材默认颜色（无图片时使用，RGB 格式）
    "红茶": (160, 82, 45),
    "牛奶": (255, 250, 240),
    "珍珠": (105, 105, 105),
    "椰果": (240, 230, 140),
    "布丁": (255, 200, 100),
    "仙草": (50, 50, 50),
}

INGREDIENT_POINTS = {  # 食材分值/金钱值，接到对应食材时获得的分数
    "红茶": 8,
    "牛奶": 5,
    "珍珠": 10,
    "椰果": 6,
    "布丁": 12,
    "仙草": 8,
}

# ============================================================
# 脑电（BCI）数据配置
# 注意：BCI服务器IP和端口请在游戏中点击"BCI设置"按钮进行配置
# 配置文件保存在 bci_config.json
# ============================================================
DEFAULT_ATTENTION = 50  # 默认专注力值（0-100），模拟数据基准值
DEAD_ZONE = 5  # 死区阈值，头动信号绝对值小于此值时视为静止（防抖动）
SMOOTHING_FACTOR = (
    0.3  # 指数平滑因子（0-1），值越大响应越快但越抖动，值越小越平滑但延迟越大
)
YAW_SCALE = 0.5  # 头动偏航角缩放系数，控制头部转动映射到杯子移动的距离
BCI_CONNECTION_TIMEOUT = 5  # 连接超时时间（秒）

# ============================================================
# 游戏模式配置
# ============================================================
GAME_MODES = {
    "regular": {
        "name": "常规模式",
        "description": "接住必接食材，完成标准配方",
        "has_required": True,
        "free_combine": False,
        "bci_mode": False,
        "ingredient_speed": 3,
        "spawn_interval": 1000,
        "ui_color": (60, 160, 100),
    },
    "challenge": {
        "name": "挑战模式",
        "description": "更快更密集，考验你的手速",
        "has_required": True,
        "free_combine": False,
        "bci_mode": False,
        "ingredient_speed": 5,
        "spawn_interval": 600,
        "ui_color": (200, 80, 60),
    },
    "creative": {
        "name": "创意模式",
        "description": "自由搭配，创造你的专属奶茶",
        "has_required": False,
        "free_combine": True,
        "bci_mode": False,
        "ingredient_speed": 3,
        "spawn_interval": 1200,
        "ui_color": (120, 80, 200),
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
    },
}

DEFAULT_GAME_MODE = "regular"  # 默认游戏模式
GAME_DURATION = 120  # 一局游戏时长（秒），修改此项可改变单局时间

# ============================================================
# 生成间隔（毫秒）
# 注：实际间隔由 GAME_MODES 中对应模式的 spawn_interval 决定
# ============================================================
INGREDIENT_SPAWN_INTERVAL = 1000  # 兼容旧代码的默认值
