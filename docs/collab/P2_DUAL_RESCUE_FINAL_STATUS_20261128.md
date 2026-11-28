# 双路径技术解救最终状态（2026-11-28）

甲：raw/rc 各一次 mutate，首次完整输出立即封存。两项 G1 COUNTEREXAMPLE、G2 FAIL；浮点输出近似统一×2，N8 逐元素等于 rescue1，未增加顶层调用。

乙：固定八格×1000=8000次独立 SA，全部有效返回，八格业务可行返回全部0；80块都无可行解，主成功率0/10、选择中位数+∞，条件regret分布未定义。全部不入围，B_receipt selected=null，SHA256 05332d1a016ddbd416eb2a09c2d50cd74ae2a8f0eb687ffeae5983c05e338055。

原始自旋独立复核通过：8000条、80块；按甲乙10配置复核27040个one-hot能量、10项反例；4727个保护文件哈希一致。无新拟合，无修复，无新增维度或split，无CIM，无SPQC1000，无论文写作/排版/编译。

已按授权全灭停止。下一步须用户另行批准技术方向；不得自行转去写论文。

完整技术报告 codex/P2_DUAL_RESCUE_RESULTS_20261128.md；八格表 codex/P2_DUAL_RESCUE_B_FULL_GRID_20261128.csv；新旧并列表 codex/P2_DUAL_RESCUE_HISTORY_20261128.csv。
