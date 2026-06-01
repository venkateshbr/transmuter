# Agent Eval Datasets

These deterministic evals are the committed phase-5 baseline for issue #81.
They run from the CI `evals` job with:

```bash
cd apps/api && uv run pytest ../../tests/evals -v --tb=short
```

The suite intentionally avoids external LLM calls. It checks that agent-facing
security validators reject prompt-injection and PII before tool execution, and
that the initiative intake fallback generates complete, reviewable financial,
KPI, risk, and milestone suggestions for representative business scenarios.

Committed JSONL datasets:

- `initiative_intake_evals.jsonl`: 20 raw intake prompts.
- `kpi_suggestion_evals.jsonl`: 10 KPI suggestion cases.
- `risk_pattern_scan_evals.jsonl`: 10 risk-pattern cases.
- `meeting_transcript_evals.jsonl`: 10 meeting transcript extraction cases.
