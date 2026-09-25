FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml ./
RUN pip install --no-cache-dir "PyYAML>=6" "jsonschema>=4" \
    && useradd --system --uid 10001 --create-home --home-dir /home/dashboard --shell /usr/sbin/nologin dashboard \
    && mkdir -p /data \
    && chown dashboard:dashboard /data
COPY --chown=dashboard:dashboard src ./src
COPY --chown=dashboard:dashboard schema ./schema
ENV PYTHONPATH=/app/src
# Процесс не root. Каталог данных на хосте должен быть доступен uid 10001 на запись.
USER dashboard
ENTRYPOINT ["python", "-m", "dashboard"]
