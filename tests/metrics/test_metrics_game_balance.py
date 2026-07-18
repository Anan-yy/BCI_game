"""
3.2.3 等级成长与游戏平衡性测试
三种玩家类型各模拟10人，每人10局，追踪收益/升级/秘方/零收益/冻结等指标
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["font.size"] = 10.5

from data.player_profile import PlayerProfile, LEVEL_THRESHOLDS
from .test_helpers import AttentionGenerator, GameSimulator, GyroGenerator

PLAYER_TYPES = {
    "高专注平稳型(高手)": "stable_high",
    "中等波动型": "medium",
    "低专注涣散型(新手)": "low_fluctuating",
}
PLAYERS_PER_TYPE = 10
GAMES_PER_TYPE = 10
FPS = 60
WARMUP_SECS = 180
FORMAL_SECS = 36 * 20
TOTAL_FRAMES = int((WARMUP_SECS + FORMAL_SECS) * FPS)


def run_single_game(player_type: str, profile: PlayerProfile, seed: int) -> dict:
    gen = AttentionGenerator(player_type, seed=seed)
    warmup_attn = gen.generate(WARMUP_SECS, FPS)
    formal_attn = gen.generate(FORMAL_SECS, FPS)

    gyro_gen = GyroGenerator(len(formal_attn), cheat_ratio=0.06, seed=seed + 1000)

    sim = GameSimulator(
        warmup_attn=warmup_attn,
        formal_attn=formal_attn,
        gyro_generator=gyro_gen,
        tier=profile.level,
        seed=seed + 2000,
    )
    sim.run_warmup()
    metrics = sim.run_formal()

    metrics["game_number"] = profile.total_games + 1
    profile.add_game_result(
        revenue=metrics["revenue"],
        mode="BCI常规",
        cups=metrics["cups"],
        secrets=metrics["secrets"],
        avg_attention=metrics["avg_attention"],
        focus_samples=None,
    )
    metrics["level_after"] = profile.level
    metrics["cumulative_revenue"] = profile.cumulative_revenue

    return metrics


def run():
    total_players = PLAYERS_PER_TYPE * len(PLAYER_TYPES)
    total_games = total_players * GAMES_PER_TYPE
    print("=" * 65)
    print("3.2.3 等级成长与游戏平衡性测试")
    print(f"每类 {PLAYERS_PER_TYPE} 人 × {GAMES_PER_TYPE} 局 = {PLAYERS_PER_TYPE * GAMES_PER_TYPE} 局")
    print(f"共 {total_players} 名模拟玩家，{total_games} 局游戏")
    print("=" * 65)

    all_results: dict[str, list[dict]] = {}

    for pname, ptype in PLAYER_TYPES.items():
        print(f"\n--- {pname} ---")
        game_log: list[dict] = []
        all_rev, all_sec, all_zero, all_freeze, all_art, all_catch = [], [], [], [], [], []
        final_levels = []

        for p in range(PLAYERS_PER_TYPE):
            profile = PlayerProfile(_username=f"{pname}_{p}")
            for g in range(GAMES_PER_TYPE):
                seed = hash(f"{ptype}_{p}_{g}") % (2**31)
                metrics = run_single_game(ptype, profile, seed)
                game_log.append(metrics)

                all_rev.append(metrics["revenue"])
                all_sec.append(metrics["secrets"])
                all_zero.append(metrics["zero_revenue_cups"] / max(metrics["cups"], 1) * 100)
                all_freeze.append(metrics["freeze_count"])
                all_art.append(metrics["artifact_count"])
                all_catch.append(metrics["total_catches"])

            final_levels.append(profile.level)

        all_results[pname] = game_log

        print(f"  每局收益:      均值 {np.mean(all_rev):.0f}  |  范围 [{min(all_rev)}-{max(all_rev)}]")
        print(f"  秘方/局:       {np.mean(all_sec):.1f} 次")
        print(f"  零收益杯:      {np.mean(all_zero):.1f}%")
        print(f"  冻结/局:       {np.mean(all_freeze):.1f} 次")
        print(f"  防作弊/局:     {np.mean(all_art):.1f} 次")
        print(f"  接住食材/局:   {np.mean(all_catch):.0f} 个")
        print(f"  最终等级:      Lv.{min(final_levels)}~Lv.{max(final_levels)} (mid={np.median(final_levels):.0f})")

    _plot_revenue_growth(all_results)
    _plot_player_comparison(all_results)
    _plot_cup_distribution(all_results)

    print("\n测试完成。\n")

    _plot_revenue_growth(all_results)
    _plot_player_comparison(all_results)
    _plot_cup_distribution(all_results)

    print("\n测试完成。\n")


def _plot_revenue_growth(all_results: dict[str, list[dict]]) -> None:
    fig, ax = plt.subplots(figsize=(5.90, 3.31))
    colors = {"高专注平稳型(高手)": "#2E86AB", "中等波动型": "#F18F01", "低专注涣散型(新手)": "#D1495B"}
    lv_lines = [80, 250, 600]
    n_players = PLAYERS_PER_TYPE

    for pname, game_log in all_results.items():
        c = colors.get(pname, "#333")
        x = np.arange(1, GAMES_PER_TYPE + 1)
        player_curves = []
        for p in range(PLAYERS_PER_TYPE):
            start = p * GAMES_PER_TYPE
            end = start + GAMES_PER_TYPE
            cum = np.cumsum([r["revenue"] for r in game_log[start:end]])
            player_curves.append(cum)
            ax.plot(x, cum, linewidth=0.6, color=c, alpha=0.4)
        mean_curve = np.mean(player_curves, axis=0)
        ax.plot(x, mean_curve, linewidth=2, color=c, marker="o", markersize=4, label=pname)

    for lv_val in lv_lines:
        ax.axhline(y=lv_val, color="gray", linestyle="--", alpha=0.4, linewidth=0.8)
        ax.text(0.5, lv_val + 8, f"Lv{lv_lines.index(lv_val)+2} ({lv_val}元)",
                color="gray", alpha=0.8)

    ax.set_xlabel("游戏局数")
    ax.set_ylabel("累计收益 (元)")
    ax.set_title("累计收益增长曲线 — 三种玩家类型", fontweight="bold")
    ax.legend()
    ax.grid(True, alpha=0.3)

    out_dir = os.path.dirname(os.path.abspath(__file__))
    out_path = os.path.join(out_dir, "revenue_growth.png")
    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"图表: {os.path.abspath(out_path)}")


def _plot_player_comparison(all_results: dict[str, list[dict]]) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(5.91, 4.40))
    fig.suptitle("三种玩家类型关键指标对比 (箱线图, n=100局)", fontweight="bold")

    pnames = list(all_results.keys())
    metrics_cfg = [
        (0, 0, "revenue", "每局收益 (元)", "#4A90D9"),
        (0, 1, "secrets", "秘方触发次数", "#F5A623"),
        (1, 0, "zero_revenue_cups", "零收益杯数 (%)", "#D1495B"),
        (1, 1, "freeze_count", "冻结次数", "#7B68EE"),
    ]

    from scipy.stats import f_oneway

    for row, col, key, title, color in metrics_cfg:
        ax = axes[row][col]
        data_list = []
        for pname in pnames:
            raw = [r[key] for r in all_results[pname]]
            if key == "zero_revenue_cups":
                raw = [r["zero_revenue_cups"] / max(r["cups"], 1) * 100 for r in all_results[pname]]
            data_list.append(raw)

        bp = ax.boxplot(data_list, tick_labels=["高专注", "中专注", "低专注"], patch_artist=True,
                         widths=0.5, showfliers=True, flierprops=dict(marker="o", markersize=3))

        for patch, c in zip(bp["boxes"], [color] * 3):
            patch.set_facecolor(c)
            patch.set_alpha(0.3)
        for whisker in bp["whiskers"]:
            whisker.set_color(color)

        ax.set_title(title)
        ax.grid(True, alpha=0.3, axis="y")

    out_dir = os.path.dirname(os.path.abspath(__file__))
    out_path = os.path.join(out_dir, "player_comparison.png")
    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"图表: {os.path.abspath(out_path)}")


def _plot_cup_distribution(all_results: dict[str, list[dict]]) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))
    fig.suptitle("单局36杯金额分布直方图 (各类型第1局示例)", fontweight="bold")

    colors = ["#2E86AB", "#F18F01", "#D1495B"]

    for ax, (pname, game_log), c in zip(axes, all_results.items(), colors):
        money_list = game_log[0]["cup_money_list"]
        ax.hist(money_list, bins=20, range=(0, max(money_list) + 5),
                color=c, edgecolor="white", alpha=0.75)
        ax.axvline(x=np.mean(money_list), color="red", linestyle="--",
                   linewidth=1.5, label=f"均值={np.mean(money_list):.0f}元")
        ax.set_title(pname[:8])
        ax.set_xlabel("杯收益 (元)")
        ax.set_ylabel("杯数")
        ax.legend()
        zero_pct = sum(1 for m in money_list if m == 0) / max(len(money_list), 1) * 100
        ax.text(0.95, 0.92, f"零收益: {zero_pct:.0f}%",
                transform=ax.transAxes, ha="right", va="top",
                bbox=dict(boxstyle="round,pad=0.3", facecolor="wheat", alpha=0.7))

    out_dir = os.path.dirname(os.path.abspath(__file__))
    out_path = os.path.join(out_dir, "cup_distribution.png")
    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"图表: {os.path.abspath(out_path)}")


if __name__ == "__main__":
    run()
