import re

import hou

###############################################################################
# General Houdini Utilities
###############################################################################


def top_stage_nodes():
    return hou.node("/stage").children()


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


def parse_light_name(nodename):
    if isinstance(nodename, hou.Node):
        nodename = nodename.name()
    return LIGHT_NAME_RE.match(nodename).group("name")


def get_standardized_name(node, associated_light_node):
    light_name = parse_light_name(associated_light_node.name())
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
