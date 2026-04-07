FROM python:3.12-slim
WORKDIR /app
COPY . .
RUN chmod +x /app/docker-entrypoint.sh && pip install -e ".[dev]"
ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
