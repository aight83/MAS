FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app
RUN pip install uv
COPY pyproject.toml uv.lock ./
RUN uv pip install --system -r pyproject.toml
COPY backend/ ./backend/
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
