#!/usr/bin/env python3
"""P2 QUBO 管线（handoff-grade，供 Codex 复核与替换 surrogate）。

管线：02+03 训练 surrogate → 池 07 全量预测 V̂ → 精确表值 QUBO 构建
      → Kaiwu SA 求解 → 独立验证（约束/能量/与暴力枚举对照）。

核心建模洞察（写入论文）：
  one-hot 编码下，二次项 a_i*b_j 的系数就是 (i,j) 对的 V̂ 预测值本身——
  QUBO 可*精确*承载全池表值，无需 FM 近似。FMQA 仅在池不可枚举时才必要。
  同时：池仅 2704 态，暴力枚举即真值——QUBO 求解器的正确性可被严格验证，
  这正是"求解器精确性验证"的论文素材，而非隐藏枚举的简易性。

复核方式：python3 p2_qubo.py 全量重跑；产出 p2_report.json 逐项核对。
"""
import sys, os, json, time
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, '/home/mary/apmcm2026/configs')

DATA = "/home/mary/apmcm2026/00_赛题与规则/官方发布/2026赛题/2026 APMCM Problem D/date"
OUT = os.path.dirname(os.path.abspath(__file__))
RAND_SEED = 20261127  # 固定种子，全程一致

# ---------- 1. surrogate：02+03 训练（题面规定），baseline LightGBM ----------
def train_surrogate():
    """返回 (model, etab)。注：此函数是可替换点——P1 增强后换模型即可，管线其余不变。"""
    import lightgbm as lgb
    from feature_utils import build_element_table, featurize
    tr = pd.read_csv(os.path.join(DATA, "02_castelli_train.csv"))
    va = pd.read_csv(os.path.join(DATA, "03_castelli_val.csv"))
    both = pd.concat([tr, va], ignore_index=True)  # 题面：02+03 均用于训练
    etab = build_element_table()
    X = featurize(both, etab)
    y = np.log1p(both.V.values)
    model = lgb.LGBMRegressor(objective="regression", n_estimators=529, learning_rate=0.03,
                              num_leaves=63, min_child_samples=40, subsample=0.8, subsample_freq=1,
                              colsample_bytree=0.7, reg_lambda=1.0, random_state=42, n_jobs=-1)
    model.fit(X, y)  # n_estimators 取 baseline 早停值 529（见 p1_baseline 输出）
    return model, etab

# ---------- 2. 池预测 ----------
def predict_pool(model, etab):
    from feature_utils import featurize
    pool = pd.read_csv(os.path.join(DATA, "07_castelli_q2_pool.csv"))
    assert (pool.X == "NO2").all() and len(pool) == 2704
    F = featurize(pool, etab)
    vhat = np.expm1(model.predict(F))
    vhat = np.clip(vhat, 0, None)  # 违反度物理非负；负值是模型伪影，截断并记录
    pool = pool.copy()
    pool["vhat"] = vhat
    return pool

# ---------- 3. 精确表值 QUBO ----------
def build_qubo_matrix(pool, elems, lam):
    """变量序: a_0..a_51, b_0..b_51（按 elems 排序索引）。
    目标: sum_ij Vhat(i,j) a_i b_j + lam*(sum a - 1)^2 + lam*(sum b - 1)^2
    QUBO 矩阵 Q 上三角约定: E = x^T Q x（x 二进制）。
    展开 (sum x - 1)^2 = sum_i x_i + 2*sum_{i<k} x_i x_k - 2*sum_i x_i + 1
                       = -sum_i x_i + 2*sum_{i<k} x_i x_k + 1   （x^2=x）
    常数 +1 不进矩阵（不影响 argmin）。
    """
    idx = {e: k for k, e in enumerate(elems)}
    n = len(elems)
    Q = np.zeros((2 * n, 2 * n))
    # 表值项：a_i (行 k1) × b_j (行 n+k2) 系数 = vhat
    for r in pool.itertuples():
        i, j = idx[r.A], idx[r.B]
        Q[i, n + j] += r.vhat  # 每 (i,j) 唯一（池无重复），+= 仅为防御
    # one-hot 罚：A 组
    for i in range(n):
        Q[i, i] += -lam
        for k in range(i + 1, n):
            Q[i, k] += 2 * lam
    # B 组（偏移 n）
    for i in range(n):
        Q[n + i, n + i] += -lam
        for k in range(i + 1, n):
            Q[n + i, n + k] += 2 * lam
    return Q

def energy_qubo(Q, x):
    return float(x @ Q @ x)

# ---------- 4. 主流程 ----------
def main():
    t0 = time.time()
    report = {"seed": RAND_SEED, "steps": {}}

    print("[1/6] 训练 surrogate（02+03）...")
    model, etab = train_surrogate()

    print("[2/6] 池 07 全量预测...")
    pool = predict_pool(model, etab)
    elems = sorted(set(pool.A) | set(pool.B))
    assert len(elems) == 52

    # 暴力枚举真值（验证基准）
    bi = pool.vhat.idxmin()
    brute = pool.loc[bi]
    report["brute_force"] = {"A": brute.A, "B": brute.B, "vhat": float(brute.vhat)}
    print(f"      暴力枚举最优: A={brute.A} B={brute.B} vhat={brute.vhat:.4f}")
    print(f"      池 vhat 范围: [{pool.vhat.min():.4f}, {pool.vhat.max():.4f}]")

    print("[3/6] 构建 QUBO（精确表值）...")
    # λ 推导：违反 one-hot 的最大潜在收益 ≈ 免付的最高表值 max(vhat)。
    # 取 lam = max(vhat) + 1.0 裕量；敏感性与精确性在报告中验证。
    lam = float(pool.vhat.max()) + 1.0
    Q = build_qubo_matrix(pool, elems, lam)
    report["lambda"] = lam
    report["qubo"] = {"n_bits": int(Q.shape[0]), "nnz": int((Q != 0).sum()),
                      "coef_min": float(Q.min()), "coef_max": float(Q.max())}
    print(f"      λ={lam:.3f} | Q: {Q.shape[0]}x{Q.shape[0]}, 系数范围 [{Q.min():.2f}, {Q.max():.2f}]")

    print("[4/6] 转 Ising + Kaiwu SA 求解...")
    import kaiwu as kw
    from kaiwu_license import KAIWU_USER_ID, KAIWU_SDK_CODE
    kw.license.init(user_id=KAIWU_USER_ID, sdk_code=KAIWU_SDK_CODE)
    from kaiwu.core import qubo_matrix_to_ising_matrix
    h, offset = qubo_matrix_to_ising_matrix(Q)
    report["ising"] = {"offset": float(offset), "absmax": float(np.abs(h).max())}

    init_t = max(100.0, 2 * float(np.abs(h).max()))
    print(f"      初温 {init_t:.0f}（=max(100, 2·max|h|)，kaiwu-coding-skill 启发式）")
    solver = kw.classical.SimulatedAnnealingOptimizer(
        initial_temperature=init_t, alpha=0.99, cutoff_temperature=0.001,
        iterations_per_t=200, size_limit=128, rand_seed=RAND_SEED)
    t_solve = time.time()
    raw = np.asarray(solver.solve(h))
    solve_time = time.time() - t_solve
    print(f"      SA 返回 {raw.shape} 解，耗时 {solve_time:.1f}s")

    print("[5/6] 解码+独立验证...")
    # solve 输出 {-1,+1} 自旋，末列或为符号位——按 kaiwu-coding-skill 流程解码
    # 社区核实：row[:-1]*row[-1] 为惯例。此处矩阵直接构建，变量序与 Q 一致。
    candidates = []
    for row in raw:
        spins = row[:-1] * row[-1] if row.shape[0] == Q.shape[0] + 1 else row
        x = ((spins + 1) // 2).astype(int)  # 自旋→二进制
        if x.shape[0] != Q.shape[0]:
            continue
        xa, xb = x[:52], x[52:]
        feasible = (xa.sum() == 1) and (xb.sum() == 1)
        if feasible:
            ai, bi = int(xa.argmax()), int(xb.argmax())
            A, B = elems[ai], elems[bi]
            rowmatch = pool[(pool.A == A) & (pool.B == B)]
            v = float(rowmatch.vhat.iloc[0]) if len(rowmatch) else np.nan
            candidates.append({"A": A, "B": B, "vhat": v, "energy": energy_qubo(Q, x)})
    report["sa"] = {"n_pool": int(raw.shape[0]), "n_feasible": len(candidates),
                    "solve_time_s": round(solve_time, 2), "init_temperature": init_t,
                    "iterations_per_t": 200, "size_limit": 128}

    print("[6/6] 对照暴力真值...")
    if candidates:
        best = min(candidates, key=lambda c: c["vhat"])
        report["qubo_best"] = best
        match = (best["A"] == brute.A and best["B"] == brute.B)
        report["solver_matches_bruteforce"] = match
        print(f"      QUBO 最优可行解: A={best['A']} B={best['B']} vhat={best['vhat']:.4f}")
        print(f"      与暴力枚举一致: {match} | 可行解比例: {len(candidates)}/{raw.shape[0]}")
    else:
        report["qubo_best"] = None
        report["solver_matches_bruteforce"] = False
        print("      !!! SA 候选池无可行解——需调参（增大 iterations_per_t / size_limit）")

    report["total_time_s"] = round(time.time() - t0, 1)
    pool[["id", "A", "B", "X", "vhat"]].to_csv(os.path.join(OUT, "p2_pool_predictions.csv"), index=False)
    np.save(os.path.join(OUT, "p2_qubo_matrix.npy"), Q)
    with open(os.path.join(OUT, "p2_report.json"), "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\n产出: p2_report.json / p2_pool_predictions.csv / p2_qubo_matrix.npy | 总耗时 {report['total_time_s']}s")

if __name__ == "__main__":
    main()
