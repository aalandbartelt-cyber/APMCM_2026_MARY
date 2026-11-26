#!/usr/bin/env python3
"""共享特征工程模块（canonical 版本）。
p1_baseline.py 内有同逻辑的行内副本（已验证产出，未动）；新代码一律从这里 import。

纪律红线：仅用 (A,B,X) 可推导特征。DFT 输出列（a_lat/volume/gap_is_direct/mu_b/
fermi_level/fermi_width）在池/盲池推理时不可用，禁入特征。
"""
import numpy as np
import pandas as pd

ZUNGER = "/home/mary/apmcm2026/01_参考学习/量子知识补充（forD题）/02_GitHub开源/perovskite-tutorial/zungervalenceradius.csv"
X_FAMILIES = ["O3", "NO2", "FO2", "N2O", "N3", "O2S", "FNO"]
ELEMS52 = "Ag Al As Au B Ba Be Bi Ca Cd Co Cr Cs Cu Fe Ga Ge Hf Hg In Ir K La Li Mg Mn Mo Na Nb Ni Os Pb Pd Pt Rb Re Rh Ru Sb Sc Si Sn Sr Ta Te Ti Tl V W Y Zn Zr".split()


def build_element_table():
    """mendeleev 全属性 + zunger 价态半径。52 元素 × 14 描述符。
    缺失值以列中位数填充（少数元素缺 ea/irad 等）。"""
    from mendeleev import element as melement
    z = pd.read_csv(ZUNGER).set_index("Element")
    rows = {}
    for sym in ELEMS52:
        e = melement(sym)
        rows[sym] = dict(
            Z=e.atomic_number, mass=e.atomic_weight,
            en=e.electronegativity_pauling() if e.electronegativity_pauling() else np.nan,
            group=e.group_id if e.group_id else 0, period=e.period,
            ie1=e.ionenergies.get(1, np.nan),
            ea=e.electron_affinity if e.electron_affinity else np.nan,
            irad=(np.median([r.ionic_radius for r in e.ionic_radii]) if e.ionic_radii else np.nan),
            arad=e.atomic_radius if e.atomic_radius else np.nan,
            covalent=e.covalent_radius if e.covalent_radius else np.nan,
            nvalence=e.nvalence() if e.nvalence() else 0,
            Rs=z.loc[sym, "Rs"], Rp=z.loc[sym, "Rp"], Rd=z.loc[sym, "Rd"],
        )
    df = pd.DataFrame(rows).T
    df.index.name = "elem"
    return df.fillna(df.median(numeric_only=True))


def featurize(df, etab):
    """(A,B,X) → 特征矩阵。A/B 各 14 描述符 + 4 交互 + X one-hot(7) = 39+1+7 维。"""
    A = etab.loc[df.A.values].reset_index(drop=True)
    B = etab.loc[df.B.values].reset_index(drop=True)
    feats = {}
    for p in etab.columns:
        feats[f"A_{p}"] = A[p].values
        feats[f"B_{p}"] = B[p].values
    feats["d_en"] = np.abs(A["en"].values - B["en"].values)
    feats["d_irad"] = np.abs(A["irad"].values - B["irad"].values)
    feats["d_Z"] = np.abs(A["Z"].values - B["Z"].values)
    feats["sum_ie1"] = A["ie1"].values + B["ie1"].values
    feats["a_eq_b"] = df.a_eq_b.values
    X = pd.get_dummies(df.X)
    for fam in X_FAMILIES:  # 保证列齐全有序（池文件可能缺某些族）
        if fam not in X.columns:
            X[fam] = 0.0
    X = X[X_FAMILIES].astype(float)
    F = pd.DataFrame(feats)
    return pd.concat([F.reset_index(drop=True), X.reset_index(drop=True)], axis=1)
