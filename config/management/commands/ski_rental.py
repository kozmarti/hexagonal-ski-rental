import sys

from django.core.management.base import BaseCommand

from config.cli import USE_CASES
from rental.adapters.inbound.cli.app import run


class Command(BaseCommand):
    help = "Ski rental counter from the terminal. Run `ski_rental --help` for the commands."

    def run_from_argv(self, argv):
        # The CLI adapter parses its own arguments: argv is ["manage.py", "ski_rental", ...].
        sys.exit(run(argv[2:], USE_CASES, sys.stdout, sys.stderr))
