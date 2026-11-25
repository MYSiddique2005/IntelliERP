"""Offline evaluation of the concept checker (app/llm/semantics) on the labelled natural-error sentences.

    cd LLM && ../Backend/.venv/bin/python -m evaluation.semantics_eval

No model is called: the rule extractor and the deterministic verdicts run on the 686 pooled sentences that
were labelled for the TRACE study (results/trace/natural). IMPORTANT: the patterns were written after reading
these sentences, so the figures below are a DEVELOPMENT result, not a held-out one. They show what the
language can express, not how it would do on new answers; a fresh sample (answers not seen when the patterns
were written) is needed for that.
"""
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "Backend"))

from app.llm.semantics import SemanticVerifier  # noqa: E402

OUT = ROOT / "LLM" / "evaluation" / "results" / "trace" / "natural"
LABELS = ("false", "true", "no-claim", "unsure")


class _Source:  # enough of a FactSource to judge rule values, which need no data
    separation_of_duties = True

    @staticmethod
    def today():
        from datetime import date
        return date(2026, 10, 5)


def rate(k: int, n: int) -> str:
    return f"{k}/{n} ({100 * k / n:.0f}%)" if n else f"{k}/0"


def main() -> None:
    units = {row["row"]: row for row in map(json.loads, (OUT / "units.jsonl").read_text().splitlines())}
    with (OUT / "sheet-annotator-1.csv").open() as handle:
        labels = {int(r["row"]): r["label"].strip().lower() for r in csv.DictReader(handle) if r["label"].strip().lower() in LABELS}
    sampled = {(r["answer_id"], r["start"]) for r in map(json.loads, (OUT / "sample.jsonl").read_text().splitlines())}
    trace = defaultdict(set)
    for row in map(json.loads, (OUT / "flags.jsonl").read_text().splitlines()):
        if row["method"] == "TRACE-hybrid" and row.get("start") is not None:
            trace.add((row["answer_id"], row["start"])) if False else trace["hybrid"].add((row["answer_id"], row["start"]))
    verifier = SemanticVerifier(source=_Source())
    mine: dict[int, list] = {}
    for row_id, unit in units.items():
        verdicts = verifier.contradicted(unit["sentence"])
        if verdicts:
            mine[row_id] = verdicts
    key = lambda r: (units[r]["answer_id"], units[r]["start"])  # noqa: E731
    false_sample = [r for r in units if labels.get(r) == "false" and key(r) in sampled]
    sample_rows = [r for r in units if key(r) in sampled and labels.get(r) in LABELS]
    found_sem = [r for r in false_sample if r in mine]
    found_trace = [r for r in false_sample if key(r) in trace["hybrid"]]
    found_union = sorted(set(found_sem) | set(found_trace))
    flagged_labelled = [r for r in mine if labels.get(r) in ("false", "true", "no-claim")]
    correct = [r for r in flagged_labelled if labels[r] == "false"]
    union_flagged = {r for r in units if (r in mine or key(r) in trace["hybrid"]) and labels.get(r) in ("false", "true", "no-claim")}
    union_correct = [r for r in union_flagged if labels[r] == "false"]
    trace_flagged = {r for r in units if key(r) in trace["hybrid"] and labels.get(r) in ("false", "true", "no-claim")}
    lines = ["# Concept checker on the labelled natural-error sentences", "",
             "DEVELOPMENT result: the patterns were written after reading these sentences (see semantics_eval.py).", "",
             "| Method | Recall on the 19 false sentences of the random sample | Precision of flags (686 pooled sentences) |", "|---|---:|---:|",
             f"| TRACE-hybrid (published) | {rate(len(found_trace), len(false_sample))} | {rate(sum(labels[r] == 'false' for r in trace_flagged), len(trace_flagged))} |",
             f"| Concept checker alone | {rate(len(found_sem), len(false_sample))} | {rate(len(correct), len(flagged_labelled))} |",
             f"| TRACE-hybrid + concept checker | {rate(len(found_union), len(false_sample))} | {rate(len(union_correct), len(union_flagged))} |", ""]
    wrong = [r for r in flagged_labelled if labels[r] != "false"]
    lines.append(f"Concept checker flagged {len(mine)} of {len(units)} pooled sentences; {len(flagged_labelled)} labelled; wrong flags: {len(wrong)}.")
    lines.append(f"False sentences it found in the whole pool: {rate(len(correct), sum(1 for r in units if labels.get(r) == 'false'))}.")
    lines.append(f"In the random sample of {len(sample_rows)} labelled sentences it flagged {sum(r in mine for r in sample_rows)}.")
    lines += ["", "## Wrong flags", ""]
    for r in wrong:
        lines.append(f"- [{labels[r]}] {units[r]['sentence'][:160]}  <- {mine[r][0].subject}")
    lines += ["", "## False sentences in the random sample the concept checker missed", ""]
    for r in false_sample:
        if r not in mine:
            lines.append(f"- {units[r]['sentence'][:200]}")
    (OUT / "semantics-report.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
