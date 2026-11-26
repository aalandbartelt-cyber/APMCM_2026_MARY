#!/usr/bin/env python3
"""P3 QUBO 管线：X 三选一 + A/B 两自由度（8,112 态），双轨实现。

建模核心（三次项降阶，论文级内容）：
  朴素目标 Σ Vhat(i,j,x)·a_i·b_j·x_x 是三次项，QUBO 不支持。本模块实现两轨：
  轨A 分解法：X 仅 3 态 → 3 个独立 104bit QUBO（每族一个），各解取最小——
     数学上与联合优化严格等价（min over x of min over (i,j)），精确无近似。
  轨B 复合位联合编码：z_{j,x} = "B=j 且 X=x"（52×3=156 位）替代 b,x 两组位，
     目标 Σ Vhat(i,j,x)·a_i·z_{j,x} 天然二次；约束 sum(a)=1, sum(z)=1。
     总 bit = 52+156 = 208。精确、无辅助位、无线性化罚。
  两轨结果必须一致——互为精确性交叉验证（论文验证节素材）。

复核：python3 p3_qubo.py；产出 p3_report.json。
"""
import sys, os, json, time
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, '/home/mary/apmcm2026/configs')

DATA = "/home/mary/apmcm2026/00_赛题与规则/官方发布/2026赛题/2026 APMCM Problem D/date"
OUT = os.path.dirname(os.path.abspath(__file__))
RAND_SEED = 20261127
X3 = ["O3", "NO2", "FO2"]


def onehot_penalty(Q, start, count, lam):
    """就地累加 one-hot 罚 lam*(sum-1)^2 到 Q 的 [start, start+count) 段。"""
    for i in range(count):
        Q[start + i, start + i] += -lam
        for k in range(i + 1, count):
            Q[start + i, start + k] += 2 * lam


def solve_qubo_kaiwu(Q, label):
    """Kaiwu SA 求解 + 解码候选（返回 spins 矩阵与求解元数据）。"""
    import kaiwu as kw
    from kaiwu.core import qubo_matrix_to_ising_matrix
    h, offset = qubo_matrix_to_ising_matrix(Q)
    init_t = max(100.0, 2 * float(np.abs(h).max()))
    solver = kw.classical.SimulatedAnnealingOptimizer(
        initial_temperature=init_t, alpha=0.99, cutoff_temperature=0.001,
        iterations_per_t=200, size_limit=128, rand_seed=RAND_SEED)
    t = time.time()
    raw = np.asarray(solver.solve(h))
    dt = time.time() - t
    print(f"      [{label}] SA: {raw.shape[0]} 解, {dt:.1f}s, 初温 {init_t:.0f}")
    return raw, {"solve_time_s": round(dt, 2), "init_temperature": init_t,
                 "ising_absmax": float(np.abs(h).max()), "offset": float(offset)}


def decode(raw, nbits):
    """spins 解码为二进制矩阵。"""
    out = []
    for row in raw:
        spins = row[:-1] * row[-1] if row.shape[0] == nbits + 1 else row
        if spins.shape[0] == nbits:
            out.append(((spins + 1) // 2).astype(int))
    return out


def main():
    t0 = time.time()
    report = {"seed": RAND_SEED, "tracks": {}}

    print("[1/5] surrogate + 池 08 预测...")
    from p2_qubo import train_surrogate
    from feature_utils import featurize
    model, etab = train_surrogate()
    pool = pd.read_csv(os.path.join(DATA, "08_castelli_q3_pool.csv"))
    assert len(pool) == 8112 and set(pool.X.unique()) == set(X3)
    pool = pool.copy()
    pool["vhat"] = np.clip(np.expm1(model.predict(featurize(pool, etab))), 0, None)
    elems = sorted(set(pool.A) | set(pool.B))
    idx = {e: k for k, e in enumerate(elems)}
    n = 52

    bi = pool.vhat.idxmin()
    brute = pool.loc[bi]
    report["brute_force"] = {"A": brute.A, "B": brute.B, "X": brute.X, "vhat": float(brute.vhat)}
    report["per_x_best"] = {k: float(v) for k, v in pool.groupby("X").vhat.min().items()}
    print(f"      暴力最优: {brute.A}-{brute.B}-{brute.X} vhat={brute.vhat:.4f} | 分族最优: "
          f"{ {k: round(v, 2) for k, v in report['per_x_best'].items()} }")

    lam = float(pool.vhat.max()) + 1.0
    report["lambda"] = lam

    # ---------- 轨 A：分解法 ----------
    print("[2/5] 轨A 分解法：3×104bit...")
    trackA = {"results": {}}
    bestA = None
    for xf in X3:
        sub = pool[pool.X == xf]
        Q = np.zeros((2 * n, 2 * n))
        for r in sub.itertuples():
            Q[idx[r.A], n + idx[r.B]] += r.vhat
        onehot_penalty(Q, 0, n, lam)
        onehot_penalty(Q, n, n, lam)
        raw, meta = solve_qubo_kaiwu(Q, f"A/{xf}")
        cands = []
        for x in decode(raw, 2 * n):
            xa, xb = x[:n], x[n:]
            if xa.sum() == 1 and xb.sum() == 1:
                A, B = elems[int(xa.argmax())], elems[int(xb.argmax())]
                m = sub[(sub.A == A) & (sub.B == B)]
                if len(m):
                    cands.append({"A": A, "B": B, "X": xf, "vhat": float(m.vhat.iloc[0])})
        if cands:
            cb = min(cands, key=lambda c: c["vhat"])
            trackA["results"][xf] = {**cb, "n_feasible": len(cands), **meta}
            if bestA is None or cb["vhat"] < bestA["vhat"]:
                bestA = cb
    trackA["best"] = bestA
    report["tracks"]["A_decomposed"] = trackA
    print(f"      轨A 最优: {bestA['A']}-{bestA['B']}-{bestA['X']} vhat={bestA['vhat']:.4f}")

    # ---------- 轨 B：复合位联合编码 208bit ----------
    print("[3/5] 轨B 复合位联合编码：208bit...")
    # 变量序: a_0..a_51 (0..51), z_{j,x} 52+ j*3 + xk (52..207)
    nb = n + n * 3
    QB = np.zeros((nb, nb))
    xpos = {x: k for k, x in enumerate(X3)}
    for r in pool.itertuples():
        zidx = n + idx[r.B] * 3 + xpos[r.X]
        QB[idx[r.A], zidx] += r.vhat
    onehot_penalty(QB, 0, n, lam)          # A 恰好一个
    onehot_penalty(QB, n, n * 3, lam)      # 复合位恰好一个
    rawB, metaB = solve_qubo_kaiwu(QB, "B/joint")
    candsB = []
    for x in decode(rawB, nb):
        xa, xz = x[:n], x[n:]
        if xa.sum() == 1 and xz.sum() == 1:
            ai = int(xa.argmax())
            zi = int(xz.argmax())
            bj, xk = zi // 3, zi % 3
            A, B, X = elems[ai], elems[bj], X3[xk]
            m = pool[(pool.A == A) & (pool.B == B) & (pool.X == X)]
            if len(m):
                candsB.append({"A": A, "B": B, "X": X, "vhat": float(m.vhat.iloc[0])})
    trackB = {"n_bits": nb, "meta": metaB, "n_feasible": len(candsB)}
    if candsB:
        bestB = min(candsB, key=lambda c: c["vhat"])
        trackB["best"] = bestB
        print(f"      轨B 最优: {bestB['A']}-{bestB['B']}-{bestB['X']} vhat={bestB['vhat']:.4f} "
              f"(可行 {len(candsB)}/{rawB.shape[0]})")
    else:
        trackB["best"] = None
        print(f"      轨B 无可行解（{rawB.shape[0]} 候选）——208bit 需调参")
    report["tracks"]["B_composite"] = trackB

    # ---------- 交叉验证 ----------
    print("[4/5] 双轨交叉验证 + 暴力对照...")
    report["crosscheck"] = {
        "A_matches_bruteforce": bool(bestA and bestA["A"] == brute.A and bestA["B"] == brute.B and bestA["X"] == brute.X),
        "B_matches_bruteforce": bool(trackB.get("best") and trackB["best"]["A"] == brute.A
                                     and trackB["best"]["B"] == brute.B and trackB["best"]["X"] == brute.X),
        "AB_agree": bool(bestA and trackB.get("best") and bestA["A"] == trackB["best"]["A"]
                         and bestA["B"] == trackB["best"]["B"] and bestA["X"] == trackB["best"]["X"]),
    }
    print(f"      {report['crosscheck']}")

    # ---------- 成本分析骨架 ----------
    print("[5/5] 成本分析...")
    report["cost_analysis"] = {
        "trackA": {"bits_per_sub": 104, "n_subproblems": 3, "total_bit_solves": 312,
                   "note": "精确分解；三次独立求解"},
        "trackB": {"bits": 208, "nnz": int((QB != 0).sum()),
                   "coef_range": [float(QB.min()), float(QB.max())],
                   "note": "联合精确编码；单次求解"},
        "spqc_capacity": 550, "bit_usage_ratio_B": round(208 / 550, 3),
    }
    report["total_time_s"] = round(time.time() - t0, 1)

    pool[["id", "A", "B", "X", "vhat"]].to_csv(os.path.join(OUT, "p3_pool_predictions.csv"), index=False)
    np.save(os.path.join(OUT, "p3_qubo_matrix_joint.npy"), QB)
    with open(os.path.join(OUT, "p3_report.json"), "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\n产出: p3_report.json / p3_pool_predictions.csv / p3_qubo_matrix_joint.npy | 总耗时 {report['total_time_s']}s")


if __name__ == "__main__":
    main()
