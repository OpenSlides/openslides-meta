override DEV_SOURCE_DIR=./dev/src/

# Commands inside the container

all: pyupgrade black autoflake isort flake8 mypy

pyupgrade:
	pyupgrade --py310-plus --exit-zero-even-if-changed $$(find . -name '*.py')

check-pyupgrade:
	pyupgrade --py310-plus $$(find . -name '*.py')

black:
	black $(dev_source_dir)

check-black:
	black --check --diff $(dev_source_dir)

autoflake:
	autoflake $(dev_source_dir)

isort:
	isort $(dev_source_dir)

check-isort:
	isort --check-only --diff $(dev_source_dir)

flake8:
	flake8 $(dev_source_dir)

mypy:
	mypy $(dev_source_dir)

validate-models:
	python $(dev_source_dir)validate.py

# Docker manage commands

run-dev:
	USER_ID=$$(id -u $${USER}) GROUP_ID=$$(id -g $${USER}) docker compose up -d --build
	docker compose exec models bash --rcfile /etc/bash_completion

stop-dev:
	docker compose down
