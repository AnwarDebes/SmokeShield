.PHONY: all test experiments figures paper frontend clean

PY := PYTHONPATH=. python3

all: test experiments figures paper

test:
	$(PY) -m pytest tests/ -v

experiments:
	$(PY) experiments/validation.py
	$(PY) experiments/interventions.py
	$(PY) experiments/scenarios.py

figures: experiments
	$(PY) experiments/make_figures.py

paper: figures
	cd paper && pdflatex -interaction=nonstopmode smokeshield.tex > /dev/null \
		&& bibtex smokeshield > /dev/null \
		&& pdflatex -interaction=nonstopmode smokeshield.tex > /dev/null \
		&& pdflatex -interaction=nonstopmode smokeshield.tex > /dev/null
	@echo "Built paper/smokeshield.pdf"

frontend:
	cd frontend && python3 -m http.server 8000

clean:
	rm -rf results/ paper/figures/*.pdf paper/*.aux paper/*.bbl paper/*.blg \
	       paper/*.log paper/*.out paper/*.toc paper/smokeshield.pdf
	find . -name __pycache__ -type d -exec rm -rf {} +
	find . -name "*.pyc" -delete
