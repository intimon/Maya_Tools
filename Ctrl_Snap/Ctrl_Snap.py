import maya.cmds as cmds

"""
Hi there!
Thanks for picking this tool!
This one is a very small one but can help a lot when adding Ctrls to Rigs by hand.

What it does:
It moves a selected Nurbs Curve to a selected Joint.

How to use it:
Select the CTRL first (Curve) > next select the Joint, while also pressing Shift on your keyboard.
Now while both selected use this script!
That’s all!! 
"""

# Create a list for the selected items
sel = cmds.ls(sl=True)

# If to few or many objects are selected > warning!
if len(sel) != 2:
    cmds.error("Select Control first, then Joint.")

# Saves your selection into a new Variable > why order matters
ctrl = sel[0]
joint = sel[1]

# Match control rotation to joint
cmds.delete(cmds.orientConstraint(joint, ctrl, mo=False))

# Freeze rotation so the control keeps the orientation but reads 0
cmds.makeIdentity(ctrl, apply=True, r=True)

# Create buffer group
buffer = cmds.group(em=True, name=f"{ctrl}_BUF")

# Match buffer to joint
cmds.delete(cmds.parentConstraint(joint, buffer, mo=False))

# Parent control under buffer
cmds.parent(ctrl, buffer)

# Zero control under buffer 
cmds.setAttr(ctrl + ".translate", 0, 0, 0)
cmds.setAttr(ctrl + ".rotate", 0, 0, 0)

# Constrain joint to control
cmds.parentConstraint(ctrl, joint, mo=False)

print(f"Created buffer and constrained {joint} to {ctrl}")s 