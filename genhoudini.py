#!/usr/bin/env hython

"""Render all lights for all renderers in luxtest.hip
"""

import argparse
import importlib
import inspect
import os
import subprocess
import sys
import traceback



###############################################################################
# Constants
###############################################################################

THIS_FILE = os.path.abspath(inspect.getsourcefile(lambda: None) or __file__)
THIS_DIR = os.path.dirname(THIS_FILE)
DEPS_DIR = os.path.join(THIS_DIR, ".deps")
PY_DEPS_DIR = os.path.join(DEPS_DIR, "python")

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



def pip_import(module_name, pip_package_name=None):
    try:
        return importlib.import_module(module_name)
    except ImportError:
        pass

    # couldn't import, first try ensuring PY_DEPS_DIR is on path,
    # and retry
    os.makedirs(PY_DEPS_DIR, exist_ok=True)
    if PY_DEPS_DIR not in sys.path:
        sys.path.insert(0, PY_DEPS_DIR)
        try:
            return importlib.import_module(module_name)
        except ImportError:
            pass

    # still couldn't import - install via pip
    if pip_package_name is None:
        pip_package_name = module_name
    os.makedirs(PY_DEPS_DIR, exist_ok=True)

    # ensurepip not necessary, houdini's python install includes it... and it was erroring
    # subprocess.check_call([sys.executable, "-m", "ensurepip"])
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--target", PY_DEPS_DIR, pip_package_name])
    print("=" * 80)

    return importlib.import_module(module_name)


tqdm = pip_import("tqdm")


###############################################################################
# Core functions
###############################################################################


def render_luxtest(hip_path=LUXTEST_HIP):
    import hou
    print(f"Loading: {hip_path}")
    hou.hipFile.load(hip_path)
    rop_nodes = [x for x in hou.node('/stage').allSubChildren() if isinstance(x, hou.RopNode)]
    num_rops = len(rop_nodes)
    print(f"Found {num_rops} ROP nodes")

    for i, rop_node in enumerate(tqdm.tqdm(rop_nodes, desc="ROP nodes")):
        print(f"Rendering node {i + 1}/{len(rop_nodes)}: {rop_node.name()}")
        rop_node.render()


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
