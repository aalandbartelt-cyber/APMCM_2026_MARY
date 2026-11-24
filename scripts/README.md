# scripts

入口脚本/构建/审计。

建议：

```text
run_<problem>.py           一键跑本题
build_paper.sh / Build_PDF.py  编译论文
make_figures.py            图源
audit_*.py                 结果/提交检查（可调用 skill 脚本）
```

规则：

- 脚本里不写裸 `python`/`Rscript`；用环境变量或绝对路径。
- 输入/输出路径用相对路径或环境变量，不写本机用户名。
- 运行命令、预期输出、未测范围写进 README。
