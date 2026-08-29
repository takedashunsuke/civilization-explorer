"""Helpers for result/raw/run-NNN/ layout."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

RUN_DIR_PATTERN = re.compile(r"^run-(\d+)$")


def normalize_run_id(run: str) -> str:
    run = run.strip()
    if RUN_DIR_PATTERN.match(run):
        return run
    if run.isdigit():
        return f"run-{int(run):03d}"
    raise ValueError(f"invalid run id: {run!r} (use run-001 or 1)")


def next_run_id(raw_root: Path) -> str:
    nums: list[int] = []
    if raw_root.is_dir():
        for p in raw_root.iterdir():
            if p.is_dir():
                m = RUN_DIR_PATTERN.match(p.name)
                if m:
                    nums.append(int(m.group(1)))
    return f"run-{max(nums, default=0) + 1:03d}"


def resolve_run_dir(raw_root: Path, run: str | None) -> tuple[Path, str]:
    raw_root.mkdir(parents=True, exist_ok=True)
    run_id = normalize_run_id(run) if run else next_run_id(raw_root)
    return raw_root / run_id, run_id


def relative_repo_path(path: Path, root: Path) -> str:
    return str(path.relative_to(root)).replace("\\", "/")


def default_file_entries() -> list[dict[str, str]]:
    labels = {
        "lush": "豊か",
        "lean": "乏しい",
        "volatile": "災害多",
        "balanced": "標準",
    }
    return [
        {
            "variant": vid,
            "label_ja": labels[vid],
            "path": "",
            "json_path": "",
            "status": "pending",
        }
        for vid in ("lush", "lean", "volatile", "balanced")
    ]


def load_manifest(manifest_path: Path) -> dict[str, Any]:
    if manifest_path.exists():
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    return {
        "experiment": "controlled_experiment",
        "experiment_seed": 42,
        "milestone_turn": 10,
        "milestone_years": 100,
        "years_per_turn": 10,
        "start_year": 1000,
        "population": 5000,
        "latest_run": None,
        "runs": [],
    }


def upsert_run_manifest(
    manifest_path: Path,
    *,
    run_id: str,
    run_dir: Path,
    repo_root: Path,
    records: list[dict[str, Any]],
    llm_provider: str,
    ollama_model: str | None,
    milestone_turn: int,
    milestone_years: int,
    start_year: int,
    years_per_turn: int,
    experiment_seed: int,
) -> None:
    data = load_manifest(manifest_path)
    run_rel = relative_repo_path(run_dir, repo_root)
    recorded_at = datetime.now(timezone.utc).isoformat()

    by_variant = {r["variant"]: r for r in records}
    files: list[dict[str, Any]] = []
    for entry in default_file_entries():
        vid = entry["variant"]
        if vid in by_variant:
            rec = by_variant[vid]
            files.append({
                "variant": vid,
                "label_ja": entry["label_ja"],
                "path": f"{run_rel}/{rec['filename']}",
                "json_path": f"{run_rel}/{rec['json_filename']}",
                "status": "done",
            })
        else:
            files.append({**entry})

    run_record = {
        "id": run_id,
        "path": run_rel,
        "recorded_at": recorded_at,
        "experiment_seed": experiment_seed,
        "start_year": start_year,
        "years_per_turn": years_per_turn,
        "milestone_turn": milestone_turn,
        "milestone_years": milestone_years,
        "end_year": start_year + milestone_years,
        "llm_provider": llm_provider,
        "files": files,
    }
    if ollama_model:
        run_record["ollama_model"] = ollama_model

    runs: list[dict[str, Any]] = data.get("runs", [])
    replaced = False
    for i, existing in enumerate(runs):
        if existing.get("id") == run_id:
            runs[i] = run_record
            replaced = True
            break
    if not replaced:
        runs.append(run_record)
    runs.sort(key=lambda r: r.get("id", ""))

    data["runs"] = runs
    data["latest_run"] = run_id
    data["recorded_at"] = recorded_at
    data["llm_provider"] = llm_provider
    data["milestone_turn"] = milestone_turn
    data["milestone_years"] = milestone_years
    data["start_year"] = start_year
    data["years_per_turn"] = years_per_turn
    data["experiment_seed"] = experiment_seed
    if ollama_model:
        data["ollama_model"] = ollama_model

    manifest_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    run_meta = {
        "id": run_id,
        "recorded_at": recorded_at,
        "experiment_seed": experiment_seed,
        "start_year": start_year,
        "years_per_turn": years_per_turn,
        "milestone_turn": milestone_turn,
        "milestone_years": milestone_years,
        "end_year": start_year + milestone_years,
        "llm_provider": llm_provider,
        "files": files,
    }
    if ollama_model:
        run_meta["ollama_model"] = ollama_model
    (run_dir / "run.json").write_text(
        json.dumps(run_meta, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    ensure_analysis_run_dir(repo_root, run_id, result_run_path=run_rel)


def analysis_run_dir(repo_root: Path, run_id: str) -> Path:
    return repo_root / "analysis" / "output" / run_id


def ensure_analysis_run_dir(
    repo_root: Path,
    run_id: str,
    *,
    result_run_path: str,
) -> Path:
    """Create analysis/output/run-NNN/ and update analysis/output/manifest.json."""
    out_dir = analysis_run_dir(repo_root, run_id)
    out_dir.mkdir(parents=True, exist_ok=True)

    readme = out_dir / "README.md"
    if not readme.exists():
        readme.write_text(
            f"# 解析出力 — {run_id}\n\n"
            f"対応する生ログ: `{result_run_path}/`\n\n"
            "| ファイル | 内容 |\n"
            "|----------|------|\n"
            "| `comparison-*.md` | 4 世界の定量・定性比較 |\n"
            "| `agent-role-deep-dive-*.md` | 同一人物の役割差 |\n"
            "| `summary.md` | 提出用サマリー |\n"
            "| `llm-response-*.md` | （任意）LLM 生出力 |\n",
            encoding="utf-8",
        )

    manifest_path = repo_root / "analysis" / "output" / "manifest.json"
    data: dict[str, Any] = {"latest_run": run_id, "runs": []}
    if manifest_path.exists():
        data = json.loads(manifest_path.read_text(encoding="utf-8"))

    rel = relative_repo_path(out_dir, repo_root)
    entry = {
        "id": run_id,
        "path": rel,
        "result_run_path": result_run_path,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    runs: list[dict[str, Any]] = data.get("runs", [])
    replaced = False
    for i, existing in enumerate(runs):
        if existing.get("id") == run_id:
            runs[i] = {**existing, **entry}
            replaced = True
            break
    if not replaced:
        runs.append(entry)
    runs.sort(key=lambda r: r.get("id", ""))
    data["runs"] = runs
    data["latest_run"] = run_id
    manifest_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return out_dir
