# -*- coding: utf-8 -*-
"""A级 vs D级 被试对比分析"""
import sys
sys.stdout.reconfigure(encoding="utf-8")

import os, re, struct
import numpy as np
from scipy import stats, signal
from datetime import datetime, timedelta
from collections import Counter

root = r"d:\code\CrazyMilkTeaCup\bci训练日志"

def read_bdf_info(fp):
    """只读header，不读数据，用于提取日期时间"""
    with open(fp, "rb") as f:
        hdr = f.read(256)
        startdate = hdr[168:176].strip().decode("ascii", "ignore").replace(chr(0), "")
        starttime = hdr[176:184].strip().decode("ascii", "ignore").replace(chr(0), "")
        hdr_bytes = int(hdr[184:192].strip())
        n_records = int(hdr[236:244].strip())
        dur_record = float(hdr[244:252].strip())
        n_signals = int(hdr[252:256].strip())
        f.seek(256 + n_signals * 216)
        nsamples_raw = f.read(n_signals * 8)
        nsamples = [int(nsamples_raw[i*8:(i+1)*8].strip()) for i in range(n_signals)]
    return startdate, starttime, n_records * dur_record, nsamples

def parse_dt(date_str, time_str):
    try:
        parts = date_str.strip().split(".")
        if len(parts) == 3:
            d, m, y = int(parts[0]), int(parts[1]), int(parts[2])
            if y < 100: y += 2000
            tparts = time_str.strip().split(".")
            hh, mm, ss = int(tparts[0]), int(tparts[1]), int(tparts[2]) if len(tparts) > 2 else 0
            return datetime(y, m, d, hh, mm, ss)
    except: pass
    return None

# A级和D级名单
A_subjects = ["刘绮岚", "林浩钊", "刘建业", "王欣瑜", "林依琪", "鲍炳煌", "陈紫涵", "陈佳艳", "白婷婷"]
D_subjects = ["沈雅文", "谭玉怡", "方正扬", "吴昕睿", "湛爱琦", "何柒梅"]

def collect_subj_info(name):
    fp = os.path.join(root, name)
    if not os.path.isdir(fp): return None
    bdfs = sorted([f for f in os.listdir(fp) if f.endswith(".bdf")],
                  key=lambda x: int(re.findall(r"\d+", x)[0]) if re.findall(r"\d+", x) else 0)
    sessions = []
    for bf in bdfs:
        try:
            s_num = int(re.findall(r"\d+", bf)[0])
            sd, st, dur, nsamp = read_bdf_info(os.path.join(fp, bf))
            dt = parse_dt(sd, st)
            sessions.append({"session": s_num, "datetime": dt, "duration_min": dur / 60, "date": sd, "time": st})
        except:
            sessions.append({"session": int(re.findall(r"\d+", bf)[0]) if re.findall(r"\d+", bf) else 0,
                             "datetime": None, "duration_min": None, "date": "err", "time": "err"})
    return sessions

print("=" * 80)
print("A级 (9人) vs D级 (6人) 对比分析")
print("=" * 80)

for group_name, group_list in [("A级 (响应者)", A_subjects), ("D级 (未响应者)", D_subjects)]:
    print(f"\n{'='*60}")
    print(f"  {group_name} ({len(group_list)}人)")
    print(f"{'='*60}")

    all_ph1_gaps = []
    all_ph2_gaps = []
    all_times = []
    durations = []
    n_total = []
    n_ph1 = []
    n_ph2 = []
    time_variety = []

    for subj in group_list:
        sessions = collect_subj_info(subj)
        if not sessions: continue

        sessions_valid = [s for s in sessions if s["datetime"] is not None]
        sessions_valid.sort(key=lambda x: x["datetime"])
        n_total.append(len(sessions_valid))

        # 阶段划分: Phase1 ≤ Jul 15, Phase2 ≥ Jul 21
        ph1 = [s for s in sessions_valid if s["datetime"] <= datetime(2026, 7, 15)]
        ph2 = [s for s in sessions_valid if s["datetime"] >= datetime(2026, 7, 21)]
        n_ph1.append(len(ph1))
        n_ph2.append(len(ph2))

        # 间隔天数
        gaps = []
        for i in range(len(sessions_valid) - 1):
            gap = (sessions_valid[i+1]["datetime"] - sessions_valid[i]["datetime"]).days
            gaps.append(gap)
            if sessions_valid[i]["datetime"] <= datetime(2026, 7, 15):
                all_ph1_gaps.append(gap)
            elif sessions_valid[i]["datetime"] >= datetime(2026, 7, 21):
                all_ph2_gaps.append(gap)

        # 录制时间
        times = [s["datetime"].hour + s["datetime"].minute/60 for s in sessions_valid if s["datetime"]]
        all_times.extend(times)
        if times:
            time_variety.append(max(times) - min(times))

        # 时长
        if sessions_valid:
            durs = [s["duration_min"] for s in sessions_valid if s["duration_min"]]
            if durs:
                durations.extend(durs)

        gap_display = ", ".join([f"{g}d" for g in gaps[:8]]) + ("..." if len(gaps) > 8 else "")
        times_display = ", ".join([f"{t:.0f}:{int((t%1)*60):02d}" for t in times[:5]]) + ("..." if len(times) > 5 else "")
        print(f"  {subj}: {len(sessions_valid)}次 | Phase1:{len(ph1)} Phase2:{len(ph2)} | 间隔: {gap_display} | 时间: {times_display}")

    print()
    print(f"  --- {group_name} 汇总统计 ---")
    print(f"  平均 Session 数: {np.mean(n_total):.1f} (range {min(n_total)}-{max(n_total)})")
    print(f"  平均 Phase1 次数: {np.mean(n_ph1):.1f}")
    print(f"  平均 Phase2 次数: {np.mean(n_ph2):.1f}")
    ph1_gaps_arr = np.array(all_ph1_gaps) if all_ph1_gaps else np.array([0])
    ph2_gaps_arr = np.array(all_ph2_gaps) if all_ph2_gaps else np.array([0])
    print(f"  Phase1 平均间隔: {ph1_gaps_arr.mean():.1f}天 (range {ph1_gaps_arr.min():.0f}-{ph1_gaps_arr.max():.0f})")
    print(f"  Phase2 平均间隔: {ph2_gaps_arr.mean():.1f}天 (range {ph2_gaps_arr.min():.0f}-{ph2_gaps_arr.max():.0f})")
    all_times_arr = np.array(all_times)
    print(f"  平均录制时间: {all_times_arr.mean():.1f}:{int((all_times_arr.mean()%1)*60):02d} (范围 {all_times_arr.min():.0f}:{int((all_times_arr.min()%1)*60):02d}-{all_times_arr.max():.0f}:{int((all_times_arr.max()%1)*60):02d})")
    if time_variety:
        tv_arr = np.array(time_variety)
        print(f"  时间段变动范围: {tv_arr.mean():.1f}h (个体内录制时间一致性)")
    if durations:
        dur_arr = np.array(durations)
        print(f"  平均单次时长: {dur_arr.mean():.1f}min (SD={dur_arr.std():.1f})")

# 统计检验 A vs D
print(f"\n\n{'='*60}")
print("  A级 vs D级 统计检验")
print(f"{'='*60}")

# 收集所有数据
def get_all_gaps(group_list):
    all_gaps = []
    for subj in group_list:
        sessions = collect_subj_info(subj)
        if not sessions: continue
        sv = [s for s in sessions if s["datetime"] is not None]
        sv.sort(key=lambda x: x["datetime"])
        for i in range(len(sv)-1):
            all_gaps.append((sv[i+1]["datetime"] - sv[i]["datetime"]).days)
    return all_gaps

def get_all_times(group_list):
    all_t = []
    for subj in group_list:
        sessions = collect_subj_info(subj)
        if not sessions: continue
        for s in sessions:
            if s["datetime"]:
                all_t.append(s["datetime"].hour + s["datetime"].minute/60)
    return all_t

def get_all_sessions(group_list):
    counts = []
    for subj in group_list:
        sessions = collect_subj_info(subj)
        if sessions:
            sv = [s for s in sessions if s["datetime"] is not None]
            counts.append(len(sv))
    return counts

for metric, get_fn, name in [
    (get_all_gaps, get_all_gaps, "录制间隔(天)"),
    (get_all_times, get_all_times, "录制时间(时)"),
    (get_all_sessions, get_all_sessions, "Session数"),
]:
    a_vals = get_fn(A_subjects)
    d_vals = get_fn(D_subjects)
    if len(a_vals) > 1 and len(d_vals) > 1:
        t, p = stats.ttest_ind(a_vals, d_vals, equal_var=False)
        cohens_d = (np.mean(a_vals) - np.mean(d_vals)) / np.sqrt((np.std(a_vals)**2 + np.std(d_vals)**2) / 2)
        print(f"  {name}: A({np.mean(a_vals):.1f}±{np.std(a_vals):.1f}) vs D({np.mean(d_vals):.1f}±{np.std(d_vals):.1f})")
        print(f"    t={t:.3f}, p={p:.4f}, d={cohens_d:.3f}")

print()
print("Done!")
