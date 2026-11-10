"""
Hi there!
Thanks for picking this tool!
This one is a very small one but can speed Locator placements up a bit.

What it does:
It created and moves a Locator to a selected Object and matches the Transformations.

How to use it:
Select the Object and click the Tool! Thats it!
"""
import maya.cmds as cmds

def locator_at_selected(use_offset_group=True):
    sel = cmds.ls(selection=True, long=True)
    if not sel:
        cmds.warning("Select at least one object.")
        return

    created = []
    for obj in sel:
        short = obj.split("|")[-1]
        matrix = cmds.xform(obj, q=True, worldSpace=True, matrix=True)
        rot_order = cmds.getAttr(obj + ".rotateOrder")

        loc = cmds.spaceLocator(name=short + "_loc")[0]
        cmds.setAttr(loc + ".rotateOrder", rot_order)

        if use_offset_group:
            # Offset group carries the world transform, locator stays clean
            grp = cmds.group(empty=True, name=short + "_loc_offset")
            cmds.setAttr(grp + ".rotateOrder", rot_order)
            cmds.xform(grp, worldSpace=True, matrix=matrix)
            loc = cmds.parent(loc, grp, relative=True)[0]
            created.append(grp)
        else:
            # Locator holds the transform, then gets frozen (rotation is lost)
            cmds.xform(loc, worldSpace=True, matrix=matrix)
            cmds.makeIdentity(loc, apply=True, t=True, r=True, s=True, n=False)
            created.append(loc)

    cmds.select(created)
    return created

locator_at_selected()