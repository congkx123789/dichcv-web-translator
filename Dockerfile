FROM python:3.10-slim

WORKDIR /app

# Install system dependencies for C++ translator binary execution
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    g++ \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Grant execution permission for C++ run script and binaries if present
RUN chmod +x Backend/All_tool/TSL_CPP_Native/*.sh 2>/dev/null || true

EXPOSE 8000

ENV PORT=8000
ENV PYTHONUNBUFFERED=1

CMD ["python3", "run_app.py"]
