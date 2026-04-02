# AI Engineering

Applied AI & ML — courses, projects, and experiments.

## Structure

```
courses/          Course work organized by source
  datacamp/       DataCamp ML courses (KNN, logistic regression, zero-to-GPT)
  hands-on-ml/    Geron's Hands-On ML (housing prices, classification)
  karpathy/       Karpathy's Zero to Hero (makemore, backprop)
  practical-stats/ Practical Statistics for Data Scientists

projects/         Original applied work
  tool-calling/   LLM tool-calling demo (Salesforce + SQLite, Gradio UI)
  embeddings/     Text embeddings exploration

kaggle/           Kaggle competitions (Titanic)
sandbox/          Scratch notebooks and experiments
```

## Setup

```bash
uv sync                          # install core deps
uv sync --extra ml               # + scikit-learn, torch
uv sync --extra llm              # + openai, gradio
uv sync --extra all              # everything

jupyter lab                      # start working
```

## Adding a new course

```bash
mkdir courses/new-course-name/
# drop notebooks in, commit, done
```

## Learning Journal

See [journal.md](journal.md) for chronological study notes.
