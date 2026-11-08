from django.apps import AppConfig


class DevToolsConfig(AppConfig):
    """Wiring and dev tooling, outside the hexagon: it may import bootstrap.py."""

    name = "config"
    label = "dev_tools"
