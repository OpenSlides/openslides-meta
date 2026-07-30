FROM python:3.12.13-slim-trixie

RUN apt-get update && apt-get install --yes make bash-completion postgresql-client wget

# Starting with debian forky this package will be packaged as yq-go
RUN wget https://github.com/mikefarah/yq/releases/download/v4.53.3/yq_linux_amd64 -O /usr/local/bin/yq &&\
    chmod +x /usr/local/bin/yq &&\
    echo "fa52a4e758c63d38299163fbdd1edfb4c4963247918bf9c1c5d31d84789eded4 /usr/local/bin/yq" | sha256sum -c -

WORKDIR /app/dev/

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 5678

STOPSIGNAL SIGKILL

ENTRYPOINT ["scripts/entrypoint.sh"]
CMD sleep infinity
