# Benchmarks（数据集放置与下载指引）

本仓库**不提交**上游大型数据集（如 RedCode-Exec / MBPP / ShellBench / AgentHarm）。复现者需自行下载并放置到本地 `benchmarks/` 目录下；本仓库提供脚本与校验工具，确保目录结构与文件格式正确。

## 1) 目录结构（复现者本地应具备）

```text
benchmarks/
├─ README.md
├─ RedCode-Exec/
│  ├─ py2text_dataset_json/          # Code 域 risky（RedCode-Exec）
│  └─ bash2text_dataset_json/        # Shell 域 risky（RedCode-Exec）
├─ MBPP/
│  └─ mbpp_code_samples.json         # Code 域 safe（从 HF 下载后标准化）
├─ ShellBench/
│  └─ shellbench_safe_commands.json  # Shell 域 safe（clone + 抽取后标准化）
├─ AgentHarm/
│  └─ agentharm_samples.json         # Owner-harm 评测样本（HF）
└─ current_eval/
   ├─ code_safe_equal_mbpp.json
   ├─ shell_safe_equal_shellbench.json
   └─ current_eval_manifest.json
```

说明：
- `RedCode-Exec/*2text_dataset_json/`：风险样本目录，来自 RedCode-Exec（上游提供按类别拆分的 JSON）。
- `MBPP/*.json`、`ShellBench/*.json`：安全样本（用于与 risky 配平，构建 current-eval）。
- `current_eval/`：由脚本从 MBPP/ShellBench 构建得到的配平 safe 集合（可再现生成，不需要提交到仓库）。

## 2) 获取数据集（推荐脚本）

### 2.1 RedCode-Exec（GitHub）

- 上游仓库：`https://github.com/AI-secure/RedCode`
- 本仓库提供提示脚本（不会自动下载大文件）：

```bash
# Linux/macOS/WSL
bash scripts/fetch_redcode.sh
```

```powershell
# Windows PowerShell
pwsh scripts/fetch_redcode.ps1
```

将下载得到的目录放置为：
- `benchmarks/RedCode-Exec/py2text_dataset_json`
- `benchmarks/RedCode-Exec/bash2text_dataset_json`

### 2.2 MBPP / ShellBench / AgentHarm（自动下载与标准化）

本仓库脚本会：
- 从 HuggingFace 下载 MBPP、AgentHarm
- 从 GitHub clone ShellBench
- 统一导出为本仓库期望的 JSON 文件名与字段

```bash
uv run python scripts/fetch_external_benchmarks.py --output-root benchmarks
```

运行成功后，至少应存在：
- `benchmarks/MBPP/mbpp_code_samples.json`
- `benchmarks/ShellBench/shellbench_safe_commands.json`
- `benchmarks/AgentHarm/agentharm_samples.json`

## 3) 构建 current_eval（配平 safe 集）

`current_eval` 用于“等量 safe vs risky”的平衡评测。它由 RedCode risky 数量决定 safe 采样数，因此可重复生成。

```bash
uv run python scripts/build_current_eval_dataset.py \
  --redcode-code-root benchmarks/RedCode-Exec/py2text_dataset_json \
  --redcode-shell-root benchmarks/RedCode-Exec/bash2text_dataset_json \
  --mbpp-json benchmarks/MBPP/mbpp_code_samples.json \
  --shellbench-json benchmarks/ShellBench/shellbench_safe_commands.json \
  --output-dir benchmarks/current_eval
```

## 4) 校验（强烈建议先跑）

```bash
uv run python scripts/verify_dataset.py --redcode-root ./benchmarks/RedCode-Exec/py2text_dataset_json
```

可选：如果你已经生成了 `current_eval_manifest.json`，也可以额外检查（见 `scripts/verify_dataset.py` 的参数说明）。

## 5) 常见问题

- Q: 为什么不把数据集提交到仓库？
  - A: 体积大、许可不一，且上游数据集本身已有权威发布渠道；本仓库以“可复现的下载与标准化流程”为准。

- Q: 我没有 HuggingFace 访问权限怎么办？
  - A: 你也可以手动下载对应数据集，然后按照上述目录结构放置，并确保文件名与脚本期望一致。
