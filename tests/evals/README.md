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
