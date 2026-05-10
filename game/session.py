"""游戏会话模块 - 管理单局游戏的初始化、循环和结算"""

from __future__ import annotations

import logging
import os
from typing import Any

import pygame

from bci.data_reader import BCIDataReader
from bci.filter import AttentionMappingCurve, DeadZoneFilter, ExponentialSmoothing
from config import (
    BACKGROUND_IMG,
    CUP_HEIGHT,
    DEFAULT_GAME_MODE,
    FOCUS_TEAPOT_IMG,
    GAME_DURATION,
    GAME_MODES,
    INGREDIENT_COLORS,
    PATIENCE_BAR_SIZE,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
)
from data.recipes import evaluate_recipe
from data.score_manager import ScoreManager
from game.font_utils import load_chinese_font
from game.hud import FocusTeapotUI, draw_hud
from game.ingredient_manager import IngredientManager
from game.patience_bar import PatienceBar
from game.sprites import CatchEffect, Cup, MissEffect, Particle
from menu.summary import SummaryScreen

logger = logging.getLogger(__name__)


class GameSession:
    """管理单局游戏的完整生命周期"""

    screen: pygame.Surface
    clock: pygame.time.Clock
    game_mode: str

    mode_name: str
    has_required: bool
    free_combine: bool
    bci_mode: bool
    spawn_interval: float

    font: pygame.font.Font
    hint_font: pygame.font.Font
    recipe_font: pygame.font.Font

    cup: Cup
    all_sprites: pygame.sprite.Group
    ingredients: pygame.sprite.Group
    catch_effects: pygame.sprite.Group
    miss_effects: pygame.sprite.Group
    particles: pygame.sprite.Group

    score_manager: ScoreManager
    ingredient_manager: IngredientManager
    patience_bar: PatienceBar

    bci_reader: BCIDataReader
    bci_available: bool
    dead_zone: DeadZoneFilter
    smooth_yaw: ExponentialSmoothing
    attention_curve: AttentionMappingCurve | None

    background: pygame.Surface | None
    has_background: bool

    creative_ingredients: list[str]
    recipe_result: dict[str, Any] | None

    running: bool
    show_summary: bool
    use_yaw_control: bool
    game_start_time: int
    focus_samples: list[float]

    attention: float | None
    raw_yaw: float
    smoothed_yaw_value: float

    focus_teapot: FocusTeapotUI | None

    def __init__(self, screen: pygame.Surface, clock: pygame.time.Clock, game_mode: str = "regular") -> None:
        self.screen = screen
        self.clock = clock
        self.game_mode = game_mode

        self._load_mode_config()
        self._load_fonts()
        self._init_game_objects()
        self._init_bci()
        self._load_background()
        self._init_state()
        self._print_mode_rules()
        self._draw_initial_frame()

    def _load_mode_config(self) -> None:
        mode_config = GAME_MODES.get(self.game_mode, GAME_MODES[DEFAULT_GAME_MODE])
        self.mode_name = mode_config["name"]
        self.has_required = mode_config["has_required"]
        self.free_combine = mode_config["free_combine"]
        self.bci_mode = mode_config["bci_mode"]
        self.spawn_interval = mode_config["spawn_interval"] / 1000.0

    def _load_fonts(self) -> None:
        self.font = load_chinese_font(36)
        self.hint_font = load_chinese_font(20)
        self.recipe_font = load_chinese_font(28)

    def _init_game_objects(self) -> None:
        self.cup = Cup()
        self.all_sprites = pygame.sprite.Group()
        self.all_sprites.add(self.cup)

        self.ingredients = pygame.sprite.Group()
        self.catch_effects = pygame.sprite.Group()
        self.miss_effects = pygame.sprite.Group()
        self.particles = pygame.sprite.Group()

        self.score_manager = ScoreManager()
        self.ingredient_manager = IngredientManager()
        self.ingredient_manager.spawn_interval = self.spawn_interval

        patience_bar_x = 20
        patience_bar_y = SCREEN_HEIGHT - CUP_HEIGHT - PATIENCE_BAR_SIZE[1] - 30
        self.patience_bar = PatienceBar(patience_bar_x, patience_bar_y)

        if self.has_required:
            self.score_manager.set_required_ingredient("红茶")

    def _init_bci(self) -> None:
        self.bci_reader = BCIDataReader()
        self.bci_available = False
        if self.bci_mode:
            self.bci_available = self.bci_reader.connect()

        self.dead_zone = DeadZoneFilter(threshold=5)
        self.smooth_yaw = ExponentialSmoothing(alpha=0.1)

        self.attention_curve = None
        if self.free_combine:
            self.attention_curve = AttentionMappingCurve()

    def _load_background(self) -> None:
        self.background = None
        self.has_background = False
        try:
            if os.path.exists(BACKGROUND_IMG):
                self.background = pygame.image.load(BACKGROUND_IMG).convert()
                self.background = pygame.transform.scale(self.background, (SCREEN_WIDTH, SCREEN_HEIGHT))
                self.has_background = True
        except Exception:
            pass

    def _init_state(self) -> None:
        self.creative_ingredients = []
        self.recipe_result = None

        self.running = True
        self.show_summary = False
        # 只有当BCI模式开启且设备连接成功时，才使用头动控制
        self.use_yaw_control = self.bci_mode and self.bci_available
        self.cup.yaw_control = self.use_yaw_control
        self.game_start_time = pygame.time.get_ticks()
        self.focus_samples = []

        self.attention = None
        self.raw_yaw = 0
        self.smoothed_yaw_value = 0

        teapot_img_path = FOCUS_TEAPOT_IMG if os.path.exists(FOCUS_TEAPOT_IMG) else None
        self.focus_teapot = None
        if teapot_img_path:
            self.focus_teapot = FocusTeapotUI(image_path=teapot_img_path, x=10, y=90, width=120, height=140)

        if self.bci_mode and not self.bci_available:
            logger.warning("BCI设备未连接，无法使用头动控制，将自动切换到键盘控制")
            self.use_yaw_control = False
            self.cup.yaw_control = False

    def _print_mode_rules(self) -> None:
        logger.info("=" * 50)
        logger.info("疯狂奶茶杯 - %s", self.mode_name)
        logger.info("=" * 50)
        if self.bci_mode:
            logger.info("脑机接口模式规则：")
            logger.info("  使用BCI设备读取专注力和头动数据")
            logger.info("  自由搭配食材，不同组合产生不同评分")
            logger.info("  专注力越高，评分加成越大")
            if not self.bci_available:
                logger.warning("  [警告] BCI设备未连接，无法读取数据")
        elif self.free_combine:
            logger.info("创意模式规则：")
            logger.info("  没有必接食材，自由搭配")
            logger.info("  不同组合产生不同评分（黑暗→米其林）")
            logger.info("  专注力越高，评分加成越大")
        else:
            logger.info("控制说明:")
            logger.info("  头动控制: 左右转头移动杯子")
            logger.info("  ESC: 返回菜单")
        logger.info("=" * 50)

    def _draw_initial_frame(self) -> None:
        if self.has_background and self.background:
            self.screen.blit(self.background, (0, 0))
        else:
            self.screen.fill((255, 255, 255))

        self.all_sprites.draw(self.screen)
        score_text = self.font.render(f"分数: {self.score_manager.score}", True, (0, 0, 0))
        self.screen.blit(score_text, (10, 10))
        mode_text = self.font.render(f"{self.mode_name}", True, (100, 50, 150))
        self.screen.blit(mode_text, (10, 50))
        pygame.display.flip()

    def run(self) -> str:
        while self.running:
            dt = self.clock.tick(60)
            keys = pygame.key.get_pressed()
            dt_sec = dt / 1000.0

            self._handle_events()
            if not self.running:
                break

            self._update_bci_data()
            self._update_cup(keys, dt_sec)

            if not self._check_time_limit():
                break

            self._update_game_objects(dt_sec)
            self._handle_collisions()
            self._render()

        return self._end_game()

    def _handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.show_summary = True
                    self.running = False
                    return

    def _update_bci_data(self) -> None:
        if self.bci_available:
            result = self.bci_reader.read_with_timeout()
            if result != (None, None):
                self.attention, self.raw_yaw = result
                # 添加调试信息：打印原始yaw值
                print(f"[BCI DEBUG] raw_yaw={self.raw_yaw:.2f}, attention={self.attention}")
                # 限幅：确保yaw在合理范围内
                if abs(self.raw_yaw) > 180:
                    print(f"[BCI WARNING] yaw值异常: {self.raw_yaw:.2f}，可能被重置为0")
                    self.raw_yaw = 0
            else:
                self.attention = 50
                self.raw_yaw = 0
        else:
            self.attention = None
            self.raw_yaw = 0

        filtered_yaw = self.dead_zone.filter(self.raw_yaw)
        self.smoothed_yaw_value = self.smooth_yaw.smooth(filtered_yaw)
        print(f"[BCI DEBUG] filtered_yaw={filtered_yaw:.2f}, smoothed_yaw={self.smoothed_yaw_value:.2f}")

        if self.attention is not None:
            self.focus_samples.append(self.attention)

    def _update_cup(self, keys: pygame.key.ScancodeWrapper, dt_sec: float) -> None:
        if self.use_yaw_control:
            self.cup.update(yaw=self.smoothed_yaw_value, dt=dt_sec)
        else:
            self.cup.update(keys=keys, dt=dt_sec)

    def _check_time_limit(self) -> bool:
        elapsed_ms = pygame.time.get_ticks() - self.game_start_time
        if elapsed_ms >= GAME_DURATION * 1000:
            self.show_summary = True
            self.running = False
            return False
        return True

    def _update_game_objects(self, dt_sec: float) -> None:
        required: list[str] | None = ["红茶"] if self.has_required else None
        ingredient = self.ingredient_manager.update(required_types=required)
        if ingredient:
            self.ingredients.add(ingredient)

        self.ingredients.update()
        self.catch_effects.update(dt=dt_sec)
        self.miss_effects.update(dt=dt_sec)
        self.particles.update(dt=dt_sec)
        self.patience_bar.update(dt_sec)

    def _handle_collisions(self) -> None:
        threshold_y = self.cup.rect.top + self.cup.rect.height * 0.8
        hits = pygame.sprite.spritecollide(self.cup, self.ingredients, False)

        self.creative_ingredients, self.recipe_result = _handle_catches(
            hits,
            self.cup,
            threshold_y,
            self.ingredients,
            self.miss_effects,
            self.catch_effects,
            self.particles,
            self.patience_bar,
            self.score_manager,
            self.free_combine,
            self.creative_ingredients,
            self.recipe_result,
        )

        _handle_misses(self.ingredients, threshold_y, self.miss_effects, self.particles)

    def _render(self) -> None:
        if self.has_background and self.background:
            self.screen.blit(self.background, (0, 0))
        else:
            self.screen.fill((255, 255, 255))

        self.all_sprites.draw(self.screen)
        self.ingredients.draw(self.screen)
        self.catch_effects.draw(self.screen)
        self.miss_effects.draw(self.screen)
        self.particles.draw(self.screen)

        draw_hud(
            screen=self.screen,
            score_manager=self.score_manager,
            mode_name=self.mode_name,
            patience_bar=self.patience_bar,
            font=self.font,
            hint_font=self.hint_font,
            recipe_font=self.recipe_font,
            focus_teapot=self.focus_teapot,
            attention=self.attention,
            smoothed_yaw=self.smoothed_yaw_value,
            bci_mode=self.bci_mode,
            free_combine=self.free_combine,
            recipe_result=self.recipe_result,
            creative_ingredients=self.creative_ingredients,
            attention_curve=self.attention_curve,
            bci_connected=self.bci_available,
        )

        pygame.display.flip()

    def _end_game(self) -> str:
        if self.show_summary:
            avg_focus = sum(self.focus_samples) / len(self.focus_samples) if self.focus_samples else 0.0
            if not self.bci_mode:
                avg_focus = 0.0

            summary = SummaryScreen(self.screen, self.score_manager.score, avg_focus, self.game_mode)
            return summary.run()

        return "quit"


def run_game(screen: pygame.Surface, clock: pygame.time.Clock, game_mode: str = "regular") -> str:
    """
    运行主游戏循环

    参数:
        screen: pygame 屏幕对象
        clock: pygame 时钟对象
        game_mode: 游戏模式

    返回:
        "quit" / "menu"
    """
    session = GameSession(screen, clock, game_mode)
    return session.run()


def _handle_catches(
    hits: list[Any],
    cup: Cup,
    threshold_y: float,
    ingredients: pygame.sprite.Group,
    miss_effects: pygame.sprite.Group,
    catch_effects: pygame.sprite.Group,
    particles: pygame.sprite.Group,
    patience_bar: PatienceBar,
    score_manager: ScoreManager,
    free_combine: bool,
    creative_ingredients: list[str],
    recipe_result: dict[str, Any] | None,
) -> tuple[list[str], dict[str, Any] | None]:
    """处理与杯子碰撞的食材

    返回:
        (creative_ingredients, recipe_result) 更新后的创意模式状态
    """
    for hit in hits:
        if hit.rect.bottom > threshold_y:
            hit.rect.bottom = int(threshold_y)
            miss_effects.add(MissEffect(hit))
            color = INGREDIENT_COLORS.get(hit.type, (200, 200, 200))
            for _ in range(4):
                p = Particle(hit.rect.centerx, int(threshold_y), color)
                p.vx *= 0.4
                p.vy *= 0.4
                p.decay *= 1.5
                particles.add(p)
            ingredients.remove(hit)
        else:
            ingredients.remove(hit)
            effect = CatchEffect(hit, cup.rect)
            catch_effects.add(effect)
            for _ in range(8):
                color = INGREDIENT_COLORS.get(hit.type, (255, 200, 0))
                particles.add(Particle(hit.rect.centerx, hit.rect.centery, color))
            cup.trigger_bounce()
            patience_bar.on_catch()

            if free_combine:
                creative_ingredients.append(hit.type)
                score_manager.add_ingredient(hit.type, is_required=False)
                recipe_result = evaluate_recipe(creative_ingredients)
            else:
                score_manager.add_ingredient(hit.type, is_required=hit.is_required)

            cup.update_level(score_manager.score)
            logger.info("接住 %s！分数: %s", hit.type, score_manager.score)

    return creative_ingredients, recipe_result


def _handle_misses(
    ingredients: pygame.sprite.Group,
    threshold_y: float,
    miss_effects: pygame.sprite.Group,
    particles: pygame.sprite.Group,
) -> None:
    """处理漏接的食材"""
    for ing in ingredients.sprites():
        if ing.rect.bottom > threshold_y:
            ing.rect.bottom = int(threshold_y)
            miss_effects.add(MissEffect(ing))
            color = INGREDIENT_COLORS.get(ing.type, (200, 200, 200))
            for _ in range(4):
                p = Particle(ing.rect.centerx, int(threshold_y), color)
                p.vx *= 0.4
                p.vy *= 0.4
                p.decay *= 1.5
                particles.add(p)
            ingredients.remove(ing)
