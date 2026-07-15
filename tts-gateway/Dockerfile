FROM python:3.11-slim

WORKDIR /app

ARG PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
ENV PIP_INDEX_URL=${PIP_INDEX_URL}
ENV PIP_TRUSTED_HOST=pypi.tuna.tsinghua.edu.cn

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Default port for the API
ENV PORT=9000
EXPOSE 9000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen('http://localhost:%s/health' % os.environ.get('PORT', '9000'), timeout=5).read()" || exit 1

CMD ["python", "app.py"]
