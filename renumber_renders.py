# execfile(r"C:\src\NVIDIA\luxtest\renumber_renders.py")

import os
import re
import shutil

from typing import NamedTuple

renders_dir = r"C:\src\NVIDIA\luxtest\renders"

renderers = ("embree", "arnold", "karma", "ris")

lights_to_rename = ("sphere", "rect", "cylinder", "disk")

shift_start = 26
shift_amount = 5

render_re = re.compile(r"""(?P<light>[^-]*)-(?P<rend>.*)\.(?P<num>\d{4})\.exr$""")


class Rename(NamedTuple):
    old: str
    new: str


renames = []

expected_renames_per_series = 55 - shift_start + 1
expected_renames = expected_renames_per_series * len(lights_to_rename) * len(renderers)

for renderer in renderers:
    rdir = os.path.join(renders_dir, renderer)
    for entry in os.scandir(rdir):
        if not entry.is_file():
            continue
        match = render_re.match(entry.name)
        if not match:
            print(f"Strange file found: {entry.path}")
            continue
        if match.group("rend") != renderer:
            print(f"Strange file found - renderer mismatch: {entry.path}")
            continue
        light = match.group("light")
        if light not in lights_to_rename:
            continue

        num = int(match.group("num"))
        if num < shift_start:
            continue
        new_num = num + shift_amount
        new_name = f"{light}-{renderer}.{new_num:04d}.exr"
        new_path = os.path.join(rdir, new_name)
        renames.append(Rename(old=entry.path, new=new_path))

print(f"Num renames: {len(renames)} - expected: {expected_renames}")
if len(renames) != expected_renames:
    raise Exception(f"wrong number of renames - actual: {len(renames)} - expected: {expected_renames}")

renames.sort(reverse=True)

for rename in renames:
    print(rename)
    shutil.move(rename.old, rename.new)

print(f"Num renames: {len(renames)} - expected: {expected_renames}")
