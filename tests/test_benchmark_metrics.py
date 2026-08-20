from pathlib import Path

from chew.benchmark.metrics import lock_hash, measure_text


def test_metrics_reports_filler_ratio_and_segments(tmp_path: Path) -> None:
    metrics = measure_text("fixture", ["um hello", "world"], 4)

    assert metrics.filler_count == 1
    assert metrics.filler_ratio == 1 / 3
    assert metrics.segment_count == 2
    lock = tmp_path / "videos.lock.json"
    lock.write_text("{}", encoding="utf-8")
    assert len(lock_hash(lock)) == 64
