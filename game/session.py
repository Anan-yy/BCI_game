"""游戏会话模块 - 管理单局游戏的初始化、循环和结算（一杯制改造）"""

from __future__ import annotations

import logging
import math
import os
import time as time_module
from typing import Any

import pygame

import config
from bci.data_reader import BCIDataReader
from config import (
    ARTIFACT_ATTENTION_THRESHOLD,
    ARTIFACT_PENALTY_DURATION,
    ARTIFACT_STILL_DURATION,
    ARTIFACT_STILL_THRESHOLD,
    BACKGROUND_IMG,
    BADGE_IMGS,
    CUP_DURATION,
    CUP_WIDTH,
    DIGIT_HEIGHT,
    DIGIT_SPACING,
    DIGIT_WIDTH,
    FOCUS_BALL_IMG,
    FOCUS_BALL_POS,
    FOCUS_BALL_SIZE,
    FORMAL_SPEED_MAX,
    FORMAL_SPEED_MIN,
    RAW_SPEED_MAX,
    RAW_SPEED_MIN,
    GAME_MODES,
    INFO_BAR_HEIGHT,
    INFO_BAR_IMG,
    INFO_BADGE_POS,
    INFO_BADGE_SIZE,
    INFO_FONT_SIZE,
    INFO_REGIONS,
    INGREDIENT_COLORS,
    INGREDIENT_IMGS,
    NUM_IMG_DIR,
    OUTLET_POSITIONS,
    OVERLAY_CLEAR_REGIONS,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    SECRET_RECIPE_SUSTAIN,
    TOTAL_CUPS,
    WARMUP_FREEZE_TIME,
    WARMUP_LOW_THRESHOLD,
    WARMUP_RESUME_THRESHOLD,
    WARMUP_RESUME_TIME,
    WARMUP_SMOOTH_WINDOW,
    get_attention_coefficient,
)
from data.score_manager import ScoreManager
from game.cup_manager import CupManager
from game.font_utils import load_chinese_font
from game.hud import draw_hud
from game.ingredient_manager import IngredientManager
from game.sprites import CatchEffect, Cup, MissEffect, Particle
from menu.summary import SummaryScreen

logger = logging.getLogger(__name__)


class GameSession:
    """管理单局游戏的完整生命周期（一杯制）"""

    screen: pygame.Surface
    clock: pygame.time.Clock
    game_mode: str

    mode_name: str
    has_required: bool
    free_combine: bool
    bci_mode: bool
    spawn_interval: float
    mode_speed: float

    font: pygame.font.Font
    hint_font: pygame.font.Font

    cup: Cup
    all_sprites: pygame.sprite.Group
    ingredients: pygame.sprite.Group
    catch_effects: pygame.sprite.Group
    miss_effects: pygame.sprite.Group
    particles: pygame.sprite.Group

    score_manager: ScoreManager
    ingredient_manager: IngredientManager
    cup_manager: CupManager

    bci_reader: BCIDataReader
    bci_available: bool

    background: pygame.Surface | None
    has_background: bool

    running: bool
    show_summary: bool
    use_yaw_control: bool
    game_start_time: float
    focus_samples: list[float]
    focus_above_seconds: float

    attention: float | None
    raw_gyro_x: float
    raw_gyro_y: float
    raw_gyro_z: float
    platform_focus_x: float
    platform_focus_y: float

    focus_min: int
    focus_max: int

    phase: str

    _raw_attention: bool

    _esc_dialog_active: bool = False
    _esc_dialog_selected: int = 0
    _pending_settings: bool = False

    def __init__(
        self,
        screen: pygame.Surface,
        clock: pygame.time.Clock,
        game_mode: str = "regular",
        profile=None,
        control_mode: str = "bci",
        audio=None,
        training_duration: float = 0,
        fixed_baseline: float | None = None,
        norm_lower: float = 30.0,
        norm_upper: float = 70.0,
        ingredient_points: dict | None = None,
        secret_threshold: float | None = None,
        secret_sustain: float = 8.0,
        secret_disabled: bool = False,
    ) -> None:
        self.screen = screen
        self.clock = clock
        self.game_mode = game_mode
        self.control_mode = control_mode
        self._profile = profile
        self._upgrade_level = 0
        self._audio = audio
        self._training_duration = training_duration
        self._training_start_time = 0.0
        self._fixed_baseline = fixed_baseline
        self._norm_lower = norm_lower
        self._norm_upper = norm_upper
        self._ingredient_points = ingredient_points
        self._secret_threshold = secret_threshold
        self._secret_sustain = secret_sustain
        self._secret_disabled = secret_disabled

        self._load_mode_config()
        self._load_fonts()
        self._init_game_objects()
        self._cache_secret_popup_image()
        self._init_bci()
        self._load_background()
        self._init_state()
        self._print_mode_rules()
        self._draw_initial_frame()

    def _load_mode_config(self) -> None:
        mode_config = GAME_MODES.get(self.game_mode, GAME_MODES["bci"])
        self.mode_name = mode_config["name"]
        self.has_required = mode_config["has_required"]
        self.free_combine = mode_config["free_combine"]
        self.bci_mode = mode_config["bci_mode"]
        self.spawn_interval = mode_config["spawn_interval"] / 1000.0
        self.mode_speed = float(mode_config["ingredient_speed"])
        self._mode_total_cups = mode_config.get("total_cups", TOTAL_CUPS)
        self._mode_secret_interval = mode_config.get("secret_recipe_cup_interval", 3)
        self._infinite = mode_config.get("infinite", False)
        self._raw_attention = mode_config.get("raw_attention", False)

        if self.control_mode in ("bci", "bci_failed"):
            if self.game_mode == "infinite":
                self.mode_name = "原萃模式"
            else:
                self.mode_name = "特调模式"

        if self._training_duration > 0:
            self.mode_name = "训练模式"

    def _load_fonts(self) -> None:
        self.font = load_chinese_font(36)
        self.hint_font = load_chinese_font(20)
        self.recipe_font = load_chinese_font(28)
        self.pause_font = load_chinese_font(48)

    def _init_game_objects(self) -> None:
        self.cup = Cup()
        self.all_sprites = pygame.sprite.Group()
        self.all_sprites.add(self.cup)

        self.ingredients = pygame.sprite.Group()
        self.catch_effects = pygame.sprite.Group()
        self.miss_effects = pygame.sprite.Group()
        self.particles = pygame.sprite.Group()

        self.score_manager = ScoreManager(points_map=self._ingredient_points)
        start_tier = self._profile.level if self._profile else 1
        self.ingredient_manager = IngredientManager(tier=start_tier)
        self.ingredient_manager.spawn_interval = self.spawn_interval

        if self.has_required:
            self.score_manager.set_required_ingredient("红茶")

        self.cup_manager = CupManager(
            has_required=self.has_required,
            required_type="红茶" if self.has_required else None,
            total_cups=self._mode_total_cups,
            secret_recipe_interval=self._mode_secret_interval,
            points_map=self._ingredient_points,
        )
        self._current_tier = 1

    def _init_bci(self) -> None:
        self.bci_reader = BCIDataReader()
        self.bci_available = False
        if self.bci_mode and self.control_mode != "bci_failed":
            self.bci_available = self.bci_reader.connect()

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

        self._top_bar = None
        self._info_bar = None
        if os.path.exists(INFO_BAR_IMG):
            try:
                self._info_bar = pygame.image.load(INFO_BAR_IMG).convert_alpha()
                self._info_bar = pygame.transform.smoothscale(self._info_bar, (SCREEN_WIDTH, INFO_BAR_HEIGHT))
            except Exception:
                pass

        self._badge_img = None
        level = self._profile.level if self._profile else 1
        idx = max(0, min(level - 1, len(BADGE_IMGS) - 1))
        badge_path = BADGE_IMGS[idx]
        if os.path.exists(badge_path):
            try:
                self._badge_img = pygame.image.load(badge_path).convert_alpha()
                self._badge_img = pygame.transform.smoothscale(self._badge_img, INFO_BADGE_SIZE)
            except Exception:
                pass

        self._focus_ball = None
        if os.path.exists(FOCUS_BALL_IMG):
            try:
                self._focus_ball = pygame.image.load(FOCUS_BALL_IMG).convert_alpha()
                self._focus_ball = pygame.transform.smoothscale(self._focus_ball, FOCUS_BALL_SIZE)
            except Exception:
                pass

        self._digit_imgs: list[pygame.Surface] = []
        for i in range(10):
            path = os.path.join(NUM_IMG_DIR, f"{i}.png")
            try:
                img = pygame.image.load(path).convert_alpha()
                img = pygame.transform.smoothscale(img, (DIGIT_WIDTH, DIGIT_HEIGHT))
                self._digit_imgs.append(img)
            except Exception:
                self._digit_imgs.append(pygame.Surface((DIGIT_WIDTH, DIGIT_HEIGHT), pygame.SRCALPHA))

    def _init_state(self) -> None:
        self.running = True
        self.show_summary = False
        self.use_yaw_control = self.bci_available
        self.cup.yaw_control = self.use_yaw_control
        self.game_start_time = time_module.time()
        self.focus_samples = []
        self.focus_above_seconds = 0.0
        self._player_level = self._profile.level if self._profile else 1

        self.attention = None
        self.raw_gyro_x = 0.0
        self.raw_gyro_y = 0.0
        self.raw_gyro_z = 0.0
        self.platform_focus_x = float(SCREEN_WIDTH // 2)
        self.platform_focus_y = float(SCREEN_HEIGHT - 100)

        self._attn_offsets: list[float] = []
        self._attn_variance = 0.0
        self._attn_mode = "中等模式"
        self._attn_smooth_buffer: list[float] = []
        self._smooth_attention: float | None = None

        self._paused = False
        self._low_attn_seconds = 0.0
        self._high_attn_seconds = 0.0
        self._blackout_alpha = 0.0

        self._prev_gyro_x = 0.0
        self._prev_gyro_y = 0.0
        self._prev_gyro_z = 0.0
        self._gyro_still_timer = 0.0
        self._artifact_frozen = False
        self._artifact_penalty_timer = 0.0
        self._artifact_alpha = 0.0
        self._secret_popup_timer = 0.0
        self._cup_attn_samples: list[float] = []
        self._cup_baseline: float = self._fixed_baseline if self._fixed_baseline is not None else 40.0

        self.focus_min = CUP_WIDTH // 2
        self.focus_max = SCREEN_WIDTH - CUP_WIDTH // 2

        if not self.bci_available and self.bci_mode:
            logger.warning("BCI设备未连接，无法使用头动控制，将自动切换到键盘控制")
            self.use_yaw_control = False
            self.cup.yaw_control = False

        self._current_tier = self._profile.level if self._profile else 1

        self.phase = "formal"
        self.normalization_lower = self._norm_lower
        self.normalization_upper = self._norm_upper
        self.cup_manager.start_new_cup()

    def start_training(self) -> None:
        self._training_start_time = time_module.time()

    def training_remaining(self) -> float:
        if self._training_duration <= 0:
            return -1.0
        elapsed = time_module.time() - self._training_start_time
        return max(0.0, self._training_duration - elapsed)

    def _print_mode_rules(self) -> None:
        logger.info("=" * 50)
        logger.info("疯狂奶茶杯 - %s（一杯制）", self.mode_name)
        logger.info("=" * 50)
        if self._raw_attention:
            logger.info("原萃模式：使用原始注意力值，不进行归一化")
        else:
            logger.info("直接开始正式游戏，第一杯结束后计算归一化值")
        if self.bci_mode:
            logger.info("脑机接口模式规则：")
            if self._infinite:
                logger.info("  无限杯数，按 ESC 退出")
            else:
                logger.info("  共 %s 杯，每杯最多 %s 秒", self._mode_total_cups, CUP_DURATION)
            logger.info("  专注力越高食材越慢，持续高专注触发秘方翻倍")
            if not self.bci_available:
                logger.warning("  [警告] BCI设备未连接，无法读取数据")
        elif self.free_combine:
            logger.info("创意模式规则：")
            if self._infinite:
                logger.info("  无限杯数，按 ESC 退出")
            else:
                logger.info("  共 %s 杯，每杯最多 %s 秒", self._mode_total_cups, CUP_DURATION)
            logger.info("  自由搭配食材，每 %s 杯触发秘方", self._mode_secret_interval)
        else:
            logger.info("控制说明:")
            logger.info("  共 %s 杯，每杯最多 %s 秒，需接住红茶", self._mode_total_cups, CUP_DURATION)
            logger.info("  每 %s 杯触发秘方翻倍", self._mode_secret_interval)
        logger.info("=" * 50)

    def _draw_initial_frame(self) -> None:
        if self.has_background and self.background:
            self.screen.blit(self.background, (0, 0))
        else:
            self.screen.fill((255, 255, 255))

        self.all_sprites.draw(self.screen)
        mode_text = self.font.render(f"{self.mode_name}", True, (100, 50, 150))
        self.screen.blit(mode_text, (10, 10))
        pygame.display.flip()

    def _normalize_to_range(self, attention: float) -> float:
        if self.normalization_upper - self.normalization_lower < 1.0:
            return 50.0
        normalized = (attention - self.normalization_lower) / (
            self.normalization_upper - self.normalization_lower
        ) * 99.0 + 1.0
        return max(1.0, min(100.0, normalized))

    def _update_formal_speed(self) -> None:
        if self.bci_mode:
            attn = self._smooth_attention if self._smooth_attention is not None else 50.0
            if self._raw_attention:
                speed = RAW_SPEED_MAX - (attn / 100.0) * (RAW_SPEED_MAX - RAW_SPEED_MIN)
            else:
                norm = self._normalize_to_range(attn)
                speed = FORMAL_SPEED_MAX - (norm - 1.0) / 99.0 * (FORMAL_SPEED_MAX - FORMAL_SPEED_MIN)
        else:
            speed = self.mode_speed

        base_speed = speed

        if self._secret_popup_timer > 0 and not self.bci_mode:
            speed *= 0.4

        self.ingredient_manager.set_current_speed(speed)
        for ing in self.ingredients:
            ing.speed = speed

        if self.bci_mode:
            speed_ratio = base_speed / self.mode_speed if self.mode_speed > 0 else 1.0
            adjusted = self.spawn_interval * (0.7 + 0.6 * speed_ratio)
            self.ingredient_manager.set_spawn_interval(max(0.3, min(3.0, adjusted)))
        else:
            self.ingredient_manager.set_spawn_interval(self.spawn_interval)

    def _update_pause_state(self, dt_sec: float) -> None:
        if self.attention is None:
            return
        if self.attention <= WARMUP_LOW_THRESHOLD:
            self._low_attn_seconds += dt_sec
            self._high_attn_seconds = 0.0
        elif self.attention > WARMUP_RESUME_THRESHOLD:
            self._high_attn_seconds += dt_sec
            self._low_attn_seconds = 0.0
        else:
            self._low_attn_seconds = 0.0
            self._high_attn_seconds = 0.0

        if not self._paused and self._low_attn_seconds >= WARMUP_FREEZE_TIME:
            self._paused = True
        elif self._paused and self._high_attn_seconds >= WARMUP_RESUME_TIME:
            self._paused = False
            self._low_attn_seconds = 0.0
            self._high_attn_seconds = 0.0
            self.ingredient_manager.reset_spawn_timer()

        target_alpha = 180 if self._paused else 0
        self._blackout_alpha += (target_alpha - self._blackout_alpha) * 0.05

    def _check_artifact(self, dt_sec: float) -> None:
        if self._artifact_frozen or not self.bci_mode or not self.bci_available:
            return

        gx = abs(self.raw_gyro_x - self._prev_gyro_x)
        gy = abs(self.raw_gyro_y - self._prev_gyro_y)
        gz = abs(self.raw_gyro_z - self._prev_gyro_z)

        self._prev_gyro_x = self.raw_gyro_x
        self._prev_gyro_y = self.raw_gyro_y
        self._prev_gyro_z = self.raw_gyro_z

        is_still = gx < ARTIFACT_STILL_THRESHOLD and gy < ARTIFACT_STILL_THRESHOLD and gz < ARTIFACT_STILL_THRESHOLD

        attn = self.attention if self.attention is not None else 50.0

        if is_still and attn > ARTIFACT_ATTENTION_THRESHOLD:
            self._gyro_still_timer += dt_sec
        else:
            self._gyro_still_timer = 0.0

        if self._gyro_still_timer >= ARTIFACT_STILL_DURATION:
            self._artifact_frozen = True
            self._artifact_penalty_timer = ARTIFACT_PENALTY_DURATION
            self._gyro_still_timer = 0.0
            self.ingredient_manager.reset_spawn_timer()
            logger.info(
                "防伪迹触发：头部静止 %.0f 秒且专注力 > %d", ARTIFACT_STILL_DURATION, ARTIFACT_ATTENTION_THRESHOLD
            )

    def _update_artifact_freeze(self, dt_sec: float) -> None:
        if not self._artifact_frozen:
            return

        self._artifact_penalty_timer -= dt_sec
        if self._artifact_penalty_timer <= 0.0:
            self._artifact_frozen = False
            self._artifact_penalty_timer = 0.0
            self._prev_gyro_x = self.raw_gyro_x
            self._prev_gyro_y = self.raw_gyro_y
            self._prev_gyro_z = self.raw_gyro_z
            self.ingredient_manager.reset_spawn_timer()
            logger.info("防伪迹惩罚结束，恢复游戏")

        target_alpha = 180 if self._artifact_frozen else 0
        self._artifact_alpha += (target_alpha - self._artifact_alpha) * 0.1

    @property
    def _game_frozen(self) -> bool:
        return self._paused or self._artifact_frozen

    def run(self) -> str:
        self._render()
        self.clock.tick(60)
        while self.running:
            dt = self.clock.tick(60)
            keys = pygame.key.get_pressed()
            dt_sec = dt / 1000.0

            self._handle_events()
            if not self.running:
                break

            if self._esc_dialog_active:
                if getattr(self, "_skip_frame", False):
                    self._skip_frame = False
                else:
                    self._render()
                continue

            if self._pending_settings:
                self._pending_settings = False
                from menu.screens.game_settings import GameSettingsScreen
                settings_font = load_chinese_font(24)
                settings_title = load_chinese_font(40)
                bg_snapshot = self.screen.copy()
                settings = GameSettingsScreen(self.screen, settings_font, settings_title, audio=self._audio, bg=bg_snapshot)
                settings.run()
                continue

            self._update_bci_data()

            self._update_cup(keys, dt_sec)
            self._update_pause_state(dt_sec)
            self._check_artifact(dt_sec)
            self._update_artifact_freeze(dt_sec)

            if not self._game_frozen:
                self._update_attention_variance()
                self._update_formal_speed()
                self._check_secret_recipe(dt_sec)
                self._check_cup_end()

            if self._training_duration > 0 and self.training_remaining() <= 0:
                self.running = False

            if not self.running:
                break

            if not self._game_frozen:
                self._update_game_objects(dt_sec)
                self._handle_collisions()

            self._render()

        return self._end_game()

    def _handle_events(self) -> None:
        show_dialog = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if self._esc_dialog_active:
                        self._esc_dialog_active = False
                    else:
                        show_dialog = True
                elif self._esc_dialog_active:
                    if event.key in (pygame.K_LEFT, pygame.K_UP):
                        self._esc_dialog_selected = (self._esc_dialog_selected - 1) % 3
                    elif event.key in (pygame.K_RIGHT, pygame.K_DOWN, pygame.K_TAB):
                        self._esc_dialog_selected = (self._esc_dialog_selected + 1) % 3
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        self._commit_esc_dialog()
            elif event.type == pygame.MOUSEBUTTONDOWN and self._esc_dialog_active:
                if event.button == 1:
                    self._handle_esc_dialog_click(event.pos)
        if show_dialog:
            self._show_esc_dialog()

    def _show_esc_dialog(self) -> None:
        self._esc_dialog_active = True
        self._esc_dialog_selected = 0
        self._skip_frame = True

    def _commit_esc_dialog(self) -> None:
        if self._esc_dialog_selected == 0:
            self._esc_dialog_active = False
        elif self._esc_dialog_selected == 1:
            self.show_summary = True
            self.running = False
        else:
            self._esc_dialog_active = False
            self._pending_settings = True

    def _handle_esc_dialog_click(self, pos: tuple[int, int]) -> None:
        if hasattr(self, "_esc_continue_rect") and self._esc_continue_rect.collidepoint(pos):
            self._esc_dialog_active = False
        elif hasattr(self, "_esc_exit_rect") and self._esc_exit_rect.collidepoint(pos):
            self.show_summary = True
            self.running = False
        elif hasattr(self, "_esc_settings_rect") and self._esc_settings_rect.collidepoint(pos):
            self._esc_dialog_active = False
            self._pending_settings = True

    def _draw_esc_dialog(self) -> None:
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        self.screen.blit(overlay, (0, 0))

        box_w, box_h = 380, 260
        box_x = (SCREEN_WIDTH - box_w) // 2
        box_y = (SCREEN_HEIGHT - box_h) // 2
        box_rect = pygame.Rect(box_x, box_y, box_w, box_h)
        pygame.draw.rect(self.screen, (30, 28, 20), box_rect, border_radius=16)
        pygame.draw.rect(self.screen, (200, 160, 100), box_rect, 3, border_radius=16)

        title = self.pause_font.render("暂停", True, (255, 255, 255))
        self.screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, box_y + 25))

        btn_w, btn_h = 150, 48
        btn_y = box_y + 90
        gap = 20
        left_x = SCREEN_WIDTH // 2 - btn_w - gap // 2
        right_x = SCREEN_WIDTH // 2 + gap // 2

        continue_selected = self._esc_dialog_selected == 0
        exit_selected = self._esc_dialog_selected == 1
        settings_selected = self._esc_dialog_selected == 2

        selected_border = (255, 255, 255)
        normal_border = (100, 100, 100)

        self._esc_continue_rect = pygame.Rect(left_x, btn_y, btn_w, btn_h)
        continue_border = selected_border if continue_selected else normal_border
        pygame.draw.rect(self.screen, (80, 180, 80), self._esc_continue_rect, border_radius=10)
        pygame.draw.rect(self.screen, continue_border, self._esc_continue_rect, 3, border_radius=10)
        continue_text = self.font.render("继续游戏", True, (255, 255, 255))
        self.screen.blit(
            continue_text,
            (
                self._esc_continue_rect.centerx - continue_text.get_width() // 2,
                self._esc_continue_rect.centery - continue_text.get_height() // 2,
            ),
        )

        self._esc_exit_rect = pygame.Rect(right_x, btn_y, btn_w, btn_h)
        exit_border = selected_border if exit_selected else normal_border
        pygame.draw.rect(self.screen, (200, 60, 60), self._esc_exit_rect, border_radius=10)
        pygame.draw.rect(self.screen, exit_border, self._esc_exit_rect, 3, border_radius=10)
        exit_text = self.font.render("退出游戏", True, (255, 255, 255))
        self.screen.blit(
            exit_text,
            (
                self._esc_exit_rect.centerx - exit_text.get_width() // 2,
                self._esc_exit_rect.centery - exit_text.get_height() // 2,
            ),
        )

        settings_btn_w = 200
        settings_btn_y = btn_y + btn_h + 16
        settings_btn_x = SCREEN_WIDTH // 2 - settings_btn_w // 2
        self._esc_settings_rect = pygame.Rect(settings_btn_x, settings_btn_y, settings_btn_w, btn_h)
        settings_border = selected_border if settings_selected else normal_border
        pygame.draw.rect(self.screen, (220, 160, 60), self._esc_settings_rect, border_radius=10)
        pygame.draw.rect(self.screen, settings_border, self._esc_settings_rect, 3, border_radius=10)
        settings_text = self.font.render("游戏设置", True, (255, 255, 255))
        self.screen.blit(
            settings_text,
            (
                self._esc_settings_rect.centerx - settings_text.get_width() // 2,
                self._esc_settings_rect.centery - settings_text.get_height() // 2,
            ),
        )

    def _update_bci_data(self) -> None:
        if self.bci_available:
            result = self.bci_reader.read_with_timeout()
            self.bci_available = self.bci_reader.connected
            if self.bci_available and result[0] is not None:
                (
                    self.attention,
                    self.platform_focus_x,
                    self.platform_focus_y,
                    self.raw_gyro_x,
                    self.raw_gyro_y,
                    self.raw_gyro_z,
                ) = result
            else:
                self.attention = 50
        else:
            if not self.bci_mode:
                self.attention = None

        if self.attention is not None:
            self.focus_samples.append(self.attention)
            self._cup_attn_samples.append(self.attention)
            self._attn_smooth_buffer.append(self.attention)
            win = int(WARMUP_SMOOTH_WINDOW * 60)
            if len(self._attn_smooth_buffer) > win:
                self._attn_smooth_buffer = self._attn_smooth_buffer[-win:]
            self._smooth_attention = sum(self._attn_smooth_buffer) / len(self._attn_smooth_buffer)
        else:
            self._smooth_attention = None

    def _update_attention_variance(self) -> None:
        if self._smooth_attention is None:
            return
        baseline = self._cup_baseline if self._cup_baseline > 0 else 40.0
        offset = self._smooth_attention - baseline
        self._attn_offsets.append(offset)
        if len(self._attn_offsets) > 60:
            self._attn_offsets = self._attn_offsets[-60:]

        if len(self._attn_offsets) >= 5:
            mean = sum(self._attn_offsets) / len(self._attn_offsets)
            self._attn_variance = sum((x - mean) ** 2 for x in self._attn_offsets) / len(self._attn_offsets)

            if self._attn_variance < 50:
                self._attn_mode = "简单模式"
                ice_prob = 0.2
            elif self._attn_variance < 150:
                self._attn_mode = "中等模式"
                ice_prob = 0.5
            else:
                self._attn_mode = "困难模式"
                if self.attention is not None and self.attention < 20:
                    ice_prob = 1.0
                else:
                    ice_prob = 0.8

            self.ingredient_manager.set_ice_probability(ice_prob)

    def _update_cup(self, keys: pygame.key.ScancodeWrapper, dt_sec: float) -> None:
        self.cup.update(keys=keys, dt=dt_sec)
        kb_pressed = keys[pygame.K_LEFT] or keys[pygame.K_RIGHT]
        if not kb_pressed and self.use_yaw_control and self.bci_available:
            fx = int(self.platform_focus_x)
            self.cup.rect.centerx = max(self.focus_min, min(self.focus_max, fx))

    def _check_secret_recipe(self, dt_sec: float) -> None:
        if self._secret_popup_timer > 0:
            self._secret_popup_timer -= dt_sec
            return
        if self._secret_disabled:
            return
        if self.cup_manager.secret_recipe_spawned:
            return
        if self.cup_manager.cup_ended:
            return

        if self._secret_threshold is not None:
            attn = self.attention if self.attention is not None else 50.0
            if attn > self._secret_threshold:
                self.focus_above_seconds += dt_sec
            else:
                self.focus_above_seconds = 0.0
            if self.focus_above_seconds >= self._secret_sustain and self.cup_manager.trigger_secret_recipe():
                self._secret_popup_timer = 4.0
                self.focus_above_seconds = 0.0
                if self._audio:
                    self._audio.play_sfx("音效/触发秘方.wav", volume=0.7)
                logger.info("秘方触发！专注力高于阈值 %.0f 持续 %.0f 秒", self._secret_threshold, self._secret_sustain)
        elif self.bci_mode and self.bci_available:
            threshold = min(self._cup_baseline + 10, 80)
            attn = self.attention if self.attention is not None else 50.0
            if attn > threshold:
                self.focus_above_seconds += dt_sec
            else:
                self.focus_above_seconds = 0.0

            if self.focus_above_seconds >= SECRET_RECIPE_SUSTAIN and self.cup_manager.trigger_secret_recipe():
                self._secret_popup_timer = 4.0
                self.focus_above_seconds = 0.0
                if self._audio:
                    self._audio.play_sfx("音效/触发秘方.wav", volume=0.7)
                logger.info("秘方触发！专注力持续高于阈值 %.0f 达 %d 秒", threshold, SECRET_RECIPE_SUSTAIN)
        else:
            if self.cup_manager.get_cup_elapsed() >= 5.0:
                if self.cup_manager.trigger_secret_recipe():
                    self._secret_popup_timer = 4.0
                    if self._audio:
                        self._audio.play_sfx("音效/触发秘方.wav", volume=0.7)
                    logger.info("第 %s 杯触发秘方！", self.cup_manager.cup_number)

    def _check_cup_end(self) -> None:
        if self.cup_manager.check_cup_end():
            if self._cup_attn_samples and self._fixed_baseline is None:
                self._cup_baseline = sum(self._cup_attn_samples) / len(self._cup_attn_samples)

            if self.cup_manager.cup_number == 1 and not self._raw_attention and self._cup_attn_samples and self._fixed_baseline is None:
                max_attn = max(self._cup_attn_samples)
                avg_attn = sum(self._cup_attn_samples) / len(self._cup_attn_samples)
                self.normalization_lower = max(avg_attn - 15.0, 0.0)
                self.normalization_upper = min(max_attn, 100.0)
                if self.normalization_upper - self.normalization_lower < 10.0:
                    mid = (self.normalization_upper + self.normalization_lower) / 2.0
                    self.normalization_lower = max(mid - 5.0, 0.0)
                    self.normalization_upper = min(mid + 5.0, 100.0)
                logger.info(
                    "第一杯结束！最高=%.1f 平均=%.1f  归一化范围: [%.1f, %.1f]",
                    max_attn,
                    avg_attn,
                    self.normalization_lower,
                    self.normalization_upper,
                )

            cup_avg_attn = sum(self._cup_attn_samples) / len(self._cup_attn_samples) if self._cup_attn_samples else (self.attention or 50.0)

            self._cup_attn_samples = []

            cup_money = self.cup_manager.settle_cup()
            had_secret = self.cup_manager.secret_recipe_spawned

            if self.bci_mode and cup_money > 0:
                attn = cup_avg_attn
                if self._raw_attention:
                    norm = attn
                else:
                    norm = self._normalize_to_range(attn)
                coeff = get_attention_coefficient(norm)
                cup_money = int(cup_money * coeff)

            self.score_manager.add_cup_money(cup_money, had_secret)
            if self._audio and cup_money > 0:
                self._audio.play_sfx("音效/加金币.wav", volume=0.5)
            self.score_manager.reset_cup_ingredients()
            self.focus_above_seconds = 0.0

            if not self._infinite and not self._training_duration:
                if self.cup_manager.all_cups_done():
                    self.show_summary = True
                    self.running = False
                    logger.info("全部 %s 杯完成，游戏结束！", self.cup_manager.total_cups)
                    return

                if self.cup_manager.is_game_time_exceeded(self.game_start_time):
                    self.show_summary = True
                    self.running = False
                    logger.info("总局时间已到，游戏结束！")
                    return

            self.cup_manager.start_new_cup()
            self.cup.update_level(0)
            self.score_manager.reset_cup_ingredients()

    def _update_game_objects(self, dt_sec: float) -> None:
        ingredient = self.ingredient_manager.update(required_types=None, ingredients_group=self.ingredients)
        if ingredient:
            self.ingredients.add(ingredient)
            if ingredient.is_required:
                ingredient.set_particle_group(self.particles)

        self.ingredients.update()
        self.catch_effects.update(dt=dt_sec)
        self.miss_effects.update(dt=dt_sec)
        self.particles.update(dt=dt_sec)

    def _handle_collisions(self) -> None:
        threshold_y = self.cup.rect.top + self.cup.rect.height * 0.8
        hits = pygame.sprite.spritecollide(self.cup, self.ingredients, False)

        _handle_catches(
            hits,
            self.cup,
            threshold_y,
            self.ingredients,
            self.miss_effects,
            self.catch_effects,
            self.particles,
            self.score_manager,
            self.cup_manager,
            audio=self._audio,
        )

        _handle_misses(self.ingredients, threshold_y, self.miss_effects, self.particles, audio=self._audio)

    def _render(self) -> None:
        if self.has_background and self.background:
            self.screen.blit(self.background, (0, 0))
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 10, config.BACKGROUND_OVERLAY_ALPHA))
            for rx, ry, rw, rh in OVERLAY_CLEAR_REGIONS:
                overlay.fill((0, 0, 0, 0), pygame.Rect(rx, ry, rw, rh))
            self.screen.blit(overlay, (0, 0))
        else:
            self.screen.fill((255, 255, 255))

        self.all_sprites.draw(self.screen)
        self.particles.draw(self.screen)
        self.ingredients.draw(self.screen)
        self.catch_effects.draw(self.screen)
        self.miss_effects.draw(self.screen)

        self._render_formal_hud()

        if self._esc_dialog_active:
            self._draw_esc_dialog()

        if self._secret_popup_timer > 0:
            self._draw_secret_popup()

        pygame.display.flip()

    def _draw_lane_lines(self) -> None:
        pass

    def _draw_focus_ball(self) -> None:
        if self._focus_ball is None or not self._digit_imgs:
            return

        bx, by = FOCUS_BALL_POS
        bw, bh = FOCUS_BALL_SIZE
        self.screen.blit(self._focus_ball, (bx - bw // 2, by - bh // 2))

        val = int(self.attention) if self.attention is not None else 0
        if self.bci_available:
            s = f"{min(val, 99):02d}"
            total_w = len(s) * DIGIT_WIDTH + (len(s) - 1) * DIGIT_SPACING
            start_x = bx - total_w // 2
            digit_y = by - DIGIT_HEIGHT // 2
            for ch in s:
                idx = ord(ch) - 48
                if 0 <= idx < len(self._digit_imgs):
                    self.screen.blit(self._digit_imgs[idx], (start_x, digit_y))
                start_x += DIGIT_WIDTH + DIGIT_SPACING

    def _draw_badge(self) -> None:
        if self._badge_img is None:
            return
        bx, by = INFO_BADGE_POS
        bw, bh = INFO_BADGE_SIZE
        self.screen.blit(self._badge_img, (bx - bw // 2, by - bh // 2))

    def _draw_info_labels(self) -> None:
        info_font = load_chinese_font(INFO_FONT_SIZE)
        is_infinite = self.cup_manager.total_cups < 0
        values = [
            f"LV.{self._player_level}",
            self.mode_name,
            "∞" if is_infinite else (str(self.cup_manager.cup_number) if self._training_duration > 0 else f"{self.cup_manager.cup_number}/{self.cup_manager.total_cups}"),
            str(self.score_manager.total_money),
        ]
        texts = [
            (cx, cy, info_font.render(v, True, (255, 255, 255)), info_font.render(v, True, (30, 15, 5)))
            for (cx, cy), v in zip(INFO_REGIONS, values)
        ]
        for cx, cy, txt, shadow in texts:
            tw, th = txt.get_size()
            x = cx - tw // 2
            y = cy - th // 2
            self.screen.blit(shadow, (x + 1, y + 1))
            self.screen.blit(txt, (x, y))

    def _render_formal_hud(self) -> None:
        self._draw_lane_lines()
        if config.SHOW_HUD_INFO:
            if self._info_bar:
                self.screen.blit(self._info_bar, (0, 0))
                self._draw_badge()
                self._draw_info_labels()
            elif self._top_bar:
                self.screen.blit(self._top_bar, (0, 0))
                mask = pygame.Surface((1280, 60), pygame.SRCALPHA)
                mask.fill((0, 0, 0, 60))
                self.screen.blit(mask, (0, 0))

        draw_hud(
            screen=self.screen,
            score_manager=self.score_manager,
            mode_name=self.mode_name,
            cup_manager=self.cup_manager,
            game_start_time=self.game_start_time,
            font=self.font,
            hint_font=self.hint_font,
            attention=self.attention,
            bci_mode=self.bci_mode,
            free_combine=self.free_combine,
            bci_connected=self.bci_available,
            skip_top_info=self._info_bar is not None,
            training_mode=(self._training_duration > 0),
        )

        if self.bci_mode:
            bci_status_color = (0, 255, 0) if self.bci_available else (255, 100, 100)
            bci_status_text = self.hint_font.render(
                f"头环: {'已连接' if self.bci_available else '未连接'}",
                True,
                bci_status_color,
            )
            self.screen.blit(bci_status_text, (10, SCREEN_HEIGHT - 30))

        if config.SHOW_FOCUS_BALL:
            self._draw_focus_ball()

        if self._blackout_alpha > 1:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, int(self._blackout_alpha)))
            self.screen.blit(overlay, (0, 0))

            if self._paused:
                pause_text = self.pause_font.render("请调整身心状态", True, (255, 255, 255))
                self.screen.blit(
                    pause_text,
                    (SCREEN_WIDTH // 2 - pause_text.get_width() // 2, SCREEN_HEIGHT // 2 - 60),
                )
                sub_text = self.hint_font.render(
                    f"保持专注力 >{WARMUP_LOW_THRESHOLD} 持续 {max(0, int(WARMUP_RESUME_TIME) - self._high_attn_seconds):.0f}s 恢复游戏",
                    True,
                    (200, 200, 200),
                )
                self.screen.blit(
                    sub_text,
                    (SCREEN_WIDTH // 2 - sub_text.get_width() // 2, SCREEN_HEIGHT // 2 + 20),
                )

        if self._artifact_alpha > 1:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, int(self._artifact_alpha)))
            self.screen.blit(overlay, (0, 0))

            if self._artifact_frozen:
                pause_text = self.pause_font.render("请放松面部肌肉", True, (255, 255, 255))
                self.screen.blit(
                    pause_text,
                    (SCREEN_WIDTH // 2 - pause_text.get_width() // 2, SCREEN_HEIGHT // 2 - 60),
                )
                sub_text = self.hint_font.render(
                    f"检测到伪迹，冻结 {self._artifact_penalty_timer:.0f}s",
                    True,
                    (200, 200, 200),
                )
                self.screen.blit(
                    sub_text,
                    (SCREEN_WIDTH // 2 - sub_text.get_width() // 2, SCREEN_HEIGHT // 2 + 20),
                )

    def _cache_secret_popup_image(self) -> None:
        self._secret_img = None
        img_path = INGREDIENT_IMGS.get("秘方", "")
        if img_path and os.path.exists(img_path):
            img = pygame.image.load(img_path).convert_alpha()
            self._secret_img = pygame.transform.scale(img, (160, 160))

    def _draw_secret_popup(self) -> None:
        timer = self._secret_popup_timer
        if timer > 3.5:
            alpha = (4.0 - timer) / 0.5
        elif timer < 0.5:
            alpha = timer / 0.5
        else:
            alpha = 1.0
        alpha = max(0.0, min(1.0, alpha))

        overlay_alpha = int(80 * alpha)
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, overlay_alpha))
        self.screen.blit(overlay, (0, 0))

        popup_w, popup_h = 260, 270
        popup_x = (SCREEN_WIDTH - popup_w) // 2
        popup_y = (SCREEN_HEIGHT - popup_h) // 2

        popup_surf = pygame.Surface((popup_w, popup_h), pygame.SRCALPHA)
        bg_alpha = int(200 * alpha)
        border_alpha = int(180 * alpha)
        pygame.draw.rect(popup_surf, (30, 25, 20, bg_alpha), (0, 0, popup_w, popup_h), border_radius=16)
        pygame.draw.rect(popup_surf, (255, 180, 100, border_alpha), (0, 0, popup_w, popup_h), 3, border_radius=16)
        self.screen.blit(popup_surf, (popup_x, popup_y))

        text_surf = self.font.render("触发秘方！", True, (255, 220, 100))
        text_surf.set_alpha(int(255 * alpha))
        text_x = popup_x + (popup_w - text_surf.get_width()) // 2
        text_y = popup_y + popup_h - text_surf.get_height() - 20
        self.screen.blit(text_surf, (text_x, text_y))

        if self._secret_img is not None:
            t = pygame.time.get_ticks() / 1000.0
            wobble_x = int(math.sin(t * 4) * 5)
            angle = math.sin(t * 3) * 2
            rotated = pygame.transform.rotate(self._secret_img, angle)
            rotated.set_alpha(int(255 * alpha))
            rx = popup_x + (popup_w - rotated.get_width()) // 2 + wobble_x
            ry = popup_y + 25
            self.screen.blit(rotated, (rx, ry))

    def _end_game(self) -> str:
        if self._training_duration > 0:
            if self.bci_reader and self.bci_available:
                self.bci_reader.disconnect()
            return ""
        if self._audio:
            self._audio.play_sfx("音效/游戏结束.wav", volume=0.6)
        if self.show_summary:
            avg_focus = sum(self.focus_samples) / len(self.focus_samples) if self.focus_samples else 0.0
            if not self.bci_mode:
                avg_focus = 0.0

            game_duration = time_module.time() - self.game_start_time
            last_5min_avg = avg_focus
            if self.focus_samples and game_duration > 0:
                sps = len(self.focus_samples) / game_duration
                n = max(1, int(sps * 300))
                last_samples = self.focus_samples[-n:]
                last_5min_avg = sum(last_samples) / len(last_samples)

            if self._profile:
                p_level = self._profile.level
                p_rev = self._profile.cumulative_revenue
                can_save = not (
                    self.control_mode in ("bci", "bci_failed") and self.bci_mode and not self.bci_available
                )
            else:
                self._upgrade_level = 1
                p_level = 1
                p_rev = 0
                can_save = False

            bg_snapshot = self.screen.copy()
            summary = SummaryScreen(
                self.screen,
                self.score_manager.score,
                avg_focus,
                self.game_mode,
                total_money=self.score_manager.total_money,
                cup_count=self.score_manager.cup_count,
                secret_count=self.score_manager.secret_recipe_count,
                max_cup_money=self.score_manager.get_max_cup_money(),
                player_level=p_level,
                cumulative_revenue=p_rev,
                upgraded=False,
                focus_samples=self.focus_samples,
                bg=bg_snapshot,
            )
            result = summary.run()

            if result == "save" and self._profile and can_save:
                upgraded = self._profile.add_game_result(
                    revenue=self.score_manager.total_money,
                    mode=self.game_mode,
                    cups=self.score_manager.cup_count,
                    secrets=self.score_manager.secret_recipe_count,
                    avg_attention=avg_focus,
                    duration=game_duration,
                    focus_samples=self.focus_samples,
                    last_5min_avg_attention=last_5min_avg,
                )
                self._upgrade_level = self._profile.level
                if upgraded and self._audio:
                    self._audio.play_sfx("音效/升级.wav", volume=0.7)
                return "save"
            return result

        if self.bci_available:
            self.bci_reader.disconnect()
        return ""


def run_game(
    screen: pygame.Surface,
    clock: pygame.time.Clock,
    game_mode: str = "regular",
    profile=None,
    control_mode: str = "bci",
    audio=None,
) -> str:
    session = GameSession(screen, clock, game_mode, profile, control_mode=control_mode, audio=audio)
    return session.run()


def _handle_catches(
    hits: list[Any],
    cup: Cup,
    threshold_y: float,
    ingredients: pygame.sprite.Group,
    miss_effects: pygame.sprite.Group,
    catch_effects: pygame.sprite.Group,
    particles: pygame.sprite.Group,
    score_manager: ScoreManager,
    cup_manager: CupManager,
    audio=None,
) -> None:
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

            score_manager.add_ingredient(hit.type, is_required=hit.is_required)
            cup_manager.add_catch(hit.type, is_required=hit.is_required)

            cup.update_level(cup_manager.catch_count)
            logger.info("接住 %s！收益: %s", hit.type, score_manager.total_money)

            if audio:
                if hit.is_required:
                    audio.play_sfx("音效/接到必接食材.wav", volume=0.3)
                else:
                    audio.play_sfx("音效/接到食材.wav", volume=0.2)


def _handle_misses(
    ingredients: pygame.sprite.Group,
    threshold_y: float,
    miss_effects: pygame.sprite.Group,
    particles: pygame.sprite.Group,
    audio=None,
) -> None:
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
            if audio and getattr(ing, "is_required", False):
                audio.play_sfx("音效/漏接必接食材.wav", volume=0.5)
