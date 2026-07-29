# -*- coding: utf-8 -*-
"""分析每人的注意力训练响应程度 - 快速版"""
import os, re, struct, sys
import numpy as np
from scipy import stats, signal

root = r"d:\code\CrazyMilkTeaCup\bci训练日志"

def read_bdf_quick(fp):
    with open(fp, "rb") as f:
        hdr = f.read(256)
        hdr_bytes = int(hdr[184:192].strip())
        n_records = int(hdr[236:244].strip())
        dur_record = float(hdr[244:252].strip())
        n_signals = int(hdr[252:256].strip())
        f.seek(256)
        labels_raw = f.read(n_signals * 16)
        labels = [labels_raw[i*16:(i+1)*16].strip().decode("ascii","ignore") for i in range(n_signals)]
        f.seek(256 + n_signals * 216)
        nsamples_raw = f.read(n_signals * 8)
        nsamples = [int(nsamples_raw[i*8:(i+1)*8].strip()) for i in range(n_signals)]
        eeg_idx = next((i for i, lab in enumerate(labels) if "BDF Annotations" not in lab and lab.strip()), 0)
        total_s = nsamples[eeg_idx] * n_records
        eeg = np.zeros(total_s, dtype=np.int32)
        ptr, sidx = 0, 0
        f.seek(hdr_bytes)
        raw = f.read()
        for rec in range(n_records):
            for ch in range(n_signals):
                ch_s = nsamples[ch]
                if ch != eeg_idx:
                    ptr += ch_s * 3
                    continue
                for s in range(ch_s):
                    if ptr + 3 > len(raw): break
                    b = raw[ptr:ptr+3]
                    val = struct.unpack("<i", b + (b"\x00" if (b[2] & 0x80) == 0 else b"\xff"))[0]
                    if sidx < total_s:
                        eeg[sidx] = val; sidx += 1
                    ptr += 3
        return eeg.astype(np.float64) / 32.0

def bp_filter(data, low, high, fs, order=3):
    nyq = fs / 2
    b, a = signal.butter(order, [low/nyq, high/nyq], btype="band")
    return signal.filtfilt(b, a, data)

def get_band_power(eeg, fs=250):
    eeg_f = bp_filter(eeg, 1, 45, fs)
    b_notch, a_notch = signal.iirnotch(50, 30, fs)
    eeg_f = signal.filtfilt(b_notch, a_notch, eeg_f)
    f, p = signal.welch(eeg_f, fs=fs, nperseg=512, noverlap=256)
    total = np.trapz(p[(f>=1)&(f<=45)], f[(f>=1)&(f<=45)])
    if total <= 0: total = 1e-12
    result = {}
    for name, (l, h) in [("delta",(1,4)),("theta",(4,8)),("alpha",(8,13)),("beta",(13,30)),("gamma",(30,45))]:
        mask = (f >= l) & (f <= h)
        result[name] = np.trapz(p[mask], f[mask]) / total
    result["theta_beta"] = result["theta"] / result["beta"] if result["beta"] > 0 else np.nan
    return result

subjects_data = {}
total_files = 0
for folder in sorted(os.listdir(root)):
    fp = os.path.join(root, folder)
    if not os.path.isdir(fp): continue
    bdfs = sorted([f for f in os.listdir(fp) if f.endswith(".bdf")],
                  key=lambda x: int(re.findall(r"\d+", x)[0]) if re.findall(r"\d+", x) else 0)
    if len(bdfs) < 2: continue
    sessions = []
    for bf in bdfs:
        try:
            s_num = int(re.findall(r"\d+", bf)[0])
            eeg = read_bdf_quick(os.path.join(fp, bf))
            feats = get_band_power(eeg)
            feats["session"] = s_num
            sessions.append(feats)
            total_files += 1
        except:
            pass
    if len(sessions) >= 3:
        subjects_data[folder] = sessions

print(f"Loaded {len(subjects_data)} subjects, {total_files} files\n")

# 评分
rankings = []
for subj, sessions in subjects_data.items():
    sessions.sort(key=lambda x: x["session"])
    n = len(sessions)
    tb = [s["theta_beta"] for s in sessions]
    a_vals = [s["alpha"] for s in sessions]
    b_vals = [s["beta"] for s in sessions]

    tb_valid = np.array([x for x in tb if not np.isnan(x) and not np.isinf(x)])
    if len(tb_valid) < 3: continue

    tb_first = tb_valid[0]
    tb_last = tb_valid[-1]
    tb_pct = (tb_last - tb_first) / abs(tb_first) * 100 if tb_first != 0 else 0

    a_pct = (a_vals[-1] - a_vals[0]) / abs(a_vals[0]) * 100 if a_vals[0] != 0 else 0
    b_pct = (b_vals[-1] - b_vals[0]) / abs(b_vals[0]) * 100 if b_vals[0] != 0 else 0

    x = np.arange(n)
    y = np.array(tb)
    valid = ~np.isnan(y) & ~np.isinf(y)
    if valid.sum() >= 3:
        slope, _, r, p, _ = stats.linregress(x[valid], y[valid])
    else:
        slope, r, p = 0, 0, 1

    score = 0
    if tb_pct < -30: score += 4
    elif tb_pct < -20: score += 3
    elif tb_pct < -10: score += 2
    elif tb_pct < 0: score += 1
    if r < -0.6: score += 4
    elif r < -0.4: score += 3
    elif r < -0.2: score += 2
    elif r < -0.1: score += 1
    if a_pct < -10: score += 1.5
    elif a_pct < -5: score += 1
    if b_pct > 10: score += 1.5
    elif b_pct > 5: score += 1
    if p < 0.05: score += 2
    elif p < 0.1: score += 1.5
    elif p < 0.2: score += 1
    if n >= 12: score += 0.5

    if score >= 7: rating = "A"
    elif score >= 5: rating = "B"
    elif score >= 3: rating = "C"
    else: rating = "D"

    rankings.append((subj, n, tb_first, tb_last, tb_pct, slope, r, p, a_pct, b_pct, rating, score))

rankings.sort(key=lambda x: (-x[11], x[4]))

print(f"{'Rank':>4}  {'Name':<8} {'Score':>5} {'Rate':>4} {'N':>3} {'TB_first':>8} {'TB_last':>8} {'TB_chg%':>8} {'r':>7} {'p':>7} {'Alpha%':>7} {'Beta%':>7}")
print("-" * 100)
for i, r in enumerate(rankings):
    print(f"{i+1:>4}  {r[0]:<8} {r[11]:>5.1f} {r[10]:>4} {r[1]:>3} {r[2]:>8.1f} {r[3]:>8.1f} {r[4]:>+8.1f}% {r[6]:>+7.3f} {r[7]:>7.4f} {r[8]:>+7.1f}% {r[9]:>+7.1f}%")

print()
print("评分: TB变化(-30%:+4, -20%:+3, -10%:+2, <0:+1) | r(-0.6:+4, -0.4:+3, -0.2:+2, -0.1:+1)")
print("       Alpha(-10%:+1.5, -5%:+1) | Beta(+10%:+1.5, +5%:+1) | p(<0.05:+2, <0.1:+1.5, <0.2:+1) | N>=12:+0.5")
