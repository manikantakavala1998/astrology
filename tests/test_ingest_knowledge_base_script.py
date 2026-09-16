import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

_SCRIPT_PATH = Path(__file__).resolve().parent.parent / "scripts" / "ingest_knowledge_base.py"


def _load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("ingest_knowledge_base", _SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_main_ingests_and_makes_content_queryable(tmp_path: Path) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    (source_dir / "notes.txt").write_text(
        "Jupiter in the 7th house brings a wise and supportive spouse.", encoding="utf-8"
    )
    store_path = tmp_path / "store"

    script = _load_script()
    total_chunks = script.main(source_dir, store_path=store_path)
    assert total_chunks >= 1

    from vedic_astro.rag import knowledge_base as kb
    from vedic_astro.rag.embeddings import embed

    results = kb.query(embed("What does Jupiter in the 7th house mean?"), top_k=1, store_path=store_path)
    assert results
    assert "Jupiter" in results[0]


def test_main_raises_for_missing_source_dir(tmp_path: Path) -> None:
    script = _load_script()
    with pytest.raises(SystemExit):
        script.main(tmp_path / "does-not-exist", store_path=tmp_path / "store")


def test_main_raises_when_no_supported_files_found(tmp_path: Path) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    (source_dir / "readme.xyz").write_text("nothing supported here", encoding="utf-8")

    script = _load_script()
    with pytest.raises(SystemExit):
        script.main(source_dir, store_path=tmp_path / "store")
