import inspect
import os
import re
import sys

from typing import Iterable, Optional, Union

import hou

###############################################################################
# Constants
###############################################################################

THIS_FILE = os.path.abspath(inspect.getsourcefile(lambda: None) or __file__)
THIS_DIR = os.path.dirname(THIS_FILE)

###############################################################################
# General Houdini Utilities
###############################################################################


def top_stage_nodes(type=""):
    nodes = hou.node("/stage").children()
    if type:
        if isinstance(type, str):
            type = lop_type(type)
        nodes = [x for x in nodes if x.type() == type]
    return nodes


RENDERER_SHORT_NAMES = {
    "BRAY_HdKarma": "karma",
    "HdArnoldRendererPlugin": "arnold",
    "HdPrmanLoaderRendererPlugin": "ris",
}


def get_renderer(node):
    return RENDERER_SHORT_NAMES[node.parm("renderer").eval()]


def lop_type(name):
    return hou.lopNodeTypeCategory().nodeType(name)


def base_type(nodetype):
    if isinstance(nodetype, hou.Node):
        nodetype = nodetype.type()
    return nodetype.namespaceOrder()[-1]


def is_light_type(nodetype):
    return base_type(nodetype) in ("light", "distantlight", "domelight")


def is_light(node):
    return is_light_type(node.type())


def get_connected_recursive(node, predicate, direction, visited=None):
    results = set()
    if predicate(node):
        results.add(node)
    if visited is None:
        visited = set([node])
    else:
        visited.add(node)
    if direction == "outputs":
        get_next = node.outputs
    elif direction == "inputs":
        get_next = node.inputs
    for other_node in get_next():
        if other_node not in visited:
            results.update(get_connected_recursive(other_node, predicate, direction, visited=visited))
    return results


def get_upstream(node, predicate):
    return get_connected_recursive(node, predicate, "inputs")


def get_downstream(node, predicate):
    return get_connected_recursive(node, predicate, "outputs")


def get_downstream_lights(node):
    return get_downstream(node, is_light)


def get_upstream_lights(node):
    return get_upstream(node, is_light)


def get_connected_lights(node):
    if is_light(node):
        return set([node])
    input_lights = get_upstream_lights(node)
    if input_lights:
        return input_lights
    return get_downstream_lights(node)


def get_rop_out_parm(node):
    if node.type() == lop_type("usd_rop"):
        return node.parm("lopoutput")
    elif node.type() == lop_type("usdrender_rop"):
        return node.parm("outputimage")
    else:
        raise TypeError(f"Unrecognized rop node type: {node} - {node.type()}")


def get_non_default_parms(nodeOrParms, frames: Optional[Iterable[Union[float, int]]] = None):
    if isinstance(nodeOrParms, hou.Node):
        parms = nodeOrParms.parms()
    else:
        parms = list(nodeOrParms)
    if frames is None:
        return set([x for x in parms if not x.isAtDefault()])
    orig_frame = hou.frame()
    non_default = None
    try:
        for frame in frames:
            hou.setFrame(frame)
            current_non_defaults = get_non_default_parms(parms)
            if non_default is None:
                non_default = current_non_defaults
            else:
                non_default.update(current_non_defaults)
    finally:
        hou.setFrame(orig_frame)
    return non_default


def parmgrep(node, input):
    regex = re.compile(input, re.IGNORECASE)
    names = [hou.text.decode(x.name()) for x in node.parms()]
    return [x for x in names if regex.search(x)]


def houdini_range(start, stop=None, step=1):
    if stop is None:
        start = 0
        stop = start - 1
    current = start
    while current <= stop:
        yield current
        current += step


def get_frames(node):
    start = node.parm("f1").eval()
    stop = node.parm("f2").eval()
    step = node.parm("f3").eval()
    return houdini_range(start, stop, step)


###############################################################################
# Naming Utils
###############################################################################

NODE_BASE_TYPE_TO_CATEGORY = {
    "usd_rop": "usd_rop",
    "usdrender_rop": "render",
    "camera": "camera_edit",
    "distantlight": "light",
    "domelight": "light",
    "light": "light",
    "editproperties": "editproperties",
    "xform": "xform",
}


def node_category(node):
    base = base_type(node)
    return NODE_BASE_TYPE_TO_CATEGORY.get(base, base)


LIGHT_NAME_RE = re.compile("^(?P<name>.*)_light$")


def parse_light_name(node_or_name):
    if isinstance(node_or_name, hou.Node):
        nodename = node_or_name.name()
    else:
        nodename = node_or_name
    return LIGHT_NAME_RE.match(nodename).group("name")


def get_standardized_name(node, associated_light_node):
    light_name = parse_light_name(associated_light_node)
    category = node_category(node)
    if category == "light":
        return f"{light_name}_light"
    elif category == "render":
        renderer = get_renderer(node)
        return f"{category}_{renderer}_{light_name}"
    elif category == "xform":
        prim_name = node.parm("primpattern").eval().rstrip("/").rsplit("/", 1)[-1]
        return f"{category}_{prim_name}_{light_name}"
    else:
        return f"{category}_{light_name}"


def standardize_node_names(dry_run=True):
    renames = []
    for node in top_stage_nodes():
        lights = get_connected_lights(node)
        if len(lights) != 1:
            continue
        light = lights.pop()
        new_name = get_standardized_name(node, light)
        old_name = node.name()
        if old_name != new_name:
            renames.append((old_name, new_name, node))
    print()
    print("=" * 80)
    if not renames:
        print("Found no nodes to rename")
        return
    renames.sort()
    print(f"Found {len(renames)} nodes to rename:")
    print("=" * 80)
    for old_name, new_name, node in renames:
        print(f"rename: {old_name} => {new_name}")
        if not dry_run:
            node.setName(new_name)
    print("=" * 80)
    if dry_run:
        print("dry_run=True - nothing changed - to change names, use:")
        print("  standardize_node_names(dry_run=False)")


def get_standardized_output_path(node, light_node):
    light_name = parse_light_name(light_node)
    if node.type() == lop_type("usd_rop"):
        return f"$HIP/usd/{light_name}.usda"
    elif node.type() == lop_type("usdrender_rop"):
        renderer = get_renderer(node)
        return f"$HIP/renders/{renderer}/{light_name}-{renderer}.$F4.exr"


def standardize_output_names(dry_run=True):
    renames = []
    rop_nodes = [x for x in top_stage_nodes() if isinstance(x, hou.RopNode)]
    for rop in rop_nodes:
        lights = get_connected_lights(rop)
        if len(lights) != 1:
            print(f"found rop that couldn't be associated with one light: {rop} - {lights}")
            continue
        light = lights.pop()
        new_output_path = get_standardized_output_path(rop, light)
        parm = get_rop_out_parm(rop)
        old_output_path = parm.rawValue()
        if old_output_path != new_output_path:
            renames.append((rop.name(), parm, old_output_path, new_output_path))
    print()
    print("=" * 80)
    if not renames:
        print("Found no node output paths to change")
        return
    renames.sort()
    print(f"Found {len(renames)} nodes with output paths to change:")
    print("=" * 80)
    for node_name, parm, old_output_path, new_output_path in renames:
        print(f"rename output for {node_name}:")
        print(f"  {old_output_path}")
        print(f"  {new_output_path}")
        if not dry_run:
            parm.set(new_output_path)
    print("=" * 80)
    if dry_run:
        print("dry_run=True - nothing changed - to change names, use:")
        print("  standardize_output_names(dry_run=False)")


###############################################################################
# Summaries
###############################################################################

SUMMARY_LINE_RE = re.compile("^\d+(?:-\d+)?:\s+.+", re.MULTILINE)


def reset_net_box_summaries(dry_run=True):
    if THIS_DIR not in sys.path:
        sys.path.append(THIS_DIR)

    import genLightParamDescriptions

    param_descriptions = genLightParamDescriptions.read_descriptions()

    stage = hou.node("/stage")

    to_update = []
    for box in stage.networkBoxes():
        # find the light
        lights = [x for x in box.nodes() if is_light(x)]
        if not lights:
            continue
        if len(lights) > 1:
            raise RuntimeError("more than one light? oh noes!")
        light = lights[0]
        light_name = parse_light_name(light)
        usd_light_name = light_name.replace("-", "_")

        # now find the sticky note with the summary
        stickies = [x for x in box.stickyNotes() if SUMMARY_LINE_RE.search(x.text())]
        if len(stickies) != 1:
            raise RuntimeError(f"can't find right sticky for net box for light {light_name}")
        sticky = stickies[0]

        # now get the new summary text
        desc = param_descriptions[usd_light_name]
        try:
            summary = genLightParamDescriptions.summarize_light(light_name, desc)
        except Exception:
            print(desc)
            print(f"error summarizing light: {light_name}")
            raise
        if not summary:
            continue

        if sticky.text() != summary:
            to_update.append((light_name, sticky, summary))

    print()
    print("=" * 80)
    if not to_update:
        print("Found no network box summaries to update")
        return
    to_update.sort()
    print(f"Found {len(to_update)} network box summaries to update:")
    print("=" * 80)
    for light_name, sticky, summary in to_update:
        print()
        print(f"{light_name}:")
        print(summary)
        if not dry_run:
            sticky.setText(summary)
    print("=" * 80)
    if dry_run:
        print("dry_run=True - nothing changed - to change summaries, use:")
        print("  reset_net_box_summaries(dry_run=False)")
