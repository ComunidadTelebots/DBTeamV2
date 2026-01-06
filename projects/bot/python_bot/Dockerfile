FROM python:3.11-slim
WORKDIR /app
COPY . /app
RUN pip install --upgrade pip setuptools wheel \
    && if [ -f requirements.txt ]; then pip install -r requirements.txt; fi
CMD ["python", "main.py"]
