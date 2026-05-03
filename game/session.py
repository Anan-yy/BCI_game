"""游戏会话模块 - 管理单局游戏的初始化、循环和结算"""

import logging
import os

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


def run_game(screen, clock, game_mode="regular"):
    """
    运行主游戏循环

    参数:
        screen: pygame 屏幕对象
        clock: pygame 时钟对象
        game_mode: 游戏模式

    返回:
        "quit" / "menu"
    """
    mode_config = GAME_MODES.get(game_mode, GAME_MODES[DEFAULT_GAME_MODE])
    mode_name = mode_config["name"]
    has_required = mode_config["has_required"]
    free_combine = mode_config["free_combine"]
    bci_mode = mode_config["bci_mode"]

    font = load_chinese_font(36)
    hint_font = load_chinese_font(20)
    recipe_font = load_chinese_font(28)

    # === 游戏对象初始化 ===
    cup = Cup()
    all_sprites = pygame.sprite.Group()
    all_sprites.add(cup)

    ingredients = pygame.sprite.Group()
    catch_effects = pygame.sprite.Group()
    miss_effects = pygame.sprite.Group()
    particles = pygame.sprite.Group()

    score_manager = ScoreManager()
    ingredient_manager = IngredientManager()
    ingredient_manager.spawn_interval = mode_config["spawn_interval"] / 1000.0

    patience_bar_x = 20
    patience_bar_y = SCREEN_HEIGHT - CUP_HEIGHT - PATIENCE_BAR_SIZE[1] - 30
    patience_bar = PatienceBar(patience_bar_x, patience_bar_y)

    # === BCI 初始化 ===
    bci_reader = BCIDataReader()
    bci_available = False
    if bci_mode:
        bci_available = bci_reader.connect()

    dead_zone = DeadZoneFilter(threshold=5)
    smooth_yaw = ExponentialSmoothing(alpha=0.3)

    attention_curve = None
    if free_combine:
        attention_curve = AttentionMappingCurve()

    # === 背景加载 ===
    background = None
    has_background = False
    try:
        if os.path.exists(BACKGROUND_IMG):
            background = pygame.image.load(BACKGROUND_IMG).convert()
            background = pygame.transform.scale(background, (SCREEN_WIDTH, SCREEN_HEIGHT))
            has_background = True
    except Exception:
        pass

    # === 创意模式状态 ===
    creative_ingredients = []
    recipe_result = None

    if has_required:
        score_manager.set_required_ingredient("红茶")

    # === 游戏状态 ===
    running = True
    show_summary = False
    use_yaw_control = False
    game_start_time = pygame.time.get_ticks()
    focus_samples = []

    teapot_img_path = FOCUS_TEAPOT_IMG if os.path.exists(FOCUS_TEAPOT_IMG) else None
    focus_teapot = None
    if teapot_img_path:
        focus_teapot = FocusTeapotUI(image_path=teapot_img_path, x=10, y=90, width=120, height=140)

    _print_mode_rules(mode_name, bci_mode, free_combine, bci_available)

    # 首帧绘制防闪烁
    if has_background and background:
        screen.blit(background, (0, 0))
    else:
        screen.fill((255, 255, 255))

    all_sprites.draw(screen)
    score_text = font.render(f"分数: {score_manager.score}", True, (0, 0, 0))
    screen.blit(score_text, (10, 10))
    mode_text = font.render(f"{mode_name}", True, (100, 50, 150))
    screen.blit(mode_text, (10, 50))
    pygame.display.flip()

    # === 主游戏循环 ===
    while running:
        dt = clock.tick(60)
        keys = pygame.key.get_pressed()
        dt_sec = dt / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_y:
                    use_yaw_control = True
                    cup.yaw_control = True
                elif event.key == pygame.K_k:
                    use_yaw_control = False
                    cup.yaw_control = False
                elif event.key == pygame.K_ESCAPE:
                    show_summary = True
                    running = False
                    break

        # 获取控制信号
        if bci_available:
            result = bci_reader.read_with_timeout()
            if result != (None, None):
                attention, raw_yaw = result
            else:
                attention = 50
                raw_yaw = 0
        else:
            attention = None
            raw_yaw = 0

        # 信号处理
        filtered_yaw = dead_zone.filter(raw_yaw)
        smoothed_yaw = smooth_yaw.smooth(filtered_yaw)

        # 更新杯子
        if use_yaw_control:
            cup.update(yaw=smoothed_yaw, dt=dt_sec)
        else:
            cup.update(keys=keys, dt=dt_sec)

        # 计时与专注力记录
        elapsed_ms = pygame.time.get_ticks() - game_start_time
        if elapsed_ms >= GAME_DURATION * 1000:
            show_summary = True
            running = False
            break

        if attention is not None:
            focus_samples.append(attention)

        # 生成并更新食材
        required = ["红茶"] if has_required else None
        ingredient = ingredient_manager.update(required_types=required)
        if ingredient:
            ingredients.add(ingredient)

        ingredients.update()
        catch_effects.update(dt=dt_sec)
        miss_effects.update(dt=dt_sec)
        particles.update(dt=dt_sec)
        patience_bar.update(dt_sec)

        # 碰撞检测
        threshold_y = cup.rect.top + cup.rect.height * 0.8
        hits = pygame.sprite.spritecollide(cup, ingredients, False)

        creative_ingredients, recipe_result = _handle_catches(
            hits,
            cup,
            threshold_y,
            ingredients,
            miss_effects,
            catch_effects,
            particles,
            patience_bar,
            score_manager,
            free_combine,
            creative_ingredients,
            recipe_result,
        )

        _handle_misses(ingredients, threshold_y, miss_effects, particles)

        # 渲染
        if has_background and background:
            screen.blit(background, (0, 0))
        else:
            screen.fill((255, 255, 255))

        all_sprites.draw(screen)
        ingredients.draw(screen)
        catch_effects.draw(screen)
        miss_effects.draw(screen)
        particles.draw(screen)

        draw_hud(
            screen=screen,
            score_manager=score_manager,
            mode_name=mode_name,
            patience_bar=patience_bar,
            font=font,
            hint_font=hint_font,
            recipe_font=recipe_font,
            focus_teapot=focus_teapot,
            attention=attention,
            smoothed_yaw=smoothed_yaw,
            bci_mode=bci_mode,
            free_combine=free_combine,
            recipe_result=recipe_result,
            creative_ingredients=creative_ingredients,
            attention_curve=attention_curve,
        )

        pygame.display.flip()

    # === 游戏结束结算 ===
    if show_summary:
        avg_focus = sum(focus_samples) / len(focus_samples) if focus_samples else 0.0
        if not bci_mode:
            avg_focus = 0.0

        summary = SummaryScreen(screen, score_manager.score, avg_focus, game_mode)
        return summary.run()

    return "quit"


def _handle_catches(
    hits,
    cup,
    threshold_y,
    ingredients,
    miss_effects,
    catch_effects,
    particles,
    patience_bar,
    score_manager,
    free_combine,
    creative_ingredients,
    recipe_result,
):
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


def _handle_misses(ingredients, threshold_y, miss_effects, particles):
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


def _print_mode_rules(mode_name, bci_mode, free_combine, bci_available):
    """打印模式规则到控制台"""
    logger.info("=" * 50)
    logger.info("疯狂奶茶杯 - %s", mode_name)
    logger.info("=" * 50)
    if bci_mode:
        logger.info("脑机接口模式规则：")
        logger.info("  使用BCI设备读取专注力和头动数据")
        logger.info("  自由搭配食材，不同组合产生不同评分")
        logger.info("  专注力越高，评分加成越大")
        if not bci_available:
            logger.warning("  [警告] BCI设备未连接，无法读取数据")
    elif free_combine:
        logger.info("创意模式规则：")
        logger.info("  没有必接食材，自由搭配")
        logger.info("  不同组合产生不同评分（黑暗→米其林）")
        logger.info("  专注力越高，评分加成越大")
    else:
        logger.info("控制说明:")
        logger.info("  方向键左/右: 移动杯子")
        logger.info("  Y: 头动模式 | K: 键盘模式 | ESC: 返回菜单")
    logger.info("=" * 50)
