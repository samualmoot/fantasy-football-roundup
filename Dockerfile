# Playwright base image includes Chromium and all required system libraries
# Note: registry is mcr.microsoft.com (not mcr.microsoft)
FROM mcr.microsoft.com/playwright:v1.54.0-jammy

WORKDIR /app

# Ensure Playwright uses the preinstalled browser cache in this image
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    PORT=8000

# Install Python dependencies first (better layer caching)
COPY requirements.txt ./
RUN python -m pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy app code
COPY . .

# Default command – Render sets $PORT automatically
CMD gunicorn fantasy_football_roundup.wsgi:application --bind 0.0.0.0:$PORT --workers=2 --threads=2


