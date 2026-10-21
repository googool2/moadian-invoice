"""The synthetic benchmark must pass (it is also run on its own in CI)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "bench"))
import bench  # noqa: E402


def test_benchmark_passes(tmp_path):
    r = bench.run(tmp_path)
    failures = [i["name"] for k in ("traps", "defects") for i in r[k] if not i["pass"]]
    assert r["summary"]["pass"], failures
