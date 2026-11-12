"""Run askround from the source tree beside this file, with nothing installed (AR38).

The plugin carries the package in `src/askround/`, and its MCP server and slash commands
call this file through the harness's `${CLAUDE_PLUGIN_ROOT}`, so `/plugin install` is the
whole install: no `pip install`, and no scripts directory that has to be on the PATH.

`src` goes first on `sys.path`, ahead of an installed copy: a plugin that ran an older
installed askround would report one version while another answered. askround has no
runtime dependencies, so the standard library is all this needs.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from askround.cli import main  # noqa: E402 - after the path, never before

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
