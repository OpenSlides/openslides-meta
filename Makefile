override DEV_SOURCE_DIR=./dev/src/

# Commands inside the container

all: pyupgrade black autoflake isort flake8 mypy

pyupgrade:
	pyupgrade --py310-plus --exit-zero-even-if-changed $$(find . -name '*.py')

check-pyupgrade:
	pyupgrade --py310-plus $$(find . -name '*.py')

black:
	black $(DEV_SOURCE_DIR)

check-black:
	black --check --diff $(DEV_SOURCE_DIR)

autoflake:
	autoflake $(DEV_SOURCE_DIR)

isort:
	isort $(DEV_SOURCE_DIR)

check-isort:
	isort --check-only --diff $(DEV_SOURCE_DIR)

flake8:
	flake8 $(DEV_SOURCE_DIR)

mypy:
	mypy $(DEV_SOURCE_DIR)

validate-models:
	python $(DEV_SOURCE_DIR)validate.py

# Docker manage commands

run-dev:
	USER_ID=$$(id -u $${USER}) GROUP_ID=$$(id -g $${USER}) docker compose up -d --build
	docker compose exec models bash --rcfile /etc/bash_completion

stop-dev:
	docker compose down
