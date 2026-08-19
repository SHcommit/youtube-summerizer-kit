"""Shell-free, cancellable subprocess execution."""

from __future__ import annotations

import asyncio
import os
import signal
from collections.abc import Mapping, Sequence
from contextlib import suppress
from dataclasses import dataclass


class ProcessTimeout(TimeoutError):
    """Raised when an external harness exceeds its deadline."""


@dataclass(frozen=True, slots=True)
class ProcessResult:
    exit_code: int
    stdout: str
    stderr: str


class ProcessExecutor:
    _INHERITED_ENV = ("PATH", "HOME", "LANG", "LC_ALL", "TMPDIR", "XDG_CONFIG_HOME")

    def __init__(self, maximum_output_bytes: int = 4 * 1024 * 1024) -> None:
        self.maximum_output_bytes = maximum_output_bytes

    async def run(
        self,
        argv: Sequence[str],
        stdin: str,
        timeout: float,
        environment: Mapping[str, str] | None = None,
    ) -> ProcessResult:
        child_environment = {name: os.environ[name] for name in self._INHERITED_ENV if name in os.environ}
        child_environment.update(environment or {})
        process = await asyncio.create_subprocess_exec(
            *argv,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=child_environment,
            start_new_session=True,
        )
        try:
            assert process.stdin is not None
            stdout_task = asyncio.create_task(self._read_bounded(process.stdout))
            stderr_task = asyncio.create_task(self._read_bounded(process.stderr))

            async def feed_stdin() -> None:
                assert process.stdin is not None
                try:
                    process.stdin.write(stdin.encode("utf-8"))
                    await process.stdin.drain()
                except (BrokenPipeError, ConnectionResetError):
                    pass
                finally:
                    process.stdin.close()

            stdout, stderr, _, _ = await asyncio.wait_for(
                asyncio.gather(stdout_task, stderr_task, process.wait(), feed_stdin()),
                timeout=timeout,
            )
        except TimeoutError as error:
            self._terminate(process)
            await process.wait()
            raise ProcessTimeout(f"process timed out after {timeout} seconds") from error
        except asyncio.CancelledError:
            self._terminate(process)
            await process.wait()
            raise
        return ProcessResult(
            exit_code=int(process.returncode or 0),
            stdout=stdout.decode("utf-8", errors="replace"),
            stderr=stderr.decode("utf-8", errors="replace"),
        )

    async def _read_bounded(self, stream: asyncio.StreamReader | None) -> bytes:
        if stream is None:
            return b""
        captured = bytearray()
        while chunk := await stream.read(64 * 1024):
            remaining = self.maximum_output_bytes - len(captured)
            if remaining > 0:
                captured.extend(chunk[:remaining])
        return bytes(captured)

    @staticmethod
    def _terminate(process: asyncio.subprocess.Process) -> None:
        if process.returncode is not None:
            return
        with suppress(ProcessLookupError):
            os.killpg(process.pid, signal.SIGKILL)
