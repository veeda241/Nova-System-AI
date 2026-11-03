"""Allows `python -m nova`."""

import sys

from .cli.app import main

if __name__ == "__main__":
    sys.exit(main())
