# 测试说明

更多入口见 `docs/index.md`。

## 1. 测试类型

- **Unit**：解析器、谓词、编译器映射、运行时动作等
- **Integration**：JSON UCA → `.spec` → 解释器 `check/enforce` 的联调链路
- **E2E**：最小可跑通用例与指标输出（冒烟）

## 2. 目录约定

- `tests/unit/`
- `tests/integration/`
- `tests/e2e/`
- `tests/golden/`

## 3. 运行

```bash
uv run pytest
```

覆盖率（核心模块）：

```bash
uv run pytest --cov=src/agentspec_codegen --cov=scripts --cov-report=term-missing
```

