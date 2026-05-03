"""
游戏精灵模块 - 定义所有游戏内的可视对象
包括：杯子、食材、粒子特效、接住特效
"""

import pygame
import math
import random
from config import *


class Cup(pygame.sprite.Sprite):
    """
    玩家控制的杯子精灵

    参数:
        groups: pygame 精灵组，可选，将杯子加入指定精灵组方便批量管理
    """

    def __init__(self, *groups):
        super().__init__(*groups)
        self._moving = False
        self._level_images = []
        self._current_level = 0

        # 加载所有等级的杯子图片
        for path in CUP_LEVEL_IMGS:
            try:
                img = pygame.image.load(path).convert_alpha()
                img = pygame.transform.scale(img, (CUP_WIDTH, CUP_HEIGHT))
                self._level_images.append(img)
            except (pygame.error, FileNotFoundError, OSError):
                # 如果某张图片加载失败，使用默认矩形代替
                fallback = pygame.Surface((CUP_WIDTH, CUP_HEIGHT), pygame.SRCALPHA)
                pygame.draw.rect(fallback, CUP_COLOR, (0, 0, CUP_WIDTH, CUP_HEIGHT))
                pygame.draw.rect(
                    fallback, WHITE, (5, 5, CUP_WIDTH - 10, CUP_HEIGHT - 10), 2
                )
                self._level_images.append(fallback)

        if not self._level_images:
            fallback = pygame.Surface((CUP_WIDTH, CUP_HEIGHT), pygame.SRCALPHA)
            pygame.draw.rect(fallback, CUP_COLOR, (0, 0, CUP_WIDTH, CUP_HEIGHT))
            self._level_images.append(fallback)

        self._orig_image = self._level_images[0]
        self.image = self._orig_image
        self.rect = self.image.get_rect()
        self.rect.centerx = SCREEN_WIDTH // 2  # 初始 X 位置：屏幕水平居中
        self.rect.bottom = SCREEN_HEIGHT - 10  # 初始 Y 位置：屏幕底部上方 10 像素
        self.speed = CUP_SPEED  # 移动速度（像素/帧），在 config.py 中定义
        self.yaw_control = False  # 是否启用头动控制
        self.last_yaw = 0

        # 动画状态
        self._tilt = 0.0  # 当前倾斜角度（度），移动时杯子会微微倾斜
        self._bounce_t = -1.0  # 弹跳进度 (0~1)，-1 表示无弹跳动画
        self._bounce_dur = 0.2  # 弹跳持续时间（秒），值越小弹跳越快

    def update_level(self, score):
        """根据分数切换杯子等级图片"""
        if score >= 100:
            new_level = 2
        elif score >= 50:
            new_level = 1
        else:
            new_level = 0

        if new_level != self._current_level and new_level < len(self._level_images):
            self._current_level = new_level
            self._orig_image = self._level_images[self._current_level]

    def trigger_bounce(self):
        """触发接住食材时的弹跳动画"""
        self._bounce_t = 0.0

    def update(self, keys=None, yaw=None, dt=1.0):
        """
        更新杯子位置和动画状态

        参数:
            keys: 按键状态字典（pygame.key.get_pressed() 返回值），键盘控制时使用
            yaw: 头动偏航角（浮点数），头动控制时使用
            dt: 帧间隔时间（秒），用于动画计算
        """
        move_dir = 0  # 移动方向：-1 左，0 停，1 右

        if self.yaw_control and yaw is not None:
            # 头动控制模式
            if abs(yaw) > DEAD_ZONE:  # DEAD_ZONE=5，死区阈值，防抖动
                self.rect.x += yaw * YAW_SCALE  # YAW_SCALE=0.5，头动映射系数
                move_dir = -1 if yaw < 0 else 1
        elif keys:
            # 键盘控制模式
            if keys[pygame.K_LEFT]:
                self.rect.x -= self.speed
                move_dir = -1
            if keys[pygame.K_RIGHT]:
                self.rect.x += self.speed
                move_dir = 1

        # 限制杯子不超出屏幕左右边界
        self.rect.left = max(0, self.rect.left)
        self.rect.right = min(SCREEN_WIDTH, self.rect.right)

        # 更新倾斜：目标角度 ±12°（5.0 为最大倾斜角度），0.2 为平滑过渡系数
        target_tilt = move_dir * 12.0
        self._tilt += (target_tilt - self._tilt) * 0.2

        # 更新弹跳动画
        if self._bounce_t >= 0:
            self._bounce_t += dt / self._bounce_dur
            if self._bounce_t >= 1.0:
                self._bounce_t = -1.0

        # 应用变换（旋转 + 缩放）
        scale = 1.0
        if self._bounce_t >= 0:
            bounce_phase = math.sin(self._bounce_t * math.pi)
            scale = 1.0 + 0.1 * bounce_phase  # 0.1 为最大缩放幅度（10%）

        rotated = pygame.transform.rotozoom(self._orig_image, -self._tilt, scale)
        new_rect = rotated.get_rect(center=(self.rect.centerx, self.rect.centery))
        new_rect.bottom = self.rect.bottom

        self.image = rotated
        self.rect = new_rect


class Particle(pygame.sprite.Sprite):
    """
    粒子特效精灵（接住食材时爆炸的彩色粒子）

    参数:
        x, y: 粒子生成位置（像素）
        color: 粒子颜色 (R, G, B)
        groups: pygame 精灵组
    """

    def __init__(self, x, y, color, *groups):
        super().__init__(*groups)
        self.color = color
        size = random.randint(3, 8)  # 粒子大小（像素），范围 3~8
        self.image = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.circle(self.image, color, (size // 2, size // 2), size // 2)
        self.rect = self.image.get_rect(center=(x, y))
        angle = random.uniform(0, 2 * math.pi)  # 随机发射方向
        speed = random.uniform(2, 6)  # 发射速度（像素/帧）
        self.vx = math.cos(angle) * speed  # 水平速度
        self.vy = math.sin(angle) * speed - 2  # 垂直速度（-2 表示初始偏上）
        self.life = 1.0  # 生命值（1.0=满，0=消亡）
        self.decay = random.uniform(2.0, 3.5)  # 生命衰减速度，值越大粒子消失越快

    def update(self, dt=0.016):
        """
        更新粒子状态

        参数:
            dt: 帧间隔时间（秒），默认 0.016（约 60fps）
        """
        self.life -= self.decay * dt
        if self.life <= 0:
            self.kill()
            return
        self.rect.x = int(self.rect.x + self.vx)
        self.rect.y = int(self.rect.y + self.vy)
        self.vy += 0.15  # 重力加速度（像素/帧²），让粒子呈抛物线下落
        self.image.set_alpha(int(self.life * 255))


class CatchEffect(pygame.sprite.Sprite):
    """
    接住食材特效（食材飞向杯子并缩小消失）

    参数:
        ingredient: 被接住的食材精灵
        cup_rect: 杯子的矩形区域
        groups: pygame 精灵组
    """

    def __init__(self, ingredient, cup_rect, *groups):
        super().__init__(*groups)
        self.image = ingredient.image.copy()
        self.rect = self.image.get_rect(center=ingredient.rect.center)
        self._target = (
            cup_rect.centerx,
            cup_rect.centery - cup_rect.height // 4,
        )  # 目标位置：杯子中心偏上
        self._start_x = self.rect.centerx
        self._start_y = self.rect.centery
        self._start_image = self.image.copy()
        self._t = 0.0
        self._duration = 0.3  # 特效持续时间（秒）
        self._done = False
        self.type = ingredient.type

    def update(self, dt=0.016):
        """
        更新特效动画

        参数:
            dt: 帧间隔时间（秒）
        """
        self._t += dt / self._duration
        if self._t >= 1.0:
            self._done = True
            self.kill()
            return

        ease = self._t * self._t  # ease-in 缓动：先慢后快
        self.rect.centerx = int(
            self._start_x + (self._target[0] - self._start_x) * ease
        )
        self.rect.centery = int(
            self._start_y + (self._target[1] - self._start_y) * ease
        )

        shrink = 1.0 - ease * 0.8  # 缩小到 20%，0.8 为最大缩小比例
        w = int(self._start_image.get_width() * shrink)
        h = int(self._start_image.get_height() * shrink)
        if w > 0 and h > 0:
            self.image = pygame.transform.scale(self._start_image, (w, h))
            self.rect.size = (w, h)


class MissEffect(pygame.sprite.Sprite):
    """接住失败特效 - 原地缩小并淡出"""

    def __init__(self, ingredient, *groups):
        super().__init__(*groups)
        self.image = ingredient.image.copy()
        self.rect = self.image.get_rect(center=ingredient.rect.center)
        self._start_image = self.image.copy()
        self._t = 0.0
        self._duration = 0.25

    def update(self, dt=0.016):
        self._t += dt / self._duration
        if self._t >= 1.0:
            self.kill()
            return

        shrink = 1.0 - self._t
        w = int(self._start_image.get_width() * shrink)
        h = int(self._start_image.get_height() * shrink)
        if w > 0 and h > 0:
            self.image = pygame.transform.scale(self._start_image, (w, h))
            self.rect = self.image.get_rect(center=self.rect.center)
        self.image.set_alpha(int(255 * shrink))


class Ingredient(pygame.sprite.Sprite):
    """
    食材精灵（从天而降的奶茶配料）

    参数:
        ing_type: 食材类型字符串，如 "红茶"、"珍珠" 等
        is_required: 是否为必接食材
        groups: pygame 精灵组
    """

    def __init__(self, ing_type, is_required=False, *groups):
        super().__init__(*groups)
        self.type = ing_type
        self.is_required = is_required
        # 尝试加载食材图片，失败则用默认圆形
        try:
            img_path = INGREDIENT_IMGS.get(ing_type)
            if img_path:
                self.image = pygame.image.load(img_path).convert_alpha()
                self.image = pygame.transform.scale(
                    self.image,
                    (
                        INGREDIENT_SIZE,
                        INGREDIENT_SIZE,
                    ),  # INGREDIENT_SIZE=40 控制食材大小
                )
            else:
                raise FileNotFoundError
        except (pygame.error, FileNotFoundError, OSError):
            # 使用默认圆形
            self.image = pygame.Surface(
                (INGREDIENT_SIZE, INGREDIENT_SIZE), pygame.SRCALPHA
            )
            color = INGREDIENT_COLORS.get(ing_type, RED)
            pygame.draw.circle(
                self.image,
                color,
                (INGREDIENT_SIZE // 2, INGREDIENT_SIZE // 2),
                INGREDIENT_SIZE // 2,
            )
        self.rect = self.image.get_rect()
        self.rect.x = random.randint(0, SCREEN_WIDTH - INGREDIENT_SIZE)
        self.rect.y = -INGREDIENT_SIZE
        self.speed = INGREDIENT_SPEED
        self._float_t = random.uniform(0, 6.28)
        self._base_centerx = self.rect.centerx
        self._orig_image = self.image.copy()

    def update(self):
        self._float_t += 0.05
        self.rect.y += self.speed
        self.rect.centerx = int(self._base_centerx + math.sin(self._float_t) * 5)

        angle = math.cos(self._float_t) * 8
        self.image = pygame.transform.rotate(self._orig_image, angle)
        self.rect = self.image.get_rect(center=self.rect.center)

        if self.rect.top > SCREEN_HEIGHT:
            self.kill()
