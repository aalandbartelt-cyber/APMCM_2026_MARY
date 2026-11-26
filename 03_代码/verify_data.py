#!/usr/bin/env python3
"""D 题数据审计脚本 — 一键重跑全部验证。
用法: python3 verify_data.py [数据目录]
输出: 控制台审计报告，全部通过退出码 0。
"""
import sys, os, json, hashlib
import pandas as pd
import numpy as np

DATA = sys.argv[1] if len(sys.argv) > 1 else "/home/mary/apmcm2026/00_赛题与规则/官方发布/2026赛题/2026 APMCM Problem D/date"
fails = []

def check(name, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}")
    if not ok:
        fails.append(name)

# ---------- 1. sha256 ----------
expected = json.load(open(os.path.join(DATA, "sha256_public.json")))
for fn, h in sorted(expected.items()):
    actual = hashlib.sha256(open(os.path.join(DATA, fn), "rb").read()).hexdigest()
    check(f"sha256 {fn}", actual == h)

# ---------- 2. 加载 ----------
tr = pd.read_csv(os.path.join(DATA, "02_castelli_train.csv"))
va = pd.read_csv(os.path.join(DATA, "03_castelli_val.csv"))
ho = pd.read_csv(os.path.join(DATA, "04_castelli_test_holdout.csv"))
check("train 形状", tr.shape == (11256, 22), str(tr.shape))
check("val 形状", va.shape == (3969, 22), str(va.shape))
check("holdout 形状", ho.shape == (3703, 6), str(ho.shape))

# ---------- 3. V 重算 ----------
def recompute_V(df):
    devs = [df.e_form - 0.21, 1.4 - df.gap, df.gap - 3.1, 5.73 - df.vbm, df.cbm - 4.50]
    return sum(np.clip(d / 0.5, 0, None) ** 2 for d in devs)

for name, df in [("train", tr), ("val", va)]:
    diff = (recompute_V(df) - df.V).abs().max()
    check(f"V 重算 {name}", diff < 2e-5, f"max diff {diff:.2e}")

# ---------- 4. 零正例 ----------
check("train 零正例", (tr.V == 0).sum() == 0)
check("val 零正例", (va.V == 0).sum() == 0)

# ---------- 5. 切分结构 ----------
def pairset(df):
    return set(zip(df.A, df.B))

tr_p, va_p, ho_p = pairset(tr), pairset(va), pairset(ho)
check("对数 1608/567/529", (len(tr_p), len(va_p), len(ho_p)) == (1608, 567, 529))
check("三档互斥", not (tr_p & va_p) and not (tr_p & ho_p) and not (va_p & ho_p))

# ---------- 6. 切分算法逆向 ----------
elems = sorted(set(tr.A) | set(tr.B))
allpairs = [(a, b) for a in elems for b in elems]
check("52 元素 2704 对", len(elems) == 52 and len(allpairs) == 2704)

def h(seed, a, b):
    return hashlib.sha256(f"{seed}|{a}|{b}".encode()).hexdigest()

r26 = sorted(allpairs, key=lambda p: h("2026", *p))
fill510 = set(r26[:510])
locked19 = ho_p - fill510
check("holdout = hash2026最小510 + 19锁定对", fill510.issubset(ho_p) and len(locked19) == 19,
      f"510命中={len(fill510 & ho_p)}/510, 锁定对数={len(locked19)}")
rest = [p for p in allpairs if p not in ho_p]
r27 = sorted(rest, key=lambda p: h("2027", *p))
check("val = 剩余按hash2027最小567", set(r27[:567]) == va_p)

# ---------- 7. 全因子网格与池 ----------
full = pd.concat([tr[["id","formula","A","B","X","a_eq_b"]], va[["id","formula","A","B","X","a_eq_b"]], ho])
check("全网格 18928 唯一三元组", len(full) == 18928 and full.groupby(["A","B","X"]).ngroups == 18928)
q2 = pd.read_csv(os.path.join(DATA, "07_castelli_q2_pool.csv"))
q3 = pd.read_csv(os.path.join(DATA, "08_castelli_q3_pool.csv"))
b2 = pd.read_csv(os.path.join(DATA, "11_castelli_q2_pool_blind.csv"))
b3 = pd.read_csv(os.path.join(DATA, "12_castelli_q3_pool_blind.csv"))
check("q2 = 全网格 NO2", set(q2.id) == set(full[full.X == "NO2"].id))
check("q3 = 全网格 X∈{O3,NO2,FO2}", set(q3.id) == set(full[full.X.isin(["O3","NO2","FO2"])].id))
check("盲池11 = q2∩holdout", set(b2.id) == set(q2.id) & set(ho.id))
check("盲池12 = q3∩holdout", set(b3.id) == set(q3.id) & set(ho.id))

# ---------- 8. 陷阱统计 ----------
allk = pd.concat([tr, va])
print(f"\n[INFO] gap==0 比例 {((allk.gap == 0).mean()):.4%} | V 中位数 {allk.V.median():.4f} | 近正例 V<2: {(allk.V < 2).sum()} 条")
print(f"[INFO] 19 锁定对: {sorted(locked19)}")

print(f"\n{'='*50}\n审计结果: {'全部通过' if not fails else f'{len(fails)} 项失败: {fails}'}")
sys.exit(0 if not fails else 1)
