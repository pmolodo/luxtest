# execfile(r"C:\src\NVIDIA\luxtest\create_attr_refs.py")
import hou

lnames = ["sphere", "rect", "disk", "cylinder"]

lights = {lname: hou.node(f"/stage/{lname}_light") for lname in lnames}

sphere_light = lights["sphere"]
rect_light = lights["rect"]
disk_light = lights["disk"]
cylinder_light = lights["cylinder"]

sl_name = "sphere"
dl_names = [x for x in lnames if x != sl_name]
source_light = lights[sl_name]
# dest_lights = [hou.node(f"/stage/{x}_light") for x in ("sphere", "disk", "cylinder")]
dest_lights = [lights[n] for n in dl_names]

l = source_light


def parmgrep(node, substr):
    substr = substr.lower()
    parm_names = [x.name() for x in node.parms()]
    return [x for x in parm_names if substr in x.lower()]


def get_keyframed(node, hidden=False):
    result = [x for x in node.parms() if len(x.keyframes()) > 1]
    if not hidden:
        result = [x for x in result if not x.isHidden()]
    return sorted(result, key=lambda n: hou.text.decode(n.name()))


def get_pnames(parms):
    return [hou.text.decode(p.name()) for p in parms]


def get_key_names(node, hidden=False):
    result = get_pnames(get_keyframed(node, hidden=hidden))
    return result


keyframed = {lname: get_keyframed(l) for lname, l in lights.items()}
key_names = {lname: set(get_key_names(l)) for lname, l in lights.items()}


# source_names = set(get_key_names(source_light))

# dest_names = [set(get_key_names(x)) for x in dest_lights]

common_names = set(key_names[sl_name])
for n in dl_names:
    common_names.intersection_update(key_names[n])

# inputs:width is defined / keyframed on all, but really we only want it on rect
common_names.discard("inputs:width")

unique_names = {lname: x - common_names for lname, x in key_names.items()}


def get_key_values(parm, keyframes=None):
    if keyframes is None:
        keyframes = parm.keyframes()
    return [(x.frame(), parm.evalAtFrame(x.frame())) for x in keyframes]


orig_vals = {
    lname: {hou.text.decode(attr.name()): get_key_values(attr) for attr in get_keyframed(l)}
    for lname, l in lights.items()
}

common_vals = {
    lname: {aname: avals for aname, avals in lvals.items() if aname in common_names}
    for lname, lvals in orig_vals.items()
}

different = {}
source_vals = common_vals[sl_name]
for dname in dl_names:
    dest_vals = common_vals[dname]
    if dest_vals == source_vals:
        continue
    different[dname] = [x for x in common_names if source_vals[x] != dest_vals[x]]


import pprint


def deleteKeyframes(attr):
    attr.deleteAllKeyframes()
    attr.revertToDefaults()
    attr.setAutoscope(False)


def makeRefAttr(source, dest):
    orig_keyframes = dest.keyframes()
    orig_vals = get_key_values(dest)
    rel_node_path = dest.node().relativePathTo(source.node())
    rel_attr_path = f"{rel_node_path}/{source.name()}"
    if dest.parmTemplate().type() == hou.parmTemplateType.String:
        ref_func = "chs"
    else:
        ref_func = "ch"
    expression = f'{ref_func}("{rel_attr_path}")'
    dest.deleteAllKeyframes()
    dest.setExpression(expression=expression, language=hou.exprLanguage.Hscript)
    new_vals = get_key_values(dest, orig_keyframes)
    if new_vals != orig_vals:
        print("Error! new_vals != orig_vals")
        print(f"orig_vals = {pprint.pformat(orig_vals)}")
        print()
        print(f"new_vals = {pprint.pformat(new_vals)}")
        print()
        dest.deleteAllKeyframes()
        dest.setKeyframes(orig_keyframes)
        raise Exception("did not match after changing")


class IsSource:
    pass


class DeleteKeyframes:
    pass


extra_attr_map = {
    "sphere": {
        "inputs:radius": IsSource,
        "inputs:width": DeleteKeyframes,
        "inputs:height": DeleteKeyframes,
    },
    "rect": {
        "inputs:width": IsSource,  # one of a kind...
        "inputs:radius": DeleteKeyframes,
    },
    "disk": {
        "inputs:radius": "sphere",
        "inputs:shaping:focus": IsSource,  # source for cylinder
        "inputs:exposure": IsSource,  # source for cylinder
        "inputs:width": DeleteKeyframes,
        "inputs:height": DeleteKeyframes,
    },
    "cylinder": {
        "inputs:radius": "sphere",
        "inputs:shaping:focus": "disk",
        "inputs:exposure": "disk",
        "inputs:width": DeleteKeyframes,
        "inputs:height": DeleteKeyframes,
    },
}


def redoDeleteKeyframes():
    for lname, attrmap in extra_attr_map.items():
        for aname, source in attrmap.items():
            if source == DeleteKeyframes:
                parm = lights[lname].parm(hou.text.encode(aname))
                deleteKeyframes(parm)


assert orig_vals["disk"] == orig_vals["cylinder"]  # all keyframed attrs agree here
assert common_vals["sphere"] == common_vals["rect"]  # all shared keyframed attrs agree

assert (
    orig_vals["sphere"]["inputs:radius"] == orig_vals["disk"]["inputs:radius"] == orig_vals["cylinder"]["inputs:radius"]
)

final_attr_node_maps = {}
final_attr_maps = {}

for lname in lnames:
    dest_node = lights[lname]
    from_source = set(common_vals[lname]) - set(different.get(lname, []))
    l_extra_attrs = extra_attr_map.get(lname, {})
    from_extra_attrs = set(l_extra_attrs)

    in_both_extra_attrs_and_source = from_source.intersection(from_extra_attrs)
    if in_both_extra_attrs_and_source:
        msg = f"Found attributes that were in both from_source and from_extra_attrs ({lname})"
        print(msg)
        for a in sorted(in_both_extra_attrs_and_source):
            print(f"  {a}")
        raise Exception(msg)

    all_changed_attrs = from_extra_attrs.union(from_source)
    l_key_names = set(key_names[lname])

    # Ignore any attrs that we have marked as DeleteKeyframes, but that already have no keyframes
    for attrname, source in list(l_extra_attrs.items()):
        if source == DeleteKeyframes:
            if attrname not in l_key_names:
                all_changed_attrs.discard(attrname)

    if all_changed_attrs != l_key_names:
        all_only = all_changed_attrs - l_key_names
        print(f"attrs only in all_changed_attrs:")
        for a in sorted(all_only):
            print(f"  {a}")
        key_names_only = l_key_names - all_changed_attrs
        print(f"attrs only in l_key_names:")
        for a in sorted(key_names_only):
            print(f"  {a}")
        raise Exception(f"Missing (or extra?) attrs for light: {lname}")

    lattr_node_map = {aname: sl_name for aname in from_source}
    lattr_node_map.update(l_extra_attrs)

    lattr_map = {}
    for aname, source_lname in lattr_node_map.items():
        if source_lname == lname or source_lname == IsSource:
            continue
        encname = hou.text.encode(aname)
        dest_attr = dest_node.parm(encname)
        if source_lname == DeleteKeyframes:
            source_attr = DeleteKeyframes
        else:
            source_attr = lights[source_lname].parm(encname)
        lattr_map[dest_attr] = source_attr

    final_attr_node_maps[lname] = lattr_node_map
    final_attr_maps[lname] = lattr_map

dry_run = False

for lname, lattr_map in final_attr_maps.items():
    print(f"{lname}:")
    print("=" * 80)
    for dest_attr, source_attr in lattr_map.items():
        if source_attr == DeleteKeyframes:
            print(f"  Deleting keyframes from: {dest_attr.path()}")
            if not dry_run:
                deleteKeyframes(dest_attr)
        else:
            print(f"  Making ref: {dest_attr.path()} <= {source_attr.path()}")
            if not dry_run:
                makeRefAttr(source_attr, dest_attr)
    print()
