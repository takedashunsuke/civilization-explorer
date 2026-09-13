"""Batch analysis helpers for result/raw/run-NNN/ → analysis/output/run-NNN/."""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

VARIANT_ORDER = ("lush", "lean", "volatile", "balanced")
VARIANT_LABEL_JA = {
    "lush": "豊か",
    "lean": "乏しい",
    "volatile": "災害多",
    "balanced": "標準",
}

SUMMARY_ROWS: list[tuple[str, str, str]] = [
    ("population_alive", "生存人口", "d"),
    ("population_delta_pct", "人口変化 %", "pct"),
    ("resource_pool", "共有資源（合計）", "f1"),
    ("trade_openness_mean", "交易開放（平均）", "f1"),
    ("conflicts_total", "争い（累計）", "d"),
    ("cooperations_total", "共同（累計）", "d"),
    ("regime_shifts", "体制転換（累計）", "d"),
    ("disasters", "災害（累計）", "d"),
    ("dominant_archetype", "台頭タイプ（代表）", "s"),
]

# Phase B resilience rows (shown under a dedicated section)
RESILIENCE_ROWS: list[tuple[str, str, str]] = [
    ("shock_count", "ショック数", "d"),
    ("disaster_deaths", "災害死", "d"),
    ("pop_trough", "人口最下点", "d"),
    ("pop_recovery_ratio", "人口回復率", "f1"),
    ("pop_retention_ratio", "人口保持率", "f1"),
    ("resource_recovery_halftime", "資源半減回復ターン", "d"),
    ("regime_break", "制度破綻", "s"),
    ("coop_vs_conflict_post_shock", "ショック後 協力比", "f1"),
    ("resilience_label", "レジリエンスラベル", "s"),
]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_result_manifest(repo_root: Path) -> dict[str, Any]:
    path = repo_root / "result" / "manifest.json"
    if not path.exists():
        return {"runs": [], "tests": []}
    return load_json(path)


def complete_run_entries(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for run in manifest.get("runs", []):
        files = run.get("files") or []
        done = [f for f in files if f.get("status") == "done" and f.get("json_path")]
        if len(done) >= 4:
            out.append(run)
    return sorted(out, key=lambda r: r.get("id", ""))


def run_json_paths(repo_root: Path, run: dict[str, Any]) -> dict[str, Path]:
    by_variant: dict[str, Path] = {}
    for entry in run.get("files", []):
        if entry.get("status") != "done":
            continue
        jp = entry.get("json_path")
        vid = entry.get("variant")
        if jp and vid:
            by_variant[vid] = repo_root / jp
    missing = [v for v in VARIANT_ORDER if v not in by_variant]
    if missing:
        raise FileNotFoundError(f"{run.get('id')}: missing variants {missing}")
    return by_variant


def load_run_payloads(repo_root: Path, run: dict[str, Any]) -> dict[str, dict[str, Any]]:
    paths = run_json_paths(repo_root, run)
    payloads: dict[str, dict[str, Any]] = {}
    for vid in VARIANT_ORDER:
        data = load_json(paths[vid])
        payloads[vid] = data
    return payloads


def _fmt_cell(value: Any, kind: str) -> str:
    if value is None or value == "":
        return "—"
    if kind == "d":
        return str(int(value))
    if kind == "f1":
        return f"{float(value):.1f}"
    if kind == "pct":
        return f"{float(value):+.1f}"
    return str(value)


def _bold_extremes(row_values: list[str], kind: str) -> list[str]:
    if kind in {"s"}:
        return row_values
    nums: list[float] = []
    for v in row_values:
        try:
            nums.append(float(v.replace("+", "")))
        except ValueError:
            return row_values
    if len(set(nums)) <= 1:
        return row_values
    lo, hi = min(nums), max(nums)
    out: list[str] = []
    for v, n in zip(row_values, nums, strict=True):
        if n == hi or n == lo:
            out.append(f"**{v}**")
        else:
            out.append(v)
    return out


def build_comparison_markdown(
    *,
    run_id: str,
    run: dict[str, Any],
    payloads: dict[str, dict[str, Any]],
    analysis_date: str,
    llm_note: str | None = None,
) -> str:
    summaries = {vid: payloads[vid]["experiment_summary"] for vid in VARIANT_ORDER}
    meta = payloads[VARIANT_ORDER[0]]
    seed = meta.get("experiment_seed") or summaries["lush"].get("seed")
    start_year = meta.get("start_year")
    end_year = meta.get("calendar_year")
    years = meta.get("milestone_years")
    llm = meta.get("llm") or {}
    result_path = run.get("path", f"result/raw/{run_id}")

    lines = [
        f"# 4 世界比較 — {analysis_date}",
        "",
        f"根拠: `{result_path}/civ-*-AD{end_year}-turn*.json` の `experiment_summary`",
        f"（seed {seed}・{years} 年・AD {start_year}→{end_year}"
        + (f"・{llm.get('provider')}" if llm.get("provider") else "")
        + "）",
        "",
    ]
    if llm_note:
        lines.extend([f"> {llm_note}", ""])

    lines.extend(["## 1. 定量比較表", "", "| 指標 | 豊か | 乏しい | 災害多 | 標準 |", "|------|------|--------|--------|------|"])

    for key, label, kind in SUMMARY_ROWS:
        cells = [_fmt_cell(summaries[vid].get(key), kind) for vid in VARIANT_ORDER]
        cells = _bold_extremes(cells, kind)
        lines.append("| " + " | ".join([label, *cells]) + " |")

    lines.extend([
        "",
        "## 1b. レジリエンス（回復／崩壊）",
        "",
        "| 指標 | 豊か | 乏しい | 災害多 | 標準 |",
        "|------|------|--------|--------|------|",
    ])
    for key, label, kind in RESILIENCE_ROWS:
        raw = []
        for vid in VARIANT_ORDER:
            val = summaries[vid].get(key)
            if isinstance(val, bool):
                val = "yes" if val else "no"
            raw.append(_fmt_cell(val, kind))
        if kind != "s":
            raw = _bold_extremes(raw, kind)
        lines.append("| " + " | ".join([label, *raw]) + " |")

    lines.extend([
        "",
        "読み方: `pop_recovery_ratio` はショック前→最下点の落差に対する期末の戻り率。"
        " 単調減少では 0 になりやすいので、併せて `pop_retention_ratio`（期末/ショック前）を見る。"
        " `resource_recovery_halftime` はショック前資源の 50% を一度割ったあと戻るまでのターン（割っていなければ —）。"
        " `resilience_label` は recovered / stressed / collapsed の簡易ラベル。",
        "",
        "## 2. 以降（定性）",
        "",
        "環境ごとの要約・意外な差・発表フックは `--llm` 実行後に `llm-response-*.md` を反映するか、手動で追記してください。",
        "",
        f"プロンプト: [analysis/prompt.md](../../analysis/prompt.md)",
        "",
    ])
    return "\n".join(lines)


def build_summary_markdown(
    *,
    run_id: str,
    run: dict[str, Any],
    payloads: dict[str, dict[str, Any]],
    comparison_name: str,
    analysis_date: str,
) -> str:
    meta = payloads[VARIANT_ORDER[0]]
    seed = meta.get("experiment_seed")
    start_year = meta.get("start_year")
    end_year = meta.get("calendar_year")
    years = meta.get("milestone_years")
    result_path = run.get("path", f"result/raw/{run_id}")
    llm = meta.get("llm") or {}

    lines = [
        f"# 実行結果サマリー — {run_id}",
        "",
        f"> **実行回:** `{run_id}` · 生ログ: [{result_path}/](../../{result_path}/)  ",
        f"> 比較: [{comparison_name}](./{comparison_name})",
        "",
        f"自動生成: {analysis_date}（`scripts/run-analysis-batch.sh`）",
        "",
        "---",
        "",
        "## 実行条件",
        "",
        "| 項目 | 値 |",
        "|------|-----|",
        f"| experiment_seed | {seed} |",
        f"| 年数 | {years} 年（暦年ラベル AD {start_year}→{end_year}） |",
        f"| LLM（実験時） | {llm.get('provider', '—')}"
        + (f" / `{llm.get('ollama_model')}`" if llm.get("ollama_model") else "")
        + " |",
        "",
        "## 定量比較",
        "",
        "記入元: `experiment_summary`（詳細は comparison を参照）",
        "",
        "| 指標 | 豊か | 乏しい | 災害多 | 標準 |",
        "|------|------|--------|--------|------|",
    ]

    summaries = {vid: payloads[vid]["experiment_summary"] for vid in VARIANT_ORDER}
    for key, label, kind in SUMMARY_ROWS[:6]:
        cells = [_fmt_cell(summaries[vid].get(key), kind) for vid in VARIANT_ORDER]
        lines.append("| " + " | ".join([label, *cells]) + " |")

    lines.extend([
        "",
        "## 定性メモ",
        "",
        "（`--llm` または手動で追記）",
        "",
    ])
    return "\n".join(lines)


def extract_prompt_template(repo_root: Path) -> str:
    text = (repo_root / "analysis" / "prompt.md").read_text(encoding="utf-8")
    m = re.search(r"```\n(あなたは文明シミュレーション.*?)\n```", text, re.DOTALL)
    if not m:
        raise RuntimeError("Could not extract prompt template from analysis/prompt.md")
    return m.group(1).strip()


def build_llm_user_message(repo_root: Path, run: dict[str, Any], payloads: dict[str, dict[str, Any]]) -> str:
    template = extract_prompt_template(repo_root)
    compact = {
        vid: {
            "variant_label_ja": VARIANT_LABEL_JA[vid],
            "experiment_summary": payloads[vid]["experiment_summary"],
            "start_year": payloads[vid].get("start_year"),
            "calendar_year": payloads[vid].get("calendar_year"),
            "milestone_years": payloads[vid].get("milestone_years"),
        }
        for vid in VARIANT_ORDER
    }
    return (
        f"{template}\n\n"
        "## 添付データ（JSON 抜粋）\n"
        f"{json.dumps(compact, ensure_ascii=False, indent=2)}"
    )


def call_ollama_chat(
    *,
    base_url: str,
    model: str,
    prompt: str,
    timeout_sec: float = 120.0,
) -> str:
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "options": {"temperature": 0.35, "num_predict": 2048},
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{base_url.rstrip('/')}/api/chat",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    message = data.get("message") or {}
    return str(message.get("content") or "").strip()


def upsert_analysis_manifest(
    repo_root: Path,
    *,
    run_id: str,
    result_run_path: str,
    files: dict[str, str],
) -> None:
    manifest_path = repo_root / "analysis" / "output" / "manifest.json"
    data: dict[str, Any] = {"latest_run": run_id, "runs": [], "tests": []}
    if manifest_path.exists():
        data = load_json(manifest_path)

    rel_dir = f"analysis/output/{run_id}"
    entry = {
        "id": run_id,
        "path": rel_dir,
        "result_run_path": result_run_path,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "files": files,
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
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def build_cross_run_markdown(
    repo_root: Path,
    runs: list[dict[str, Any]],
    analysis_date: str,
) -> str:
    lines = [
        f"# 実証 run 横断サマリー — {analysis_date}",
        "",
        f"対象: {len(runs)} run（`result/manifest.json` の完了分）",
        "",
        "## 争い（累計）— 災害多 − 乏しい",
        "",
        "| run | seed | 豊か | 乏しい | 災害多 | 標準 | Δ(災害多−乏しい) |",
        "|-----|------|------|--------|--------|------|------------------|",
    ]
    for run in runs:
        payloads = load_run_payloads(repo_root, run)
        seed = payloads["lush"].get("experiment_seed")
        vals = {
            vid: int(payloads[vid]["experiment_summary"]["conflicts_total"])
            for vid in VARIANT_ORDER
        }
        delta = vals["volatile"] - vals["lean"]
        lines.append(
            f"| {run['id']} | {seed} | {vals['lush']} | {vals['lean']} | "
            f"{vals['volatile']} | {vals['balanced']} | {delta:+d} |"
        )
    lines.append("")
    return "\n".join(lines)


def process_run(
    repo_root: Path,
    run: dict[str, Any],
    *,
    use_llm: bool = False,
    force: bool = False,
    analysis_date: str | None = None,
) -> dict[str, str]:
    from experiment_runs import ensure_analysis_run_dir

    run_id = run["id"]
    result_path = run.get("path", f"result/raw/{run_id}")
    payloads = load_run_payloads(repo_root, run)
    day = analysis_date or date.today().isoformat()
    comparison_name = f"comparison-{day}.md"
    out_dir = ensure_analysis_run_dir(repo_root, run_id, result_run_path=result_path)
    comparison_path = out_dir / comparison_name
    summary_path = out_dir / "summary.md"

    if comparison_path.exists() and not force:
        print(f"  skip {run_id}: {comparison_name} exists (use --force)")
        return {"comparison": str(comparison_path.relative_to(repo_root))}

    llm_note = None
    llm_response_name: str | None = None

    if use_llm:
        from config import get_settings

        settings = get_settings()
        if settings.llm_provider != "ollama":
            raise RuntimeError("--llm requires LLM_PROVIDER=ollama in backend/.env")
        prompt = build_llm_user_message(repo_root, run, payloads)
        print(f"  LLM {run_id} ...", flush=True)
        try:
            body = call_ollama_chat(
                base_url=settings.ollama_base_url,
                model=settings.ollama_model,
                prompt=prompt,
                timeout_sec=max(120.0, settings.llm_timeout_sec * 10),
            )
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Ollama request failed for {run_id}: {exc}") from exc
        llm_response_name = f"llm-response-{day}.md"
        (out_dir / llm_response_name).write_text(
            f"# LLM 解析生出力 — {run_id}\n\n{body}\n",
            encoding="utf-8",
        )
        llm_note = "定性セクションは `llm-response-*.md` を参照"

    comparison_path.write_text(
        build_comparison_markdown(
            run_id=run_id,
            run=run,
            payloads=payloads,
            analysis_date=day,
            llm_note=llm_note,
        ),
        encoding="utf-8",
    )
    summary_path.write_text(
        build_summary_markdown(
            run_id=run_id,
            run=run,
            payloads=payloads,
            comparison_name=comparison_name,
            analysis_date=day,
        ),
        encoding="utf-8",
    )

    files: dict[str, str] = {
        "summary": f"analysis/output/{run_id}/summary.md",
        "comparison": f"analysis/output/{run_id}/{comparison_name}",
    }
    if llm_response_name:
        files["llm_response"] = f"analysis/output/{run_id}/{llm_response_name}"

    upsert_analysis_manifest(repo_root, run_id=run_id, result_run_path=result_path, files=files)
    print(f"  wrote {run_id}: {comparison_name}, summary.md" + (f", {llm_response_name}" if llm_response_name else ""))
    return files
