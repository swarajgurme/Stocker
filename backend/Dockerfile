# Stocker Backend Dockerfile
# Multi-stage build for production

FROM python:3.11-slim as builder

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for layer caching
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt


# Production stage
FROM python:3.11-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /root/.local /root/.local

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 stocker && chown -R stocker:stocker /app

# Environment
ENV PATH=/root/.local/bin:$PATH
ENV FLASK_ENV=production
ENV FLASK_DEBUG=False

# Create necessary directories
RUN mkdir -p logs reports

# Expose port
EXPOSE 5000

# Switch to non-root user
USER stocker

# Run with gunicorn in production
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "server_new:app"]
