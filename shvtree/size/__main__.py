"""Implementation of command line application."""
import argparse
import collections.abc
import json
import logging
import sys

import ruamel.yaml

from .. import SHVTree, load, load_yaml

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse passed arguments and return result."""
    parser = argparse.ArgumentParser(
        "shvtree-size", description="Silicon Heaven Tree types sizes in Chainpack"
    )
    parser.add_argument(
        "-j",
        "--json",
        action="store_true",
        help="Print output in JSON format.",
    )
    parser.add_argument(
        "file",
        nargs=argparse.OPTIONAL,
        default="-",
        help="SHV Tree description file. Stdin is used if none is specified.",
    )
    return parser.parse_args()


def sizes(tree: SHVTree) -> collections.abc.Iterator[tuple[str, str]]:
    """Iterate over type sizes in the tree."""
    for n, v in tree.types.items():
        try:
            siz = v.chainpack_bytes()
            if siz is None:
                yield n, "Unterminated"
            else:
                yield n, str(siz)
        except RecursionError:
            yield n, "Infinite recursive"


def main() -> int:
    """Application's entrypoint."""
    args = parse_args()

    try:
        tree = load_yaml(sys.stdin) if args.file == "-" else load(args.file)
    except (ValueError, ruamel.yaml.parser.ParserError) as exc:
        print(f"Invalid input: {exc}")
        return 1

    if args.json:
        json.dump(dict(sizes(tree)), sys.stdout)
    else:
        w = max(len(n) for n in tree.types)
        for n, siz in sizes(tree):
            print(f"{n:>{w}} {siz}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
