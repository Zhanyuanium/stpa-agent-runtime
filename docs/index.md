# 文档索引（从这里开始）

本文档集的目标是把“设计说明、复现步骤、开发规范、限制与边界”拆分为**短而一致**的主题页，避免 `README.md` 过载与重复。

## 1. 我应该读哪一篇？

- **想快速跑通一次实验**：`docs/experiments/code-domain.md`（Code）与 `docs/shell-runtime.md`（Shell）
- **想理解系统由哪些模块组成**：`docs/architecture.md`
- **想核对产物与审计口径**：`docs/runtime-guard.md`
- **想做开发与提测**：`docs/development.md`、`docs/testing.md`
- **想了解当前局限与未来工作**：`docs/limitations.md`

## 2. 文档约定

- **语言**：默认中文；保留必要的英文术语/文件名以避免歧义。
- **命令**：示例以 `uv` 为入口；路径使用相对路径（以仓库根目录为基准）。
- **数据政策**：上游数据与运行产物不入库（见 `.gitignore`），文档只描述“如何放置/如何生成”。

