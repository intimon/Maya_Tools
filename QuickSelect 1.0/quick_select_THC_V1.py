"""
Quick Select UI v2 for Maya  (Maya 2022+, PySide2 / PySide6)
-------------------------------------------------------------
A window that wraps Maya's built-in Quick Select Sets.

- Lists ALL quick select sets in the scene on launch (also ones made via
  Create > Sets > Quick Select Set) and keeps itself in sync.
- Type a name, pick a colour, press Enter / Create -> selection becomes a quick set.
- Click a button: select.  Shift+click: add.  Ctrl+click: toggle.
- Right-click a button: Change Color, Reset Color, Rename, Replace Members, Delete.
- "+ New Group" creates a group. Drag buttons (left mouse) into groups.
    * Drop on a group's empty area -> moves to the end of that group
    * Drop on another button       -> inserts before that button
    * Drop into "Ungrouped"        -> removes it from its group
- Group menu button (or right-click header): Rename / Delete group.

Everything is stored in the scene:
- Quick sets are real objectSets (text = "gSelectionSet").
- Colour / group / order live in a string attribute "qsMeta" on each set.
- The list of groups lives on a network node called "quickSelectUI_data".

Usage:
    import quick_select_ui_v2
    quick_select_ui_v2.show()
"""

import contextlib
import json
import maya.cmds as cmds
import maya.OpenMayaUI as omui

from PySide6 import QtCore, QtGui, QtWidgets, QtSvg
from shiboken6 import wrapInstance

try:
    # Newer Maya versions
    from PySide6 import QtCore, QtGui, QtWidgets, QtSvg
    from shiboken6 import wrapInstance
except ImportError:
    # Older Maya versions
    from PySide2 import QtCore, QtGui, QtWidgets, QtSvg
    from shiboken2 import wrapInstance

WINDOW_ID = "quickSelectUIv2Window"
QUICK_SET_TAG = "gSelectionSet"
META_ATTR = "qsMeta"
DATA_NODE = "quickSelectUI_data"
DATA_ATTR = "config"
MIME = "application/x-quickselect-set"
DEFAULT_COLOR = "#5d5d5d"
UNGROUPED = "Ungrouped"
BIG_ORDER = 10 ** 6

SECTION_STYLE = "QFrame#section { border: 1px solid #555555; border-radius: 4px; }"
SECTION_HOVER_STYLE = ("QFrame#section { border: 1px solid #5285a6; border-radius: 4px; "
                       "background: rgba(82, 133, 166, 45); }")

_window = None
_chunk_depth = 0


# ====================================================================== helpers
@contextlib.contextmanager
def undo_chunk():
    """Bundle several scene edits into a single undo step."""
    global _chunk_depth
    if _chunk_depth == 0:
        cmds.undoInfo(openChunk=True)
    _chunk_depth += 1
    try:
        yield
    finally:
        _chunk_depth -= 1
        if _chunk_depth == 0:
            cmds.undoInfo(closeChunk=True)


def _qexec(obj, *args):
    """exec() on PySide6, exec_() on PySide2."""
    fn = getattr(obj, "exec", None) or getattr(obj, "exec_")
    return fn(*args)


def _maya_main_window():
    ptr = omui.MQtUtil.mainWindow()
    return wrapInstance(int(ptr), QtWidgets.QWidget) if ptr else None


def _safe_name(text):
    safe = "".join(c if (c.isalnum() or c == "_") else "_" for c in text.strip())
    if safe and safe[0].isdigit():
        safe = "_" + safe
    return safe


def _confirm(parent, title, text):
    answer = QtWidgets.QMessageBox.warning(
        parent, title, text,
        QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
        QtWidgets.QMessageBox.No)
    return answer == QtWidgets.QMessageBox.Yes


def button_style(hex_color):
    c = QtGui.QColor(hex_color)
    if not c.isValid():
        c = QtGui.QColor(DEFAULT_COLOR)
    lum = 0.299 * c.red() + 0.587 * c.green() + 0.114 * c.blue()
    fg = "#111111" if lum > 150 else "#f2f2f2"
    return (
        "QPushButton {{ background-color: {bg}; color: {fg}; "
        "border: 1px solid rgba(0,0,0,110); border-radius: 4px; padding: 3px 12px; }}"
        "QPushButton:hover {{ border: 1px solid #ffffff; }}"
        "QPushButton:pressed {{ background-color: {dark}; }}"
    ).format(bg=c.name(), fg=fg, dark=c.darker(130).name())


# ============================================================== Icon_SVG
LOGO_SVG = """
<svg xmlns="http://www.w3.org/2000/svg"
     viewBox="0 0 30.93 35.3">
    <g fill="#2e6cb5">
        <path d="M30.26 8.33 16.14.18c-.42-.24-.93-.24-1.34 0L.67 8.33C.25 8.57 0 9.01 0 9.49V25.8c0 .48.26.92.67 1.16l14.12 8.15s.03.01.05.02c.07.04.15.07.23.09.03 0 .05.02.08.02.1.02.21.04.32.04s.21-.02.32-.04c.03 0 .05-.02.08-.02.08-.02.16-.06.23-.09.02 0 .03-.01.05-.02l14.12-8.15c.42-.24.67-.68.67-1.16V9.5c0-.48-.26-.92-.67-1.16Zm-14.8-5.44L26.91 9.5l-11.45 6.59L4.01 9.5zM2.69 11.84l11.43 6.58v13.2l-11.43-6.6zm14.12 19.79v-13.2l11.43-6.58v13.18z"/>
        <path d="M3.74 14.8c0-.28.2-.39.45-.25l7.91 4.57c.24.14.44.48.44.76v2.37c0 .28-.2.39-.44.25l-2.21-1.28c-.24-.14-.43-.03-.43.25l.14 5.84c0 .28-.19.39-.43.25l-2.05-1.18c-.24-.14-.44-.48-.44-.76v-5.75c0-.28-.2-.62-.44-.76l-2.1-1.21c-.24-.14-.44-.48-.43-.76z"/>
        <path d="M18.83 19.11c-.24.14-.44.48-.44.76V29c0 .28.2.39.44.25l2.05-1.18c.24-.14.44-.48.44-.76v-2.37c0-.28.2-.62.44-.76L23.81 23c.24-.14.44-.03.44.25v2.37c0 .28.2.39.44.25l2.05-1.18c.24-.14.44-.48.44-.76V14.8c0-.28-.2-.39-.44-.25l-2.05 1.18c-.24.14-.44.48-.44.76v2.37c0 .28-.2.62-.44.76l-2.05 1.18c-.24.14-.44.03-.43-.25l.03-2.39c0-.28-.19-.39-.43-.25z"/>
        <path d="M15.8 14.02c-.24.14-.64.14-.88 0L8.56 10.3c-.24-.14-.44-.48-.44-.76v-.67c0-.28.2-.62.44-.76l6.46-3.73c.24-.14.64-.14.88 0l5 2.88c.24.14.44.44.43.67s-.24.42-.52.42h-3.38c-.28 0-.71-.11-.95-.25l-.59-.34a.97.97 0 0 0-.88 0l-2.05 1.18c-.24.14-.24.37 0 .51l2.05 1.18c.24.14.64.14.88 0l.59-.34c.24-.14.67-.25.95-.25h3.38c.28 0 .51.18.51.41s-.2.53-.44.67z"/>
    </g>
</svg>
"""




# ============================================================== scene data layer
def quick_sets():
    """Return every Maya Quick Select Set, including sets made outside this UI.

    Maya stores Quick Select Sets as objectSets tagged with the text
    ``gSelectionSet``. Query the tag first, then try the underlying text
    attribute as a compatibility fallback across Maya versions.
    """
    found = []
    for set_name in cmds.ls(type="objectSet", long=False) or []:
        is_quick_set = False
        try:
            is_quick_set = cmds.sets(set_name, query=True, text=True) == QUICK_SET_TAG
        except Exception:
            pass

        if not is_quick_set:
            try:
                if cmds.attributeQuery("text", node=set_name, exists=True):
                    is_quick_set = cmds.getAttr(
                        "{}.text".format(set_name)) == QUICK_SET_TAG
            except Exception:
                pass

        if is_quick_set:
            found.append(set_name)
    return found


def read_meta(set_name):
    if cmds.attributeQuery(META_ATTR, node=set_name, exists=True):
        try:
            data = json.loads(cmds.getAttr("{}.{}".format(set_name, META_ATTR)) or "{}")
            if isinstance(data, dict):
                return data
        except Exception:
            pass
    return {}


def write_meta(set_name, meta):
    try:
        if not cmds.attributeQuery(META_ATTR, node=set_name, exists=True):
            cmds.addAttr(set_name, longName=META_ATTR, dataType="string")
        cmds.setAttr("{}.{}".format(set_name, META_ATTR), json.dumps(meta), type="string")
        return True
    except Exception as exc:
        cmds.warning("Quick Select: could not store data on '{}' ({})".format(set_name, exc))
        return False


def load_groups():
    if not cmds.objExists(DATA_NODE):
        return []
    try:
        data = json.loads(cmds.getAttr("{}.{}".format(DATA_NODE, DATA_ATTR)) or "[]")
        return [g for g in data if isinstance(g, dict) and g.get("name")]
    except Exception:
        return []


def save_groups(groups):
    with undo_chunk():
        if not cmds.objExists(DATA_NODE):
            cmds.createNode("network", name=DATA_NODE, skipSelect=True)
            cmds.addAttr(DATA_NODE, longName=DATA_ATTR, dataType="string")
        cmds.setAttr("{}.{}".format(DATA_NODE, DATA_ATTR), json.dumps(groups), type="string")


def collect_sets():
    """Sorted list of dicts: name, color, group, order."""
    group_names = {g["name"] for g in load_groups()}
    entries = []
    for s in quick_sets():
        meta = read_meta(s)
        group = meta.get("group", "")
        if group not in group_names:
            group = ""
        entries.append({
            "name": s,
            "color": meta.get("color", DEFAULT_COLOR),
            "group": group,
            "order": meta.get("order", BIG_ORDER),
        })
    entries.sort(key=lambda e: (e["order"], e["name"].lower()))
    return entries


# ================================================================== flow layout
class FlowLayout(QtWidgets.QLayout):
    """Lays widgets out left to right and wraps onto new lines."""

    def __init__(self, parent=None, spacing=4):
        super(FlowLayout, self).__init__(parent)
        self._items = []
        self._spacing = spacing
        self.setContentsMargins(0, 0, 0, 0)

    def addItem(self, item):
        self._items.append(item)

    def count(self):
        return len(self._items)

    def itemAt(self, index):
        return self._items[index] if 0 <= index < len(self._items) else None

    def takeAt(self, index):
        return self._items.pop(index) if 0 <= index < len(self._items) else None

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._do_layout(QtCore.QRect(0, 0, width, 0), True)

    def setGeometry(self, rect):
        super(FlowLayout, self).setGeometry(rect)
        self._do_layout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QtCore.QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        m = self.contentsMargins()
        return size + QtCore.QSize(m.left() + m.right(), m.top() + m.bottom())

    def _do_layout(self, rect, test_only):
        m = self.contentsMargins()
        eff = rect.adjusted(m.left(), m.top(), -m.right(), -m.bottom())
        x, y = eff.x(), eff.y()
        line_h = 0
        sp = self._spacing
        for item in self._items:
            hint = item.sizeHint()
            w, h = hint.width(), hint.height()
            if x + w > eff.right() + 1 and line_h > 0:
                x = eff.x()
                y = y + line_h + sp
                line_h = 0
            if not test_only:
                item.setGeometry(QtCore.QRect(QtCore.QPoint(x, y), hint))
            x = x + w + sp
            line_h = max(line_h, h)
        return y + line_h - rect.y() + m.bottom()


# ================================================================ set button
class SetButton(QtWidgets.QPushButton):
    def __init__(self, ui, entry):
        super(SetButton, self).__init__(entry["name"])
        self.ui = ui
        self.set_name = entry["name"]
        self.group = entry["group"]
        self.color = entry["color"]
        self._press_pos = None

        self.setMinimumHeight(26)
        self.setStyleSheet(button_style(self.color))
        self.setAcceptDrops(True)
        self.setToolTip("Click: select  |  Shift: add  |  Ctrl: toggle\n"
                        "Drag: move to a group  |  Right-click: options")
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_menu)
        self.clicked.connect(self._on_click)

    # --- click / select
    def _on_click(self, *_):
        self.ui.select_set(self.set_name)

    # --- context menu
    def _show_menu(self, pos):
        menu = QtWidgets.QMenu(self)
        a_color = menu.addAction("Change Color...")
        a_reset = menu.addAction("Reset Color")
        menu.addSeparator()
        a_rename = menu.addAction("Rename...")
        menu.addSeparator()
        a_update = menu.addAction("Replace Members with Current Selection")
        a_add = menu.addAction("Add Current Selection to Set")
        a_remove = menu.addAction("Remove Current Selection from Set")
        menu.addSeparator()
        a_delete = menu.addAction("Delete...")

        chosen = _qexec(menu, self.mapToGlobal(pos))
        if chosen == a_color:
            self.ui.change_color(self.set_name, self.color)
        elif chosen == a_reset:
            self.ui.set_color(self.set_name, DEFAULT_COLOR)
        elif chosen == a_rename:
            self.ui.rename_set(self.set_name)
        elif chosen == a_update:
            self.ui.replace_members(self.set_name)
        elif chosen == a_add:
            self.ui.edit_members(self.set_name, add=True)
        elif chosen == a_remove:
            self.ui.edit_members(self.set_name, add=False)
        elif chosen == a_delete:
            self.ui.delete_set(self.set_name)

    # --- drag source
    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self._press_pos = event.pos()
        super(SetButton, self).mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._press_pos is None or not (event.buttons() & QtCore.Qt.LeftButton):
            return super(SetButton, self).mouseMoveEvent(event)
        if (event.pos() - self._press_pos).manhattanLength() < QtWidgets.QApplication.startDragDistance():
            return super(SetButton, self).mouseMoveEvent(event)

        self._press_pos = None
        drag = QtGui.QDrag(self)
        mime = QtCore.QMimeData()
        mime.setData(MIME, QtCore.QByteArray(self.set_name.encode("utf-8")))
        drag.setMimeData(mime)
        drag.setPixmap(self.grab())
        drag.setHotSpot(event.pos())

        self.ui.dragging = True
        result = _qexec(drag, QtCore.Qt.MoveAction)
        self.setDown(False)
        self.ui.end_drag(result == QtCore.Qt.MoveAction)

    # --- drop target (insert before this button)
    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat(MIME):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        name = bytes(event.mimeData().data(MIME)).decode("utf-8")
        self.ui.move_set(name, self.group, before=self.set_name)
        event.setDropAction(QtCore.Qt.MoveAction)
        event.accept()


# ================================================================ group section
class GroupSection(QtWidgets.QFrame):
    def __init__(self, ui, key, members):
        super(GroupSection, self).__init__()
        self.ui = ui
        self.key = key                      # "" means Ungrouped
        self.title = key or UNGROUPED
        self.count = len(members)

        self.setObjectName("section")
        self.setStyleSheet(SECTION_STYLE)
        self.setAcceptDrops(True)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 6)
        layout.setSpacing(4)

        header_row = QtWidgets.QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(2)

        self.header = QtWidgets.QPushButton()
        self.header.setFlat(True)
        self.header.setStyleSheet(
            "text-align: left; font-weight: bold; padding: 2px 4px; border: none;")
        self.header.clicked.connect(self.toggle)
        if key:
            self.header.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
            self.header.customContextMenuRequested.connect(self._header_menu)
            self.header.setToolTip("Click to collapse; right-click for group options")

            self.menu_btn = QtWidgets.QToolButton()
            self.menu_btn.setText("\u22ee")
            self.menu_btn.setToolTip("Rename or delete this group")
            self.menu_btn.setStyleSheet("QToolButton { border: none; padding: 2px 6px; }")
            self.menu_btn.clicked.connect(self._show_group_menu)
            header_row.addWidget(self.header, 1)
            header_row.addWidget(self.menu_btn)
        else:
            header_row.addWidget(self.header, 1)
        layout.addLayout(header_row)

        self.body = QtWidgets.QWidget()
        flow = FlowLayout(self.body, spacing=4)
        for entry in members:
            flow.addWidget(SetButton(ui, entry))
        if not members:
            hint = ("Drag buttons here" if key
                    else "Select objects, type a name above and press Create")
            label = QtWidgets.QLabel(hint)
            label.setStyleSheet("color: #888888; font-style: italic; padding: 2px 4px;")
            flow.addWidget(label)
        layout.addWidget(self.body)

        self.body.setVisible(key not in ui.collapsed)
        self._update_header()

    def _update_header(self):
        arrow = u"\u25B6" if self.key in self.ui.collapsed else u"\u25BC"
        self.header.setText(u"{} {}  ({})".format(arrow, self.title, self.count))

    def toggle(self, *_):
        if self.key in self.ui.collapsed:
            self.ui.collapsed.discard(self.key)
        else:
            self.ui.collapsed.add(self.key)
        self.body.setVisible(self.key not in self.ui.collapsed)
        self._update_header()

    def _header_menu(self, pos):
        self._show_group_menu(self.header.mapToGlobal(pos))

    def _show_group_menu(self, global_pos=None):
        if not self.key:
            return
        menu = QtWidgets.QMenu(self)
        a_rename = menu.addAction("Rename Group...")
        a_delete = menu.addAction("Delete Group...")
        if global_pos is None or isinstance(global_pos, bool):
            global_pos = self.menu_btn.mapToGlobal(
                self.menu_btn.rect().bottomLeft())
        chosen = _qexec(menu, global_pos)
        if chosen == a_rename:
            self.ui.rename_group(self.key)
        elif chosen == a_delete:
            self.ui.delete_group(self.key)

    # --- drop target (append to this group)
    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat(MIME):
            self.setStyleSheet(SECTION_HOVER_STYLE)
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self.setStyleSheet(SECTION_STYLE)

    def dropEvent(self, event):
        self.setStyleSheet(SECTION_STYLE)
        name = bytes(event.mimeData().data(MIME)).decode("utf-8")
        self.ui.move_set(name, self.key)
        event.setDropAction(QtCore.Qt.MoveAction)
        event.accept()


# ================================================================== main window
class QuickSelectWindow(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(QuickSelectWindow, self).__init__(parent)
        self.setObjectName(WINDOW_ID)
        self.setWindowTitle("Quick Select")
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.Window)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.resize(360, 480)

        self.collapsed = set()
        self.dragging = False
        self._pending = False
        self.new_color = DEFAULT_COLOR
        self._script_jobs = []

        self._build_ui()

        self._refresh_timer = QtCore.QTimer(self)
        self._refresh_timer.setSingleShot(True)
        self._refresh_timer.setInterval(50)
        self._refresh_timer.timeout.connect(self._timer_fired)

        for event in ("SceneOpened", "NewSceneOpened", "SetModified", "Undo", "Redo"):
            self._script_jobs.append(cmds.scriptJob(event=[event, self.request_refresh]))

        self.refresh()

    # ------------------------------------------------------------------- UI
    def _build_ui(self):
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        row = QtWidgets.QHBoxLayout()
        self.name_edit = QtWidgets.QLineEdit()
        self.name_edit.setPlaceholderText("Name for the selection, e.g. Left_Arm_Controls")
        self.name_edit.setMinimumHeight(26)
        self.name_edit.returnPressed.connect(self.create_set)
        row.addWidget(self.name_edit, 1)

        self.color_btn = QtWidgets.QPushButton()
        self.color_btn.setFixedSize(30, 26)
        self.color_btn.setToolTip("Color for the new quick selection")
        self.color_btn.clicked.connect(self.pick_new_color)
        row.addWidget(self.color_btn)

        create_btn = QtWidgets.QPushButton("Create")
        create_btn.setMinimumHeight(26)
        create_btn.clicked.connect(self.create_set)
        row.addWidget(create_btn)
        root.addLayout(row)
        self._update_swatch()

        row2 = QtWidgets.QHBoxLayout()
        group_btn = QtWidgets.QPushButton("+ New Group")
        group_btn.clicked.connect(self.create_group)
        refresh_btn = QtWidgets.QPushButton("Refresh")
        refresh_btn.setToolTip("Rescan the scene for Quick Select Sets, including ones created in Maya's native UI")
        refresh_btn.clicked.connect(self.refresh)
        row2.addWidget(group_btn)
        row2.addStretch(1)
        row2.addWidget(refresh_btn)
        root.addLayout(row2)


        self.scroll = QtWidgets.QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.content = QtWidgets.QWidget()
        self.content_layout = QtWidgets.QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(6)
        self.scroll.setWidget(self.content)
        root.addWidget(self.scroll, 1)
        

        # --- Footer: instructions left, logo right ---
        footer = QtWidgets.QHBoxLayout()
        footer.setSpacing(10)

        tip = QtWidgets.QLabel(
            "Drag buttons into groups  |  "
            "Drop on a button to insert before it  |  "
            "Right-click for options"
        )
        tip.setWordWrap(True)
        tip.setStyleSheet(
            "color: #888888; font-size: 10px;"
        )
        footer.addWidget(tip, 1)

        # Render the embedded SVG
        logo_label = QtWidgets.QLabel()
        logo_label.setFixedSize(35, 40)
        logo_label.setAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
        )

        renderer = QtSvg.QSvgRenderer(
            QtCore.QByteArray(LOGO_SVG.encode("utf-8"))
        )

        if renderer.isValid():
            pixmap = QtGui.QPixmap(35, 40)
            pixmap.fill(QtCore.Qt.transparent)

            painter = QtGui.QPainter(pixmap)
            renderer.render(painter)
            painter.end()

            logo_label.setPixmap(pixmap)
            footer.addWidget(logo_label)

        root.addLayout(footer)



    def _update_swatch(self):
        self.color_btn.setStyleSheet(
            "QPushButton {{ background-color: {}; border: 1px solid #222222; border-radius: 4px; }}"
            "QPushButton:hover {{ border: 1px solid #ffffff; }}".format(self.new_color))

    def pick_new_color(self, *_):
        color = QtWidgets.QColorDialog.getColor(QtGui.QColor(self.new_color), self, "Color for new selection")
        if color.isValid():
            self.new_color = color.name()
            self._update_swatch()

    # ------------------------------------------------------------- refreshing
    def request_refresh(self, *_):
        try:
            self._refresh_timer.start()
        except RuntimeError:
            pass

    def _timer_fired(self):
        if self.dragging:
            self._pending = True
            return
        self.refresh()

    def end_drag(self, moved):
        self.dragging = False
        if moved or self._pending:
            self._pending = False
            self.request_refresh()

    def refresh(self, *_):
        self._pending = False
        scroll_pos = self.scroll.verticalScrollBar().value()

        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()

        entries = collect_sets()
        keys = [""] + [g["name"] for g in load_groups()]
        for key in keys:
            members = [e for e in entries if e["group"] == key]
            self.content_layout.addWidget(GroupSection(self, key, members))
        self.content_layout.addStretch(1)

        QtCore.QTimer.singleShot(0, lambda: self.scroll.verticalScrollBar().setValue(scroll_pos))

    # --------------------------------------------------------------- set actions
    def create_set(self, *_):
        text = self.name_edit.text().strip()
        sel = cmds.ls(selection=True)
        if not text:
            cmds.warning("Quick Select: please enter a name first.")
            return
        if not sel:
            cmds.warning("Quick Select: nothing is selected.")
            return

        name = _safe_name(text)
        if cmds.objExists(name):
            answer = QtWidgets.QMessageBox.question(
                self, "Name already exists",
                "'{}' already exists in the scene.\nCreate it with a unique name instead?".format(name),
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.Cancel,
                QtWidgets.QMessageBox.Yes)
            if answer != QtWidgets.QMessageBox.Yes:
                return

        with undo_chunk():
            actual = cmds.sets(sel, name=name, text=QUICK_SET_TAG)
            write_meta(actual, {"color": self.new_color, "group": ""})
        self.name_edit.clear()
        self.request_refresh()

    @staticmethod
    def select_set(set_name):
        if not cmds.objExists(set_name):
            return
        members = cmds.sets(set_name, q=True) or []
        if not members:
            cmds.warning("Quick Select: '{}' is empty.".format(set_name))
            return
        mods = QtWidgets.QApplication.keyboardModifiers()
        if bool(mods & QtCore.Qt.ShiftModifier):
            cmds.select(members, add=True)
        elif bool(mods & QtCore.Qt.ControlModifier):
            cmds.select(members, toggle=True)
        else:
            cmds.select(members, replace=True)

    def change_color(self, set_name, current):
        color = QtWidgets.QColorDialog.getColor(QtGui.QColor(current), self, "Color for '{}'".format(set_name))
        if color.isValid():
            self.set_color(set_name, color.name())

    def set_color(self, set_name, hex_color):
        with undo_chunk():
            meta = read_meta(set_name)
            meta["color"] = hex_color
            write_meta(set_name, meta)
        self.request_refresh()

    def rename_set(self, set_name):
        text, ok = QtWidgets.QInputDialog.getText(self, "Rename Quick Selection", "New name:", text=set_name)
        new = _safe_name(text) if ok else ""
        if not new or new == set_name:
            return
        try:
            cmds.rename(set_name, new)
        except Exception as exc:
            cmds.warning("Quick Select: could not rename ({})".format(exc))
        self.request_refresh()

    def replace_members(self, set_name):
        sel = cmds.ls(selection=True)
        if not sel:
            cmds.warning("Quick Select: nothing is selected.")
            return
        if not _confirm(self, "Replace Members",
                        "Replace the members of '{}' with the current selection?".format(set_name)):
            return
        with undo_chunk():
            cmds.sets(clear=set_name)
            cmds.sets(sel, add=set_name)
        self.request_refresh()

    def edit_members(self, set_name, add=True):
        """Add/remove the current Maya selection from an existing quick set."""
        selection = cmds.ls(selection=True, long=True) or []
        if not selection:
            cmds.warning("Quick Select: select one or more objects first.")
            return
        if not cmds.objExists(set_name):
            cmds.warning("Quick Select: set '{}' no longer exists.".format(set_name))
            self.request_refresh()
            return
        try:
            with undo_chunk():
                if add:
                    cmds.sets(selection, add=set_name)
                else:
                    # Only remove members that are actually in the set.
                    members = cmds.sets(set_name, query=True) or []
                    member_names = set(cmds.ls(members, long=True) or members)
                    to_remove = [item for item in selection if item in member_names]
                    if not to_remove:
                        cmds.warning("Quick Select: none of the selected objects are members of '{}'.".format(set_name))
                        return
                    cmds.sets(to_remove, remove=set_name)
        except Exception as exc:
            cmds.warning("Quick Select: could not {} members for '{}': {}".format(
                "add" if add else "remove", set_name, exc))
        self.request_refresh()

    def delete_set(self, set_name):
        if not _confirm(self, "Delete Quick Selection",
                        "Are you sure you want to delete '{}'?\n"
                        "(The objects themselves will not be deleted.)".format(set_name)):
            return
        try:
            cmds.delete(set_name)
        except Exception as exc:
            cmds.warning("Quick Select: could not delete '{}' ({})".format(set_name, exc))
        self.request_refresh()

    # -------------------------------------------------------- moving (drag/drop)
    def move_set(self, set_name, group, before=None):
        if set_name == before:
            return
        entries = collect_sets()
        if not any(e["name"] == set_name for e in entries):
            return

        siblings = [e["name"] for e in entries if e["group"] == group and e["name"] != set_name]
        index = siblings.index(before) if before in siblings else len(siblings)
        siblings.insert(index, set_name)

        with undo_chunk():
            for i, name in enumerate(siblings):
                meta = read_meta(name)
                meta["order"] = i
                if name == set_name:
                    meta["group"] = group
                write_meta(name, meta)

    # ------------------------------------------------------------ group actions
    def create_group(self, *_):
        text, ok = QtWidgets.QInputDialog.getText(self, "New Group", "Group name:")
        name = text.strip()
        if not ok or not name:
            return
        groups = load_groups()
        taken = [g["name"].lower() for g in groups] + [UNGROUPED.lower()]
        if name.lower() in taken:
            QtWidgets.QMessageBox.information(self, "Quick Select", "A group called '{}' already exists.".format(name))
            return
        groups.append({"name": name})
        save_groups(groups)
        self.request_refresh()

    def rename_group(self, old):
        text, ok = QtWidgets.QInputDialog.getText(self, "Rename Group", "New name:", text=old)
        new = text.strip()
        if not ok or not new or new == old:
            return
        groups = load_groups()
        taken = [g["name"].lower() for g in groups if g["name"] != old] + [UNGROUPED.lower()]
        if new.lower() in taken:
            QtWidgets.QMessageBox.information(self, "Quick Select", "A group called '{}' already exists.".format(new))
            return
        with undo_chunk():
            for g in groups:
                if g["name"] == old:
                    g["name"] = new
            save_groups(groups)
            for s in quick_sets():
                meta = read_meta(s)
                if meta.get("group") == old:
                    meta["group"] = new
                    write_meta(s, meta)
        if old in self.collapsed:
            self.collapsed.discard(old)
            self.collapsed.add(new)
        self.request_refresh()

    def delete_group(self, key):
        if not key:
            return
        if not _confirm(self, "Delete Group",
                        "Delete the group '{}'?\n\n"
                        "Its quick selection sets will be kept and moved to '{}'.".format(key, UNGROUPED)):
            return
        try:
            with undo_chunk():
                # Persist the group list without this group and verify the result.
                remaining = [g for g in load_groups() if g.get("name") != key]
                save_groups(remaining)
                # Remove group assignments from every quick set, including sets
                # that are not currently visible in the UI.
                for set_name in quick_sets():
                    meta = read_meta(set_name)
                    if meta.get("group") == key:
                        meta["group"] = ""
                        write_meta(set_name, meta)
            self.collapsed.discard(key)
            if any(g.get("name") == key for g in load_groups()):
                cmds.warning("Quick Select: group '{}' could not be removed from scene data.".format(key))
            self.refresh()
        except Exception as exc:
            cmds.warning("Quick Select: could not delete group '{}': {}".format(key, exc))
            self.request_refresh()

    # ------------------------------------------------------------------- close
    def closeEvent(self, event):
        for job in self._script_jobs:
            if cmds.scriptJob(exists=job):
                cmds.scriptJob(kill=job, force=True)
        self._script_jobs = []
        super(QuickSelectWindow, self).closeEvent(event)


# ==================================================================== entry point
def show():
    global _window
    for widget in QtWidgets.QApplication.topLevelWidgets():
        if widget.objectName() == WINDOW_ID:
            try:
                widget.close()
            except RuntimeError:
                pass
    _window = QuickSelectWindow(_maya_main_window())
    _window.show()
    _window.raise_()
    return _window


if __name__ == "__main__":
    show()