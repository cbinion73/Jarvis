FROM python:3.12-slim

WORKDIR /app

# System dependencies (skip audio/desktop, include what's needed for server)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    build-essential \
    git \
    curl \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Playwright browsers (for web agent tools)
RUN pip install playwright && playwright install chromium --with-deps

# Create server-safe requirements (exclude audio/desktop packages)
COPY requirements.txt requirements_full.txt
RUN grep -v -E "pyaudio|sounddevice|pyttsx3|cadquery" requirements_full.txt > requirements.txt
COPY requirements_crewai.txt requirements_crewai.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir -r requirements_crewai.txt

# Copy source
COPY . .

# Create required directories
RUN mkdir -p data/logs data/settings data/agents data/conversations \
    data/workstreams data/system data/family data/health \
    data/calendar data/forge data/catalyst data/workshop

EXPOSE 8787

CMD ["python", "-m", "jarvis", "serve", "--host", "0.0.0.0", "--port", "8787"]
