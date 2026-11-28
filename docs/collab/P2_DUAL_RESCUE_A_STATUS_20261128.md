# 双路径解救：路径甲首个回报点

两发首次完整输出均封存；各一次调用，无重跑。两项 G1 COUNTEREXAMPLE、G2 FAIL，按已冻结协议进入路径乙固定八格，无甲附加候选。

|配置|G1|G2|最坏原regret|整数矩阵与rescue1是否相同|首次输出SHA256|
|---|---|---|---:|---|---|
|A-raw-M8|COUNTEREXAMPLE|FAIL|45.650041072698|True|7f5937a437c177ff767813511e0f7d741699d19194b655d0bd8e72993b8694c7|
|A-rc-M8|COUNTEREXAMPLE|FAIL|26.530610677732|True|a54cbaf63845d47d1dcce94c2e8122b0bbf671e089b05c9ef9c172b7a933b331|

生成前冻结：81f47ede613977cdc050afb923d38302b6fc7dac。A_receipt SHA256：81895fa84e9495692fdcb9ce0f174a94989e143e0d4fec8b41b8a8f9b18b6380。
所有旧结果保留，尚无新 SA 或真机提交；即将按协议执行乙，不写论文。
