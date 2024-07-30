import os

import hou

from pxr import Sdf

node = hou.pwd()
stage = node.editableStage()

this_hip_file = os.path.abspath(hou.hipFile.path())
this_dir = os.path.dirname(this_hip_file)
custom_laya_data_usda = os.path.join(this_dir, "customLayerData.usda")

metadata_layer = Sdf.Layer.FindOrOpen(custom_laya_data_usda)
new_metadata = metadata_layer.customLayerData

light_name = node.name().rsplit("_", 1)[-1]

usd_rop_node = hou.node(f"/stage/usd_rop_{light_name}")
start_frame = round(usd_rop_node.parm("f1").eval())
end_frame = round(usd_rop_node.parm("f2").eval())

new_metadata["MovieCaptureSettings"]["capture_frame_start"] = start_frame
new_metadata["MovieCaptureSettings"]["capture_frame_end"] = end_frame
new_metadata["MovieCaptureSettings"]["capture_name"] = f"{light_name}-rtx"
new_metadata["omni_layer"]["authoring_layer"] = f"./{light_name}.usda"
new_metadata["renderSettings"]["rtx:externalFrameCounter"] = end_frame

stage.GetSessionLayer().customLayerData = new_metadata
