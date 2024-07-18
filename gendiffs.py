#!/usr/bin/env python


"""Generate a web page showing UsdLux image diffs

...between the reference embree implementation and other renderers (ie, arnold,
karma, and RenderMan RIS)
"""


import argparse
import inspect
import os
import shutil
import subprocess
import sys
import textwrap
import traceback

from typing import Iterable

###############################################################################
# Constants
###############################################################################

THIS_FILE = os.path.abspath(inspect.getsourcefile(lambda: None) or __file__)
THIS_DIR = os.path.dirname(THIS_FILE)

if THIS_DIR not in sys.path:
    sys.path.append(THIS_DIR)

import genLightParamDescriptions

RENDERS_DIR_NAME = "renders"
RENDERS_ROOT = os.path.join(THIS_DIR, RENDERS_DIR_NAME)
WEB_DIR_NAME = "web"
WEB_ROOT = os.path.join(THIS_DIR, WEB_DIR_NAME)
WEB_IMG_ROOT = os.path.join(WEB_ROOT, "img")

RENDERERS = [
    "karma",
    "ris",
    "arnold",
]

OUTPUT_DIR = "diff"

MAP = "magma"

HTML_START = """<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>UsdLux Comparison</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="description" content="Comparison of hydra delegates to hdEmbree UsdLux reference">
    <link rel="stylesheet" href="luxtest.css">
  </head>
  <body>
"""

OIIOTOOL = os.environ.get("LUXTEST_OIIOTOOL", "oiiotool")

###############################################################################
# Utilities
###############################################################################


def is_ipython():
    try:
        __IPYTHON__  # type: ignore
    except NameError:
        return False
    return True


if sys.platform == "win32":
    to_shell_cmd = subprocess.list2cmdline
else:

    def to_shell_cmd(cmd_list):
        import shlex

        return " ".join(shlex.quote(x) for x in cmd_list)


def needs_update(existing, dependent):
    if os.path.exists(dependent):
        return os.path.getmtime(existing) > os.path.getmtime(dependent)
    return True


def iter_frames(light_description):
    frames = light_description.get("frames")
    if not frames:
        start = end = 1
    else:
        start, end = frames
    return range(start, end + 1)


def get_image_path(light_name, renderer: str, frame: int, ext: str, prefix=""):
    ext = ext.lstrip(".")
    filename = f"{prefix}{light_name}-{renderer}.{frame:04}.{ext}"
    if ext == "png":
        base_dir = WEB_IMG_ROOT
    elif ext == "exr":
        base_dir = os.path.join(RENDERS_ROOT, renderer)
    else:
        raise ValueError(f"unrecognized extension: {ext}")
    return os.path.join(base_dir, filename)


def get_image_url(light_name, renderer: str, frame: int, ext: str, prefix=""):
    image_path = get_image_path(light_name, renderer, frame, ext, prefix=prefix)
    rel_path = os.path.relpath(image_path, WEB_ROOT)
    return rel_path.replace(os.sep, "/")


def run(cmd: Iterable[str]):
    print(to_shell_cmd(cmd))
    exit_code = subprocess.call(cmd)
    print(f"   exit code: {exit_code}")
    return exit_code


###############################################################################
# Core functions
###############################################################################


def update_png(exr_path, png_path):
    if needs_update(exr_path, png_path):
        cmd = [
            OIIOTOOL,
            exr_path,
            "--ch",
            "R,G,B",
            "--colorconvert",
            "linear",
            "sRGB",
            "-o",
            png_path,
        ]
        run(cmd)
        assert os.path.isfile(png_path)


def update_diff(exr_path1, exr_path2, diff_path):
    if needs_update(exr_path1, diff_path) or needs_update(exr_path2, diff_path):
        cmd = [
            OIIOTOOL,
            exr_path1,
            exr_path2,
            "--diff",
            "--absdiff",
            "--mulc",
            "2,2,2,1",
            "--colormap",
            MAP,
            "--colorconvert",
            "linear",
            "sRGB",
            diff_path,
        ]
        run(cmd)
        assert os.path.isfile(diff_path)


def gen_images(light_descriptions):
    for name, description in light_descriptions.items():
        for frame in iter_frames(description):
            embree_exr_path = get_image_path(name, "embree", frame, "exr")
            embree_png_path = get_image_path(name, "embree", frame, "png")
            update_png(embree_exr_path, embree_png_path)

            for renderer in RENDERERS:
                renderer_exr_path = get_image_path(name, renderer, frame, "exr")
                renderer_png_path = get_image_path(name, renderer, frame, "png")
                update_png(renderer_exr_path, renderer_png_path)

                diff_png_path = get_image_path(name, renderer, frame, "png", prefix="diff-")
                update_diff(embree_exr_path, renderer_exr_path, diff_png_path)


def gen_html(light_descriptions):
    html = HTML_START
    for name, description in light_descriptions.items():
        summaries_by_start_frame = genLightParamDescriptions.get_light_group_summaries(name, description)

        html += textwrap.dedent(
            f"""<h1>{name}</h1>

            <table>
            <tr>
                <td>Frame</td>
                <td>Ref</td>
            """
        )
        for renderer in RENDERERS:
            html += textwrap.dedent(
                f"""
                    <td>{renderer}</td>
                    <td>{renderer} diff</td>
                """
            )

        html += "\n</tr>"
        for frame in iter_frames(description):

            if frame in summaries_by_start_frame:
                desc = summaries_by_start_frame[frame]
                html += "  <tr></tr>\n"
                html += "  <tr>\n"
                html += f"    <td></td><td colspan='{len(RENDERERS) + 1}'><em>{desc}</em></td>\n"
                html += "  </tr>\n"

            html += "  <tr>\n"
            html += f"    <td>{frame:04}</td>"

            embree_url = get_image_url(name, "embree", frame, "png")

            html += f'    <td><img src="{embree_url}"</td>\n'

            for renderer in RENDERERS:
                renderer_url = get_image_url(name, renderer, frame, "png")
                diff_url = get_image_url(name, renderer, frame, "png", prefix="diff-")

                html += f'    <td><img src="{renderer_url}"</td>\n'
                html += f'    <td><img src="{diff_url}"</td>\n'

            html += "  </tr>"

        html += "</table>\n"

    with open(os.path.join(WEB_ROOT, "luxtest.html"), "w", encoding="utf8") as f:
        f.write(html)

    shutil.copyfile("luxtest.css", os.path.join(WEB_ROOT, "luxtest.css"))


def gen_diffs():
    light_descriptions = genLightParamDescriptions.read_descriptions()

    os.makedirs(WEB_IMG_ROOT, exist_ok=True)
    gen_images(light_descriptions)
    gen_html(light_descriptions)


###############################################################################
# CLI
###############################################################################


def get_parser():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    return parser


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    parser = get_parser()
    parser.parse_args(argv)
    try:
        gen_diffs()
    except Exception:  # pylint: disable=broad-except

        traceback.print_exc()
        return 1
    return 0


if __name__ == "__main__" and not is_ipython():
    sys.exit(main())
