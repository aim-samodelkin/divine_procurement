FROM python:3.12-slim
WORKDIR /app

# Copy only dependency manifest first so pip install is cached separately from code changes
COPY pyproject.toml ./
RUN mkdir -p app && pip install --no-build-isolation ".[dev]"

COPY . .
RUN chmod +x /app/docker-entrypoint.sh

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
