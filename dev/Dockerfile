FROM python:3.12.9-slim-bookworm

RUN apt-get update && apt-get install --yes make bash-completion postgresql-client

WORKDIR /app/dev/

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 5678

STOPSIGNAL SIGKILL

ENTRYPOINT ["scripts/entrypoint.sh"]
CMD sleep infinity
