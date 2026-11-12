FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Static files collected into the image, with hashed names (see config/env.py). The key is
# only there because the settings refuse to load without one when DEBUG is off.
RUN DJANGO_HASHED_STATIC=1 DJANGO_SECRET_KEY=collectstatic-only \
    python manage.py collectstatic --no-input

EXPOSE 8000

# Production (the hosted demo): migrations, then gunicorn on the port the host gives ($PORT).
# Render's free plan has no pre-deploy step, so migrations run at each start; they are quick
# when there is nothing to do. docker compose replaces this command with runserver.
CMD ["sh", "-c", "python manage.py migrate --no-input && exec gunicorn config.wsgi --bind 0.0.0.0:${PORT:-8000} --workers 2 --access-logfile -"]
