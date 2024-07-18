#!/usr/bin/env python

"""Generate .json file describing the various parameters for each light"""

import argparse
import collections.abc
import dataclasses
import inspect
import json
import math
import os
import sys
import traceback

from typing import Any, Collection, Dict, Iterable, List, Optional, Set, Tuple, TypeAlias, Union

from pxr import Sdf, Usd, UsdLux

IntFloat: TypeAlias = Union[int, float]

THIS_FILE = os.path.abspath(inspect.getsourcefile(lambda: None) or __file__)
THIS_DIR = os.path.dirname(THIS_FILE)
USD_DIR = os.path.join(THIS_DIR, "usd")


###############################################################################
# Constants
###############################################################################

LIGHT_NAME_SUFFIX = "_light"
OUTPUT_JSON_PATH = os.path.join(THIS_DIR, "light_descriptions.json")
USD_EXTENSIONS = (".usd", ".usda", ".usdc")

MISSING = object()

###############################################################################
# Utilities
###############################################################################


def is_ipython():
    try:
        __IPYTHON__  # type: ignore
    except NameError:
        return False
    return True


def is_iterable(obj) -> bool:
    try:
        iter(obj)
    except Exception:
        return False
    return True


def is_sorted(vals: Iterable):
    last = MISSING
    for current in vals:
        if last is MISSING:
            last = current
        elif last > current:
            return False
    return True


def vals_close(val1, val2):
    if isinstance(val1, float) or isinstance(val2, float):
        return math.isclose(val1, val2)
    return val1 == val2


def tuple_remove(tup, item):
    return tuple(x for x in tup if x != item)


def to_json_val(obj):
    if isinstance(obj, (int, float, str, type(None))):
        return obj
    elif isinstance(obj, Sdf.AssetPath):
        return obj.path
    elif isinstance(obj, collections.abc.Mapping):
        return {to_json_val(key): to_json_val(val) for key, val in obj.items()}
    elif is_iterable(obj):
        return list(to_json_val(x) for x in obj)
    raise RuntimeError(f"Do not know how to serialize: {obj}")


def format_val(val):
    if isinstance(val, float):
        if math.isclose(val, int(val)):
            val = int(val)
        else:
            return f"{val:.1f}".lstrip("0")
    elif isinstance(val, str):
        split = val.split("/")
        while split and split[0] in (".", ".."):
            del split[0]
        val = "/".join(split)
        return repr(val)
    elif isinstance(val, bool):
        # on/off are shorter than True/False
        return "on" if val else "off"
    return str(val)


def format_attr(attr_name):
    split = attr_name.split(":")
    if split[0] == "inputs":
        del split[0]
    if split[0] == "shaping":
        del split[0]
    return ":".join(split)


def get_light_name(light):
    if isinstance(light, Usd.Prim):
        light = light.GetName()
    if not light.endswith(LIGHT_NAME_SUFFIX):
        raise ValueError(f"light did not end with {LIGHT_NAME_SUFFIX!r}: {light}")
    return light[: -len(LIGHT_NAME_SUFFIX)]


def get_fallback(attr: Usd.Attribute):
    if not attr.HasFallbackValue():
        # xformOp:transform technically has no fallback, but we assume identity
        sdf_type = attr.GetTypeName().type
        py_type = sdf_type.pythonClass
        if py_type and py_type.__module__ == "pxr.Gf":
            return py_type()
        elif sdf_type.typeName == "SdfAssetPath":
            return ""
        return None
    prim_def = attr.GetPrim().GetPrimDefinition()
    attr_def = prim_def.GetAttributeDefinition(attr.GetName())
    if not attr_def:
        raise RuntimeError(f"Error getting attr defintion for {attr.GetPath()}")
    return attr_def.GetFallbackValue()


def find_usds(path: str, recurse=False):
    if os.path.isfile(path):
        paths = [path]
    elif os.path.isdir(path):
        paths = []
        for entry in os.scandir(path):
            if entry.is_file() and entry.name.endswith(USD_EXTENSIONS):
                paths.append(entry.path)
            elif entry.is_dir() and recurse:
                paths.extend(find_usds(entry.path), recurse=recurse)
    else:
        raise ValueError(f"path was not a file or directory: {path}")
    return paths


###############################################################################
# Dataclasses
###############################################################################


@dataclasses.dataclass
class FrameGroup:
    """A frame group is a range over which exactly 1 parameter is varying, and in the same direction"""

    # for each frame, dict from attr names to values
    # frames and attrs are both sorted
    frame_vals: Dict[IntFloat, Dict[str, Any]]
    varying: str  # the one varying attribute - "" for a single-frame group, non-empty for multi-frame
    constants: Tuple[str]  # constant, but not at default
    defaults: Tuple[str]  # constant, AND default
    increasing: bool = True

    def __post_init__(self):
        # sort the things...
        self.constants = tuple(sorted(self.constants))
        self.defaults = tuple(sorted(self.defaults))

        attrs = self.attrs()

        sorted_frame_vals = {}
        for frame in sorted(self.frame_vals):
            vals = self.frame_vals[frame]
            try:
                sorted_frame_vals[frame] = {attr: vals[attr] for attr in attrs}
            except KeyError as err:
                print(f"Frame {frame} was missing attr {err.args[0]!r}")
                raise
        self.frame_vals = sorted_frame_vals

        # verify assumptions
        self.validate()

    def frames(self):
        return tuple(self.frame_vals)

    def attrs(self) -> Tuple[str]:
        attrs = list(self.constants)
        attrs.extend(self.defaults)
        if self.varying:
            attrs.append(self.varying)
        return tuple(sorted(attrs))

    def validate(self):
        assert isinstance(self.constants, tuple)
        assert isinstance(self.defaults, tuple)
        attrs = self.attrs()
        if len(attrs) != len(set(attrs)):
            dupe = None
            known = set()
            for a in attrs:
                if a in known:
                    dupe = a
                    break
                known.add(a)
            raise ValueError(
                f"duplicate attribute: {dupe} - varying: {self.varying} - constants: {self.constants} - defaults:"
                f" {self.defaults}"
            )

        if len(self.frame_vals) == 0:
            raise ValueError("empty frames")
        if len(self.frame_vals) == 1:
            if self.varying:
                raise ValueError("had only 1 frame, but had a varying attr")
        elif not self.varying:
            raise ValueError("had only more than 1 frame, but did not have a varying attr")

        if not is_sorted(self.frame_vals):
            raise ValueError("attrs were not sorted")

        for frame, vals in self.frame_vals.items():
            if tuple(vals) != attrs:
                # Something is wrong with attrs on this frame - figure out what,
                # and print more informative error
                vals_set = set(vals)
                attrs_set = set(attrs)
                if vals_set != attrs_set:
                    missing = attrs_set - vals_set
                    if missing:
                        raise ValueError(f"frame {frame} missing attributes: {', '.join(missing)}")
                    extra = vals_set - attrs_set
                    raise ValueError(f"frame {frame} had extra attributes: {', '.join(extra)}")
                # same set, so must just be out of order
                if not is_sorted(vals):
                    raise ValueError(f"attrs for frame {frame} not sorted: {', '.join(vals)}")
                elif not is_sorted(attrs):
                    raise ValueError(f"self.attrs() was not sorted: {', '.join(attrs)}")
                # hmm... not sure what's wrong?
                raise ValueError(f"Unknown error with attributes for frame {frame} - wanted {attrs}, got {tuple(vals)}")

    def find_varying_vals(self, this_frame: IntFloat, other: "FrameGroup", other_frame: IntFloat):
        this_vals = self.frame_vals[this_frame]
        other_vals = other.frame_vals[other_frame]
        # returns dict from attr name to "increasing" bool
        attr_to_increasing = {}
        for attr in self.attrs():
            old = this_vals[attr]
            new = other_vals[attr]
            if not vals_close(old, new):
                attr_to_increasing[attr] = new > old
        return attr_to_increasing

    def combine(self, other: "FrameGroup") -> bool:
        """Adds the frame_vals from single-frame FrameGroup other to this group, if possible

        Returns true if the the frame_vals were combined (in which case other can be discarded)
        """
        attrs = self.attrs()
        if attrs != other.attrs():
            raise ValueError("to combine two FrameGroups, must be over same set of attrs")

        # below two are just confirming assumptions, so I don't have to think about general case...
        if len(other.frame_vals) != 1:
            raise ValueError("currenly only support adding a frame group of size 1")
        if max(self.frame_vals) >= min(other.frame_vals):
            raise ValueError("currenly only support adding a frame group whose frames are all strictly greater")
        can_combine = False
        this_frame = self.frames()[-1]
        other_frame = other.frames()[0]

        new_varying = self.find_varying_vals(this_frame, other, other_frame)
        if len(self.frame_vals) == 1:
            # This is the only situation in which we can potentially set the self.varying...
            assert self.varying == ""

            if len(new_varying) == 1:
                self.varying, self.increasing = list(new_varying.items())[0]

                # remove varying attr from defaults or constants
                if self.varying in self.constants:
                    self.constants = tuple_remove(self.constants, self.varying)
                elif self.varying in self.defaults:
                    self.defaults = tuple_remove(self.defaults, self.varying)
                else:
                    raise RuntimeError(
                        f"programming logic error - new varying value {self.varying} not found in either "
                        f"constants ({self.constants}) or defaults ({self.defaults})"
                    )
                can_combine = True

        elif len(new_varying) == 1 and list(new_varying.items())[0] == (self.varying, self.increasing):
            can_combine = True

        if can_combine:
            # only thing we should need to do is add in the new frames
            self.frame_vals[other_frame] = other.frame_vals[other_frame]
            self.validate()
        return can_combine

    @classmethod
    def for_frame(
        cls, frame: IntFloat, vals: Dict[Usd.Attribute, IntFloat], default_vals: Optional[Dict[str, Any]] = None
    ) -> "FrameGroup":
        # if we only have one frame, there's nothing to vary, so all we can do
        # is check which are at defaults
        if default_vals is None:
            default_vals = {}

        default_attrs = []
        constant_attrs = []

        for attr, val in vals.items():
            name = attr.GetName()
            default = default_vals.get(name, MISSING)
            if default is MISSING:
                default = get_fallback(attr)
                default_vals[name] = default
            if vals_close(val, default):
                default_attrs.append(name)
            else:
                constant_attrs.append(name)
        vals_by_name = {attr.GetName(): val for attr, val in vals.items()}
        frame_vals = {frame: vals_by_name}
        return cls(
            frame_vals=frame_vals,
            varying="",
            constants=constant_attrs,
            defaults=default_attrs,
        )

    @classmethod
    def for_frame_attrs(
        cls, frame: IntFloat, attrs: Iterable[Usd.Attribute], default_vals: Optional[Dict[str, Any]] = None
    ) -> "FrameGroup":
        all_names = sorted(attr.GetName() for attr in attrs)
        if len(all_names) != len(set(all_names)):
            raise ValueError(f"name clash in attrs: {attrs}")
        vals = {attr: to_json_val(attr.Get(frame)) for attr in attrs}
        default_vals = {}
        return cls.for_frame(frame, vals, default_vals=default_vals)

    def to_dict(self):
        frames = self.frames()
        start = frames[0]
        end = frames[-1]
        if self.varying:
            varying_vals = {frame: vals[self.varying] for frame, vals in self.frame_vals.items()}
        else:
            varying_vals = {}

        if self.constants:
            # constant vals by def should be same for all frames - grab first
            first_vals = next(iter(self.frame_vals.values()))
            constants = {n: first_vals[n] for n in self.constants}
        else:
            constants = {}
        return {
            "frames": (start, end),
            "varying_attr_name": self.varying,
            "varying_vals": varying_vals,
            "non_default_constants": constants,
        }


# Note: this assumes defaults can't be animated, which isn't strictly always
# true in Houdini, but should be for our scene...


@dataclasses.dataclass
class FrameGroupFinder:
    all_attrs: List[Usd.Attribute]
    all_frames: List[IntFloat]
    frame_groups: List[FrameGroup] = dataclasses.field(default_factory=list)

    def run(self):
        for frame in self.all_frames:
            self.run_frame(frame)

    def run_frame(self, frame: IntFloat):
        new_group = FrameGroup.for_frame_attrs(frame, self.all_attrs)
        if not self.frame_groups:
            # special case, very first frame
            self.frame_groups.append(new_group)
            return
        last_group = self.frame_groups[-1]
        combined = last_group.combine(new_group)
        if not combined:
            self.frame_groups.append(new_group)

    @classmethod
    def find(cls, all_attrs: Iterable[Usd.Attribute], all_frames: Iterable[IntFloat]) -> List[FrameGroup]:
        finder = cls(all_attrs=list(all_attrs), all_frames=list(all_frames))
        finder.run()
        return finder.frame_groups


###############################################################################
# Core functions
###############################################################################


def write_light_param_descriptions(path: str, recurse: bool = False, json_out_path=OUTPUT_JSON_PATH, errors="raise"):
    usd_paths = find_usds(path, recurse=recurse)
    if not usd_paths:
        raise ValueError(f"Could not find any USD files at path: {path}")
    descriptions = {}
    for usd_path in usd_paths:
        stage = Usd.Stage.Open(usd_path)
        print(f"Processing: {usd_path}")
        descriptions.update(gen_light_param_descriptions(stage, errors=errors))

    print(f"Got {len(descriptions)} descriptions")
    print("=" * 80)
    for light_name, desc in descriptions.items():
        print()
        print(f"{light_name}:")
        print(summarize_light(light_name, desc))
    print("=" * 80)
    print
    print(f"Writing as json: {json_out_path}")
    with open(json_out_path, "w", encoding="utf8") as writer:
        json.dump(descriptions, writer, sort_keys=True, indent=4)
    return


SUMMARY_OVERRIDES = {
    "distant": {
        (21, 25): "cam rotate from 0 to 80 (intensity 3720)",
        (26, 30): "light rotate from 0 to 80 (intensity 3720)",
    },
}


def find_summary_override(light_name: str, start: int, end: int):
    light_overrides = SUMMARY_OVERRIDES.get(light_name)
    if light_overrides is None:
        return None
    for frames, desc in light_overrides.items():
        override_start, override_end = frames
        if override_start <= start and end <= override_end:
            return frames, desc
    return None


def get_light_group_summaries(light_name, light_description):
    groups = light_description.get("frame_groups")
    if not groups:
        return []

    already_printed_overrides: Set[Tuple[int, int]] = set()

    summaries_by_start_frame = {}
    for group in groups:
        start, end = group["frames"]

        override = find_summary_override(light_name, start, end)
        if override is not None:
            override_frames, override_desc = override
            if override_frames in already_printed_overrides:
                continue
            already_printed_overrides.add(override_frames)
            start, end = override_frames
            frame_desc = override_desc
        else:
            varying = group["varying_attr_name"]
            if not varying:
                frame_desc = "(constant)"
            else:
                vals = group["varying_vals"]

                # if we're dealing with a description we read from json, all keys were stringified
                def get_val(frame):
                    val = vals.get(frame)
                    if val is not None:
                        return val
                    return vals[str(frame)]

                varying_desc = f"{format_attr(varying)} from {format_val(get_val(start))} to {format_val(get_val(end))}"
                constants = group["non_default_constants"]
                if not constants:
                    constants_desc = ""
                else:
                    constant_descs = []
                    for const_name, val in constants.items():
                        constant_descs.append(f"{format_attr(const_name)}={format_val(val)}")
                    constants_desc = ", ".join(constant_descs)
                    constants_desc = f" ({constants_desc})"
                frame_desc = f"{varying_desc}{constants_desc}"

        if start == end:
            frame_str = str(start)
        else:
            frame_str = f"{start}-{end}"

        summaries_by_start_frame[start] = f"{frame_str}: {frame_desc}"
    return summaries_by_start_frame


def summarize_light(light_name, light_description):
    summaries = get_light_group_summaries(light_name, light_description)
    if not summaries:
        return ""

    return "\n".join(summaries.values())


def gen_light_param_descriptions(stage: Usd.Stage, errors="raise"):
    lights = [x for x in stage.Traverse() if x.HasAPI(UsdLux.LightAPI)]
    if not lights:
        raise RuntimeError(f"stage had no lights: {stage}")

    all_descs = {}
    layer = stage.GetRootLayer()
    stage_path = layer.realPath
    if not stage_path:
        stage_path = layer.identifier
    for light in lights:
        try:
            light_desc = get_light_param_description(light)
            light_name = light_desc.pop("light_name")
            light_desc["usd_path"] = stage_path
            if light_name in all_descs:
                raise ValueError(f"Light name appeared twice: {light_name}")
            all_descs[light_name] = light_desc
        except Exception:
            print(f"WARNING: Error processing light {light.GetPath()} in stage {stage_path}")
            if errors == "raise":
                raise

    return all_descs


def get_light_param_description(light: Usd.Prim) -> Dict[str, any]:
    light_name = get_light_name(light)

    attrs = light.GetAuthoredAttributes()
    attrs = [x for x in attrs if not x.GetNamespace().split(":", 1)[0] == "houdini"]
    attrs = [x for x in attrs if x.GetName() != "extent"]
    # ValueMightBeTimeVarying doesn't GUARANTEE that results will have
    # more than 1 time sample - so just use slower GetTimeSamples()
    attrs = [x for x in attrs if len(x.GetTimeSamples()) > 1]
    attrs.sort(key=lambda x: x.GetPath())

    light_data = {"light_name": light_name}
    all_samples = Usd.Attribute.GetUnionedTimeSamples(attrs)
    if not all_samples:
        return light_data
    all_samples.sort()

    # we render at fixes frames, no at samples - so get first / last, then iterate over range
    start = math.floor(all_samples[0])
    # want end to be the value to pass to range, which needs to be > the last sample
    end_plus_one = int(all_samples[-1]) + 1
    frames = list(range(start, end_plus_one))

    frame_groups = FrameGroupFinder.find(all_attrs=attrs, all_frames=frames)
    light_data["frame_groups"] = [x.to_dict() for x in frame_groups]
    attr_names = [x.GetName() for x in attrs]

    # xformOps are commonly set to non-default, and uninteresting for us - only
    # include them if they're varying
    all_varying = set()
    removed = set()
    for group in light_data["frame_groups"]:
        if group["varying_attr_name"]:
            all_varying.add(group["varying_attr_name"])
        for key in list(group["non_default_constants"]):
            if key.startswith("xformOp:"):
                removed.add(key)
                del group["non_default_constants"][key]

    non_varying_removed = removed - all_varying
    if non_varying_removed:
        attr_names = [x for x in attr_names if x not in non_varying_removed]

    light_data["frames"] = (frames[0], frames[-1])
    light_data["attrs"] = attr_names
    return light_data


def read_descriptions(path=OUTPUT_JSON_PATH):
    with open(path, "r", encoding="utf8") as reader:
        return json.load(reader)


###############################################################################
# CLI
###############################################################################


def get_parser():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=USD_DIR,
        help="path to a single usd file or a directory to search for usd files",
    )
    parser.add_argument(
        "-r",
        "--recurse",
        action="store_true",
        help="if PATH is a directory, whether to search sub-directories recursively",
    )
    parser.add_argument(
        "-e",
        "--errors",
        choices=("raise", "warn"),
        default="raise",
        help=(
            "How to handle errors when processing a given usda or light - if "
            "'raise', then any error will immediately halt; if 'warn', then a "
            "warning will continue, then processing will continue on other "
            "lights or usda files"
        ),
    )
    return parser


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    parser = get_parser()
    args = parser.parse_args()
    try:
        write_light_param_descriptions(args.path, recurse=args.recurse, errors=args.errors)
    except Exception:  # pylint: disable=broad-except

        traceback.print_exc()
        return 1
    return 0


if __name__ == "__main__" and not is_ipython():
    sys.exit(main())
