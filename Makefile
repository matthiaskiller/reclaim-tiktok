SHELL = /bin/bash

.PHONY: help
help:
	@echo "Commands:"
	@echo "style   : executes style formatting."
	@echo "clean   : cleans all unnecessary files."
	@echo "test    : runs all non training tests"
# @echo "conda_env    : creates a conda environment."


# Styling
# Execute even if a file called style exists
.PHONY: style
style:
	black .
	flake8
	isort .

# # Environment possibilities
# conda_env:
# 	conda create -n make_ocean python=3.9.11
# 	conda activate make_ocean && \
# 	python -m pip install -e . ".[dev]" && \
# 	pre-commit install && \
# 	pre-commit autoupdate

# Cleaning
.PHONY: clean
clean: #style
	find . -type f -name "*.DS_Store" -ls -delete
	find . | grep -E "(__pycache__|\.pyc|\.pyo)" | xargs rm -rf
	find . | grep -E ".pytest_cache" | xargs rm -rf
	find . | grep -E ".ipynb_checkpoints" | xargs rm -rf
#	rm -f .coverage

# # Test code
# .PHONY: test
# test:
# 	pytest

# # Coverage
# # creates .coverage, coverage html(for human) and xml (for vscode extension) report
# .PHONY: coverage
# coverage:
# 	coverage run -m pytest
# 	coverage html
# 	coverage xml

# # Environment possibilities
# conda_env:
# 	conda create -n make_ocean python=3.9.11
# 	conda activate make_ocean && \
# 	python -m pip install -e . ".[dev]" && \
# 	pre-commit install && \
# 	pre-commit autoupdate

# run pre-commit
.PHONY: pre-commit
pre-commit:
	pre-commit run --all-files 