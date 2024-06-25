#!/usr/bin/env hython

"""Render all lights for all renderers in luxtest.hip
"""

import argparse
import inspect
import os
import sys
import traceback

from typing import Iterable

###############################################################################
# Constants
###############################################################################

THIS_FILE = os.path.abspath(inspect.getsourcefile(lambda: None) or __file__)
THIS_DIR = os.path.dirname(THIS_FILE)

LUXTEST_HIP = os.path.join(THIS_DIR, "luxtest.hip")

###############################################################################
# Utilities
###############################################################################


def is_ipython():
    try:
        __IPYTHON__  # type: ignore
    except NameError:
        return False
    return True


###############################################################################
# Core functions
###############################################################################


def render_luxtest(hip_path=LUXTEST_HIP, renderers: Iterable[str] = (), lights: Iterable[str] = ()):
    import hou
    print(f"Loading: {hip_path}")
    hou.hipFile.load(hip_path)
    usdrender_type = hou.lopNodeTypeCategory().nodeType("usdrender_rop")

    rop_nodes = [x for x in hou.node('/stage').allSubChildren() if x.type() == usdrender_type]
    if lights:
        light_prefixes = tuple(f"render_{l}_" for l in lights)
        rop_nodes = [x for x in rop_nodes if x.name().startswith(light_prefixes)]
    if renderers:
        renderer_suffixes = tuple(f"_{r}" for r in renderers)
        rop_nodes = [x for x in rop_nodes if x.name().endswith(renderer_suffixes)]
    rop_nodes.sort(key=lambda node: node.name())
    num_rops = len(rop_nodes)
    print()
    print("=" * 80)
    print(f"Found {num_rops} usdrender ROP nodes:")
    for rop_node in rop_nodes:
        print(rop_node.name())
    print("=" * 80)
    print()

    for i, rop_node in enumerate(rop_nodes):
        print(f"Rendering node {i + 1}/{num_rops}: {rop_node.name()}")
        rop_node.render(output_progress=True, verbose=True)


###############################################################################
# CLI
###############################################################################


def get_parser():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "hip_file", nargs="?", default=LUXTEST_HIP,
        help="path to the .hip file to render")
    parser.add_argument("-r", "--renderer", choices=("karma", "ris", "arnold"),
                        action="append", dest="renderers",
                        help="Only render images for the given renderer; if not"
                        " specified, render images for all renderers. May be"
                        " repeated.")
    parser.add_argument("-l", "--light",
                        choices=("cylinder", "disk", "distant", "dome", "rect", "sphere", "visible-rect"),
                        action="append", dest="lights",
                        help="Only render images for the given lights; if not"
                        " specified, render images for all lights. May be"
                        " repeated.")
    return parser


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    parser = get_parser()
    args = parser.parse_args(argv)
    try:
        render_luxtest(args.hip_file, lights=args.lights, renderers=args.renderers)
    except Exception:  # pylint: disable=broad-except

        traceback.print_exc()
        return 1
    return 0


if __name__ == "__main__" and not is_ipython():
    sys.exit(main())
