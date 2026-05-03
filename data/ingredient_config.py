"""
食材属性配置表 - 定义所有食材的详细属性
用于后续关卡解锁、价格计算等功能的扩展
"""

# 食材类型定义
# 每个食材包含以下属性：
#   name: 显示名称
#   type: 食材类别（"base"=基底，"topping"=配料）
#   price: 价格/分值
#   is_required: 是否为必接食材
#   unlock_level: 解锁等级，达到该等级后才会在游戏中出现
INGREDIENT_TYPES = {
    "红茶": {
        "name": "红茶",
        "type": "base",  # 基底类食材
        "price": 8,  # 分值/金钱
        "is_required": False,  # 非必接
        "unlock_level": 1,  # 初始解锁
    },
    "牛奶": {
        "name": "牛奶",
        "type": "base",
        "price": 5,
        "is_required": False,
        "unlock_level": 1,
    },
    "珍珠": {
        "name": "珍珠",
        "type": "topping",  # 配料类食材
        "price": 10,
        "is_required": True,  # 必接食材
        "unlock_level": 2,  # 等级 2 解锁
    },
    "椰果": {
        "name": "椰果",
        "type": "topping",
        "price": 6,
        "is_required": False,
        "unlock_level": 1,
    },
    "布丁": {
        "name": "布丁",
        "type": "topping",
        "price": 12,
        "is_required": True,
        "unlock_level": 3,  # 等级 3 解锁
    },
    "仙草": {
        "name": "仙草",
        "type": "topping",
        "price": 8,
        "is_required": False,
        "unlock_level": 2,
    },
}


def get_ingredient_info(ing_type):
    """
    获取指定食材的完整信息

    参数:
        ing_type: 食材名称字符串，如 "红茶"

    返回:
        食材属性字典，不存在时返回 None
    """
    return INGREDIENT_TYPES.get(ing_type)


def get_available_ingredients(level=1):
    """
    根据玩家等级获取当前可用的食材列表

    参数:
        level: 玩家当前等级，默认 1

    返回:
        可用食材名称列表
    """
    return [k for k, v in INGREDIENT_TYPES.items() if v["unlock_level"] <= level]
