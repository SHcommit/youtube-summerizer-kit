import asyncio
import os
import sys

import pytest

from chew.harness.process import ProcessExecutor, ProcessTimeout


@pytest.mark.asyncio
async def test_process_receives_stdin_and_separates_output() -> None:
    executor = ProcessExecutor()
    code = "import sys; print(sys.stdin.read().upper()); print('warning', file=sys.stderr)"

    result = await executor.run((sys.executable, "-c", code), "hello", 2)

    assert result.exit_code == 0
    assert result.stdout.strip() == "HELLO"
    assert result.stderr.strip() == "warning"


@pytest.mark.asyncio
async def test_process_times_out_and_is_terminated() -> None:
    executor = ProcessExecutor()

    with pytest.raises(ProcessTimeout):
        await executor.run((sys.executable, "-c", "import time; time.sleep(5)"), "", 0.05)


@pytest.mark.asyncio
async def test_process_does_not_inherit_unapproved_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("YTSUM_TEST_SECRET", "must-not-leak")
    code = "import os; print(os.getenv('YTSUM_TEST_SECRET', 'missing'))"

    result = await ProcessExecutor().run((sys.executable, "-c", code), "", 2)

    assert result.stdout.strip() == "missing"
    assert "YTSUM_TEST_SECRET" in os.environ


@pytest.mark.asyncio
async def test_process_drains_output_while_feeding_large_stdin() -> None:
    code = (
        "import sys; "
        "sys.stdout.write('x' * 1000000); sys.stdout.flush(); "
        "data=sys.stdin.read(); print(len(data), file=sys.stderr)"
    )
    result = await ProcessExecutor(maximum_output_bytes=32).run((sys.executable, "-c", code), "y" * 1_000_000, 3)

    assert len(result.stdout) == 32
    assert result.stderr.strip() == "1000000"


@pytest.mark.asyncio
async def test_early_exit_preserves_error_result_when_stdin_pipe_breaks() -> None:
    code = "import sys; print('Not logged in', file=sys.stderr); raise SystemExit(1)"

    result = await ProcessExecutor().run((sys.executable, "-c", code), "large prompt" * 1_000_000, 3)

    assert result.exit_code == 1
    assert "Not logged in" in result.stderr


@pytest.mark.asyncio
async def test_terminate_uses_sigterm_before_sigkill() -> None:
    """Process that exits on SIGTERM should not be SIGKILLed."""
    import sys as _sys
    executor = ProcessExecutor()
    code = (
        "import signal, sys\n"
        "signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))\n"
        "import time; time.sleep(30)\n"
    )
    process = await asyncio.create_subprocess_exec(
        _sys.executable, "-c", code,
        stdin=asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
        start_new_session=True,
    )
    await asyncio.sleep(0.1)  # allow child to install signal handler before SIGTERM
    executor._terminate(process)
    await executor._await_termination(process, sigterm_timeout=3.0)
    assert process.returncode == 0  # clean exit via SIGTERM handler


@pytest.mark.asyncio
async def test_await_termination_escalates_to_sigkill_when_process_ignores_sigterm() -> None:
    """Process that ignores SIGTERM must be killed within timeout + small buffer."""
    import time as _time2
    import sys as _sys
    executor = ProcessExecutor()
    code = (
        "import signal, time\n"
        "signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
        "time.sleep(30)\n"
    )
    process = await asyncio.create_subprocess_exec(
        _sys.executable, "-c", code,
        stdin=asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
        start_new_session=True,
    )
    start = _time2.monotonic()
    executor._terminate(process)
    await executor._await_termination(process, sigterm_timeout=0.5)
    elapsed = _time2.monotonic() - start
    assert process.returncode is not None  # process was killed
    assert elapsed < 2.0  # killed well within test budget
