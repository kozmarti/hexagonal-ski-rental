"""Settings that depend on where the app runs: docker compose / CI, or the hosted demo."""

from config import env
from config.urls import healthz

NEON = "postgresql://demo:secret@ep-snowy-peak-123.eu-central-1.aws.neon.tech/ski?sslmode=require"


class TestDatabase:
    def test_the_hosted_demo_uses_neons_url_with_ssl(self):
        database = env.database({"DATABASE_URL": NEON, "POSTGRES_HOST": "db"})

        assert database["ENGINE"] == "django.db.backends.postgresql"
        assert database["HOST"] == "ep-snowy-peak-123.eu-central-1.aws.neon.tech"
        assert (database["NAME"], database["USER"], database["PASSWORD"]) == (
            "ski",
            "demo",
            "secret",
        )
        assert database["OPTIONS"] == {"sslmode": "require"}
        # Neon suspends an idle database: a kept connection is checked before use.
        assert database["CONN_HEALTH_CHECKS"] is True

    def test_without_a_url_docker_compose_and_ci_variables_are_used(self):
        database = env.database({"POSTGRES_HOST": "localhost", "POSTGRES_PORT": "5433"})

        assert (database["HOST"], database["PORT"], database["NAME"]) == (
            "localhost",
            "5433",
            "ski_rental",
        )


class TestAllowedHosts:
    def test_renders_address_is_added_by_itself(self):
        hosts = env.allowed_hosts(
            {"DJANGO_ALLOWED_HOSTS": "localhost", "RENDER_EXTERNAL_HOSTNAME": "ski.onrender.com"}
        )

        assert hosts == ["localhost", "ski.onrender.com"]

    def test_spaces_and_empty_entries_are_ignored(self):
        assert env.allowed_hosts({"DJANGO_ALLOWED_HOSTS": " a.test , ,b.test"}) == [
            "a.test",
            "b.test",
        ]


class TestStaticFilesStorage:
    HASHED = "whitenoise.storage.CompressedManifestStaticFilesStorage"
    PLAIN = "django.contrib.staticfiles.storage.StaticFilesStorage"

    def test_development_and_tests_use_plain_names(self, tmp_path):
        assert env.static_files_storage(tmp_path, {}) == self.PLAIN

    def test_the_image_build_asks_for_hashed_names(self, tmp_path):
        assert env.static_files_storage(tmp_path, {"DJANGO_HASHED_STATIC": "1"}) == self.HASHED

    def test_the_running_image_finds_the_collected_names(self, tmp_path):
        (tmp_path / "staticfiles.json").write_text("{}")

        assert env.static_files_storage(tmp_path, {}) == self.HASHED


def test_the_health_check_answers_without_the_database(rf):
    # No django_db mark: any query would fail the test.
    response = healthz(rf.get("/healthz/"))

    assert response.status_code == 200
    assert response.content == b"ok"


def test_tests_never_follow_the_https_redirect_of_production(settings):
    """The production settings (DEBUG off, as in CI) redirect HTTP to HTTPS; the test client
    speaks plain HTTP, so tests/conftest.py turns the redirect off whatever the .env says."""
    assert settings.SECURE_SSL_REDIRECT is False
