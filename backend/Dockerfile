FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app/backend
WORKDIR /app
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY backend /app/backend
COPY data /app/data
RUN useradd --create-home --uid 10001 supportiq && mkdir /app/artifacts && chown -R supportiq:supportiq /app
USER supportiq
RUN python -m app.ml.training
EXPOSE 8000
CMD ["sh", "-c", "alembic -c backend/alembic.ini upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
