# ---------- base image ----------
FROM python:3.12-slim

# ---------- system packages ----------
# • chromium + chromium-driver  → for selenium.webdriver.Chrome
# • basic deps for headless browser
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

RUN pip install --upgrade pip && \
    pip install poetry && \
    poetry install --no-root --only main

# install Playwright-Chromium (harmless duplicate to system Chromium)
RUN poetry run playwright install --with-deps chromium

# ---------- copy source code ----------
COPY . .

# ---------- 2-line addition for the dual-process launch script ----------
COPY start.sh /start.sh
RUN chmod +x /start.sh
# ------------------------------------------------------------------------

# ---------- default process (unused by Fly since we set [processes]) ----
CMD ["poetry", "run", "python", "-m", "web"]