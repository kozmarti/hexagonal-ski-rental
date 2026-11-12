"""Settings that depend on where the app runs: development (docker compose) or the hosted
demo (Render, with the database on Neon). Small functions, so they can be tested without
reloading the settings module."""

from collections.abc import Mapping
from pathlib import Path

import dj_database_url


def database(environ: Mapping[str, str]) -> dict:
    """DATABASE_URL when it is set (the hosted demo: Neon gives one URL, with sslmode=require),
    otherwise the POSTGRES_* variables of docker compose and CI."""
    if url := environ.get("DATABASE_URL"):
        # Neon suspends an idle database: check a kept connection before using it.
        return dj_database_url.parse(url, conn_max_age=60, conn_health_checks=True)
    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": environ.get("POSTGRES_DB", "ski_rental"),
        "USER": environ.get("POSTGRES_USER", "ski_rental"),
        "PASSWORD": environ.get("POSTGRES_PASSWORD", "ski_rental"),
        "HOST": environ.get("POSTGRES_HOST", "db"),
        "PORT": environ.get("POSTGRES_PORT", "5432"),
    }


def allowed_hosts(environ: Mapping[str, str]) -> list[str]:
    """DJANGO_ALLOWED_HOSTS, plus the address Render gives the service (RENDER_EXTERNAL_HOSTNAME,
    e.g. hexagonal-ski-rental.onrender.com), so it never has to be typed by hand."""
    hosts = environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if render_host := environ.get("RENDER_EXTERNAL_HOSTNAME"):
        hosts.append(render_host)
    return [host.strip() for host in hosts if host.strip()]


def static_files_storage(static_root: Path, environ: Mapping[str, str]) -> str:
    """In the production image, static file names carry a hash of their content
    (app.3f2a1c.css): a changed file gets a new name, so browsers never keep an old copy, and
    WhiteNoise can let them cache it for a year. The image's collectstatic asks for it
    (DJANGO_HASHED_STATIC=1) and writes the list of names (staticfiles.json), which the app then
    finds at start. Development and tests have neither: plain names."""
    if environ.get("DJANGO_HASHED_STATIC") == "1" or (static_root / "staticfiles.json").exists():
        return "whitenoise.storage.CompressedManifestStaticFilesStorage"
    return "django.contrib.staticfiles.storage.StaticFilesStorage"
