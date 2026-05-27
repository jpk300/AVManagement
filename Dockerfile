FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN mkdir -p /data
ENV FLASK_APP=app.py
EXPOSE 5000
CMD ["sh", "-c", "python seed.py && python app.py"]
