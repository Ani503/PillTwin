.PHONY: all audit build evaluate app test clean

PYTHON = PYTHONPATH=. .venv/bin/python
PIP = .venv/bin/pip
UVICORN = PYTHONPATH=. .venv/bin/uvicorn
PYTEST = PYTHONPATH=. .venv/bin/pytest

all: audit

audit:
	$(PYTHON) scripts/audit_data.py
	$(PYTHON) scripts/audit_design.py

build:
	$(PYTHON) scripts/build_data.py

evaluate:
	@echo "Phase 4: Evaluation (pending later phases)"
	$(PYTHON) scripts/evaluate.py

app:
	@echo "Phase 5 & 6: Launching PillTwin server..."
	$(UVICORN) app.main:app --host 127.0.0.1 --port 8000 --workers 1

test:
	$(PYTEST) tests/ -v

clean:
	rm -rf __pycache__ .pytest_cache reports/ui_checks/*.png
