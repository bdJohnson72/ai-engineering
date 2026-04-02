# CLAUDE.md

## Project Overview

Personal AI/ML learning repository. Organized by source (courses, projects, sandbox). Not a production codebase — optimized for learning and shareability.

## Development Environment

- **Python**: 3.12+
- **Package Manager**: uv
- **Primary Interface**: Jupyter notebooks

```bash
uv sync                  # core deps (numpy, pandas, matplotlib, jupyter)
uv sync --extra ml       # + scikit-learn, torch
uv sync --extra llm      # + openai, gradio
uv sync --extra all      # everything
jupyter lab              # start working
```

## Structure

- `courses/` — Organized by source (karpathy, datacamp, hands-on-ml, etc.)
- `projects/` — Original applied work (tool-calling, embeddings)
- `kaggle/` — Competition notebooks
- `sandbox/` — Scratch work and experiments
- `journal.md` — Chronological learning log

## Conventions

- One folder per course or project
- Notebooks should be self-contained (explain context in markdown cells)
- Data files live alongside their notebooks in a `data/` subfolder
- No formal test/lint pipeline — this is a learning repo
