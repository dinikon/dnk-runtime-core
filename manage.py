from pathlib import Path
import sys

project_root = Path(__file__).resolve().parent
src_path = project_root / "src"
src_path_str = str(src_path)
if src_path_str not in sys.path:
    sys.path.insert(0, src_path_str)

from management.cli import main


if __name__ == "__main__":
    main()
