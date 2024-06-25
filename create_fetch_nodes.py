
    
    if not out_context:
        raise Exception("Error: Could not find /out context.")
    
    created_nodes = []
    all_fetch_nodes = []
    # Iterate through all nodes in the /stage context
    for render_node in usdrender_rop_nodes:
        fetch_name = f"fetch_{render_node.name()}"
        fetch_path = f"/out/{fetch_name}"
        fetch_node = hou.node(fetch_path)
        if not fetch_node:
            # Create a fetch node in the /out context
            out_context.createNode('fetch', node_name=fetch_name)
            fetch_node = hou.node(fetch_path)
            assert fetch_node
            fetch_node.parm('source').set(render_node.path())
            created_nodes.append(fetch_node)
        all_fetch_nodes.append(fetch_node)
    if created_nodes:
        out_context.layoutChildren(items=created_nodes)
    return created_nodes, all_fetch_nodes
            