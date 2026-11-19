FROM python:3.12-slim
WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app app
COPY scripts scripts
ARG VERSION=dev
ENV APP_VERSION=$VERSION DB_PATH=/data/campus.db PORT=5000
RUN useradd -m appuser && mkdir /data && chown appuser /data
USER appuser
EXPOSE 5000
CMD ["python", "scripts/serve.py"]
