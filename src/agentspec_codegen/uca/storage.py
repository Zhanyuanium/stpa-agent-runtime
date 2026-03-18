from __future__ import annotations

import json
from pathlib import Path

from .models import UcaKnowledgeBase


def load_uca_knowledge_base(path: str | Path) -> UcaKnowledgeBase:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return UcaKnowledgeBase.model_validate(payload)


def dump_uca_knowledge_base(knowledge_base: UcaKnowledgeBase, path: str | Path) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        knowledge_base.model_dump_json(indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
