"""Implementation of command line application."""
import argparse
import logging
import sys

from .. import load, load_yaml
from .check import Checks, check

logger = logging.getLogger(__name__)


def parse_args():
    """Parse passed arguments and return result."""
    parser = argparse.ArgumentParser(
        "shvtree-check", description="Silicon Heaven Tree cheker"
    )
    parser.add_argument(
        "-l",
        "--list-checks",
        action="store_true",
        help="List available checks if specified instead of checking file.",
    )
    parser.add_argument(
        "-d",
        "--disable-checks",
        action="append",
        help="Checks to be skipped "
        + "(can be specified multiple times or joined by comma)",
    )
    parser.add_argument(
        "file",
        nargs=argparse.REMAINDER,
        help="Files to count foos in. Stdin is used if none is specified.",
    )
    return parser.parse_args()


def do_check(path: str, disable: Checks) -> bool:
    """Perform check for the given file and report found issues."""
    tree = load_yaml(sys.stdin) if path == "-" else load(path)
    res = check(tree, disable)
    if res:
        print(f"Issues for '{path}':")
        for report in res:
            print(report)
    return not res


def main() -> int:
    """Application's entrypoint."""
    args = parse_args()

    if args.list_checks:
        for flag in Checks:
            print(f"{flag.name}")
        return 0

    disable = Checks(0)
    checksmap = {v.name: v.value for v in Checks}
    if args.disable_checks:
        for arg in ",".join(args.disable_checks).split(","):
            if arg not in checksmap:
                print(f"Invalid check: {arg}", file=sys.stderr)
                return 1
            disable |= Checks(checksmap[arg])

    if args.file:
        valid = True
        for path in args.file:
            valid &= do_check(path, disable)
    else:
        valid = do_check("-", disable)

    return 0 if valid else 1


if __name__ == "__main__":
    sys.exit(main())
