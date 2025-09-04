# Commands inside the container
paths = src/ tests/

all: pyupgrade black autoflake isort flake8 mypy sqlfluff

pyupgrade:
	pyupgrade --py310-plus --exit-zero-even-if-changed $$(find . -name '*.py')

check-pyupgrade:
	pyupgrade --py310-plus $$(find . -name '*.py')

black:
	black $(paths)

check-black:
	black --check --diff $(paths)

autoflake:
	autoflake $(paths)

isort:
	isort $(paths)

check-isort:
	isort --check-only --diff $(paths)

flake8:
	flake8 $(paths)

mypy:
	mypy src/

sqlfluff:
	sqlfluff fix --dialect postgres --verbose

validate-models:
	python -m src.validate

generate-relational-schema:
	python -m src.generate_sql_schema

drop-database:
	dropdb -f -e --if-exists -h ${DATABASE_HOST} -p ${DATABASE_PORT} -U ${DATABASE_USER} ${DATABASE_NAME}

create-database:
	createdb -e -h ${DATABASE_HOST} -p ${DATABASE_PORT} -U ${DATABASE_USER} ${DATABASE_NAME}

apply-db-schema:
	scripts/apply_db_schema.sh

apply-test-data:
	scripts/apply_data.sh base_data.sql
	scripts/apply_data.sh test_data.sql

create-database-with-schema: drop-database create-database apply-db-schema

create-test-data: create-database-with-schema apply-test-data

run-psql:
	psql -h ${DATABASE_HOST} -p ${DATABASE_PORT} -U ${DATABASE_USER} -d ${DATABASE_NAME}

# Docker manage commands

run-dev:
	USER_ID=$$(id -u $${USER}) GROUP_ID=$$(id -g $${USER}) docker compose up -d --build
	docker compose exec models bash --rcfile /etc/bash_completion

stop-dev:
	docker compose down
