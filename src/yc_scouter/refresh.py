"""The unattended refresh: verify what the notebooks produced, then fold it into facts.

Run after File 1 (and File 2, if it ran) in the scheduled workflow::

    python -m yc_scouter.refresh

Exit status is the gate: non-zero means the newest dataset fails its contract and
nothing should be committed. The workflow relies on that — it never commits past a
failing step, so a broken refresh leaves the previous, true dataset as the newest.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

from . import config, contract, pipeline


def _two_newest(stage: str, data_dir: Path) -> tuple[Path | None, Path | None]:
    files = sorted(Path(data_dir).glob(f"yc_dataset_{stage}_*.parquet"))
    newest = files[-1] if files else None
    previous = files[-2] if len(files) > 1 else None
    return newest, previous


def main(data_dir: Path = config.DATA_DIR) -> int:
    problems: list[str] = []

    for stage, checker in (("base", contract.check_base), ("ai", contract.check_ai)):
        newest, previous = _two_newest(stage, data_dir)
        if newest is None:
            print(f"[{stage}] no dataset found — skipped")
            continue
        new_df = pd.read_parquet(newest)
        prev_df = pd.read_parquet(previous) if previous else None
        violations = checker(new_df, prev_df)
        status = "ok" if not violations else "FAILED"
        against = previous.name if previous else "nothing (first run)"
        print(f"[{stage}] {newest.name}: {len(new_df)} rows, checked against {against} — {status}")
        for v in violations:
            print(f"    - {v}")
        if violations:
            problems.append(f"{stage}: {len(violations)} violation(s)")

    if problems:
        print("Contract failed; not folding into facts:", "; ".join(problems))
        return 1

    store = pipeline.build_facts(data_dir=data_dir)
    print(
        f"[facts] {len(store)} facts for {store['company_id'].nunique()} companies "
        f"→ {Path(data_dir) / 'facts.parquet'}"
    )
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised by the workflow
    sys.exit(main())
