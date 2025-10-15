# syntax=docker/dockerfile:1
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

# משתמש לא-root
RUN useradd -m runner && chown -R runner:runner /app
USER runner

EXPOSE 8000

# מריצים את uvicorn דרך gunicorn (ASGI)
CMD ["gunicorn","-k","uvicorn.workers.UvicornWorker","-w","1","--threads","4","--timeout","120","-b","0.0.0.0:8000","wsgi:app","--log-level","info","--capture-output"]

