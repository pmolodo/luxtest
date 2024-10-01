import inspect
import os
import subprocess
import sys

from typing import Tuple

THIS_FILE = os.path.abspath(inspect.getsourcefile(lambda: None) or __file__)
THIS_DIR = os.path.dirname(THIS_FILE)

if THIS_DIR not in sys.path:
    sys.path.append(THIS_DIR)

import luxtest_const


def try_decode(input_bytes):
    for codec in luxtest_const.CODEC_LIST:
        try:
            return input_bytes.decode(codec)
        except UnicodeDecodeError:
            pass
    return input_bytes


def get_renders_root() -> str:
    for test_path in luxtest_const.DEFAULT_RENDERS_ROOTS:
        if os.path.isdir(test_path):
            return test_path

    # couldn't find the renders path - clone it
    renders_root = luxtest_const.DEFAULT_RENDERS_ROOTS[0]
    # don't fetch all blobs for faster clone
    subprocess.run(["git", "clone", "--filter=blob:none", luxtest_const.DEFAULT_RENDERS_REPO_URL, renders_root])
    if not os.path.isdir(renders_root):
        raise RuntimeError(f"error cloning repo {luxtest_const.DEFAULT_RENDERS_REPO_URL!r} to {renders_root!r}")
    return renders_root


def get_render_dirs() -> Tuple[str, ...]:
    return tuple(x.name for x in os.scandir(get_renders_root()) if x.is_dir())


def get_image_path(light_name, renderer: str, frame: int, ext: str, prefix="", renders_root=""):
    if not renders_root:
        renders_root = get_renders_root()
    ext = ext.lstrip(".")
    filename = f"{prefix}{light_name}-{renderer}.{frame:04}.{ext}"
    if ext == "png":
        base_dir = luxtest_const.WEB_IMG_ROOT
    elif ext == "exr":
        base_dir = os.path.join(renders_root, renderer)
    else:
        raise ValueError(f"unrecognized extension: {ext}")
    return os.path.join(base_dir, filename)


def get_image_url(light_name, renderer: str, frame: int, ext: str, prefix="", renders_root=""):
    if not renders_root:
        renders_root = get_renders_root()
    image_path = get_image_path(light_name, renderer, frame, ext, prefix=prefix, renders_root=renders_root)
    rel_path = os.path.relpath(image_path, luxtest_const.WEB_ROOT)
    return rel_path.replace(os.sep, "/")
