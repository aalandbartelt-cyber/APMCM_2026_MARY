#!/usr/bin/env python3
"""P1 surrogate 基线：元素描述符 + LightGBM，group-wise CV。
纪律：只用 (A,B,X) 可推导特征——DFT 输出列（a_lat/volume/mu_b/fermi*）推理时不可用，禁入。
评估：排序导向（near-positive 子集 Kendall tau / top-k 精度）+ 全局 RMSE。
"""
import os
import numpy as np
import pandas as pd
import lightgbm as lgb
from scipy.stats import kendalltau

DATA = "/home/mary/apmcm2026/00_赛题与规则/官方发布/2026赛题/2026 APMCM Problem D/date"
OUT = "/home/mary/apmcm2026/03_代码"
ZUNGER = "/home/mary/apmcm2026/01_参考学习/量子知识补充（forD题）/02_GitHub开源/perovskite-tutorial/zungervalenceradius.csv"

# ---------- 1. 元素描述符表 ----------
def build_element_table():
    """mendeleev 全属性 + zunger 半径合并。"""
    from mendeleev import element as melement
    z = pd.read_csv(ZUNGER).set_index("Element")
    rows = {}
    elems = "Ag Al As Au B Ba Be Bi Ca Cd Co Cr Cs Cu Fe Ga Ge Hf Hg In Ir K La Li Mg Mn Mo Na Nb Ni Os Pb Pd Pt Rb Re Rh Ru Sb Sc Si Sn Sr Ta Te Ti Tl V W Y Zn Zr".split()
    for sym in elems:
        e = melement(sym)
        rows[sym] = dict(
            Z=e.atomic_number, mass=e.atomic_weight,
            en=e.electronegativity_pauling() if e.electronegativity_pauling() else np.nan,
            group=e.group_id if e.group_id else 0, period=e.period,
            ie1=e.ionenergies.get(1, np.nan), ea=e.electron_affinity if e.electron_affinity else np.nan,
            irad=(np.median([r.ionic_radius for r in e.ionic_radii]) if e.ionic_radii else np.nan),
            arad=e.atomic_radius if e.atomic_radius else np.nan,
            covalent=e.covalent_radius if e.covalent_radius else np.nan,
            nvalence=e.nvalence() if e.nvalence() else 0,
            Rs=z.loc[sym, "Rs"], Rp=z.loc[sym, "Rp"], Rd=z.loc[sym, "Rd"],
        )
    df = pd.DataFrame(rows).T
    df.index.name = "elem"
    return df.fillna(df.median(numeric_only=True))

# ---------- 2. 特征工程 ----------
X_FAMILIES = ["O3", "NO2", "FO2", "N2O", "N3", "O2S", "FNO"]

def featurize(df, etab):
    """(A,B,X) -> 特征矩阵。A/B 各 14 描述符 + 差值/比值 + X one-hot。"""
    props = etab.columns.tolist()
    A = etab.loc[df.A.values].reset_index(drop=True)
    B = etab.loc[df.B.values].reset_index(drop=True)
    feats = {}
    for p in props:
        feats[f"A_{p}"] = A[p].values
        feats[f"B_{p}"] = B[p].values
    # 关键交互：半径失配容忍因子相关、电负性差
    feats["d_en"] = np.abs(A["en"].values - B["en"].values)
    feats["d_irad"] = np.abs(A["irad"].values - B["irad"].values)
    feats["d_Z"] = np.abs(A["Z"].values - B["Z"].values)
    feats["sum_ie1"] = A["ie1"].values + B["ie1"].values
    feats["a_eq_b"] = df.a_eq_b.values
    X = pd.get_dummies(df.X)[X_FAMILIES].astype(float)
    F = pd.DataFrame(feats)
    return pd.concat([F.reset_index(drop=True), X.reset_index(drop=True)], axis=1)

# ---------- 3. 数据 ----------
tr = pd.read_csv(os.path.join(DATA, "02_castelli_train.csv"))
va = pd.read_csv(os.path.join(DATA, "03_castelli_val.csv"))

print("构建元素描述符表...")
etab = build_element_table()
print("描述符维度:", etab.shape)

Xtr = featurize(tr, etab); ytr = tr.V.values
Xva = featurize(va, etab); yva = va.V.values
print("特征矩阵:", Xtr.shape, Xva.shape)

# ---------- 4. 训练（目标：低 V 区域精排序→对数变换压长尾）----------
ytr_t = np.log1p(ytr)
params = dict(objective="regression", n_estimators=2000, learning_rate=0.03,
              num_leaves=63, min_child_samples=40, subsample=0.8, subsample_freq=1,
              colsample_bytree=0.7, reg_lambda=1.0, random_state=42, n_jobs=-1)
model = lgb.LGBMRegressor(**params)
model.fit(Xtr, ytr_t, eval_set=[(Xva, np.log1p(yva))],
          callbacks=[lgb.early_stopping(100, verbose=False), lgb.log_evaluation(0)])
print(f"best iter: {model.best_iteration_}")

# ---------- 5. 评估 ----------
pred_va = np.expm1(model.predict(Xva))
rmse = np.sqrt(np.mean((pred_va - yva) ** 2))
print(f"\n[val] RMSE = {rmse:.4f}")

# 排序导向指标：near-positive 子集
for thresh in [2, 5]:
    mask = yva < thresh
    if mask.sum() > 5:
        tau, p = kendalltau(pred_va[mask], yva[mask])
        print(f"[val] V<{thresh} 子集 (n={mask.sum()}): Kendall tau = {tau:.4f} (p={p:.2e})")

# top-k 精度：预测 top-k 中有多少真低 V
for k in [20, 50, 100]:
    topk = np.argsort(pred_va)[:k]
    hit = (yva[topk] < 2).mean()
    print(f"[val] 预测 top-{k} 中真 V<2 比例 = {hit:.2%} (基线 {(yva<2).mean():.2%})")

# 全局 tau
tau_all, _ = kendalltau(pred_va, yva)
print(f"[val] 全局 Kendall tau = {tau_all:.4f}")

# ---------- 6. group-wise CV（(A,B) 对分组）----------
from sklearn.model_selection import GroupKFold
print("\n[group-CV] 5-fold on train:")
groups = tr.A + "|" + tr.B
gkf = GroupKFold(n_splits=5)
taus, rmses = [], []
for fold, (itr, ite) in enumerate(gkf.split(Xtr, ytr_t, groups)):
    m = lgb.LGBMRegressor(**{**params, "n_estimators": model.best_iteration_ or 1000})
    m.fit(Xtr.iloc[itr], ytr_t[itr])
    p = np.expm1(m.predict(Xtr.iloc[ite]))
    yt = ytr[ite]
    rmses.append(np.sqrt(np.mean((p - yt) ** 2)))
    mask = yt < 2
    tau = kendalltau(p[mask], yt[mask])[0] if mask.sum() > 5 else np.nan
    taus.append(tau)
    print(f"  fold{fold}: RMSE={rmses[-1]:.3f}, tau(V<2, n={mask.sum()})={tau:.4f}")
print(f"  mean: RMSE={np.mean(rmses):.3f}, tau={np.nanmean(taus):.4f}")

# ---------- 7. 特征重要性 ----------
imp = pd.Series(model.feature_importances_, index=Xtr.columns).sort_values(ascending=False)
print("\n[特征重要性 top15]")
print(imp.head(15).to_string())

# ---------- 8. 保存 ----------
model.booster_.save_model(os.path.join(OUT, "p1_lgbm_baseline.txt"))
imp.to_csv(os.path.join(OUT, "p1_feature_importance.csv"))
etab.to_csv(os.path.join(OUT, "element_descriptors.csv"))
print("\n模型与描述符表已保存到", OUT)
