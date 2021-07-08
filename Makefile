.DEFAULT_GOAL := tox
.PHONY: tox lint test build plot plot_v plot_d dash dash_v dash_d

lint:
	poetry run black spyc/
	poetry run flake8 spyc/
	poetry run pylint spyc/ --exit-zero
	poetry run mypy spyc/

test: lint  ## Run tests with coverage, lint first
	poetry run pytest --cov=spyc tests/

tox:
	poetry run python -m tox -e py39

build: tox # run tox first before building
	poetry build

plot:
	poetry run python -m spyc.main plot tests/

plot_v:
	poetry run python -m spyc.main plot tests/ -v

plot_d:
	poetry run python -m spyc.main plot tests/ -d

dash:
	poetry run python -m spyc.main dash tests/

dash_v:
	poetry run python -m spyc.main dash tests/ -v

dash_d:
	poetry run python -m spyc.main dash tests/ -d