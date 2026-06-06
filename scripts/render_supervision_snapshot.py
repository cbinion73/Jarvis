from __future__ import annotations

import argparse
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from jarvis.supervision_snapshot import (
    DEFAULT_HTML_OUTPUT,
    DEFAULT_JSON_OUTPUT,
    build_supervision_snapshot,
    write_supervision_snapshot,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Render a local JARVIS supervision snapshot.")
    parser.add_argument("--html-output", default=str(DEFAULT_HTML_OUTPUT))
    parser.add_argument("--json-output", default=str(DEFAULT_JSON_OUTPUT))
    args = parser.parse_args()

    snapshot = build_supervision_snapshot()
    outputs = write_supervision_snapshot(
        snapshot,
        html_output=Path(args.html_output),
        json_output=Path(args.json_output),
    )
    print(outputs["html"])
    print(outputs["json"])


if __name__ == "__main__":
    main()
