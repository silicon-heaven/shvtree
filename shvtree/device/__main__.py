"""Implementation of command line application demoing the SHV Tree."""
import argparse
import asyncio
import logging
import pathlib
import typing

import asyncinotify
import shv

from .. import load
from . import SHVTreeDummyDevice

logger = logging.getLogger(__name__)
log_levels = (
    logging.DEBUG,
    logging.INFO,
    logging.WARNING,
    logging.ERROR,
    logging.CRITICAL,
)


def parse_args() -> argparse.Namespace:
    """Parse passed arguments and return result."""
    parser = argparse.ArgumentParser(
        "shvtree-dummy", description="Silicon Heaven Tree dummy"
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {SHVTreeDummyDevice.APP_VERSION}",
    )
    parser.add_argument(
        "-v",
        action="count",
        default=0,
        help="Increase verbosity level of logging",
    )
    parser.add_argument(
        "-q",
        action="count",
        default=0,
        help="Decrease verbosity level of logging",
    )
    parser.add_argument(
        "TREE",
        nargs=1,
        help="Path to the file describing the tree.",
    )
    parser.add_argument(
        "URL",
        nargs="?",
        default="tcp://test@localhost?password=test&devmount=test/dummy",
        help="SHV RPC URL specifying connection to the broker.",
    )
    return parser.parse_args()


def main() -> None:
    """Application's entrypoint."""
    args = parse_args()

    logging.basicConfig(
        level=log_levels[sorted([1 - args.v + args.q, 0, len(log_levels) - 1])[1]],
        format="[%(asctime)s] [%(levelname)s] - %(message)s",
    )

    tree_path = pathlib.Path(args.TREE[0])

    class Device(SHVTreeDummyDevice):
        tree = load(tree_path)

    loop = asyncio.get_event_loop()

    inotify_task = loop.create_task(inotify_watch(tree_path, Device))
    logger.info("Starting the device.")
    server = loop.run_until_complete(Device.connect(shv.RpcUrl.parse(args.URL)))
    assert isinstance(server, SHVTreeDummyDevice)
    try:
        loop.run_until_complete(server.task)
    except KeyboardInterrupt:
        loop.run_until_complete(server.disconnect())
    logger.info("The device terminated.")

    inotify_task.cancel()
    try:
        loop.run_until_complete(inotify_task)
    except asyncio.CancelledError:
        pass


async def inotify_watch(
    tree_path: pathlib.Path, device: typing.Type[SHVTreeDummyDevice]
) -> None:
    """Wait for changes in the source file and update the tree."""
    with asyncinotify.Inotify() as inotify:

        def add_watch() -> None:
            inotify.add_watch(
                tree_path, asyncinotify.Mask.MODIFY | asyncinotify.Mask.CLOSE_WRITE
            )

        add_watch()
        logger.debug("Waiting for the inotify modification: %s", tree_path)
        async for event in inotify:
            if asyncinotify.Mask.IGNORED in event.mask:
                add_watch()
            try:
                logger.info("Reloading file: %s", tree_path)
                device.tree = load(tree_path)
            except RuntimeError as exc:
                logger.error("Failed to reload tree: %s", exc)


if __name__ == "__main__":
    main()
