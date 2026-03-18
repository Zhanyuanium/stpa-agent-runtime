# Rule Compiler (UCA -> AgentSpec DSL)

## Purpose
- Convert validated UCA entries into deterministic AgentSpec `.spec` rules.
- Keep generation stable for regression and golden-file testing.
- Render rules using Jinja2 templates to align with project technical design.

## Input
- `UcaKnowledgeBase` from `src/agentspec_codegen/uca/models.py`.

## Output
- `CompilationArtifact` list:
  - `rule_id`
  - `uca_id`
  - `predicates`
  - `spec_text`

## Mapping Strategy
- Prefer `predicate_hints` from UCA entry.
- Fallback to risk-category defaults in `DEFAULT_PREDICATE_BY_RISK`.
- Rule ID normalization: `UCA-CODE-001` -> `uca_code_001`.
- Support both code-domain and shell-domain risk mappings.

## Regression Safety
- Golden snapshot in `tests/golden/`.
- Generated rule must parse with existing `Rule.from_text`.
- Shell UCA samples must compile and produce deterministic text.
