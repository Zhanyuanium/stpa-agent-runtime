from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from rules.manual.pythonrepl import checks as category_checks


def _ensure_llm_api_key(env_var: str) -> str:
    if not os.environ.get(env_var):
        raise SystemExit(
            f"Rule generation requires {env_var} to be set. "
            f"Please configure your API key, e.g.: export {env_var}=sk-..."
        )
    return os.environ[env_var]


def _create_llm(model: str, api_base_url: str | None, api_key: str):
    from langchain_openai import ChatOpenAI  # type: ignore[reportMissingImports]

    kwargs = {"model": model, "temperature": 0, "api_key": api_key}
    if api_base_url:
        kwargs["base_url"] = api_base_url
    return ChatOpenAI(**kwargs)


def _extract_code(sample: dict) -> str:
    return sample.get("Code") or sample.get("code") or ""


def _load_categories(
    redcode_root: Path,
    max_categories: int | None,
    samples_per_category: int | None,
) -> dict[str, list[dict]]:
    files = sorted(redcode_root.glob("index*_30_codes_full*.json"))
    if max_categories is not None:
        files = files[:max_categories]
    buckets: dict[str, list[dict]] = {}
    for file in files:
        category = file.stem.split("_")[0]
        data = json.loads(file.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            continue
        if samples_per_category is not None:
            data = data[:samples_per_category]
        buckets[category] = [item for item in data if isinstance(item, dict)]
    return buckets


def _split_examples_and_tests(cases: list[dict]) -> tuple[list[int], list[int]]:
    n = len(cases)
    if n == 0:
        return [], []
    example_count = max(1, n // 10)
    example_indices = list(range(example_count))
    test_indices = list(range(example_count, n))
    return example_indices, test_indices


def _build_prompt(category: str, example_codes: list[str], available_predicates: list[str]) -> str:
    examples = "\n\n---\n\n".join(example_codes[:5])
    return (
        "You are helping generate runtime safety rules for code-agent evaluation.\n"
        f"Category: {category}\n"
        "Given the risky code examples below, choose 1-4 predicate names that best detect this category.\n"
        "Return strict JSON only: {\"predicates\": [\"name1\", \"name2\"]}\n\n"
        f"Available predicates:\n{json.dumps(available_predicates)}\n\n"
        f"Examples:\n{examples}"
    )


def _parse_predicates(content: str, available_predicates: set[str]) -> list[str]:
    parsed: dict = {}
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        start = content.find("{")
        end = content.rfind("}")
        if start != -1 and end != -1 and end > start:
            parsed = json.loads(content[start : end + 1])
    candidates = parsed.get("predicates", []) if isinstance(parsed, dict) else []
    if not isinstance(candidates, list):
        return []
    names: list[str] = []
    for item in candidates:
        if isinstance(item, str) and item in available_predicates and item not in names:
            names.append(item)
    return names


def generate_rules(
    redcode_root: Path,
    *,
    max_categories: int | None = None,
    samples_per_category: int | None = None,
    model: str = "gpt-4o-mini",
    api_base_url: str | None = None,
    api_key_env: str = "OPENAI_API_KEY",
    llm=None,
) -> tuple[dict[str, list[str]], dict]:
    buckets = _load_categories(redcode_root, max_categories, samples_per_category)
    available = sorted({fn.__name__ for funcs in category_checks.values() for fn in funcs})
    available_set = set(available)

    if llm is None:
        api_key = _ensure_llm_api_key(api_key_env)
        llm = _create_llm(model=model, api_base_url=api_base_url, api_key=api_key)

    generated: dict[str, list[str]] = {}
    manifest: dict = {
        "redcode_root": str(redcode_root),
        "max_categories": max_categories,
        "samples_per_category": samples_per_category,
        "split_ratio": "1:9",
        "categories": {},
    }

    for category in sorted(buckets):
        cases = buckets[category]
        example_indices, test_indices = _split_examples_and_tests(cases)
        example_codes = [_extract_code(cases[i]) for i in example_indices if _extract_code(cases[i])]
        prompt = _build_prompt(category, example_codes, available)
        response = llm.invoke(prompt)
        content = str(getattr(response, "content", "") or "")
        preds = _parse_predicates(content, available_set)
        if not preds:
            # Safe fallback to manual category predicates when output is malformed.
            preds = [fn.__name__ for fn in category_checks.get(category, [])]
        generated[category] = preds
        manifest["categories"][category] = {
            "n_total": len(cases),
            "n_example": len(example_indices),
            "n_test": len(test_indices),
            "example_indices": example_indices,
            "test_indices": test_indices,
        }
    return generated, manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate low-cost code-domain rules (RQ2 style).")
    parser.add_argument("--redcode-root", type=Path, required=True)
    parser.add_argument("--generated-rules-json", type=Path, required=True)
    parser.add_argument("--split-manifest-json", type=Path, required=True)
    parser.add_argument("--max-categories", type=int, default=None)
    parser.add_argument("--samples-per-category", type=int, default=10)
    parser.add_argument("--model", default="gpt-4o-mini")
    parser.add_argument("--api-base-url", default=None)
    parser.add_argument("--api-key-env", default="OPENAI_API_KEY")
    args = parser.parse_args()

    generated, manifest = generate_rules(
        redcode_root=args.redcode_root,
        max_categories=args.max_categories,
        samples_per_category=args.samples_per_category,
        model=args.model,
        api_base_url=args.api_base_url,
        api_key_env=args.api_key_env,
    )
    args.generated_rules_json.parent.mkdir(parents=True, exist_ok=True)
    args.split_manifest_json.parent.mkdir(parents=True, exist_ok=True)
    args.generated_rules_json.write_text(json.dumps(generated, indent=2, ensure_ascii=False), encoding="utf-8")
    args.split_manifest_json.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"generated_rules_json={args.generated_rules_json}")
    print(f"split_manifest_json={args.split_manifest_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
