#!/usr/bin/env python

import sys
import os
import argparse
from glob import glob

TESTS = [
    ("distant", 15),
    ("dome", 1),
    ("cylinder", 40),
    ("disk", 40),
    ("rect", 40),
    ("sphere", 40),
    ("visible-rect", 1),
]

def run_test(usd_path: str, output_path: str, delegate: str, resolution: int, camera: str, frames: str):

    camera_str = f"--camera {camera}" if camera else ""

    cmd = f"usdrecord --disableCameraLight --disableGpu --imageWidth {resolution} {camera_str} --renderer {delegate}" \
         f" --colorCorrectionMode disabled {usd_path} {output_path} --frames {frames}"

    print(cmd)
    return os.system(cmd)

def main():
    os.makedirs("renders/embree", exist_ok=True)

    failures = []
    for test, end in TESTS:
        frames = ','.join([str(x) for x in range(1, end+1)])
        usd_path = f"usd/{test}.usda"
        output_path = f"renders/embree/embree-{test}.####.exr"
        resolution = 512
        camera = "/cameras/camera1"
        delegate = "Embree"

        exitcode = run_test(usd_path, output_path, delegate, resolution, camera, frames)
        if exitcode:
            failures.append(test)
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

    # parser = argparse.ArgumentParser(description = "Run the UsdLux_2 test suite")
    # parser.add_argument("-d", "--delegates", 
    #                   nargs="+", 
    #                   default=["Embree"],
    #                   help="Delegates to use to render the test suite. Can specify multiple delegates, which will run each specified delegate sequentially. If no delegate is specified, Embree will be used."
    # )
    # parser.add_argument("-r", "--resolution",
    #                   type=int,
    #                   default=512,
    #                   help="Resolution of the rendered test images"
    # )

    # parser.add_argument("-i", "--input",
    #                     nargs="+",
    #                     help="Glob pattern to match input usd layers to render"
    # )

    # parser.add_argument("-o", "--output-dir",
    #                     default=".",
    #                     help="Base directory under which to write the rendered images. Subdirectories will be created for each render delegate. If unspecified, the current directory will be used")

    # args = parser.parse_args()
    # print(args)

    # if not args.input:
    #     print("ERROR: no input specified. Please specify a glob pattern to match usd layers to render")
    #     sys.exit(1)

    # input_layers = []
    # for pattern in args.input:
    #     input_layers += glob(pattern)

    # if not input_layers:
    #     print(f"ERROR: input patterns {args.input} did not match any files")
    #     sys.exit(2)

    # for delegate in args.delegates:
    #     delegate_output_dir = os.path.join(args.output_dir, delegate)
    #     os.makedirs(delegate_output_dir, exist_ok=True)

    #     for layer in input_layers:
    #         head, tail = os.path.split(layer)
    #         base, ext = os.path.splitext(tail)
    #         output_file = base + ".exr"
    #         output_path = os.path.join(delegate_output_dir, output_file)

    #         run_test(layer, output_path, delegate, args.resolution, "camera1")





if __name__ == "__main__":
    sys.exit(main())