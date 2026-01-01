import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from rich.console import Console

from dogent.cli import DogentCLI


class ExitTests(unittest.IsolatedAsyncioTestCase):
    async def test_graceful_exit_ignores_broken_pipe(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            with mock.patch.dict(os.environ, {"HOME": tmp_home}, clear=False), mock.patch(
                "pathlib.Path.home", return_value=Path(tmp_home)
            ):
                console = Console(file=io.StringIO(), force_terminal=True, color_system=None)
                cli = DogentCLI(root=Path(tmp), console=console, interactive_prompts=False)

                def raise_broken_pipe(*args, **kwargs):  # type: ignore[no-untyped-def]
                    raise BrokenPipeError()

                with mock.patch.object(cli.console, "print", new=raise_broken_pipe):
                    await cli._graceful_exit()


if __name__ == "__main__":
    unittest.main()
