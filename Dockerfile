FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY rig ./rig
RUN pip install --no-cache-dir -e .
EXPOSE 8082
CMD ["python", "-m", "rig.watchdog.watchdog"]
