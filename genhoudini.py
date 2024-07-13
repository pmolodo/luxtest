#!/usr/bin/env hython

"""Render all lights for all renderers in luxtest.hip"""

import argparse
import inspect
import os
import re
import sys
import traceback

from typing import Iterable, Optional

###############################################################################
# Constants
###############################################################################

THIS_FILE = os.path.abspath(inspect.getsourcefile(lambda: None) or __file__)
THIS_DIR = os.path.dirname(THIS_FILE)

LUXTEST_HIP = os.path.join(THIS_DIR, "luxtest.hip")
HUSK_PRE_RENDER = os.path.join(THIS_DIR, "husk_pre_render.py")

HOUDINI_ATTR_RE = re.compile(r"""^\s*[A-Za-z_][A-Za-z_0-9]* houdini:[A-Za-z_][A-Za-z_0-9:]*.*""")

###############################################################################
# Utilities
###############################################################################


def is_ipython():
    try:
        __IPYTHON__  # type: ignore
    except NameError:
        return False
    return True


def filter_lights(rop_nodes: Iterable["hou.Node"], lights: Iterable[str]):
    if not lights:
        return rop_nodes
    light_suffixes = tuple(f"_{l}" for l in lights)
    return [x for x in rop_nodes if x.name().endsiwth(light_suffixes)]


def filter_renderers(rop_nodes: Iterable["hou.Node"], renderers: Iterable[str]):
    if not renderers:
        return rop_nodes

    renderer_prefixes = tuple(f"render_{r}_" for r in renderers)
    rop_nodes = [x for x in rop_nodes if x.name().startswith(renderer_prefixes)]


###############################################################################
# Core functions
###############################################################################


def render_luxtest(
    hip_path=LUXTEST_HIP,
    renderers: Optional[Iterable[str]] = None,
    lights: Optional[Iterable[str]] = None,
    frame: Optional[int] = None,
    images=True,
    usd=True,
):
    import hou

    print(f"Loading: {hip_path}")
    hou.hipFile.load(hip_path)

    renderers = list(renderers) if renderers else []
    lights = list(lights) if lights else []

    if usd:
        output_usd(lights=lights)
    if images:
        render_images(renderers=renderers, lights=lights, frame=frame)


def output_usd(lights: Iterable[str] = ()):
    import hou

    usdrop_type = hou.lopNodeTypeCategory().nodeType("usd_rop")
    rop_nodes = [x for x in hou.node("/stage").allSubChildren() if x.type() == usdrop_type]
    rop_nodes = filter_lights(rop_nodes, lights)
    rop_nodes.sort(key=lambda node: node.name())
    num_rops = len(rop_nodes)
    print()
    print("=" * 80)
    print(f"Found {num_rops} usd ROP nodes:")
    for rop_node in rop_nodes:
        print(rop_node.name())
    print("=" * 80)
    print()

    for i, rop_node in enumerate(rop_nodes):
        print(f"Outputing USD node {i + 1}/{num_rops}: {rop_node.name()}")
        rop_node.render()

        # strip out houdini-specific attributes
        outpath = rop_node.parm("lopoutput").eval()
        with open(outpath, "r", encoding="utf8") as reader:
            lines = reader.readlines()
        newlines = [x for x in lines if not HOUDINI_ATTR_RE.match(x)]
        if len(newlines) != len(lines):
            with open(outpath, "w", encoding="utf8", newline="\n") as writer:
                writer.writelines(newlines)


def render_images(
    renderers: Iterable[str] = (),
    lights: Iterable[str] = (),
    frame: Optional[int] = None,
):
    import hou

    usdrender_type = hou.lopNodeTypeCategory().nodeType("usdrender_rop")

    rop_nodes = [x for x in hou.node("/stage").allSubChildren() if x.type() == usdrender_type]
    rop_nodes = filter_lights(rop_nodes, lights)
    rop_nodes = filter_renderers(rop_nodes, renderers)
    rop_nodes.sort(key=lambda node: node.name())
    num_rops = len(rop_nodes)
    print()
    print("=" * 80)
    print(f"Found {num_rops} usdrender ROP nodes:")
    for rop_node in rop_nodes:
        print(rop_node.name())
    print("=" * 80)
    print()

    render_kwargs = {
        "output_progress": True,
        "verbose": True,
    }
    if frame is not None:
        render_kwargs["frame_range"] = (frame, frame)
    for i, rop_node in enumerate(rop_nodes):
        print(f"Rendering node {i + 1}/{num_rops}: {rop_node.name()}")
        rop_node.parm("husk_prerender").set(HUSK_PRE_RENDER)
        rop_node.render(**render_kwargs)


###############################################################################
# CLI
###############################################################################


def get_parser():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "hip_file",
        nargs="?",
        default=LUXTEST_HIP,
        help="path to the .hip file to render",
    )
    parser.add_argument("--no-images", dest="images", action="store_false", help="Disable rendering output images")
    parser.add_argument("--no-usd", dest="usd", action="store_false", help="Disable writing out usda files")
    parser.add_argument(
        "-r",
        "--renderer",
        choices=("karma", "ris", "arnold"),
        action="append",
        dest="renderers",
        help=(
            "Only render images for the given renderer; if not"
            " specified, render images for all renderers. May be"
            " repeated."
        ),
    )
    parser.add_argument(
        "-l",
        "--light",
        choices=(
            "cylinder",
            "disk",
            "distant",
            "dome",
            "rect",
            "sphere",
            "visible-rect",
        ),
        action="append",
        dest="lights",
        help=(
            "Only render images for the given lights; if not specified, render images for all lights. May be repeated."
        ),
    )
    parser.add_argument(
        "-f",
        "--frame",
        type=int,
        help="Only render the single given frame for all lights",
    )
    return parser


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    parser = get_parser()
    args = parser.parse_args(argv)
    try:
        render_luxtest(
            args.hip_file,
            lights=args.lights,
            renderers=args.renderers,
            frame=args.frame,
            images=args.images,
            usd=args.usd,
        )
    except Exception:  # pylint: disable=broad-except

        traceback.print_exc()
        return 1
    return 0


if __name__ == "__main__" and not is_ipython():
    sys.exit(main())
