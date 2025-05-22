# ---------- base image ----------
FROM python:3.12-slim

# ---------- system packages ----------
# • chromium + chromium‐driver → still installed because Playwright/Selenium
#   are in your deps (harmless if unused)
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
        wget gnupg ca-certificates \
        fonts-liberation libnss3 libatk1.0-0 libatk-bridge2.0-0 \
        libxkbcommon0 libxcomposite1 libxdamage1 libgbm1 \
        libgtk-3-0 libasound2 \
        chromium chromium-driver; \
    rm -rf /var/lib/apt/lists/*

# ---------- project setup ----------
WORKDIR /app
COPY pyproject.toml poetry.lock* ./

RUN pip install --upgrade pip \
 && pip install poetry \
 && poetry install --no-root --only main

# install Playwright-Chromium (safe duplicate of system Chromium)
RUN poetry run playwright install --with-deps chromium

# ---------- copy source code ----------
COPY . .

# ---------- NO default CMD ----------
# The command for each Machine comes from the [processes]
# section in fly.toml, so we leave CMD/ENTRYPOINT unset here.