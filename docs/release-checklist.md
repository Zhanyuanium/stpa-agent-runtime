# 发布前检查清单（自检用）

更多入口见 `docs/index.md`。这里的“发布”指一次可复现的实验/论文产出快照，而非对外发布包。

## 1. 质量门禁

- [ ] `uv run pytest` 通过
- [ ] `uv run pytest --cov=src --cov-report=term-missing` 可运行且无失败
- [ ] 最小 E2E 冒烟链路通过（能产出结果 JSON 与 report）

## 2. 产物校验

- [ ] UCA KB 文件可被加载/校验（Code/Shell）
- [ ] 编译器能生成可解析的 `.spec`
- [ ] 实验脚本能同时输出 `*_result.json` 与 `*_report.md`
- [ ] `01~05` 审计产物齐全（见 `docs/runtime-guard.md`）

## 3. 安全与数据政策

- [ ] 未提交基准原始数据（`benchmarks/*`）
- [ ] 未提交 API Key / `.env` 等敏感信息
- [ ] 文档写清本地数据放置位置与生成方式（不要求入库）

## 4. 文档一致性

- [ ] `README.md` 为导航页且不与 `docs/` 重复冲突
- [ ] `docs/architecture.md`、`docs/runtime-guard.md`、`docs/shell-runtime.md` 已更新
- [ ] 复现步骤经过一次实际验证（命令与路径不失配）
- [ ] 导出报告前复核 `docs/limitations.md`（避免过度解读）

