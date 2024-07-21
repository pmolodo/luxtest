#!/usr/bin/env python

"""Run the UsdLux_2 test suite"""

import argparse
import inspect
import os
import subprocess
import sys
import traceback

from glob import glob
from typing import Iterable, List, Optional

###############################################################################
# Constants
###############################################################################

THIS_FILE = os.path.abspath(inspect.getsourcefile(lambda: None) or __file__)
THIS_DIR = os.path.dirname(THIS_FILE)

if THIS_DIR not in sys.path:
    sys.path.append(THIS_DIR)

import genLightParamDescriptions

EMBREE_DELEGATE = "Embree"
DEFAULT_DELEGATES = (EMBREE_DELEGATE,)
DEFAULT_INPUT_GLOBS = (os.path.join(THIS_DIR, "usd", "*.usda"),)
DEFAULT_OUTPUT_DIR = os.path.join(THIS_DIR, "renders")
DEFAULT_RESOLUTION = 512
DEFAULT_CAMERA = "/cameras/camera1"

DEFAULT_SEED = 1

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


###############################################################################
# Core functions
###############################################################################


def run_tests(
    input_usd_globs: Iterable[str] = DEFAULT_INPUT_GLOBS,
    output_dir=DEFAULT_OUTPUT_DIR,
    delegates=DEFAULT_DELEGATES,
    resolution=DEFAULT_RESOLUTION,
    camera=DEFAULT_CAMERA,
    frames: Optional[str] = None,
    seed: int = DEFAULT_SEED,
) -> List[str]:
    """Runs tests on input usds matching given glob, for all given delegates

    Returns
    -------
    failures: List[str]
    """

    light_descriptions = genLightParamDescriptions.read_descriptions()

    if not input_usd_globs:
        errmsg = (
            "ERROR: no input usd glob patterns specified. Please specify a glob pattern to match usd layers to render"
        )
        print(errmsg)
        return [errmsg]

    input_layers = []
    for pattern in input_usd_globs:
        print(f"globbing: {pattern}")
        new_layers = glob(pattern)
        print(f"found {len(new_layers)} layers")
        for f in new_layers:
            print(f"  {f}")
        input_layers.extend(new_layers)

    if not input_layers:
        errmsg = f"ERROR: input patterns {input_usd_globs} did not match any files"
        print(errmsg)
        return [errmsg]

    failures = []
    for delegate in delegates:
        delegate_output_dir = os.path.join(output_dir, delegate.lower())
        os.makedirs(delegate_output_dir, exist_ok=True)

        for layer in input_layers:
            input_file = os.path.basename(layer)
            base = os.path.splitext(input_file)[0]
            output_file = f"{base}-{delegate.lower()}.####.exr"
            output_path = os.path.join(delegate_output_dir, output_file)
            if frames is None:
                test_frames = light_descriptions.get(base, {}).get("frames")
                if test_frames:
                    start, end = test_frames
                    if start == end:
                        test_frames = f"{start}"
                    else:
                        test_frames = f"{start}:{end}"
                else:
                    test_frames = "1"
            else:
                test_frames = frames

            print("-" * 80)
            exitcode = run_test(
                layer,
                output_path,
                delegate=delegate,
                resolution=resolution,
                camera=camera,
                frames=test_frames,
                seed=seed,
            )
            if exitcode:
                failures.append(layer)
    return failures


def run_test(
    usd_path: str,
    output_path: str,
    delegate: str,
    resolution: int,
    camera: str,
    frames: str,
    seed: int,
):

    usdrecord = "usdrecord"
    if sys.platform == "win32":
        usdrecord += ".cmd"

    cmd = [
        usdrecord,
        "--disableCameraLight",
        "--disableGpu",
        "--imageWidth",
        str(resolution),
        "--renderer",
        delegate,
        "--colorCorrectionMode=disabled",
    ]
    if frames:
        cmd.extend(["--frames", frames])
    if camera:
        cmd.extend(["--camera", camera])
    cmd.extend([usd_path, output_path])
    try:
        print(to_shell_cmd(cmd))
    except Exception:
        print(cmd)
        raise
    env = dict(os.environ)
    env["HDEMBREE_RANDOM_NUMBER_SEED"] = str(seed)
    return subprocess.check_call(cmd, env=env)


###############################################################################
# CLI
###############################################################################


def get_parser():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "-d",
        "--delegates",
        nargs="+",
        default=DEFAULT_DELEGATES,
        help=(
            "Delegates to use to render the test suite. Can specify multiple delegates, which will run each specified"
            " delegate sequentially."
        ),
    )
    parser.add_argument(
        "-r",
        "--resolution",
        type=int,
        default=DEFAULT_RESOLUTION,
        help="Resolution of the rendered test images",
    )
    parser.add_argument(
        "-c",
        "--camera",
        default=DEFAULT_CAMERA,
        help="Prim path to camera to render from",
    )
    parser.add_argument(
        "-i",
        "--input",
        nargs="+",
        default=DEFAULT_INPUT_GLOBS,
        help="Glob pattern(s) to match input usd filepaths to render",
    )

    parser.add_argument(
        "-o",
        "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
        help=(
            "Base directory under which to write the rendered images. Subdirectories will be created for each render"
            " delegate."
        ),
    )
    parser.add_argument(
        "-f",
        "--frames",
        help="Frame string, in FRAMESPEC format used by usdrecord (see --frames arg in `usdrecord --help`).",
    )
    parser.add_argument(
        "-s",
        "--seed",
        type=int,
        default=DEFAULT_SEED,
        help="Set a random number seed, for repeatable results; set to -1 to use a different seed on each invocation",
    )

    return parser


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    parser = get_parser()
    args = parser.parse_args(argv)
    print(args)

    try:
        failures = run_tests(
            args.input,
            output_dir=args.output_dir,
            delegates=args.delegates,
            resolution=args.resolution,
            camera=args.camera,
            frames=args.frames,
            seed=args.seed,
        )
    except Exception:  # pylint: disable=broad-except
        traceback.print_exc()
        return 1

    print()
    if failures:
        print("!" * 80)
        print(f"Enountered {len(failures)} failures:")
        for f in failures:
            print(f)
        print("!" * 80)
        return 1
    print("All lights successfully rendered")
    return 0


if __name__ == "__main__" and not is_ipython():
    sys.exit(main())
