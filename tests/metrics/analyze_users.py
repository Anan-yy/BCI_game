"""20人训练数据分析 — 生成论文图表"""

import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["font.size"] = 10.5

PROFILES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "profiles")
OUT_DIR = os.path.dirname(os.path.abspath(__file__))


def load_all_profiles() -> list[dict]:
    users = []
    for fname in sorted(os.listdir(PROFILES_DIR)):
        if fname.endswith("_training.json") or not fname.endswith(".json"):
            continue
        fpath = os.path.join(PROFILES_DIR, fname)
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue
        username = fname.replace(".json", "")
        th = data.get("training_history", [])
        gh = data.get("games_history", [])
        if not th and not gh:
            continue
        user = {
            "name": username,
            "level": data.get("level", 1),
            "cum_rev": data.get("cumulative_revenue", 0),
            "training": [],
            "games": [],
        }
        for t in th:
            user["training"].append({
                "date": t.get("date", "")[:10],
                "duration": t.get("duration", 0),
                "money": t.get("total_money", 0),
                "cups": t.get("total_cups", 0),
                "secrets": t.get("secret_count", 0),
                "failed": t.get("failed_cup_count", 0),
                "mem_ok": t.get("memory_successes", 0),
                "mem_fail": t.get("memory_failures", 0),
                "avg_attn": t.get("avg_attention", 0),
                "s1_avg": t.get("stage1_avg", 0),
                "s2_avg": t.get("stage2_avg", 0),
                "s3_avg": t.get("stage3_avg", 0),
                "s1_min": t.get("stage1_min", 0),
                "s2_min": t.get("stage2_min", 0),
                "s3_min": t.get("stage3_min", 0),
                "rounds": t.get("rounds", 0),
            })
        for g in gh:
            user["games"].append({
                "date": g.get("date", "")[:10],
                "mode": g.get("mode", ""),
                "revenue": g.get("revenue", 0),
                "cups": g.get("cups", 0),
                "secrets": g.get("secrets", 0),
                "avg_attn": g.get("avg_attention", 0),
                "duration": g.get("duration", 0),
            })
        users.append(user)
    return users


def fig1_training_compliance(users):
    """图1: 训练依从性 — 每人训练次数分布"""
    counts = [len(u["training"]) for u in users if u["training"]]
    if not counts:
        return
    fig, ax = plt.subplots(figsize=(5.90, 2.91))
    bins = np.arange(0.5, max(counts) + 1.5, 1)
    ax.hist(counts, bins=bins, color="#4A90D9", edgecolor="white", alpha=0.85)
    ax.set_xlabel("训练次数")
    ax.set_ylabel("人数")
    ax.set_title("训练依从性分布 (n=20)", fontweight="bold")
    mean_c = np.mean(counts)
    ax.axvline(mean_c, color="red", linestyle="--", linewidth=1.2, label=f"均值={mean_c:.1f}次")
    ax.legend()
    out = os.path.join(OUT_DIR, "user_compliance.png")
    plt.tight_layout()
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"图1: {out}")


def fig2_attention_trend(users):
    """图2: 专注力趋势 — 有≥3次训练的用户，按训练次序画专注力折线"""
    trend_data = {}
    for u in users:
        if len(u["training"]) >= 3:
            for idx, t in enumerate(u["training"]):
                if idx not in trend_data:
                    trend_data[idx] = []
                trend_data[idx].append(t["avg_attn"])

    if not trend_data or max(trend_data.keys()) < 2:
        return
    fig, ax = plt.subplots(figsize=(5.90, 2.91))
    xs = sorted(trend_data.keys())
    means = [np.mean(trend_data[x]) for x in xs]
    stds = [np.std(trend_data[x]) for x in xs]
    ns = [len(trend_data[x]) for x in xs]

    ax.errorbar(xs, means, yerr=stds, marker="o", linewidth=2, color="#D1495B",
                capsize=4, markersize=6, label=f"均值±1σ (n={ns[0]}人)")
    for i, x in enumerate(xs):
        ax.text(x, means[i] + stds[i] + 1, f"n={ns[i]}", ha="center", fontsize=9, color="gray")

    ax.set_xlabel("训练次数")
    ax.set_ylabel("平均专注力")
    ax.set_title(f"专注力变化趋势 (≥3次训练, n={ns[0]}人)", fontweight="bold")
    ax.set_xticks(xs)
    ax.set_xticklabels([f"第{x+1}次" for x in xs])
    ax.grid(True, alpha=0.3)
    ax.legend()
    out = os.path.join(OUT_DIR, "user_attention_trend.png")
    plt.tight_layout()
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"图2: {out}")


def fig3_stage_comparison(users):
    """图3: 三阶段专注力对比 — 箱线图"""
    s1_vals, s2_vals, s3_vals = [], [], []
    for u in users:
        for t in u["training"]:
            if t["s1_avg"] > 0:
                s1_vals.append(t["s1_avg"])
            if t["s2_avg"] > 0:
                s2_vals.append(t["s2_avg"])
            if t["s3_avg"] > 0:
                s3_vals.append(t["s3_avg"])

    if not s1_vals:
        return
    fig, ax = plt.subplots(figsize=(5.90, 3.31))
    data = [s1_vals, s2_vals, s3_vals]
    bp = ax.boxplot(data, tick_labels=["原萃阶段", "特调阶段", "忆调阶段"],
                     patch_artist=True, widths=0.5, showfliers=True,
                     flierprops=dict(marker="o", markersize=4))
    colors = ["#F18F01", "#4A90D9", "#7B68EE"]
    for patch, c in zip(bp["boxes"], colors):
        patch.set_facecolor(c)
        patch.set_alpha(0.3)
    for whisker, c in zip(bp["whiskers"], colors * 2):
        whisker.set_color(c)

    from scipy.stats import kruskal
    h, p = kruskal(s1_vals, s2_vals, s3_vals)
    stars = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "n.s."
    ax.set_title(f"三阶段专注力对比 (n={len(s1_vals)}条记录)\np={p:.4f} {stars}", fontweight="bold")
    ax.set_ylabel("专注力")
    ax.grid(True, alpha=0.3, axis="y")

    for i, vals in enumerate(data):
        ax.text(i + 1, max(vals) + 1, f"μ={np.mean(vals):.1f}", ha="center", fontsize=9)

    out = os.path.join(OUT_DIR, "user_stage_comparison.png")
    plt.tight_layout()
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"图3: {out}")


def fig4_revenue_vs_attention(users):
    """图4: 收益与专注力散点图"""
    attn_list, rev_list = [], []
    for u in users:
        for t in u["training"]:
            if t["avg_attn"] > 0 and t["money"] > 0:
                attn_list.append(t["avg_attn"])
                rev_list.append(t["money"])

    if not attn_list:
        return
    fig, ax = plt.subplots(figsize=(5.90, 3.31))
    ax.scatter(attn_list, rev_list, alpha=0.7, c="#D1495B", edgecolors="white", s=40)

    from numpy import corrcoef
    r = corrcoef(attn_list, rev_list)[0, 1]
    z = np.polyfit(attn_list, rev_list, 1)
    p = np.poly1d(z)
    xs = np.linspace(min(attn_list), max(attn_list), 100)
    ax.plot(xs, p(xs), "--", color="gray", alpha=0.5, linewidth=1.5)

    ax.set_xlabel("平均专注力")
    ax.set_ylabel("训练收益 (元)")
    ax.set_title(f"专注力与收益相关性 (n={len(attn_list)}条记录)\nr = {r:.3f}", fontweight="bold")
    ax.grid(True, alpha=0.3)
    out = os.path.join(OUT_DIR, "user_revenue_vs_attention.png")
    plt.tight_layout()
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"图4: {out}")


def fig5_baseline_profile(users):
    """图5: 群体基线画像 — 专注力直方图 + 等级分布"""
    all_attn = []
    for u in users:
        for t in u["training"]:
            if t["avg_attn"] > 0:
                all_attn.append(t["avg_attn"])

    level_counts = {1: 0, 2: 0, 3: 0, 4: 0}
    for u in users:
        lv = u.get("level", 1)
        level_counts[lv] = level_counts.get(lv, 0) + 1

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 3.5))

    if all_attn:
        ax1.hist(all_attn, bins=15, color="#4A90D9", edgecolor="white", alpha=0.85)
        ax1.axvline(np.mean(all_attn), color="red", linestyle="--", linewidth=1.2,
                     label=f"均值={np.mean(all_attn):.1f}")
        ax1.set_xlabel("平均专注力")
        ax1.set_ylabel("记录数")
        ax1.set_title(f"专注力分布 (n={len(all_attn)}条)", fontweight="bold")
        ax1.legend()

    lvs = [1, 2, 3, 4]
    counts = [level_counts.get(lv, 0) for lv in lvs]
    bars = ax2.bar(lvs, counts, color=["#ccc", "#4A90D9", "#F18F01", "#D1495B"],
                    edgecolor="white")
    for lv, cnt in zip(lvs, counts):
        if cnt > 0:
            ax2.text(lv, cnt + 0.3, str(cnt), ha="center", fontsize=9)
    ax2.set_xlabel("等级")
    ax2.set_ylabel("人数")
    ax2.set_title(f"等级分布 (n={len(users)}人)", fontweight="bold")
    ax2.set_xticks(lvs)
    ax2.set_xticklabels([f"Lv.{lv}" for lv in lvs])

    plt.tight_layout()
    out = os.path.join(OUT_DIR, "user_baseline_profile.png")
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"图5: {out}")


def print_summary(users):
    """打印汇总统计"""
    print("\n" + "=" * 60)
    print("20人训练数据 — 汇总统计")
    print("=" * 60)

    train_users = [u for u in users if u["training"]]
    print(f"\n总用户数: {len(train_users)}")
    all_train = []
    for u in train_users:
        all_train.extend(u["training"])
    print(f"总训练记录: {len(all_train)} 条")

    if all_train:
        durations = [t["duration"] for t in all_train if t["duration"] > 0]
        if durations:
            print(f"平均训练时长: {np.mean(durations)/60:.1f} 分钟")
            print(f"完成≥15分钟: {sum(1 for d in durations if d>=900)}/{len(durations)} 条")

        moneys = [t["money"] for t in all_train]
        print(f"平均每训练收益: {np.mean(moneys):.0f} 元 (范围 {min(moneys)}-{max(moneys)})")

        attns = [t["avg_attn"] for t in all_train if t["avg_attn"] > 0]
        if attns:
            print(f"平均专注力: {np.mean(attns):.1f} (范围 {min(attns):.1f}-{max(attns):.1f})")

    counts = [len(u["training"]) for u in train_users]
    print(f"每人平均训练次数: {np.mean(counts):.1f} (范围 {min(counts)}-{max(counts)})")

    level_dist = {1: 0, 2: 0, 3: 0, 4: 0}
    for u in train_users:
        level_dist[u.get("level", 1)] = level_dist.get(u.get("level", 1), 0) + 1
    print(f"等级分布: Lv.1={level_dist[1]}人 Lv.2={level_dist[2]}人 Lv.3={level_dist[3]}人 Lv.4={level_dist[4]}人")


def main():
    users = load_all_profiles()
    if not users:
        print("无有效用户数据")
        return

    print_summary(users)
    fig1_training_compliance(users)
    fig2_attention_trend(users)
    fig3_stage_comparison(users)
    fig4_revenue_vs_attention(users)
    fig5_baseline_profile(users)
    print("\n全部图表生成完成。")


if __name__ == "__main__":
    main()
