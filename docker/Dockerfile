FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip python3-venv \
    curl wget ca-certificates \
    nginx mysql-client openssh-client \
    shellcheck \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

COPY . /workspace

RUN python3 -m pip install --no-cache-dir uv && \
    uv sync --extra dev

CMD ["bash"]
