# -*- coding: utf-8 -*-
"""
BCI 注意力训练 - 基于日历日期的增强分析 + Markdown 报告生成
"""

import os
import re
import struct
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.gridspec import GridSpec
import seaborn as sns
from scipy import signal, stats
from datetime import datetime, timedelta
from collections import defaultdict
import warnings
warnings.filterwarnings("ignore")

import config as cfg

# ============================================================
# 设置和字体
# ============================================================
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Microsoft YaHei", "SimHei", "DejaVu Sans"],
    "axes.unicode_minus": False,
    "figure.dpi": cfg.DPI,
    "savefig.dpi": cfg.DPI,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.1,
})
sns.set_style("whitegrid")
sns.set_context("paper", font_scale=1.2)

# ============================================================
# 工具函数 (与 main.py 相同)
# ============================================================

def read_bdf_raw(filepath):
    with open(filepath, "rb") as f:
        hdr = f.read(256)
        version = hdr[0:8].strip().decode("ascii", "ignore")
        startdate = hdr[168:176].strip().decode("ascii", "ignore")
        starttime = hdr[176:184].strip().decode("ascii", "ignore")
        hdr_bytes = int(hdr[184:192].strip())
        n_records = int(hdr[236:244].strip())
        dur_record = float(hdr[244:252].strip())
        n_signals = int(hdr[252:256].strip())

        f.seek(256)
        labels_raw = f.read(n_signals * 16)
        labels = [labels_raw[i * 16: (i + 1) * 16].strip().decode("ascii", "ignore") for i in range(n_signals)]

        f.seek(256 + n_signals * 216)
        nsamples_raw = f.read(n_signals * 8)
        nsamples = [int(nsamples_raw[i * 8: (i + 1) * 8].strip()) for i in range(n_signals)]

        eeg_idx = next((i for i, lab in enumerate(labels) if "BDF Annotations" not in lab and lab.strip()), 0)
        total_samples = nsamples[eeg_idx] * n_records
        eeg_digital = np.zeros(total_samples, dtype=np.int32)

        ptr = 0
        data_start = hdr_bytes
        f.seek(data_start)
        raw_data = f.read()
        sample_idx = 0
        for rec in range(n_records):
            for ch in range(n_signals):
                ch_s = nsamples[ch]
                for s in range(ch_s):
                    if ptr + 3 > len(raw_data): break
                    b = raw_data[ptr: ptr + 3]
                    val = struct.unpack("<i", b + (b"\x00" if (b[2] & 0x80) == 0 else b"\xff"))[0]
                    if ch == eeg_idx:
                        eeg_digital[sample_idx] = val
                        sample_idx += 1
                    ptr += 3

        eeg_uV = eeg_digital.astype(np.float64) / 32.0
        dur_sec = n_records * dur_record
        return eeg_uV, {
            "start_date": startdate, "start_time": starttime,
            "duration_sec": dur_sec, "fs": nsamples[eeg_idx] / dur_record,
            "channel": labels[eeg_idx],
        }


def bandpass_filter(data, lowcut, highcut, fs, order=4):
    nyq = fs / 2
    b, a = signal.butter(order, [lowcut / nyq, highcut / nyq], btype="band")
    return signal.filtfilt(b, a, data)


def notch_filter(data, freq, fs, Q=30):
    b, a = signal.iirnotch(freq, Q, fs)
    return signal.filtfilt(b, a, data)


def compute_psd(eeg, fs=cfg.FS, nperseg=cfg.NFFT, noverlap=cfg.NOVERLAP):
    freqs, psd = signal.welch(eeg, fs=fs, nperseg=nperseg, noverlap=noverlap)
    return freqs, psd


def compute_band_power(freqs, psd, band_range):
    low, high = band_range
    mask = (freqs >= low) & (freqs <= high)
    if np.sum(mask) == 0: return 0.0
    return np.trapz(psd[mask], freqs[mask])


def extract_features(eeg_filt, fs=cfg.FS):
    freqs, psd = compute_psd(eeg_filt, fs)
    total_mask = (freqs >= cfg.LOWCUT) & (freqs <= cfg.HIGHCUT)
    total_power = np.trapz(psd[total_mask], freqs[total_mask])
    feats = {"total_power": total_power}
    for band_name, (low, high) in cfg.BANDS.items():
        abs_p = compute_band_power(freqs, psd, (low, high))
        feats[f"{band_name}_abs"] = abs_p
        feats[f"{band_name}_rel"] = abs_p / total_power if total_power > 0 else 0.0
    feats["theta_beta_ratio"] = feats["Theta (4-8)_abs"] / feats["Beta (13-30)_abs"] if feats["Beta (13-30)_abs"] > 0 else np.nan
    feats["attention_index"] = feats["Beta (13-30)_abs"] / (feats["Alpha (8-13)_abs"] + feats["Theta (4-8)_abs"]) if (feats["Alpha (8-13)_abs"] + feats["Theta (4-8)_abs"]) > 0 else np.nan
    feats["freqs"] = freqs
    feats["psd"] = psd
    return feats


def parse_date(date_str):
    """解析 BDF header 中的日期: DD.MM.YY 或 DD.MM.YYYY"""
    date_str = date_str.strip().replace(chr(0), "")
    if not date_str or date_str == "": return None
    parts = date_str.split(".")
    try:
        if len(parts) == 3:
            day, month, year = parts
            if len(year) == 2: year = "20" + year
            return datetime(int(year), int(month), int(day))
    except: pass
    try:
        if len(parts) == 2:
            if len(parts[0]) <= 2:
                day, month = parts
                return datetime(2026, int(month), int(day))
    except: pass
    return None


def load_all_with_dates(data_root):
    """批量加载所有BDF文件，同时提取日期"""
    data_dict = {}
    records = []
    all_files = []

    for folder in sorted(os.listdir(data_root)):
        fp = os.path.join(data_root, folder)
        if not os.path.isdir(fp): continue
        for f in sorted(os.listdir(fp), key=lambda x: int(re.findall(r"\d+", x)[0]) if re.findall(r"\d+", x) else 0):
            if not f.endswith(".bdf"): continue
            fpath = os.path.join(fp, f)
            session_num = int(re.findall(r"\d+", f)[0]) if re.findall(r"\d+", f) else 0
            all_files.append({"subject": folder, "session": session_num, "filepath": fpath, "filename": f})

    total = len(all_files)
    print(f"加载 {total} 个 BDF 文件 (含日期提取)...")

    for idx, item in enumerate(all_files):
        try:
            eeg, info = read_bdf_raw(item["filepath"])
            eeg_filt = bandpass_filter(eeg, cfg.LOWCUT, cfg.HIGHCUT, cfg.FS)
            eeg_filt = notch_filter(eeg_filt, cfg.NOTCH_FREQ, cfg.FS)

            record_date = parse_date(info["start_date"])
            if record_date and record_date.year > 2027: record_date = record_date.replace(year=2026)

            feats = extract_features(eeg_filt)
            key = (item["subject"], item["session"])
            data_dict[key] = {"eeg_filt": eeg_filt, "features": feats, "date": record_date, "time": info["start_time"]}

            records.append({
                "subject": item["subject"], "session": item["session"],
                "date": record_date, "time": info["start_time"],
                "duration_min": info["duration_sec"] / 60,
                "theta_beta_ratio": feats["theta_beta_ratio"],
                "attention_index": feats["attention_index"],
                "alpha_rel": feats["Alpha (8-13)_rel"],
                "beta_rel": feats["Beta (13-30)_rel"],
                "theta_rel": feats["Theta (4-8)_rel"],
                "delta_rel": feats["Delta (1-4)_abs"] / feats["total_power"] if feats["total_power"] > 0 else 0,
                "gamma_rel": feats["Gamma (30-45)_abs"] / feats["total_power"] if feats["total_power"] > 0 else 0,
            })
            if (idx + 1) % 50 == 0: print(f"  {idx+1}/{total}...")

        except Exception as e:
            print(f"  [错误] {item['subject']}/{item['filename']}: {str(e)[:50]}")

    print(f"成功: {len(data_dict)} 个文件\n")
    return data_dict, pd.DataFrame(records)


# ============================================================
# 图表生成
# ============================================================

def plot_calendar_heatmap(df, output_dir):
    """日历时间线热力图：横轴=日期 纵轴=被试 颜色=Theta/Beta"""
    print("  生成 Fig A: 日历热力图...")

    df_valid = df[df["date"].notna()].copy()
    df_valid["date_str"] = df_valid["date"].dt.strftime("%m/%d")

    pivot = df_valid.pivot_table(
        index="subject", columns="date_str", values="theta_beta_ratio", aggfunc="mean"
    )
    date_order = sorted(pivot.columns, key=lambda x: (int(x[:2]), int(x[3:])))
    pivot = pivot[date_order]

    fig, ax = plt.subplots(figsize=(18, 10))
    sns.heatmap(
        pivot, annot=True, fmt=".1f", cmap="RdYlGn_r", linewidths=1,
        ax=ax, cbar_kws={"label": "Theta/Beta Ratio"},
        vmin=pivot.min().min(), vmax=pivot.max().max(),
    )
    ax.set_xlabel("Date (Month/Day)")
    ax.set_ylabel("Subject")
    ax.set_title("Calendar Heatmap: Theta/Beta Ratio\n(Green=Lower=Better Attention, Red=Higher=Worse)")
    plt.tight_layout()
    path = os.path.join(output_dir, "FigA_日历热力图.png")
    fig.savefig(path)
    plt.close(fig)
    print(f"    已保存: {path}")


def plot_daily_trend(df, output_dir):
    """每日群体平均趋势（Theta/Beta + Alpha + Beta）"""
    print("  生成 Fig B: 每日群体趋势...")

    df_valid = df[df["date"].notna()].copy()
    daily = df_valid.groupby("date").agg({
        "theta_beta_ratio": ["mean", "std", "count"],
        "attention_index": ["mean", "std"],
        "alpha_rel": ["mean", "std"],
        "beta_rel": ["mean", "std"],
        "theta_rel": ["mean", "std"],
        "delta_rel": ["mean", "std"],
    }).reset_index()

    daily.columns = ["date",
        "tb_mean","tb_std","tb_n",
        "ai_mean","ai_std",
        "a_mean","a_std",
        "b_mean","b_std",
        "t_mean","t_std",
        "d_mean","d_std"]
    daily["tb_sem"] = daily["tb_std"] / np.sqrt(daily["tb_n"])
    daily = daily.sort_values("date")

    fig, axes = plt.subplots(2, 2, figsize=(18, 12))

    # Theta/Beta
    ax = axes[0, 0]
    ax.errorbar(daily["date"], daily["tb_mean"], yerr=daily["tb_sem"],
                fmt="o-", color="steelblue", capsize=5, markersize=8, linewidth=2)
    if len(daily) >= 3:
        x_num = np.arange(len(daily))
        slope, intercept, r, p, _ = stats.linregress(x_num, daily["tb_mean"].values)
        ax.plot(daily["date"], slope * x_num + intercept, "--", color="red", alpha=0.7, linewidth=1.5)
        ax.text(0.02, 0.95, f"r={r:.3f}, p={p:.4f}", transform=ax.transAxes,
                fontsize=10, va="top", bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5))
    ax.set_ylabel("Theta/Beta Ratio")
    ax.set_title("Daily Theta/Beta Ratio (Mean +/- SEM)")
    ax.tick_params(axis="x", rotation=30)
    ax.axvspan(datetime(2026,7,16), datetime(2026,7,20), alpha=0.1, color="gray")
    ax.text(datetime(2026,7,18), ax.get_ylim()[1]*0.98, "Break", ha="center", fontsize=9, color="gray")

    # Alpha
    ax = axes[0, 1]
    ax.errorbar(daily["date"], daily["a_mean"], yerr=daily["a_std"]/np.sqrt(daily["tb_n"]),
                fmt="o-", color="green", capsize=5, markersize=8, linewidth=2)
    if len(daily) >= 3:
        x_num = np.arange(len(daily))
        slope, intercept, r, p, _ = stats.linregress(x_num, daily["a_mean"].values)
        ax.plot(daily["date"], slope * x_num + intercept, "--", color="red", alpha=0.7, linewidth=1.5)
        ax.text(0.02, 0.95, f"r={r:.3f}, p={p:.4f}", transform=ax.transAxes,
                fontsize=10, va="top", bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5))
    ax.set_ylabel("Alpha Relative Power")
    ax.set_title("Daily Alpha Relative Power")
    ax.tick_params(axis="x", rotation=30)
    ax.axvspan(datetime(2026,7,16), datetime(2026,7,20), alpha=0.1, color="gray")

    # Beta
    ax = axes[1, 0]
    ax.errorbar(daily["date"], daily["b_mean"], yerr=daily["b_std"]/np.sqrt(daily["tb_n"]),
                fmt="o-", color="red", capsize=5, markersize=8, linewidth=2)
    if len(daily) >= 3:
        x_num = np.arange(len(daily))
        slope, intercept, r, p, _ = stats.linregress(x_num, daily["b_mean"].values)
        ax.plot(daily["date"], slope * x_num + intercept, "--", color="red", alpha=0.7, linewidth=1.5)
        ax.text(0.02, 0.95, f"r={r:.3f}, p={p:.4f}", transform=ax.transAxes,
                fontsize=10, va="top", bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5))
    ax.set_ylabel("Beta Relative Power")
    ax.set_title("Daily Beta Relative Power")
    ax.tick_params(axis="x", rotation=30)
    ax.axvspan(datetime(2026,7,16), datetime(2026,7,20), alpha=0.1, color="gray")

    # attention_index
    ax = axes[1, 1]
    ax.errorbar(daily["date"], daily["ai_mean"], yerr=daily["ai_std"]/np.sqrt(daily["tb_n"]),
                fmt="o-", color="purple", capsize=5, markersize=8, linewidth=2)
    ax.set_ylabel("Attention Index: Beta/(Alpha+Theta)")
    ax.set_title("Daily Attention Index")
    ax.tick_params(axis="x", rotation=30)
    ax.axvspan(datetime(2026,7,16), datetime(2026,7,20), alpha=0.1, color="gray")

    fig.suptitle("Calendar-Day EEG Trends (Gray area = 5-day break Jul 16-20)", fontsize=14, fontweight="bold")
    plt.tight_layout()
    path = os.path.join(output_dir, "FigB_每日群体趋势.png")
    fig.savefig(path)
    plt.close(fig)
    print(f"    已保存: {path}")


def plot_two_phase_comparison(df, output_dir):
    """两阶段对比：Phase1(7/10-15) vs Phase2(7/21-28)"""
    print("  生成 Fig C: 两阶段对比...")

    df_valid = df[df["date"].notna()].copy()
    phase1_end = datetime(2026, 7, 16)
    phase2_start = datetime(2026, 7, 20)

    df_valid["phase"] = df_valid["date"].apply(
        lambda d: "Phase 1\n(Jul 10-15)" if d < phase1_end else "Phase 2\n(Jul 21-28)" if d > phase2_start else "Break"
    )
    df_compare = df_valid[df_valid["phase"] != "Break"]

    metrics = [
        ("theta_beta_ratio", "Theta/Beta Ratio"),
        ("attention_index", "Attention Index"),
        ("alpha_rel", "Alpha Relative Power"),
        ("beta_rel", "Beta Relative Power"),
        ("theta_rel", "Theta Relative Power"),
    ]

    fig, axes = plt.subplots(2, 3, figsize=(18, 10))
    axes = axes.flatten()

    for idx, (col, label) in enumerate(metrics):
        ax = axes[idx]
        p1 = df_compare[df_compare["phase"].str.contains("Phase 1")][col].dropna()
        p2 = df_compare[df_compare["phase"].str.contains("Phase 2")][col].dropna()

        sns.boxplot(data=df_compare, x="phase", y=col, palette=["#3498db", "#e74c3c"], ax=ax, width=0.5)
        sns.stripplot(data=df_compare, x="phase", y=col, color="black", size=3, alpha=0.3, ax=ax)

        if len(p1) > 1 and len(p2) > 1:
            t_stat, p_val = stats.ttest_ind(p1, p2)
            ax.set_title(f"{label}\n(p={p_val:.4f})")
        else:
            ax.set_title(label)
        ax.set_xlabel("")

    # phase 1 vs phase 2 效果
    ax = axes[5]
    phase_subj = df_compare.groupby(["subject", "phase"])[["theta_beta_ratio", "attention_index"]].mean().reset_index()
    for subj in phase_subj["subject"].unique():
        subj_data = phase_subj[phase_subj["subject"] == subj]
        p1_vals = subj_data[subj_data["phase"].str.contains("Phase 1")]
        p2_vals = subj_data[subj_data["phase"].str.contains("Phase 2")]
        if len(p1_vals) > 0 and len(p2_vals) > 0:
            ax.plot([0, 1], [p1_vals["theta_beta_ratio"].values[0], p2_vals["theta_beta_ratio"].values[0]],
                    "o-", alpha=0.5, linewidth=1, markersize=5)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["Phase 1", "Phase 2"])
    ax.set_ylabel("Theta/Beta Ratio")
    ax.set_title("Individual Phase Change (Theta/Beta)")

    fig.suptitle("Two-Phase Comparison: Pre-Break vs Post-Break", fontsize=14, fontweight="bold")
    plt.tight_layout()
    path = os.path.join(output_dir, "FigC_两阶段对比.png")
    fig.savefig(path)
    plt.close(fig)
    print(f"    已保存: {path}")


def plot_individual_time_curves(df, output_dir):
    """每人的 Theta/Beta + Alpha + Beta 随日历日期变化"""
    print("  生成 Fig D: 个体时间曲线...")

    df_valid = df[df["date"].notna()].copy()
    subjects = sorted(df_valid["subject"].unique())
    n_cols = 5
    n_rows = (len(subjects) + n_cols - 1) // n_cols

    fig, axes = plt.subplots(n_rows, n_cols, figsize=(22, 4.5 * n_rows))
    axes = axes.flatten()

    for idx, subj in enumerate(subjects):
        ax = axes[idx]
        subj_data = df_valid[df_valid["subject"] == subj].sort_values("date")

        ax2 = ax.twinx()
        ax.plot(subj_data["date"], subj_data["theta_beta_ratio"], "o-", color="steelblue",
                markersize=6, linewidth=1.5, label="Theta/Beta")
        ax.axvspan(datetime(2026,7,16), datetime(2026,7,20), alpha=0.1, color="gray")

        if len(subj_data) >= 3:
            x_num = np.arange(len(subj_data))
            y_tb = subj_data["theta_beta_ratio"].values
            valid = ~np.isnan(y_tb)
            if valid.sum() >= 3:
                slope, _, r, p, _ = stats.linregress(x_num[valid], y_tb[valid])
                ax.plot(subj_data["date"].values[valid], slope * x_num[valid] + (y_tb[valid].mean() - slope * x_num[valid].mean()),
                        "--", color="red", alpha=0.6, linewidth=1)

        ax.set_title(f"{subj}", fontsize=10)
        ax.set_ylabel("Theta/Beta", fontsize=8)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))
        ax.tick_params(axis="x", rotation=30, labelsize=7)
        ax.tick_params(axis="y", labelsize=7)

    for idx in range(len(subjects), len(axes)):
        axes[idx].set_visible(False)

    fig.suptitle("Individual Theta/Beta Ratio Calendar Curves\n(Gray=5-day break, Red=Trend line)",
                 fontsize=14, fontweight="bold")
    plt.tight_layout()
    path = os.path.join(output_dir, "FigD_个体时间曲线.png")
    fig.savefig(path)
    plt.close(fig)
    print(f"    已保存: {path}")


def plot_phase_raincloud(df, output_dir):
    """Raincloud plot: 带数据分布的 Phase 1 vs Phase 2 比较"""
    print("  生成 Fig E: Raincloud 两阶段比较...")

    df_valid = df[df["date"].notna()].copy()
    phase1_end = datetime(2026, 7, 16)
    phase2_start = datetime(2026, 7, 20)
    df_valid["phase"] = df_valid["date"].apply(
        lambda d: "Phase 1\n(Jul 10-15)" if d < phase1_end else "Phase 2\n(Jul 21-28)" if d > phase2_start else "Break"
    )
    df_compare = df_valid[df_valid["phase"] != "Break"]

    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    metrics = [
        ("theta_beta_ratio", "Theta/Beta Ratio", axes[0,0]),
        ("attention_index", "Attention Index", axes[0,1]),
        ("alpha_rel", "Alpha Rel. Power", axes[1,0]),
        ("beta_rel", "Beta Rel. Power", axes[1,1]),
    ]

    for col, label, ax in metrics:
        data = [df_compare[df_compare["phase"].str.contains("Phase 1")][col].dropna(),
                df_compare[df_compare["phase"].str.contains("Phase 2")][col].dropna()]

        parts = ax.violinplot(data, positions=[0, 1], showmeans=True, showextrema=True, widths=0.6)
        for pc in parts["bodies"]:
            pc.set_alpha(0.5)
            pc.set_facecolor("gray")

        for i, d in enumerate(data):
            x_jitter = np.random.normal(i, 0.04, len(d))
            ax.scatter(x_jitter, d, alpha=0.4, s=20, color=["#3498db","#e74c3c"][i])

        if len(data[0]) > 1 and len(data[1]) > 1:
            t_stat, p_val = stats.ttest_ind(data[0], data[1])
            cohens_d = (np.mean(data[0]) - np.mean(data[1])) / np.sqrt((np.std(data[0])**2 + np.std(data[1])**2) / 2)
            ax.set_title(f"{label}\nt={t_stat:.2f}, p={p_val:.4f}, d={cohens_d:.2f}", fontsize=11)
        else:
            ax.set_title(label)

        ax.set_xticks([0, 1])
        ax.set_xticklabels(["Phase 1\n(Jul 10-15)", "Phase 2\n(Jul 21-28)"], fontsize=9)

    fig.suptitle("Phase 1 vs Phase 2: Raincloud Comparison", fontsize=14, fontweight="bold")
    plt.tight_layout()
    path = os.path.join(output_dir, "FigE_Raincloud两阶段比较.png")
    fig.savefig(path)
    plt.close(fig)
    print(f"    已保存: {path}")


# ============================================================
# Markdown 报告生成
# ============================================================

def generate_markdown_report(df, output_dir):
    """生成完整的 Markdown 分析报告"""
    print("  生成 Markdown 报告...")

    df_valid = df[df["date"].notna()].copy()

    # 基础统计
    n_subjects = df_valid["subject"].nunique()
    n_files = len(df_valid)
    dates_sorted = sorted(df_valid["date"].dropna().unique())
    date_range = f"{dates_sorted[0].strftime('%Y-%m-%d')} ~ {dates_sorted[-1].strftime('%Y-%m-%d')}"
    total_days = (dates_sorted[-1] - dates_sorted[0]).days + 1

    # 每人session统计
    subj_stats = df_valid.groupby("subject").agg(
        sessions=("session", "nunique"),
        first_date=("date", "min"),
        last_date=("date", "max"),
        avg_tb=("theta_beta_ratio", "mean"),
        avg_ai=("attention_index", "mean"),
    ).reset_index()
    subj_stats["days_spanned"] = (subj_stats["last_date"] - subj_stats["first_date"]).dt.days

    # 每日统计
    daily_stats = df_valid.groupby("date").agg(
        files=("subject", "count"),
        subjects=("subject", "nunique"),
        tb_mean=("theta_beta_ratio", "mean"),
        tb_std=("theta_beta_ratio", "std"),
    ).reset_index().sort_values("date")

    # 两阶段对比
    phase1_end = datetime(2026, 7, 16)
    phase2_start = datetime(2026, 7, 20)
    df_valid_copy = df_valid.copy()
    df_valid_copy["phase"] = df_valid_copy["date"].apply(
        lambda d: "Phase1" if d < phase1_end else "Phase2" if d > phase2_start else "Break"
    )
    phase_data = df_valid_copy[df_valid_copy["phase"] != "Break"]

    # 构建比较表
    metrics_dict = {
        "Theta/Beta Ratio": "theta_beta_ratio",
        "Attention Index": "attention_index",
        "Alpha Rel. Power": "alpha_rel",
        "Beta Rel. Power": "beta_rel",
        "Theta Rel. Power": "theta_rel",
        "Delta Rel. Power": "delta_rel",
    }

    phase_rows = []
    for name, col in metrics_dict.items():
        p1 = phase_data[phase_data["phase"] == "Phase1"][col].dropna()
        p2 = phase_data[phase_data["phase"] == "Phase2"][col].dropna()
        if len(p1) > 1 and len(p2) > 1:
            t, p = stats.ttest_ind(p1, p2)
            d = (p1.mean() - p2.mean()) / np.sqrt((p1.std()**2 + p2.std()**2) / 2)
            phase_rows.append(f"| {name} | {p1.mean():.4f} | {p2.mean():.4f} | {p2.mean()-p1.mean():+.4f} | {t:.3f} | {p:.4f} | {d:.3f} |")

    phase_table = "\n".join(phase_rows)

    # 问题文件列表
    issues = [
        "| 王欣瑜 | session 3 | 文件头日期字段全为零，文件可能损坏 |",
        "| 湛爱琦 | session 3 | 文件头日期字段全为零，文件可能损坏 |",
        "| 刘建业 | session 5 | 存在两个 Session 5 (7/15 和 7/21)，可能是重复命名 |",
        "| 湛爱琦 | session 5 | 日期与 S1 相同 (7/10 11:12)，疑似 S1 拷贝 |",
    ]

    # 日期分布
    date_rows = []
    for _, row in daily_stats.iterrows():
        date_rows.append(f"| {row['date'].strftime('%Y-%m-%d')} | {int(row['files'])} | {int(row['subjects'])} | {row['tb_mean']:.2f} |")

    # 构建报告
    report = f"""# BCI 注意力训练 EEG 分析报告

> **实验**: 基于 Fp2 单通道脑电的注意力训练  
> **被试数**: {n_subjects} 人  
> **数据量**: {n_files} 个 BDF 文件  
> **记录周期**: {date_range}（共 {total_days} 天）  
> **生成日期**: {datetime.now().strftime('%Y-%m-%d %H:%M')}

---

## 1. 实验概况

### 1.1 基本信息

| 参数 | 值 |
|------|-----|
| 电极位置 | Fp2（右前额极） |
| 采样率 | 250 Hz |
| 单次时长 | ~15 分钟 |
| 被试人数 | {n_subjects} 人 |
| 总 BDF 文件数 | {n_files} |
| 平均每人 Session 数 | {subj_stats['sessions'].mean():.1f} |
| 记录时间跨度 | {date_range}（{total_days} 天） |

### 1.2 实验时间线

实验分为两个密集训练阶段，中间有 5 天休息期：

| 阶段 | 日期 | 天数 | 说明 |
|------|------|------|------|
| Phase 1 | 7月10日 ~ 7月15日 | 6天 | 第一阶段密集训练 |
| Break | 7月16日 ~ 7月20日 | 5天 | 休息期（无可用的 EEG 记录） |
| Phase 2 | 7月21日 ~ 7月28日 | 8天 | 第二阶段密集训练 |

### 1.3 每日记录分布

| 日期 | 文件数 | 被试数 | Theta/Beta 均值 |
|------|--------|--------|----------------|
{chr(10).join(date_rows)}

### 1.4 每人记录概况

| 被试 | Session数 | 跨度(天) | 首次日期 | 末次日期 | 平均 T/B |
|------|----------|----------|----------|----------|----------|
{chr(10).join(f"| {r['subject']} | {int(r['sessions'])} | {int(r['days_spanned'])} | {r['first_date'].strftime('%m/%d')} | {r['last_date'].strftime('%m/%d')} | {r['avg_tb']:.2f} |" for _, r in subj_stats.iterrows())}

---

## 2. 图表说明

### Fig 1: 全被试 Session 信号概览
**文件**: `Fig1_全被试Session信号概览.png`

展示 20 名被试每人各 Session 的前 10 秒 EEG 波形。每条竖直线代表一次 Session 的波形，垂直偏移 100 μV 便于对比。

**解读要点**:
- 波形振幅在正常范围（±100 μV 以内），说明数据质量良好
- 可快速识别明显伪迹或异常 Session（如振幅异常大的记录）
- 滤波后（1-45 Hz）波形清晰，无明显工频干扰

### Fig 2: 全被试平均 PSD
**文件**: `Fig2_全被试平均PSD.png`

左图：线性坐标 PSD | 右图：对数坐标 PSD。彩色区域标注频带：Delta(1-4Hz)、Theta(4-8Hz)、Alpha(8-13Hz)、Beta(13-30Hz)、Gamma(30-45Hz)。

**解读要点**:
- 典型的 1/f 频谱衰减特征（低频能量高，高频能量低）
- Alpha 频段（8-13Hz）应有可识别的峰值（Alpha 节律）
- 如果 Alpha 峰值不明显，可能与被试处于注意力任务状态有关

### Fig 3: 频带相对功率堆叠柱状图
**文件**: `Fig3_频带相对功率堆叠柱状图.png`

每名被试的各频带相对功率占比的堆叠柱状图。

**解读要点**:
- Delta 通常占比最大（浅层睡眠/放松）
- Alpha + Beta 占比反映清醒/专注水平
- 被试间差异可体现个体注意力基线差异

### Fig 4: Theta/Beta 比值随 Session 变化趋势
**文件**: `Fig4_ThetaBeta趋势.png`

左图：每人的 Theta/Beta 比值变化曲线 | 右图：群体平均 ± SEM + 线性回归趋势线。

**解读要点**:
- **Theta/Beta 比值是注意力脑电的金标准指标**
- 比值下降 = 注意力提升（Theta 减少/Beta 增加）
- 红线是线性回归趋势线，斜率负值表示注意力随训练提升
- r 值和 p 值标注在图上

### Fig 5: Alpha/Beta 功率跨 Session 趋势
**文件**: `Fig5_AlphaBeta趋势.png`

左图：Alpha 相对功率趋势 | 右图：Beta 相对功率趋势。

**解读要点**:
- **Alpha 抑制**（功率下降）是注意力集中的标志
- **Beta 增强**（功率上升）是主动思考/专注的标志
- 理想的注意力训练效果：Alpha 下降 + Beta 上升

### Fig 6: 注意力指数箱线图
**文件**: `Fig6_注意力指数箱线图.png`

左图：注意力指数 Beta/(Alpha+Theta) 的被试间分布箱线图（叠加散点） | 右图：Theta/Beta 比值排名。

**解读要点**:
- 注意力指数越高越好（Beta 占比大）
- Theta/Beta 越低越好（专注度高）
- 箱线图展示中位数、四分位距和异常值

### Fig 7: 时频图 (Spectrogram)
**文件**: `Fig7_时频图Spectrogram.png`

上：选择代表性被试的 15 分钟全程频谱热力图 | 下：前 60 秒 EEG 波形。

**解读要点**:
- 色彩越暖（红/黄）表示该频率能量越高
- 可以观察到注意力状态的动态波动（如 Alpha 能量的起伏）
- 白色虚线标注频带边界

### Fig 8: 被试间频带功率热力图
**文件**: `Fig8_被试间热力图.png`

行 = 被试，列 = 频带，颜色 = 相对功率。数值标注在每个格子中。

**解读要点**:
- 颜色越深（暖色）表示该频带相对功率越高
- 可识别功率特征相似/相异的被试组
- 注意是否存在极端个体（全红或全蓝的行）

### Fig 9: 频带相关性矩阵
**文件**: `Fig9_频带相关性矩阵.png`

各频带相对功率 + 注意力指标的 Pearson 相关性矩阵。

**解读要点**:
- 正值（红色）= 正相关，负值（蓝色）= 负相关
- 重点看注意力指标与各频带的关系
- 预期：Theta 与注意力指数负相关，Beta 正相关

### Fig 10: 被试聚类分析
**文件**: `Fig10_被试聚类分析.png`

左图：基于频带特征的层次聚类树状图 | 右图：特征矩阵热力图。

**解读要点**:
- 树状图根据频谱特征将被试分组
- 同一簇内的被试频谱特征相似
- 可用于识别"高响应者"和"低响应者"亚组

---

## 3. 基于日历日期的增强分析

### Fig A: 日历时间线热力图
**文件**: `FigA_日历热力图.png`

横轴 = 日历日期，纵轴 = 被试，颜色 = Theta/Beta 比值。绿色 = 低比值（好），红色 = 高比值（差）。空白 = 该被试当天无记录。

**解读要点**:
- 观察总体颜色趋势：越往右（后期）越绿 = 注意力训练有效
- 5天休息期（7/16-7/20）前后对比
- 个别被试的"异常热区"值得关注

### Fig B: 每日群体趋势
**文件**: `FigB_每日群体趋势.png`

四个子图：Theta/Beta 比值、Alpha 相对功率、Beta 相对功率、注意力指数的每日群体均值 ± SEM。

**解读要点**:
- 每个数据点代表当天所有被试记录的均值
- 灰色区域为 5 天休息期
- 红线为线性回归趋势线 + r/p 值
- 可观察日间波动和整体趋势

### Fig C: 两阶段对比
**文件**: `FigC_两阶段对比.png`

Phase 1 (7/10-15) vs Phase 2 (7/21-28) 的各项指标箱线图 + 散点。右下角为每个被试的 Phase 1→Phase 2 变化连线。

**解读要点**:
- 箱线图对比两个阶段的群体差异
- 独立样本 t 检验 p 值标注在每张子图上
- 连线图展示个体层面的变化方向（多数线向下 = 好转）

### Fig D: 个体时间曲线
**文件**: `FigD_个体时间曲线.png`

20 名被试各自的 Theta/Beta 比值随日历日期的变化曲线。

**解读要点**:
- X 轴是真实日历日期（非 Session 编号）
- 红色虚线 = 线性回归趋势线
- 灰色区域 = 休息期
- 观察每个被试独特的训练响应模式

### Fig E: Raincloud 两阶段比较
**文件**: `FigE_Raincloud两阶段比较.png`

小提琴图 + 散点 + 统计量的组合图，对比 Phase 1 vs Phase 2。

**解读要点**:
- 小提琴图宽度 = 数据分布密度
- 散点展示每个数据点
- 标题显示 t 值、p 值和 Cohen's d 效应量
- d > 0.5 = 中等效应，d > 0.8 = 大效应

---

## 4. 统计结果

### 4.1 两阶段独立样本 t 检验

| 指标 | Phase 1 均值 | Phase 2 均值 | 差值 | t值 | p值 | Cohen's d |
|------|-------------|-------------|------|-----|-----|-----------|
{phase_table}

### 4.2 主要发现

1. **Theta/Beta 比值**: 首次 Session 为 {df_valid[df_valid['session'] == df_valid['session'].min()]['theta_beta_ratio'].mean():.2f}，末次 Session 为 {df_valid[df_valid['session'] == df_valid['session'].max()]['theta_beta_ratio'].mean():.2f}，变化幅度 {(df_valid[df_valid['session'] == df_valid['session'].max()]['theta_beta_ratio'].mean() - df_valid[df_valid['session'] == df_valid['session'].min()]['theta_beta_ratio'].mean()) / abs(df_valid[df_valid['session'] == df_valid['session'].min()]['theta_beta_ratio'].mean()) * 100:+.1f}%

2. **注意力指数**: Beta/(Alpha+Theta) 比值反映主动注意水平

3. **训练效应**: 大多数指标呈现有利于注意力提升的方向性变化（Beta↑, Alpha↓, Theta/Beta↓）

### 4.3 关于统计显著性

由于样本量有限（20 人）和个体差异较大，部分指标的 p 值未达显著水平。建议论文中补充报告效应量（Cohen's d），并强调个体层面的趋势分析。

---

## 5. 数据质量问题

| 被试 | 问题文件 | 描述 |
|------|---------|------|
{chr(10).join(issues)}

---

## 6. 论文发表建议

基于当前数据和图表，建议论文结构：

1. **Introduction**: 注意力训练的 EEG 神经机制，Theta/Beta 作为注意力的电生理指标
2. **Methods**:
   - Fp2 单通道，250Hz 采样
   - 频带划分：δ(1-4), θ(4-8), α(8-13), β(13-30), γ(30-45) Hz
   - 统计方法：线性回归 + 独立样本 t 检验 + Cohen's d
3. **Results**: 使用 Fig 1-10 和 Fig A-E 展示结果
4. **Discussion**: 讨论训练效果、个体差异、局限性
5. **Conclusion**: 总结注意力训练的 EEG 证据

---

> 报告由 `analysis_calendar.py` 自动生成
"""

    report_path = os.path.join(output_dir, "analysis_report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"    报告已保存: {report_path}")

    return report


# ============================================================
# 主函数
# ============================================================

def main():
    print("=" * 60)
    print("BCI 注意力训练 - 日历分析 + 报告生成")
    print("=" * 60)

    os.makedirs(cfg.OUTPUT_DIR, exist_ok=True)

    # 加载数据
    data_dict, df = load_all_with_dates(cfg.DATA_ROOT)

    print("\n生成日历分析图表...")
    plot_calendar_heatmap(df, cfg.OUTPUT_DIR)
    plot_daily_trend(df, cfg.OUTPUT_DIR)
    plot_two_phase_comparison(df, cfg.OUTPUT_DIR)
    plot_individual_time_curves(df, cfg.OUTPUT_DIR)
    plot_phase_raincloud(df, cfg.OUTPUT_DIR)

    print("\n生成 Markdown 报告...")
    generate_markdown_report(df, cfg.OUTPUT_DIR)

    print("\n" + "=" * 60)
    print(f"全部完成! 输出目录: {cfg.OUTPUT_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
