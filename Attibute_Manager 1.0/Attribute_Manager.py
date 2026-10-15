#-----------------------------------------------------
#-------------- Open Attribute Manager ---------------
def attribute_manager():
    win = "AttrManagerTabs"
    if cmds.window(win, exists=True):
        cmds.deleteUI(win)

    attr_list = []


# --------------- Refresh Function ---------------
    def refresh():
        cmds.textScrollList("attrList", e=True, removeAll=True)
        for i, a in enumerate(attr_list):
            label = f"{i+1}. {a['name']} ({a['type']})"
            if a['type'] == "enum" and a['enum'] == "- - - - - -":
                label += " [DIVIDER]"
            elif a['type'] == "enum" and a['enum']:
                label += f" [{a['enum']}]"
            if a.get("existing"):
                label += " [EXISTING]"
            cmds.textScrollList("attrList", e=True, append=label)


# --------- Get Object ------------------
    def get_object():
        obj = cmds.textFieldButtonGrp("objField", q=True, text=True)
        return obj if cmds.objExists(obj) else None


# ------------ Move Attributes ------------------
    def move(dir):
        sel = cmds.textScrollList("attrList", q=True, selectIndexedItem=True)
        if not sel:
            return

        i = sel[0] - 1
        if dir == "up" and i > 0:
            attr_list[i], attr_list[i-1] = attr_list[i-1], attr_list[i]
            i -= 1
        elif dir == "down" and i < len(attr_list) - 1:
            attr_list[i], attr_list[i+1] = attr_list[i+1], attr_list[i]
            i += 1
        else:
            return

        refresh()
        cmds.textScrollList("attrList", e=True, selectIndexedItem=i+1)


# ----------- Create Attribute ----------------
    def add_new_default():
        base_name = "newAttr"
        count = 1
        existing_names = [a["name"] for a in attr_list]

        while f"{base_name}{count}" in existing_names:
            count += 1
        
        # Definition Defualt Attribute
        default_attr = {
            'name': f"{base_name}{count}",
            'orig_name': f"{base_name}{count}",
            'type': "float",
            'enum': "",
            'existing': False,
            'value': "0",
            'min': None,
            'max': None,
            'hasMin': False,
            'hasMax': False,
            'state': "keyable",
        }
        attr_list.append(default_attr)
        refresh()
        cmds.textScrollList("attrList", e=True, selectIndexedItem=len(attr_list))
        load_settings(len(attr_list)-1)
        
        
# ------------ Create Devider -------------------
    def add_smart_divider():
        base_name = "divider"
        count = 1
        existing_names = [a["name"] for a in attr_list]

        while f"{base_name}{count}" in existing_names:
            count += 1

        # Define Divider
        divider_attr = {
            'name': f"{base_name}{count}",
            'orig_name': f"{base_name}{count}",
            'type': "enum",
            'enum': "- - - - - -",
            'existing': False,
            'value': 0,
            'min': None,
            'max': None,
            'hasMin': False,
            'hasMax': False,
            'state': "displayable",
        }

        sel = cmds.textScrollList("attrList", q=True, selectIndexedItem=True)
        if sel:
            idx = sel[0] - 1
            attr_list.insert(idx + 1, divider_attr)
            refresh()
            cmds.textScrollList("attrList", e=True, selectIndexedItem=idx + 2)
        else:
            attr_list.append(divider_attr)
            refresh()
            cmds.textScrollList("attrList", e=True, selectIndexedItem=len(attr_list))

        load_settings(len(attr_list)-1)

# -------------- Load Existing Attributes ------------
    def load_existing():
        obj = get_object()
        if not obj:
            cmds.warning("Invalid object")
            return

        attr_list.clear()

        for a in cmds.listAttr(obj, userDefined=True) or []:
            maya_type = cmds.getAttr(f"{obj}.{a}", type=True)

            if maya_type in ["double", "float"]:
                t = "float"
            elif maya_type in ["long", "short", "byte"]:
                t = "int"
            elif maya_type == "bool":
                t = "bool"
            elif maya_type == "enum":
                t = "enum"
            elif maya_type == "double3":
                t = "vector"
            elif maya_type == "string":
                t = "string"
            else:
                t = "float"

            enum = ""
            if t == "enum":
                enum = cmds.attributeQuery(a, node=obj, listEnum=True)[0]

            minVal = None
            maxVal = None
            hasMin = False
            hasMax = False

            try:
                minVal = cmds.addAttr(f"{obj}.{a}", query=True, min=True)
                hasMin = minVal is not None
            except:
                pass

            try:
                maxVal = cmds.addAttr(f"{obj}.{a}", query=True, max=True)
                hasMax = maxVal is not None
            except:
                pass

            full = f"{obj}.{a}"

            if cmds.getAttr(full, lock=True):
                state = "locked"
            elif cmds.getAttr(full, keyable=True):
                state = "keyable"
            elif cmds.getAttr(full, channelBox=True):
                state = "displayable"
            else:
                state = "hidden"

            attr_list.append({
                'name': a,
                'orig_name': a,
                'type': t,
                'enum': enum,
                'existing': True,
                'value': cmds.getAttr(f"{obj}.{a}"),
                'state': state,
                'min': minVal,
                'max': maxVal,
                'hasMin': hasMin,
                'hasMax': hasMax,
            })

        refresh()


# ------------------- Delete Selected Attribute -------------------
    def delete_selected():
        sel = cmds.textScrollList("attrList", q=True, selectIndexedItem=True)
        if not sel:
            return

        i = sel[0] - 1
        attr = attr_list[i]

        obj = get_object()
        if obj and cmds.attributeQuery(attr['name'], node=obj, exists=True):
            full = f"{obj}.{attr['name']}"
            if cmds.getAttr(full, lock=True):
                cmds.warning("Cannot delete locked attribute")
                return

            for c in cmds.listConnections(full, p=True, s=True, d=True) or []:
                try:
                    cmds.disconnectAttr(c, full)
                    cmds.disconnectAttr(full, c)
                except:
                    pass

            cmds.deleteAttr(full)

        attr_list.pop(i)
        refresh()


# ---------------- Attribute State -----------------
    def set_attr_state(obj, name, state):
        full = f"{obj}.{name}"
    
        # Always unlock first (Maya ignores visibility changes on locked attrs)
        cmds.setAttr(full, lock=False)
    
        if state == "locked":
            cmds.setAttr(full, keyable=False)
            cmds.setAttr(full, channelBox=False)
            cmds.setAttr(full, lock=True)
    
        elif state == "keyable":
            cmds.setAttr(full, keyable=True)
            cmds.setAttr(full, channelBox=False)

        elif state == "displayable":
            cmds.setAttr(full, keyable=False)
            cmds.setAttr(full, channelBox=True)

        elif state == "hidden":
            cmds.setAttr(full, keyable=False)
            cmds.setAttr(full, channelBox=False)

# ------------- Reorder Attributes ---------------------
    def reorder_attributes(obj):
        for idx, attr in enumerate(attr_list):
            try:
                cmds.reorderAttr(obj, attribute=attr['name'], index=idx)
            except:
                pass

    # ===== ONLY APPLY FUNCTION (NO DUPLICATE) =====
    def apply():
        obj = get_object()
        if not obj:
            cmds.warning("Invalid object")
            return

        cmds.undoInfo(openChunk=True)

        # --- 1) Store attribute info
        attr_info = {}
        for a in attr_list:
            name = a['name']
            if cmds.attributeQuery(name, node=obj, exists=True):
                full = f"{obj}.{name}"
                attr_info[name] = {
                    "value": cmds.getAttr(full),
                    "connections": {
                        "in": cmds.listConnections(full, s=True, d=False, p=True) or [],
                        "out": cmds.listConnections(full, s=False, d=True, p=True) or []
                    },
                    "lock": cmds.getAttr(full, lock=True),
                    "state": "locked" if cmds.getAttr(full, lock=True) else (
                        "keyable" if cmds.getAttr(full, keyable=True) else (
                            "displayable" if cmds.getAttr(full, channelBox=True) else "hidden"
                        )
                    )
                }

        # --- 2) Delete existing user attributes
        for a in cmds.listAttr(obj, userDefined=True) or []:
            if cmds.attributeQuery(a, node=obj, exists=True):
                try:
                    cmds.deleteAttr(f"{obj}.{a}")
                except:
                    pass

        # --- 3) Recreate attributes in correct order
        for a in attr_list:
            name = a['name']

            if a['type'] == "float":
                kwargs = {}
                if a['hasMin']: kwargs['min'] = float(a['min'])
                if a['hasMax']: kwargs['max'] = float(a['max'])
                if a['value'] not in [None, ""]: kwargs['dv'] = float(a['value'])
                cmds.addAttr(obj, ln=name, at="float", **kwargs)

            elif a['type'] == "int":
                kwargs = {}
                if a['hasMin']: kwargs['min'] = int(a['min'])
                if a['hasMax']: kwargs['max'] = int(a['max'])
                if a['value'] not in [None, ""]: kwargs['dv'] = int(a['value'])
                cmds.addAttr(obj, ln=name, at="long", **kwargs)

            elif a['type'] == "bool":
                dv = 1 if a['value'] else 0
                cmds.addAttr(obj, ln=name, at="bool", dv=dv)

            elif a['type'] == "enum":
                enums = a['enum'].split(",") if a['enum'] else ["- - - - - -"]
                cmds.addAttr(obj, ln=name, at="enum", en=":".join(enums))

            elif a['type'] == "vector":
                cmds.addAttr(obj, ln=name, at="double3")
                for ax in "XYZ":
                    child = f"{name}{ax}"
                    cmds.addAttr(obj, ln=child, at="double", p=name)
                    set_attr_state(obj, child, a['state'])
                continue  # prevent applying state to parent

            elif a['type'] == "string":
                cmds.addAttr(obj, ln=name, dt="string")
                if a['value'] not in [None, ""]:
                    cmds.setAttr(f"{obj}.{name}", a['value'], type="string")

            set_attr_state(obj, name, a['state'])

        # --- 4) Restore connections (if any)
        for name, info in attr_info.items():
            for c in info["connections"]["in"]:
                try:
                    cmds.connectAttr(c, f"{obj}.{name}")
                except:
                    pass
            for c in info["connections"]["out"]:
                try:
                    cmds.connectAttr(f"{obj}.{name}", c)
                except:
                    pass

        cmds.undoInfo(closeChunk=True)
        cmds.warning("Success: Attributes rebuilt and applied")


# -------------- Select Attribute -----------------
    def select_item():
        sel = cmds.textScrollList("attrList", q=True, selectIndexedItem=True)
        if not sel:
            return
        load_settings(sel[0]-1)


# -------------- Load Attribute Settings ------------------
    def load_settings(index):
        a = attr_list[index]
        cmds.textField("nameField", e=True, text=a["name"])
        cmds.optionMenu("typeMenu", e=True, value=a["type"])

        if a["type"] == "bool":
            cmds.optionMenu("boolDefaultMenu", e=True, value=("On" if a["value"] else "Off"))
        else:
            cmds.textField("defaultField", e=True, text=str(a["value"]))

        cmds.textField("enumField", e=True, text=a["enum"])
        cmds.checkBox("minCheck", e=True, v=a["hasMin"])
        cmds.checkBox("maxCheck", e=True, v=a["hasMax"])
        cmds.textField("minField", e=True, text=str(a["min"]) if a["min"] else "")
        cmds.textField("maxField", e=True, text=str(a["max"]) if a["max"] else "")
        cmds.radioButtonGrp("stateGroup", e=True, select={"keyable":1,"displayable":2,"hidden":3}[a["state"]])


# ----------------- Update Selected Attribute ----------------
    def update_selected():
        sel = cmds.textScrollList("attrList", q=True, selectIndexedItem=True)
        if not sel:
            return
        idx = sel[0]-1
        a = attr_list[idx]

        a["name"] = cmds.textField("nameField", q=True, text=True)
        a["type"] = cmds.optionMenu("typeMenu", q=True, value=True)

        if a["type"] == "bool":
            a["value"] = (cmds.optionMenu("boolDefaultMenu", q=True, value=True) == "On")
        else:
            a["value"] = cmds.textField("defaultField", q=True, text=True)

        a["enum"] = cmds.textField("enumField", q=True, text=True)
        a["hasMin"] = cmds.checkBox("minCheck", q=True, v=True)
        a["hasMax"] = cmds.checkBox("maxCheck", q=True, v=True)
        a["min"] = cmds.textField("minField", q=True, text=True)
        a["max"] = cmds.textField("maxField", q=True, text=True)

        stateIndex = cmds.radioButtonGrp("stateGroup", q=True, select=True)
        a["state"] = {1:"keyable", 2:"displayable", 3:"hidden"}[stateIndex]

        refresh()

# ---------------------- UI of Tool ---------------------
    def update_ui():
        t = cmds.optionMenu("typeMenu", q=True, value=True)
        cmds.textField("enumField", e=True, enable=(t == "enum"))
        cmds.textField("defaultField", e=True, enable=(t != "bool"))
        cmds.optionMenu("boolDefaultMenu", e=True, visible=(t == "bool"))
        cmds.textField("defaultField", e=True, visible=(t != "bool"))
        cmds.checkBox("minCheck", e=True, visible=(t in ["float","int"]))
        cmds.checkBox("maxCheck", e=True, visible=(t in ["float","int"]))
        cmds.textField("minField", e=True, visible=(t in ["float","int"]))
        cmds.textField("maxField", e=True, visible=(t in ["float","int"]))
        cmds.text("sliderLabel", e=True, visible=(t in ["float","int"]))
        cmds.intField("divField", e=True, visible=(t in ["float","int"]))

    cmds.window(win, title="Attribute Manager (Beta)", resizeToFitChildren=True)
    tab = cmds.tabLayout(innerMarginWidth=6, innerMarginHeight=6)

    tab1 = cmds.columnLayout(adjustableColumn=True)

    cmds.textFieldButtonGrp(
        "objField",
        label="Object",
        buttonLabel="Pick",
        bc=lambda *_: (
            cmds.textFieldButtonGrp("objField", e=True, text=(cmds.ls(sl=True)[0] if cmds.ls(sl=True) else "")),
            load_existing()
        )
    )

    cmds.separator(h=8)

    cmds.textScrollList("attrList", h=220, allowMultiSelection=False, selectCommand=lambda *_: select_item())

    cmds.separator(h=6)

    cmds.rowLayout(nc=6, adjustableColumn=3, columnAlign=(1, "left"), columnAttach=[(1, "left", 0),(2, "left", 4),(3, "both", 10),(4, "right", 4),(5, "right", 0),(6, "right", 0)])
    cmds.button(label="New", width=80, bgc=(0.3, 0.7, 0.3), c=lambda *_: add_new_default())
    cmds.button(label="Delete", width=80, bgc=(0.8, 0.3, 0.3), c=lambda *_: delete_selected())
    cmds.button(label="Divider", width=80, bgc=(0.4, 0.4, 0.4), c=lambda *_: add_smart_divider())
    cmds.separator(style="none")
    cmds.button(label="Move Up", width=80, c=lambda *_: move("up"))
    cmds.button(label="Move Down", width=80, c=lambda *_: move("down"))
    cmds.setParent("..")

    cmds.separator(h=10)

    cmds.frameLayout(label="Attribute Settings", collapsable=False, marginWidth=6)
    cmds.columnLayout(adjustableColumn=True)

    cmds.textField("nameField", placeholderText="Attribute name")
    cmds.optionMenu("typeMenu", cc=lambda *_: update_ui())
    for t in ["float", "int", "bool", "enum", "vector", "string"]:
        cmds.menuItem(label=t)

    cmds.textField("enumField", placeholderText="Enum values (comma separated)")

    cmds.rowLayout(nc=4)
    cmds.checkBox("minCheck", label="Min", v=False)
    cmds.textField("minField", placeholderText="Min value")
    cmds.checkBox("maxCheck", label="Max", v=False)
    cmds.textField("maxField", placeholderText="Max value")
    cmds.setParent("..")

    cmds.rowLayout(nc=3, adjustableColumn=2)
    cmds.text("defaultLabel", label="Default Value:")
    cmds.textField("defaultField", placeholderText="Default value")
    cmds.optionMenu("boolDefaultMenu", visible=False)
    cmds.menuItem(label="Off")
    cmds.menuItem(label="On")
    cmds.setParent("..")

    cmds.rowLayout(nc=2, adjustableColumn=2)
    cmds.text("sliderLabel", label="Slider Steps:")
    cmds.intField("divField", value=10, min=1)
    cmds.setParent("..")

    cmds.radioButtonGrp("stateGroup", label="State:", labelArray3=["Keyable", "Displayable", "Hidden"], numberOfRadioButtons=3, select=1)

    cmds.separator(h=8)

    cmds.rowLayout(nc=2)
    cmds.button(label="Apply to Attribute", width=160, bgc=(0.6, 0.6, 0.9), c=lambda *_: update_selected())
    cmds.setParent("..")

    cmds.setParent("..")
    cmds.setParent("..")

    cmds.separator(h=12)

    cmds.button(label="Apply (Rebuild Attributes / Commit)", bgc=(0.4, 0.7, 0.4), c=lambda *_: apply())

    cmds.setParent("..")

    tab2 = cmds.columnLayout(adjustableColumn=True)
    cmds.text(label="Attribute Manager Tool", align="center")
    cmds.separator()
    cmds.text(label="Instructions:", align="left")
    cmds.text(label="1) Pick Object: Loads Attributes automatically", align="left")
    cmds.text(label="2) Select Attribute in the list that needs adjustment...", align="left")
    cmds.text(label="2) ... or create/ delete or Move attributes and Dividers", align="left")
    cmds.text(label="3) Attribute Settings: Edit and Apply to selected Attribute. ", align="left")
    cmds.text(label="4) Commit to all Attributes (Rebuilds Attributes)", align="left")
    cmds.separator()
    cmds.text(label="Produced & Tested in Maya 2024", align="center")
    cmds.text(label="Feedback/Bugs: timon.holzer@outlook.com", align="center")
    cmds.text(label="   ", align="center")
    cmds.text(label="Created by Timon Holzer", align="center")
    cmds.setParent("..")

    cmds.tabLayout(tab, edit=True, tabLabel=((tab1, "Attributes"), (tab2, "About")))
    cmds.showWindow(win)

#---------------------------------------------------------------
# ----------------- Close Attriubute Manager -------------------
attribute_manager()