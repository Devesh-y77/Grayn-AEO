FROM python:3.12-slim

# Install system dependencies required by Playwright
RUN apt-get update && apt-get install -y \
    libgbm1 \
    libnss3 \
    libatk-bridge2.0-0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libasound2 \
    libpango-1.0-0 \
    libcups2 \
    libx11-xcb1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install mcp sse-starlette apscheduler playwright

# Install Playwright browser binaries
RUN playwright install chromium
RUN playwright install-deps

COPY . .

# Expose backend port
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
