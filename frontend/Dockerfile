FROM python:3.11-slim
WORKDIR /app
# Install project dependencies from pyproject.toml (build context must be project root)
COPY pyproject.toml /app/
RUN pip install --no-cache-dir .
COPY . /app
EXPOSE 3000
CMD ["python", "app.py"]
