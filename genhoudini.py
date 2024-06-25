#!/usr/bin/env hython

"""Render all lights for all renderers in luxtest.hip
"""

import argparse
import inspect
import os
import sys
import traceback


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


def render_luxtest(hip_path=LUXTEST_HIP):
    import hou
    print(f"Loading: {hip_path}")
    hou.hipFile.load(hip_path)
    usdrender_type = hou.lopNodeTypeCategory().nodeType("usdrender_rop")
    rop_nodes = [x for x in hou.node('/stage').allSubChildren() if x.type() == usdrender_type]
    num_rops = len(rop_nodes)
    print(f"Found {num_rops} usdrender ROP nodes")

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
    return parser


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    parser = get_parser()
    args = parser.parse_args(argv)
    try:
        render_luxtest(args.hip_file)
    except Exception:  # pylint: disable=broad-except

        traceback.print_exc()
        return 1
    return 0


if __name__ == "__main__" and not is_ipython():
    sys.exit(main())
