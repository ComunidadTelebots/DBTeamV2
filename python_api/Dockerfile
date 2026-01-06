FROM python:3.11-slim
WORKDIR /app
COPY . /app
RUN pip install --upgrade pip setuptools wheel \
    && if [ -f requirements_ai.txt ]; then pip install -r requirements_ai.txt; fi \
    && if [ -f requirements.txt ]; then pip install -r requirements.txt; fi
CMD ["python", "ai_server.py"]
