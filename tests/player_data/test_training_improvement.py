"""训练模式统计：第1局 vs 第4局 — 专注力 & 正确杯数配对 t 检验"""
import os, json
import numpy as np
from scipy import stats
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial']
plt.rcParams['axes.unicode_minus'] = False

PROFILES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'profiles')
OUT_DIR = os.path.dirname(__file__)

profiles = [f for f in os.listdir(PROFILES_DIR)
            if f.endswith('.json') and '_training' not in f and f != 'default.json']

names, atn1, atn4, cup1, cup4 = [], [], [], [], []
for p in sorted(profiles):
    path = os.path.join(PROFILES_DIR, p)
    data = json.load(open(path, encoding='utf-8'))
    th = data.get('training_history', [])
    if len(th) >= 4:
        s1, s4 = th[0], th[3]
        names.append(p.replace('.json', ''))
        atn1.append(s1.get('avg_attention', 0))
        atn4.append(s4.get('avg_attention', 0))
        cup1.append(s1.get('total_cups', 0) - s1.get('failed_cup_count', 0))
        cup4.append(s4.get('total_cups', 0) - s4.get('failed_cup_count', 0))

atn1 = np.array(atn1); atn4 = np.array(atn4)
cup1 = np.array(cup1); cup4 = np.array(cup4)
n = len(names)

t_a, p_a = stats.ttest_rel(atn1, atn4)
t_c, p_c = stats.ttest_rel(cup1, cup4)

diffs_a = atn4 - atn1
diffs_c = cup4 - cup1

print(f"Players: {n}")
print()
print("=== avg_attention ===")
print(f"  S1: mean={atn1.mean():.1f}  SD={atn1.std(ddof=1):.1f}")
print(f"  S4: mean={atn4.mean():.1f}  SD={atn4.std(ddof=1):.1f}")
print(f"  diff mean={diffs_a.mean():.1f}  SD={diffs_a.std(ddof=1):.1f}")
sig_a = '***' if p_a < 0.001 else ('**' if p_a < 0.01 else ('*' if p_a < 0.05 else 'n.s.'))
print(f"  paired t-test: t={t_a:.4f}, p={p_a:.6f}  {sig_a}")
print()
print("=== correct cups (total_cups - failed_cup_count) ===")
print(f"  S1: mean={cup1.mean():.1f}  SD={cup1.std(ddof=1):.1f}")
print(f"  S4: mean={cup4.mean():.1f}  SD={cup4.std(ddof=1):.1f}")
print(f"  diff mean={diffs_c.mean():.1f}  SD={diffs_c.std(ddof=1):.1f}")
sig_c = '***' if p_c < 0.001 else ('**' if p_c < 0.01 else ('*' if p_c < 0.05 else 'n.s.'))
print(f"  paired t-test: t={t_c:.4f}, p={p_c:.4f}  {sig_c}")

fig, axes = plt.subplots(2, 2, figsize=(14, 10))

ax = axes[0, 0]
means_a = [atn1.mean(), atn4.mean()]
sems_a = [stats.sem(atn1), stats.sem(atn4)]
bars = ax.bar(['第1局', '第4局'], means_a, yerr=sems_a, color=['#4A90D9', '#E8833A'],
              capsize=10, edgecolor='#333', linewidth=1.2)
ax.bar_label(bars, fmt='%.1f', padding=4, fontsize=11)
ax.set_ylabel('avg_attention', fontsize=12)
ax.set_title(f'专注力均值对比 (n={n})\np = {p_a:.5f}', fontsize=13, fontweight='bold')
ax.set_ylim(0, max(means_a) + max(sems_a) + 10)
ax.grid(axis='y', alpha=0.3)

ax = axes[0, 1]
means_c = [cup1.mean(), cup4.mean()]
sems_c = [stats.sem(cup1), stats.sem(cup4)]
bars = ax.bar(['第1局', '第4局'], means_c, yerr=sems_c, color=['#4A90D9', '#E8833A'],
              capsize=10, edgecolor='#333', linewidth=1.2)
ax.bar_label(bars, fmt='%.1f', padding=4, fontsize=11)
ax.set_ylabel('correct_cups', fontsize=12)
ax.set_title(f'正确杯数对比 (n={n})\np = {p_c:.4f} (n.s.)', fontsize=13, fontweight='bold')
ax.set_ylim(0, max(means_c) + max(sems_c) + 6)
ax.grid(axis='y', alpha=0.3)

ax = axes[1, 0]
for i, nm in enumerate(names):
    ax.plot([0, 1], [atn1[i], atn4[i]], 'o-', markersize=6, linewidth=1.2, alpha=0.7,
            color='#2ECC71' if atn4[i] > atn1[i] else '#E74C3C')
ax.set_xticks([0, 1])
ax.set_xticklabels(['第1局', '第4局'])
ax.set_ylabel('avg_attention', fontsize=12)
ax.set_title('个体专注力变化', fontsize=13, fontweight='bold')
ax.grid(axis='y', alpha=0.3)

ax = axes[1, 1]
bp = ax.boxplot([atn1, atn4], labels=['第1局', '第4局'], patch_artist=True,
                widths=0.4, medianprops=dict(color='black', linewidth=2))
bp['boxes'][0].set_facecolor('#4A90D9'); bp['boxes'][0].set_alpha(0.7)
bp['boxes'][1].set_facecolor('#E8833A'); bp['boxes'][1].set_alpha(0.7)
ax.set_ylabel('avg_attention', fontsize=12)
ax.set_title(f'专注力分布对比\np = {p_a:.5f}', fontsize=13, fontweight='bold')
ax.grid(axis='y', alpha=0.3)

plt.tight_layout(pad=2)
out_png = os.path.join(OUT_DIR, 'training_improvement.png')
plt.savefig(out_png, dpi=150, bbox_inches='tight')
plt.close()
print(f"\nChart saved: {out_png}")
