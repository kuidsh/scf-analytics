FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir "psycopg[binary]==3.2.3"
COPY scfa ./scfa
EXPOSE 8080
CMD ["python", "-m", "scfa.app"]
