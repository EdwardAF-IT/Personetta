"""Allow running as: python -m generator"""

from generator.cli.main import main
import sys

if __name__ == "__main__":
    sys.exit(main())
