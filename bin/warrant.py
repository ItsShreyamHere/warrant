"""Run warrant from a plugin checkout without pip install (used by the hooks)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from warrant.cli import main  # noqa: E402

sys.exit(main())
