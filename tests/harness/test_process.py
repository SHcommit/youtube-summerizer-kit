import os
import sys

import pytest

from ytsum.harness.process import ProcessExecutor, ProcessTimeout


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
    result = await ProcessExecutor(maximum_output_bytes=32).run(
        (sys.executable, "-c", code), "y" * 1_000_000, 3
    )

    assert len(result.stdout) == 32
    assert result.stderr.strip() == "1000000"


@pytest.mark.asyncio
async def test_early_exit_preserves_error_result_when_stdin_pipe_breaks() -> None:
    code = "import sys; print('Not logged in', file=sys.stderr); raise SystemExit(1)"

    result = await ProcessExecutor().run(
        (sys.executable, "-c", code), "large prompt" * 1_000_000, 3
    )

    assert result.exit_code == 1
    assert "Not logged in" in result.stderr
