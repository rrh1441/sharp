FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends wget gnupg ca-certificates fonts-liberation libnss3 libatk1.0-0 libatk-bridge2.0-0 libxkbcommon0 libxcomposite1 libxdamage1 libgbm1 libgtk-3-0 libasound2 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY pyproject.toml poetry.lock ./
RUN pip install --upgrade pip && pip install poetry && poetry install --no-root
RUN poetry run playwright install --with-deps chromium
COPY . .
CMD ["poetry","run","python","-m","web"]
