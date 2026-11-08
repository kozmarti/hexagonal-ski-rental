"""Helpers shared by the view tests."""

HTMX = {"HX-Request": "true"}


def html(response) -> str:
    return response.content.decode()


class Recorder:
    """A fake use case: records its inputs and returns a fixed result, or raises."""

    def __init__(self, result=None, error=None):
        self.result, self.error, self.calls = result, error, []

    def execute(self, *args):
        self.calls.append(args[0] if args else None)
        if self.error:
            raise self.error
        return self.result
