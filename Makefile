# AFTBench Makefile
# ==================
SHELL       := /bin/bash
PYTHON      := python
VENV        := .venv
BIN         := $(VENV)/bin
PIP         := $(BIN)/pip
PY          := $(BIN)/python
PYTEST      := $(BIN)/pytest

.PHONY: help setup lint typecheck test smoke pilot ablations analyze report acceptance clean

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	  awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

# ---------- environment ----------

setup:  ## Create venv and install package + dev deps
	$(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip setuptools wheel
	$(PIP) install -e ".[dev]"
	@echo "Virtual environment ready.  Activate:  source $(VENV)/bin/activate"

# ---------- quality ----------

lint:  ## Run ruff linter (if installed)
	$(PY) -m ruff check src/ tests/ || true

typecheck:  ## Run mypy (if installed)
	$(PY) -m mypy src/aftbench --ignore-missing-imports || true

test:  ## Run full test suite
	$(PYTEST) tests/ -v

# ---------- benchmark profiles ----------

smoke:  ## Run smoke profile (fast sanity check)
	$(PY) -m aftbench run --profile smoke

pilot:  ## Run pilot profile (small-scale evaluation)
	$(PY) -m aftbench run --profile pilot

ablations:  ## Run ablation suite
	$(PY) -m aftbench run --profile ablations

# ---------- analysis ----------

analyze:  ## Compute metrics from latest results
	$(PY) -m aftbench analyze

report:  ## Generate final report (tables + figures)
	$(PY) -m aftbench report

# ---------- acceptance ----------

acceptance: lint typecheck test smoke analyze  ## Full acceptance gate
	@echo "Acceptance checks passed."

# ---------- maintenance ----------

clean:  ## Remove build artifacts and venv
	rm -rf $(VENV) build/ dist/ *.egg-info src/*.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.pyc' -delete 2>/dev/null || true
