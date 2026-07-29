# -*- coding: utf-8 -*-
"""
BCI 注意力训练 EEG 分析 - 完整分析脚本
生成 10 张论文级图表 + 统计报告
"""

import os
import re
import warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
import seaborn as sns
from scipy import signal, stats
from scipy.ndimage import gaussian_filter1d
from collections import defaultdict

warnings.filterwarnings("ignore")

import config as cfg

# ============================================================
#  第一部分：设置中文字体和样式
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
sns.set_context("paper", font_scale=1.3)

# ============================================================
#  第二部分：BDF 读取（纯 Python，不依赖 mne）
# ============================================================

def read_bdf_raw(filepath):
    """
    纯 Python 读取 BioSemi BDF 文件，返回 EEG (Fp2) 数据 (uV)。
    BioSemi 24-bit: 1 LSB = 1/32 uV = 31.25 nV
    """
    import struct

    with open(filepath, "rb") as f:
        hdr = f.read(256)

        version = hdr[0:8].strip().decode("ascii", "ignore")
        if "BIOSEMI" not in version and "24BIT" not in version:
            version = hdr[0:8].strip().decode("ascii", "ignore")

        startdate = hdr[168:176].strip().decode("ascii", "ignore")
        starttime = hdr[176:184].strip().decode("ascii", "ignore")
        hdr_bytes = int(hdr[184:192].strip())
        n_records = int(hdr[236:244].strip())
        dur_record = float(hdr[244:252].strip())
        n_signals = int(hdr[252:256].strip())

        f.seek(256)
        labels_raw = f.read(n_signals * 16)
        labels = [
            labels_raw[i * 16 : (i + 1) * 16]
            .strip()
            .decode("ascii", "ignore")
            for i in range(n_signals)
        ]

        f.seek(256 + n_signals * 216)
        nsamples_raw = f.read(n_signals * 8)
        nsamples = [
            int(nsamples_raw[i * 8 : (i + 1) * 8].strip())
            for i in range(n_signals)
        ]

        eeg_idx = next(
            (
                i
                for i, lab in enumerate(labels)
                if "BDF Annotations" not in lab and lab.strip()
            ),
            0,
        )

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
                    if ptr + 3 > len(raw_data):
                        break
                    b = raw_data[ptr : ptr + 3]
                    val = struct.unpack(
                        "<i",
                        b + (b"\x00" if (b[2] & 0x80) == 0 else b"\xff"),
                    )[0]
                    if ch == eeg_idx:
                        eeg_digital[sample_idx] = val
                        sample_idx += 1
                    ptr += 3

        eeg_uV = eeg_digital.astype(np.float64) / 32.0

        dur_sec = n_records * dur_record
        t = np.linspace(0, dur_sec, len(eeg_uV), endpoint=False)

        info = {
            "subject": "",
            "session": 0,
            "filepath": filepath,
            "start_date": startdate,
            "start_time": starttime,
            "duration_sec": dur_sec,
            "n_samples": len(eeg_uV),
            "fs": nsamples[eeg_idx] / dur_record,
            "channel": labels[eeg_idx],
            "n_channels": n_signals,
        }
        return t, eeg_uV, info


# ============================================================
#  第三部分：数据加载
# ============================================================

def collect_all_files(data_root):
    """扫描所有被试文件夹，收集 BDF 文件路径"""
    all_files = []
    for folder in sorted(os.listdir(data_root)):
        folder_path = os.path.join(data_root, folder)
        if not os.path.isdir(folder_path):
            continue
        bdf_files = sorted(
            [f for f in os.listdir(folder_path) if f.endswith(".bdf")],
            key=lambda x: int(re.findall(r"\d+", x)[0])
            if re.findall(r"\d+", x)
            else 0,
        )
        for bf in bdf_files:
            session_num = int(re.findall(r"\d+", bf)[0]) if re.findall(r"\d+", bf) else 0
            all_files.append(
                {
                    "subject": folder,
                    "session": session_num,
                    "filepath": os.path.join(folder_path, bf),
                }
            )
    return pd.DataFrame(all_files)


def load_all_data(df_files):
    """批量加载所有 BDF 文件，返回数据字典和汇总 DataFrame"""
    data_dict = {}
    records = []

    total = len(df_files)
    print(f"正在加载 {total} 个 BDF 文件...")

    for idx, row in enumerate(df_files.itertuples()):
        try:
            t, eeg, info = read_bdf_raw(row.filepath)
            info["subject"] = row.subject
            info["session"] = row.session

            eeg_filt = bandpass_filter(eeg, cfg.LOWCUT, cfg.HIGHCUT, cfg.FS)
            eeg_filt = notch_filter(eeg_filt, cfg.NOTCH_FREQ, cfg.FS)

            key = (row.subject, row.session)
            data_dict[key] = {"t": t, "eeg_raw": eeg, "eeg_filt": eeg_filt, "info": info}

            records.append(
                {
                    "subject": row.subject,
                    "session": row.session,
                    "duration_min": info["duration_sec"] / 60,
                    "n_samples": info["n_samples"],
                    "mean_uV": float(np.mean(eeg_filt)),
                    "std_uV": float(np.std(eeg_filt)),
                    "max_uV": float(np.max(np.abs(eeg_filt))),
                }
            )

            if (idx + 1) % 20 == 0:
                print(f"  {idx+1}/{total} 完成...")

        except Exception as e:
            print(f"  [错误] {row.subject}/session{row.session}: {e}")

    print(f"加载完成: 成功 {len(data_dict)} 个文件")
    return data_dict, pd.DataFrame(records)


# ============================================================
#  第四部分：预处理
# ============================================================

def bandpass_filter(data, lowcut, highcut, fs, order=4):
    """Butterworth 带通滤波"""
    nyq = fs / 2
    b, a = signal.butter(order, [lowcut / nyq, highcut / nyq], btype="band")
    return signal.filtfilt(b, a, data)


def notch_filter(data, freq, fs, Q=30):
    """陷波滤波器"""
    b, a = signal.iirnotch(freq, Q, fs)
    return signal.filtfilt(b, a, data)


# ============================================================
#  第五部分：特征提取
# ============================================================

def compute_psd(eeg, fs=cfg.FS, nperseg=cfg.NFFT, noverlap=cfg.NOVERLAP):
    """Welch 方法计算 PSD"""
    freqs, psd = signal.welch(eeg, fs=fs, nperseg=nperseg, noverlap=noverlap)
    return freqs, psd


def compute_band_power(freqs, psd, band_range):
    """计算指定频带的绝对功率 (积分)"""
    low, high = band_range
    mask = (freqs >= low) & (freqs <= high)
    if np.sum(mask) == 0:
        return 0.0
    return np.trapz(psd[mask], freqs[mask])


def compute_band_power_relative(freqs, psd, band_range, total_power):
    """计算相对功率 (归一化到总功率)"""
    abs_power = compute_band_power(freqs, psd, band_range)
    return abs_power / total_power if total_power > 0 else 0.0


def extract_features(eeg_filt, fs=cfg.FS):
    """从一段 EEG 数据提取所有频带特征"""
    freqs, psd = compute_psd(eeg_filt, fs)

    total_mask = (freqs >= cfg.LOWCUT) & (freqs <= cfg.HIGHCUT)
    total_power = np.trapz(psd[total_mask], freqs[total_mask])

    features = {}
    features["total_power"] = total_power

    for band_name, (low, high) in cfg.BANDS.items():
        abs_p = compute_band_power(freqs, psd, (low, high))
        rel_p = abs_p / total_power if total_power > 0 else 0.0
        features[f"{band_name}_abs"] = abs_p
        features[f"{band_name}_rel"] = rel_p

    features["theta_beta_ratio"] = (
        features["Theta (4-8)_abs"] / features["Beta (13-30)_abs"]
        if features["Beta (13-30)_abs"] > 0
        else np.nan
    )
    features["alpha_beta_ratio"] = (
        features["Alpha (8-13)_abs"] / features["Beta (13-30)_abs"]
        if features["Beta (13-30)_abs"] > 0
        else np.nan
    )
    features["attention_index"] = (
        features["Beta (13-30)_abs"]
        / (features["Alpha (8-13)_abs"] + features["Theta (4-8)_abs"])
        if (features["Alpha (8-13)_abs"] + features["Theta (4-8)_abs"]) > 0
        else np.nan
    )
    features["freqs"] = freqs
    features["psd"] = psd

    return features


def extract_all_features(data_dict):
    """对所有被试提取特征"""
    feature_list = []
    psd_collection = defaultdict(list)

    print("\n正在提取特征...")
    for (subject, session), d in data_dict.items():
        feats = extract_features(d["eeg_filt"])
        feats["subject"] = subject
        feats["session"] = session
        feature_list.append(feats)
        psd_collection[subject].append((feats["freqs"], feats["psd"]))

    df_features = pd.DataFrame(feature_list)
    df_features = df_features.drop(columns=["freqs", "psd"], errors="ignore")
    print(f"特征提取完成: {len(df_features)} 条记录")

    return df_features, psd_collection


# ============================================================
#  第六部分：可视化 - 图1：单个被试跨Session信号总览
# ============================================================

def fig1_all_subject_session_overview(data_dict, df_features, output_dir):
    """图1：全体被试 - 每个Session的30秒波形片段 + 柱状图"""
    print("    生成 Fig 1: 全被试 Session 概览...")

    subjects = sorted(df_features["subject"].unique())
    n_cols = 5
    n_rows = (len(subjects) + n_cols - 1) // n_cols

    fig, axes = plt.subplots(n_rows, n_cols, figsize=(24, 4 * n_rows))
    axes = axes.flatten()

    for idx, subj in enumerate(subjects):
        ax = axes[idx]
        subj_data = df_features[df_features["subject"] == subj]
        sessions = sorted(subj_data["session"].unique())

        colors = plt.cm.viridis(np.linspace(0.1, 0.9, len(sessions)))
        for si, s in enumerate(sessions):
            key = (subj, s)
            if key in data_dict:
                seg = data_dict[key]["eeg_filt"][: int(10 * cfg.FS)]
                t_seg = np.arange(len(seg)) / cfg.FS
                offset = si * 80
                ax.plot(t_seg, seg + offset, color=colors[si], linewidth=0.5, alpha=0.8)

        ax.set_title(f"{subj} ({len(sessions)} sessions)", fontsize=10)
        ax.set_xlabel("Time (s)", fontsize=8)
        ax.set_ylabel("Amplitude (offset)", fontsize=8)
        ax.tick_params(labelsize=7)

    for idx in range(len(subjects), len(axes)):
        axes[idx].set_visible(False)

    fig.suptitle(
        "图1: 全体被试 EEG 信号概览\n(每行=不同Session的前10秒, 垂直偏移100uV)",
        fontsize=14,
        fontweight="bold",
    )
    plt.tight_layout()
    path = os.path.join(output_dir, "Fig1_全被试Session信号概览.png")
    fig.savefig(path)
    plt.close(fig)
    print(f"    已保存: {path}")


# ============================================================
#  第七部分：可视化 - 图2：全被试平均 PSD
# ============================================================

def fig2_average_psd(df_features, psd_collection, output_dir):
    """图2：全被试平均功率谱密度 + 频带标注"""
    print("    生成 Fig 2: 全被试平均 PSD...")

    all_psd = []
    for subj, psd_list in psd_collection.items():
        for freqs, psd in psd_list:
            all_psd.append(psd)

    if not all_psd:
        print("    无 PSD 数据, 跳过")
        return

    min_len = min(len(p) for p in all_psd)
    all_psd_aligned = np.array([p[:min_len] for p in all_psd])
    freqs_aligned = freqs[:min_len]

    mean_psd = np.mean(all_psd_aligned, axis=0)
    std_psd = np.std(all_psd_aligned, axis=0)
    sem_psd = std_psd / np.sqrt(len(all_psd_aligned))

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=cfg.FIGSIZE_WIDE)

    ax1.fill_between(freqs_aligned, mean_psd - sem_psd, mean_psd + sem_psd, alpha=0.3, color="gray")
    ax1.plot(freqs_aligned, mean_psd, "k-", linewidth=1.5)
    ax1.set_xlabel("Frequency (Hz)")
    ax1.set_ylabel("Power Spectral Density (uV^2/Hz)")
    ax1.set_title("Average PSD (Mean +/- SEM)")
    ax1.set_xlim(0, cfg.HIGHCUT)

    for band_name, (low, high) in cfg.BANDS.items():
        ax1.axvspan(low, high, alpha=cfg.BAND_ALPHA, color=cfg.BAND_COLORS[band_name])
        ax1.text(
            (low + high) / 2, ax1.get_ylim()[1] * 0.95, band_name.split("(")[0],
            ha="center", fontsize=8, color=cfg.BAND_COLORS[band_name], fontweight="bold",
        )

    ax2.loglog(freqs_aligned, mean_psd, "k-", linewidth=1.5)
    ax2.fill_between(freqs_aligned, np.maximum(mean_psd - sem_psd, 1e-3), mean_psd + sem_psd, alpha=0.3, color="gray")
    for band_name, (low, high) in cfg.BANDS.items():
        ax2.axvspan(low, high, alpha=cfg.BAND_ALPHA, color=cfg.BAND_COLORS[band_name])
    ax2.set_xlabel("Frequency (Hz)")
    ax2.set_ylabel("Power Spectral Density (uV^2/Hz)")
    ax2.set_title("Average PSD (Log-Log Scale)")
    ax2.set_xlim(1, cfg.HIGHCUT)

    fig.suptitle("图2: 全被试平均功率谱密度 (PSD)", fontsize=14, fontweight="bold")
    plt.tight_layout()
    path = os.path.join(output_dir, "Fig2_全被试平均PSD.png")
    fig.savefig(path)
    plt.close(fig)
    print(f"    已保存: {path}")


# ============================================================
#  第八部分：可视化 - 图3：频带相对功率堆叠柱状图
# ============================================================

def fig3_band_power_stacked(df_features, output_dir):
    """图3：每个被试的频带相对功率堆叠柱状图"""
    print("    生成 Fig 3: 频带相对功率堆叠柱状图...")

    band_cols = [b for b in df_features.columns if b.endswith("_rel")]
    subj_band = df_features.groupby("subject")[band_cols].mean()

    band_labels = [c.replace("_rel", "") for c in band_cols]
    colors = [cfg.BAND_COLORS.get(bl, "#888888") for bl in band_labels]

    fig, ax = plt.subplots(figsize=(16, 8))
    subj_band.plot(kind="bar", stacked=True, ax=ax, color=colors, width=0.8)

    ax.set_xlabel("Subject")
    ax.set_ylabel("Relative Power")
    ax.set_title("图3: 各被试频带相对功率占比")
    ax.legend(loc="upper right", fontsize=8, ncol=2)
    ax.set_ylim(0, 1.05)
    ax.tick_params(axis="x", rotation=45)
    plt.tight_layout()
    path = os.path.join(output_dir, "Fig3_频带相对功率堆叠柱状图.png")
    fig.savefig(path)
    plt.close(fig)
    print(f"    已保存: {path}")


# ============================================================
#  第九部分：可视化 - 图4：Theta/Beta 比值跨 Session 趋势
# ============================================================

def fig4_theta_beta_trend(df_features, output_dir):
    """图4：Theta/Beta 比值随训练次数的变化趋势"""
    print("    生成 Fig 4: Theta/Beta 比值跨 Session 趋势...")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=cfg.FIGSIZE_WIDE)

    subjects = sorted(df_features["subject"].unique())
    colors = plt.cm.tab20(np.linspace(0, 1, len(subjects)))

    for idx, subj in enumerate(subjects):
        subj_data = df_features[df_features["subject"] == subj].sort_values("session")
        ax1.plot(
            subj_data["session"], subj_data["theta_beta_ratio"],
            "o-", color=colors[idx], alpha=0.6, markersize=5, linewidth=1, label=subj,
        )

    ax1.set_xlabel("Session")
    ax1.set_ylabel("Theta/Beta Ratio")
    ax1.set_title("Individual Trends")
    ax1.legend(bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=6)

    all_sessions = df_features.groupby("session")["theta_beta_ratio"].agg(["mean", "std", "count"])
    all_sessions["sem"] = all_sessions["std"] / np.sqrt(all_sessions["count"])
    sessions = all_sessions.index.values
    ax2.fill_between(
        sessions,
        all_sessions["mean"] - all_sessions["sem"],
        all_sessions["mean"] + all_sessions["sem"],
        alpha=0.3, color="steelblue",
    )
    ax2.plot(sessions, all_sessions["mean"], "o-", color="steelblue", linewidth=2, markersize=8)

    valid = all_sessions.dropna()
    if len(valid) >= 3:
        x = valid.index.values
        y = valid["mean"].values
        slope, intercept, r, p, std_err = stats.linregress(x, y)
        x_line = np.linspace(x.min(), x.max(), 100)
        ax2.plot(x_line, slope * x_line + intercept, "--", color="red", linewidth=1.5, alpha=0.7)
        ax2.text(
            0.05, 0.95, f"Slope={slope:.4f}\nr={r:.3f}, p={p:.4f}",
            transform=ax2.transAxes, fontsize=9, verticalalignment="top",
            bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5),
        )

    ax2.set_xlabel("Session")
    ax2.set_ylabel("Theta/Beta Ratio")
    ax2.set_title("Group Average (Mean +/- SEM)")

    fig.suptitle(
        "图4: Theta/Beta 比值随训练次数变化\n(比值越低 = 注意力越好)",
        fontsize=14, fontweight="bold",
    )
    plt.tight_layout()
    path = os.path.join(output_dir, "Fig4_ThetaBeta趋势.png")
    fig.savefig(path)
    plt.close(fig)
    print(f"    已保存: {path}")


# ============================================================
#  第十部分：可视化 - 图5：Alpha 功率跨 Session 趋势
# ============================================================

def fig5_alpha_trend(df_features, output_dir):
    """图5：Alpha 相对功率 + Beta 相对功率 跨 Session 趋势"""
    print("    生成 Fig 5: Alpha/Beta 功率跨 Session 趋势...")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=cfg.FIGSIZE_WIDE)

    for ax, col, title, ylabel in [
        (ax1, "Alpha (8-13)_rel", "Alpha Relative Power", "Alpha Relative Power"),
        (ax2, "Beta (13-30)_rel", "Beta Relative Power", "Beta Relative Power"),
    ]:
        sessions_mean = df_features.groupby("session")[col].agg(["mean", "std", "count"])
        sessions_mean["sem"] = sessions_mean["std"] / np.sqrt(sessions_mean["count"])
        s = sessions_mean.index.values
        ax.fill_between(
            s,
            sessions_mean["mean"] - sessions_mean["sem"],
            sessions_mean["mean"] + sessions_mean["sem"],
            alpha=0.3, color="steelblue",
        )
        ax.plot(s, sessions_mean["mean"], "o-", color="steelblue", linewidth=2, markersize=8)

        valid = sessions_mean.dropna()
        if len(valid) >= 3:
            x = valid.index.values
            y = valid["mean"].values
            slope, intercept, r, p, _ = stats.linregress(x, y)
            ax.plot(
                np.linspace(x.min(), x.max(), 100),
                slope * np.linspace(x.min(), x.max(), 100) + intercept,
                "--", color="red", linewidth=1.5, alpha=0.7,
            )
            ax.text(
                0.05, 0.95, f"r={r:.3f}, p={p:.4f}",
                transform=ax.transAxes, fontsize=9, verticalalignment="top",
                bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5),
            )

        ax.set_xlabel("Session")
        ax.set_ylabel(ylabel)
        ax.set_title(title)

    fig.suptitle(
        "图5: Alpha 和 Beta 相对功率随训练次数变化\n(Alpha下降+Beta上升 = 注意力提升)",
        fontsize=14, fontweight="bold",
    )
    plt.tight_layout()
    path = os.path.join(output_dir, "Fig5_AlphaBeta趋势.png")
    fig.savefig(path)
    plt.close(fig)
    print(f"    已保存: {path}")


# ============================================================
#  第十一部分：可视化 - 图6：注意力指数箱线图 + 散点
# ============================================================

def fig6_attention_boxplot(df_features, output_dir):
    """图6：注意力指数 (Beta/(Alpha+Theta)) 被试间分布"""
    print("    生成 Fig 6: 注意力指数箱线图...")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=cfg.FIGSIZE_WIDE)

    order = df_features.groupby("subject")["attention_index"].median().sort_values().index.tolist()

    sns.boxplot(
        data=df_features, x="subject", y="attention_index", order=order,
        palette="Set3", ax=ax1, linewidth=0.8,
    )
    sns.stripplot(
        data=df_features, x="subject", y="attention_index", order=order,
        color="black", size=3, alpha=0.3, ax=ax1,
    )
    ax1.set_xlabel("Subject")
    ax1.set_ylabel("Attention Index: Beta/(Alpha+Theta)")
    ax1.set_title("Attention Index Distribution")
    ax1.tick_params(axis="x", rotation=45, labelsize=8)

    subj_theta_beta = df_features.groupby("subject")["theta_beta_ratio"].agg(["mean", "std"])
    subj_theta_beta = subj_theta_beta.sort_values("mean")
    colors_bar = plt.cm.RdYlGn_r(np.linspace(0.2, 0.8, len(subj_theta_beta)))
    ax2.barh(
        range(len(subj_theta_beta)), subj_theta_beta["mean"],
        xerr=subj_theta_beta["std"], color=colors_bar, edgecolor="gray", linewidth=0.5,
    )
    ax2.set_yticks(range(len(subj_theta_beta)))
    ax2.set_yticklabels(subj_theta_beta.index, fontsize=8)
    ax2.set_xlabel("Theta/Beta Ratio")
    ax2.set_title("Theta/Beta Ratio Ranking\n(lower = better attention)")
    ax2.axvline(x=subj_theta_beta["mean"].median(), color="red", linestyle="--", alpha=0.5, label="Median")
    ax2.legend(fontsize=8)

    fig.suptitle(
        "图6: 注意力相关指标的被试间比较",
        fontsize=14, fontweight="bold",
    )
    plt.tight_layout()
    path = os.path.join(output_dir, "Fig6_注意力指数箱线图.png")
    fig.savefig(path)
    plt.close(fig)
    print(f"    已保存: {path}")


# ============================================================
#  第十二部分：可视化 - 图7：单次 Session 时频图 (Spectrogram)
# ============================================================

def fig7_spectrogram(data_dict, output_dir):
    """图7：选取一个有代表性被试的某个Session，绘制时频图"""
    print("    生成 Fig 7: 时频图 (Spectrogram)...")

    subjects = sorted(set(k[0] for k in data_dict.keys()))
    if not subjects:
        print("    无数据, 跳过")
        return

    demo_subj = subjects[len(subjects) // 2]
    demo_sessions = sorted([k[1] for k in data_dict.keys() if k[0] == demo_subj])
    if not demo_sessions:
        print("    无数据, 跳过")
        return

    demo_session = demo_sessions[len(demo_sessions) // 2]
    key = (demo_subj, demo_session)
    if key not in data_dict:
        print("    无数据, 跳过")
        return

    eeg = data_dict[key]["eeg_filt"]
    fs = cfg.FS

    f, t_spec, Sxx = signal.spectrogram(eeg, fs=fs, nperseg=cfg.NFFT, noverlap=cfg.NOVERLAP)
    Sxx_db = 10 * np.log10(Sxx + 1e-12)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(18, 10), gridspec_kw={"height_ratios": [3, 1]})

    im = ax1.pcolormesh(
        t_spec, f, Sxx_db, shading="gouraud", cmap="jet", vmin=-20, vmax=30,
    )
    ax1.set_ylabel("Frequency (Hz)")
    ax1.set_title(f"Spectrogram - {demo_subj} Session {demo_session}")
    ax1.set_ylim(0, cfg.HIGHCUT)

    for band_name, (low, high) in cfg.BANDS.items():
        ax1.axhline(low, color="white", linestyle="--", linewidth=0.5, alpha=0.5)
        ax1.axhline(high, color="white", linestyle="--", linewidth=0.5, alpha=0.5)

    cbar = plt.colorbar(im, ax=ax1)
    cbar.set_label("Power (dB)")

    eeg_sub = eeg[: int(60 * fs)]
    t_sub = np.arange(len(eeg_sub)) / fs
    ax2.plot(t_sub, eeg_sub, "k-", linewidth=0.5)
    ax2.set_xlabel("Time (s)")
    ax2.set_ylabel("Amplitude (uV)")
    ax2.set_title(f"EEG Waveform (first 60s)")

    fig.suptitle(
        "图7: 单次Session时频分析 (Spectrogram + EEG波形)",
        fontsize=14, fontweight="bold",
    )
    plt.tight_layout()
    path = os.path.join(output_dir, "Fig7_时频图Spectrogram.png")
    fig.savefig(path)
    plt.close(fig)
    print(f"    已保存: {path}")


# ============================================================
#  第十三部分：可视化 - 图8：被试间热力图
# ============================================================

def fig8_heatmap(df_features, output_dir):
    """图8：被试 × 频带 热力图"""
    print("    生成 Fig 8: 被试间频带功率热力图...")

    band_rel_cols = [c for c in df_features.columns if c.endswith("_rel")]
    subj_band = df_features.groupby("subject")[band_rel_cols].mean()
    subj_band.columns = [c.replace("_rel", "") for c in band_rel_cols]

    fig, ax = plt.subplots(figsize=(12, 10))
    sns.heatmap(
        subj_band, annot=True, fmt=".3f", cmap="YlOrRd",
        linewidths=0.5, ax=ax, cbar_kws={"label": "Relative Power"},
        vmin=0, vmax=subj_band.values.max(),
    )
    ax.set_xlabel("Frequency Band")
    ax.set_ylabel("Subject")
    ax.set_title("图8: 被试间频带相对功率热力图")

    plt.tight_layout()
    path = os.path.join(output_dir, "Fig8_被试间热力图.png")
    fig.savefig(path)
    plt.close(fig)
    print(f"    已保存: {path}")


# ============================================================
#  第十四部分：可视化 - 图9：频带间相关性矩阵
# ============================================================

def fig9_correlation_matrix(df_features, output_dir):
    """图9：频带功率 Pearson 相关性矩阵"""
    print("    生成 Fig 9: 频带相关性矩阵...")

    band_rel_cols = [c for c in df_features.columns if c.endswith("_rel")]
    corr_cols = band_rel_cols + ["theta_beta_ratio", "attention_index"]
    corr_cols = [c for c in corr_cols if c in df_features.columns]
    corr_df = df_features[corr_cols].dropna()

    corr_matrix = corr_df.corr()
    clean_labels = [
        c.replace("_rel", "").replace("_", " ") for c in corr_matrix.columns
    ]

    fig, ax = plt.subplots(figsize=(14, 12))
    mask = np.triu(np.ones_like(corr_matrix, dtype=bool), k=1)
    sns.heatmap(
        corr_matrix, annot=True, fmt=".2f", cmap="RdBu_r",
        center=0, vmin=-1, vmax=1, linewidths=0.5, ax=ax,
        xticklabels=clean_labels, yticklabels=clean_labels, mask=mask,
    )
    ax.set_title("图9: 频带功率与注意力指标相关性矩阵")
    plt.tight_layout()
    path = os.path.join(output_dir, "Fig9_频带相关性矩阵.png")
    fig.savefig(path)
    plt.close(fig)
    print(f"    已保存: {path}")


# ============================================================
#  第十五部分：可视化 - 图10：被试聚类
# ============================================================

def fig10_subject_clustering(df_features, output_dir):
    """图10：基于频带特征的被试层次聚类"""
    print("    生成 Fig 10: 被试聚类分析...")

    from scipy.cluster.hierarchy import dendrogram, linkage
    from sklearn.preprocessing import StandardScaler

    band_rel_cols = [c for c in df_features.columns if c.endswith("_rel")]
    subj_band = df_features.groupby("subject")[band_rel_cols].mean()

    subj_band.columns = [c.replace("_rel", "").replace("(", "").replace(")", "") for c in band_rel_cols]

    scaler = StandardScaler()
    scaled = scaler.fit_transform(subj_band)

    linked = linkage(scaled, method="ward")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=cfg.FIGSIZE_WIDE)

    dendrogram(
        linked, labels=subj_band.index.tolist(),
        leaf_rotation=90, leaf_font_size=9, ax=ax1,
        color_threshold=0.7 * max(linked[:, 2]),
    )
    ax1.set_title("Hierarchical Clustering (Ward)")
    ax1.set_ylabel("Distance")

    sns.heatmap(
        subj_band, cmap="YlOrRd", annot=True, fmt=".3f",
        ax=ax2, cbar_kws={"label": "Relative Power"},
    )
    ax2.set_title("Feature Matrix")
    ax2.set_xlabel("Frequency Band")

    fig.suptitle(
        "图10: 被试聚类分析 - 基于频带相对功率特征",
        fontsize=14, fontweight="bold",
    )
    plt.tight_layout()
    path = os.path.join(output_dir, "Fig10_被试聚类分析.png")
    fig.savefig(path)
    plt.close(fig)
    print(f"    已保存: {path}")


# ============================================================
#  第十六部分：统计分析 & 报告生成
# ============================================================

def generate_statistics(df_features, output_dir):
    """生成统计报告"""
    print("\n" + "=" * 60)
    print("统计分析报告")
    print("=" * 60)

    report_lines = []
    report_lines.append("=" * 60)
    report_lines.append("BCI 注意力训练 EEG 分析 - 统计报告")
    report_lines.append("=" * 60)

    total_files = len(df_features)
    total_subjects = df_features["subject"].nunique()
    avg_sessions = df_features.groupby("subject")["session"].nunique().mean()
    avg_duration = df_features["total_power"].count()

    report_lines.append(f"\n被试数: {total_subjects}")
    report_lines.append(f"总 BDF 文件数: {total_files}")
    report_lines.append(f"平均每人 Session 数: {avg_sessions:.1f}")

    for metric, label, better_dir in [
        ("theta_beta_ratio", "Theta/Beta 比值", "下降"),
        ("attention_index", "注意力指数 Beta/(Alpha+Theta)", "上升"),
        ("Alpha (8-13)_rel", "Alpha 相对功率", "下降"),
        ("Beta (13-30)_rel", "Beta 相对功率", "上升"),
    ]:
        if metric in df_features.columns:
            sessions_data = df_features.groupby("session")[metric].mean().dropna()
            if len(sessions_data) >= 2:
                first = sessions_data.iloc[0]
                last = sessions_data.iloc[-1]
                pct_change = (last - first) / abs(first) * 100 if first != 0 else 0

                x = sessions_data.index.values
                y = sessions_data.values
                slope, intercept, r, p, _ = stats.linregress(x, y)

                report_lines.append(f"\n--- {label} ---")
                report_lines.append(f"  首次 Session 均值: {first:.4f}")
                report_lines.append(f"  末次 Session 均值: {last:.4f}")
                report_lines.append(f"  变化幅度: {pct_change:+.1f}% ({better_dir})")
                report_lines.append(f"  线性回归斜率: {slope:.6f} / session")
                report_lines.append(f"  相关系数 r: {r:.3f}")
                report_lines.append(f"  p 值: {p:.4f} {'***显著' if p < 0.001 else '**显著' if p < 0.01 else '*显著' if p < 0.05 else '不显著'}")

    for line in report_lines:
        print(line)

    report_path = os.path.join(output_dir, "statistics_report.txt")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))
    print(f"\n报告已保存: {report_path}")

    return report_lines


# ============================================================
#  第十七部分：主函数
# ============================================================

def main():
    print("=" * 60)
    print("BCI 注意力训练 EEG 分析")
    print("=" * 60)

    os.makedirs(cfg.OUTPUT_DIR, exist_ok=True)

    df_files = collect_all_files(cfg.DATA_ROOT)
    print(f"\n扫描到 {len(df_files)} 个 BDF 文件")
    print(f"被试数: {df_files['subject'].nunique()}")
    print(f"Session 范围: {df_files['session'].min()} - {df_files['session'].max()}")

    data_dict, df_info = load_all_data(df_files)

    df_features, psd_collection = extract_all_features(data_dict)

    print("\n正在生成图表...")

    fig1_all_subject_session_overview(data_dict, df_features, cfg.OUTPUT_DIR)
    fig2_average_psd(df_features, psd_collection, cfg.OUTPUT_DIR)
    fig3_band_power_stacked(df_features, cfg.OUTPUT_DIR)
    fig4_theta_beta_trend(df_features, cfg.OUTPUT_DIR)
    fig5_alpha_trend(df_features, cfg.OUTPUT_DIR)
    fig6_attention_boxplot(df_features, cfg.OUTPUT_DIR)
    fig7_spectrogram(data_dict, cfg.OUTPUT_DIR)
    fig8_heatmap(df_features, cfg.OUTPUT_DIR)
    fig9_correlation_matrix(df_features, cfg.OUTPUT_DIR)
    fig10_subject_clustering(df_features, cfg.OUTPUT_DIR)

    generate_statistics(df_features, cfg.OUTPUT_DIR)

    print("\n" + "=" * 60)
    print(f"全部完成! 图表和报告保存在: {cfg.OUTPUT_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
