FROM python:3.12-slim-bookworm

LABEL org.opencontainers.image.title="video-gen development sandbox"
LABEL org.opencontainers.image.description="Disposable Python, FFmpeg, and pytest runtime for video-gen"

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install --yes --no-install-recommends bash ca-certificates ffmpeg \
    && ln -sf /bin/bash /bin/sh \
    && rm -rf /var/lib/apt/lists/*

RUN python -m pip install \
    --disable-pip-version-check \
    --no-cache-dir \
    pytest==8.4.2

WORKDIR /var/tmp/work
