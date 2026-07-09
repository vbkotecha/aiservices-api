FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/

EXPOSE 8000

# Use startup_check.py which tries imports, captures errors, starts uvicorn
CMD ["python", "/app/src/startup_check.py"]
