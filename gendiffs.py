#!/usr/bin/env python

import inspect
import os
import shutil
import sys

###############################################################################
# Constants
###############################################################################

THIS_FILE = os.path.abspath(inspect.getsourcefile(lambda: None) or __file__)
THIS_DIR = os.path.dirname(THIS_FILE)

if THIS_DIR not in sys.path:
    sys.path.append(THIS_DIR)

import genLightParamDescriptions

TEST_ROOT = "renders"
WEB_ROOT = "web"

RENDERERS = [
    "karma",
    "ris",
    "arnold",
]

OUTPUT_DIR = "diff"

MAP = "magma"

HTML = """<!DOCTYPE html>
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

###############################################################################
# Main
###############################################################################

light_descriptions = genLightParamDescriptions.read_descriptions()


def needs_update(existing, dependent):
    if os.path.exists(dependent):
        return os.path.getmtime(existing) > os.path.getmtime(dependent)
    return True


os.makedirs(os.path.join(WEB_ROOT, "img"), exist_ok=True)

for name, description in light_descriptions.items():
    start, end = description["frames"]
    summaries_by_start_frame = genLightParamDescriptions.get_light_group_summaries(name, description)

    HTML += f"""<h1>{name}</h1>

<table>
  <tr>
    <td>Frame</td>
    <td>Ref</td>
"""
    for renderer in RENDERERS:
        HTML += f"""
    <td>{renderer}</td>
    <td>{renderer} diff</td>
"""

    HTML += """
  </tr>
"""

    for frame in range(start, end + 1):

        if frame in summaries_by_start_frame:
            desc = summaries_by_start_frame[frame]
            HTML += "  <tr></tr>\n"
            HTML += "  <tr>\n"
            HTML += f"    <td></td><td colspan='{len(RENDERERS)+1}'><em>{desc}</em></td>\n"
            HTML += "  </tr>\n"

        HTML += "  <tr>\n"
        HTML += f"    <td>{frame:04}</td>"

        embree_base = os.path.join(TEST_ROOT, "embree", f"{name}-embree.{frame:04}")
        embree_exr = f"{embree_base}.exr"
        embree_png = f"{name}-embree.{frame:04}.png"
        embree_png_path = os.path.join(WEB_ROOT, "img", embree_png)

        HTML += f'    <td><img src="img/{embree_png}"</td>\n'

        oiiotool = os.environ.get("LUXTEST_OIIOTOOL", "oiiotool")

        cmd = f"{oiiotool} {embree_exr} --ch R,G,B --colorconvert linear sRGB -o {embree_png_path}"
        if needs_update(embree_exr, embree_png_path):
            print(cmd)
            result = os.system(cmd)
            print(result)
            assert os.path.isfile(embree_png_path)

        for renderer in RENDERERS:
            renderer_base = os.path.join(TEST_ROOT, renderer, f"{name}-{renderer}.{frame:04}")
            renderer_exr = f"{renderer_base}.exr"
            renderer_png = f"{name}-{renderer}.{frame:04}.png"
            renderer_png_path = os.path.join(WEB_ROOT, "img", renderer_png)

            cmd = f"{oiiotool} {renderer_exr} --ch R,G,B --colorconvert linear sRGB -o {renderer_png_path}"
            if needs_update(renderer_exr, renderer_png_path):
                print(cmd)
                os.system(cmd)
                assert os.path.isfile(renderer_png_path)

            output_png = f"diff-{name}-{renderer}.{frame:04}.png"
            output_path = os.path.join(WEB_ROOT, "img", output_png)

            HTML += f'    <td><img src="img/{renderer_png}"</td>\n'
            HTML += f'    <td><img src="img/{output_png}"</td>\n'

            if needs_update(renderer_exr, output_path) or needs_update(embree_exr, output_path):
                cmd = (
                    f"{oiiotool} {embree_exr} {renderer_exr} --diff --absdiff --mulc 2,2,2,1 --colormap"
                    f" {MAP} --colorconvert linear sRGB -o {output_path}"
                )
                print(cmd)
                os.system(cmd)

        HTML += "  </tr>"

    HTML += "</table>\n"

with open(os.path.join(WEB_ROOT, "luxtest.html"), "w") as f:
    f.write(HTML)

shutil.copyfile("luxtest.css", os.path.join(WEB_ROOT, "luxtest.css"))
