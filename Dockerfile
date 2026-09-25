FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml ./
RUN pip install --no-cache-dir "PyYAML>=6" "jsonschema>=4"
COPY src ./src
COPY schema ./schema
ENV PYTHONPATH=/app/src
ENTRYPOINT ["python", "-m", "dashboard"]
