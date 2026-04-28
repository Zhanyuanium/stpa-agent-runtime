# 开发指南

更多入口见 `docs/index.md`。

## 1. 环境

- Python **3.11+**（建议）
- 依赖管理：`uv`

## 2. 初始化

```bash
uv sync --extra dev
```

## 3. 常用命令

```bash
uv run pytest
uv run pytest --cov=src --cov-report=term-missing
```

## 4. 分支与提交约定

- 建议在本地特性分支上开发。
- 提交信息采用简洁前缀风格（与仓库历史一致）：
  - `feat(scope): ...`
  - `fix(scope): ...`
  - `test(scope): ...`
  - `docs(scope): ...`
  - `chore(scope): ...`

