PYTHON ?= python3
export PYTHONPATH := src

.PHONY: run test lint

run:
	$(PYTHON) -m depgraph $(ARGS)

test:
	$(PYTHON) -m unittest discover -s tests -t . -v

lint:
	$(PYTHON) -m flake8 src tests
