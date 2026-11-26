#!/usr/bin/env python3
"""精度适配实验：SPQC 8bit [-128,127] 硬件约束的操作化（零配额成本）。

回答三个问题（直接对应题面"hardware coefficient constraints ... item by item"）：
  Q1 原始矩阵离 8bit 合规有多远？（位宽校验）
  Q2 截断/压缩适配后，求解质量损失多少？（SA 命中率 vs 暴力真值）
  Q3 精度损失的根本原因：候选间最小间隙 vs 量化分辨率

产出：precision_report.json —— 成本账本"精度项"的实证数据。
复核：python3 precision_experiment.py
"""
import sys, os, json, time
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, '/home/mary/apmcm2026/configs')
OUT = os.path.dirname(os.path.abspath(__file__))
RAND_SEED = 20261127


def sa_hit_test(h, n_bits, pool, elems, label, ipt=200):
    """SA 求解并评估：可行率/最优命中/耗时。"""
    import kaiwu as kw
    solver = kw.classical.SimulatedAnnealingOptimizer(
        initial_temperature=max(100.0, 2 * float(np.abs(h).max())), alpha=0.99,
        cutoff_temperature=0.001, iterations_per_t=ipt, size_limit=128, rand_seed=RAND_SEED)
    t = time.time()
    raw = np.asarray(solver.solve(h))
    dt = time.time() - t
    nfeas, bestv, bestpair = 0, None, None
    for row in raw:
        spins = row[:-1] * row[-1] if row.shape[0] == n_bits + 1 else row
        if spins.shape[0] != n_bits:
            continue
        x = ((spins + 1) // 2).astype(int)
        xa, xb = x[:52], x[52:]
        if xa.sum() == 1 and xb.sum() == 1:
            nfeas += 1
            A, B = elems[int(xa.argmax())], elems[int(xb.argmax())]
            m = pool[(pool.A == A) & (pool.B == B)]
            if len(m):
                v = float(m.vhat.iloc[0])
                if bestv is None or v < bestv:
                    bestv, bestpair = v, f"{A}-{B}"
    hit = bestpair == "Y-Zr"
    print(f"      [{label}] {dt:.1f}s 可行{nfeas}/128 最优{bestpair} vhat={bestv} {'✅命中' if hit else '❌未中'}")
    return {"label": label, "time_s": round(dt, 2), "n_feasible": nfeas,
            "best": bestpair, "best_vhat": bestv, "hit_bruteforce": hit}


def main():
    import kaiwu as kw
    from kaiwu_license import KAIWU_USER_ID, KAIWU_SDK_CODE
    kw.license.init(user_id=KAIWU_USER_ID, sdk_code=KAIWU_SDK_CODE)
    from kaiwu.core import qubo_matrix_to_ising_matrix
    from kaiwu.preprocess import (calculate_ising_matrix_bit_width,
                                  adjust_ising_matrix_precision)

    report = {}
    print("[1/4] 加载 P2 矩阵 + 转 Ising...")
    Q = np.load(os.path.join(OUT, "p2_qubo_matrix.npy"))
    pool = pd.read_csv(os.path.join(OUT, "p2_pool_predictions.csv"))
    elems = sorted(set(pool.A) | set(pool.B))
    h, offset = qubo_matrix_to_ising_matrix(Q)
    print(f"      Ising 系数范围: [{h.min():.2f}, {h.max():.2f}], max|h|={np.abs(h).max():.2f}")

    print("[2/4] Q1 位宽合规校验...")
    try:
        compliant = calculate_ising_matrix_bit_width(h, bit_width=8)
        print(f"      8bit 合规: {compliant}")
    except Exception as e:
        compliant = f"ERR {type(e).__name__}: {str(e)[:100]}"
        print(f"      校验返回: {compliant}")
    report["bit_width_check_raw"] = str(compliant)
    report["raw_ising"] = {"min": float(h.min()), "max": float(h.max()),
                           "absmax": float(np.abs(h).max())}

    print("[3/4] Q2 适配前后 SA 对照...")
    res_raw = sa_hit_test(h, 104, pool, elems, "原始矩阵(不合规/模拟)")
    report["sa_raw"] = res_raw

    h_adj = adjust_ising_matrix_precision(h, bit_width=8)
    print(f"      适配后 Ising 范围: [{h_adj.min():.2f}, {h_adj.max():.2f}], "
          f"唯一值数: {len(np.unique(h_adj))} (原始 {len(np.unique(h))})")
    report["adjusted_ising"] = {"min": float(h_adj.min()), "max": float(h_adj.max()),
                                "n_unique": int(len(np.unique(h_adj))),
                                "n_unique_raw": int(len(np.unique(h)))}
    res_adj = sa_hit_test(h_adj, 104, pool, elems, "8bit适配后")
    report["sa_adjusted"] = res_adj

    print("[4/4] Q3 量化分辨率 vs 候选间隙分析...")
    # 池 vhat 排序后最小间隙——决定需要多少分辨率
    v = np.sort(pool.vhat.values)
    gaps = np.diff(v)
    gaps_nonzero = gaps[gaps > 0]
    # Ising 域缩放比：量化步长对 vhat 分辨率的映射
    scale = float(np.abs(h_adj).max() / np.abs(h).max()) if np.abs(h).max() else 0
    report["resolution"] = {
        "pool_vhat_min_gap": float(gaps_nonzero.min()),
        "pool_vhat_p1_gap": float(np.percentile(gaps_nonzero, 1)),
        "scale_ratio_after_adjust": round(scale, 6),
        "vhat_resolution_loss_est": float(gaps_nonzero.min() / scale) if scale else None,
        "note": "min_gap 是最优与次优候选可能的最小 vhat 差；"
                "若量化噪声 > min_gap 则排序不再可靠",
    }
    print(f"      池 vhat 最小间隙 {gaps_nonzero.min():.4f} | 缩放比 {scale:.4f}")

    with open(os.path.join(OUT, "precision_report.json"), "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\n产出: precision_report.json")

if __name__ == "__main__":
    main()
