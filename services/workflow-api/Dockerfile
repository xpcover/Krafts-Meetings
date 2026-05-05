FROM python:3.11-slim

WORKDIR /app

COPY services/workflow-api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/workflow-api/app ./app

RUN useradd -r -s /bin/false appuser
USER appuser

EXPOSE 8060

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8060"]
