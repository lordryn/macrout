import sys
import json
import pyautogui
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QPushButton,
    QLabel, QSpinBox, QHeaderView, QAbstractItemView,
    QCheckBox, QGroupBox, QAction, QFileDialog, QMessageBox,
    QMenuBar, QSlider, QDialog, QLineEdit, QDialogButtonBox,
    QMenu
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QColor, QFont

from pynput import keyboard

from src.engine import MacroEngine
from src.events import (
    MacroEvent, ClickEvent, KeyEvent, WaitEvent,
    MousePressEvent, MouseReleaseEvent, FlagEvent
)


# --- Dialog for editing hotkeys ---
class HotkeyDialog(QDialog):
    def __init__(self, record_hotkey, play_hotkey, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Set Hotkeys')
        self.resize(300, 150)
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel('Start/Stop Recording:'))
        self.record_edit = QLineEdit(record_hotkey)
        self.record_edit.setPlaceholderText("<ctrl>+<alt>+r")
        layout.addWidget(self.record_edit)

        layout.addWidget(QLabel('Start/Stop Playback:'))
        self.play_edit = QLineEdit(play_hotkey)
        self.play_edit.setPlaceholderText("<ctrl>+<alt>+p")
        layout.addWidget(self.play_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_values(self):
        return self.record_edit.text(), self.play_edit.text()


class EventTable(QTableWidget):
    # Signal: source_rows (list), target_row (int), insert_mode (str: 'above'/'below')
    rows_moved = pyqtSignal(list, int, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(7)
        self.setHorizontalHeaderLabels(["Type", "Action", "X", "Y", "Button/Key", "Delay", "Variance"])
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)

        # Enable Drag & Drop
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setViewportMargins(0, 0, 0, 0)
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setDropIndicatorShown(True)

    def dropEvent(self, event):
        """
        Hijack the drop event. Instead of letting Qt try to move pixels,
        we pause and ask the user WHERE they want to insert the rows.
        """
        if event.source() == self:
            # 1. Get Drop Target Row
            target_row = self.indexAt(event.pos()).row()

            # If dropped on empty space (below last row), default to end
            if target_row == -1:
                target_row = self.rowCount() - 1

            # 2. Get Source Rows
            source_rows = sorted(set(item.row() for item in self.selectedItems()))
            if not source_rows: return

            # 3. Create Context Menu at Mouse Position
            menu = QMenu(self)
            # Display intuitive labels
            action_above = menu.addAction(f"Insert Above Row {target_row + 1}")
            action_below = menu.addAction(f"Insert Below Row {target_row + 1}")
            menu.addSeparator()
            action_cancel = menu.addAction("Cancel")

            # Show menu
            selected_action = menu.exec_(self.cursor().pos())

            # 4. Emit Signal based on user choice
            if selected_action == action_above:
                self.rows_moved.emit(source_rows, target_row, 'above')
            elif selected_action == action_below:
                self.rows_moved.emit(source_rows, target_row, 'below')

            # Always accept to stop Qt's default (glitchy) move behavior
            event.accept()
        else:
            event.ignore()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Macrout 2.1 - Automation IDE")
        self.resize(1000, 650)

        self.engine = MacroEngine()

        # View Settings
        self.show_releases = True
        self.sync_coords = True
        self.smart_delete = True

        # Hotkeys
        self.hotkey_record = '<ctrl>+<alt>+r'
        self.hotkey_play = '<ctrl>+<alt>+p'
        self.hotkey_listener = None

        # UI Components
        self._setup_menu()
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)

        self._setup_top_stats()
        self._setup_table()
        self._setup_controls()

        self._last_highlighted_idx = -1

        self.timer = QTimer()
        self.timer.timeout.connect(self._on_tick)
        self.timer.start(50)

        self._start_hotkey_listener()

    def _setup_menu(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu('File')

        save_action = QAction('Save', self)
        save_action.setShortcut('Ctrl+S')
        save_action.triggered.connect(self.save_events)
        file_menu.addAction(save_action)

        load_action = QAction('Load', self)
        load_action.setShortcut('Ctrl+O')
        load_action.triggered.connect(self.load_events)
        file_menu.addAction(load_action)

        exit_action = QAction('Exit', self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        settings_menu = menubar.addMenu('Settings')

        hk_action = QAction('Set Hotkeys', self)
        hk_action.triggered.connect(self.edit_hotkeys)
        settings_menu.addAction(hk_action)

        self.act_always_top = QAction('Always on Top', self, checkable=True)
        self.act_always_top.setChecked(False)
        self.act_always_top.triggered.connect(self.toggle_always_on_top)
        settings_menu.addAction(self.act_always_top)

        self.act_sync = QAction('Sync Coordinates', self, checkable=True)
        self.act_sync.setChecked(True)
        self.act_sync.triggered.connect(self.toggle_sync)
        settings_menu.addAction(self.act_sync)

        self.act_smart_del = QAction('Smart Delete (Paired)', self, checkable=True)
        self.act_smart_del.setChecked(True)
        self.act_smart_del.triggered.connect(self.toggle_smart_delete)
        settings_menu.addAction(self.act_smart_del)

        self.act_hide_rel = QAction('Hide Release Events', self, checkable=True)
        self.act_hide_rel.setChecked(False)
        self.act_hide_rel.triggered.connect(self.toggle_releases)
        settings_menu.addAction(self.act_hide_rel)

        trans_action = QAction('Adjust Transparency', self)
        trans_action.triggered.connect(self.show_transparency_dialog)
        settings_menu.addAction(trans_action)

    def _setup_top_stats(self):
        stats_group = QGroupBox("Live Stats")
        stats_layout = QHBoxLayout()

        self.lbl_mouse_pos = QLabel("Mouse: (0, 0)")
        self.lbl_mouse_pos.setStyleSheet("font-weight: bold; color: #007ACC;")

        self.lbl_loop_time = QLabel("Loop Time: 0.00s")
        self.lbl_total_est = QLabel("Total Est: 0.00s")

        stats_layout.addWidget(self.lbl_mouse_pos)
        stats_layout.addStretch()
        stats_layout.addWidget(self.lbl_loop_time)
        stats_layout.addSpacing(20)
        stats_layout.addWidget(self.lbl_total_est)

        stats_group.setLayout(stats_layout)
        self.main_layout.addWidget(stats_group)

    def _setup_table(self):
        self.table = EventTable()
        self.table.itemChanged.connect(self.on_cell_changed)

        # Connect Custom Signals
        self.table.rows_moved.connect(self.handle_row_move)

        # Context Menu
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.open_context_menu)

        self.main_layout.addWidget(self.table)

    def _setup_controls(self):
        controls_group = QGroupBox("Controls")
        layout = QHBoxLayout()

        self.btn_record = QPushButton("Record")
        self.btn_record.clicked.connect(self.toggle_recording)

        self.btn_play = QPushButton("Play")
        self.btn_play.clicked.connect(self.toggle_playback)

        self.btn_delete = QPushButton("Delete")
        self.btn_delete.clicked.connect(self.delete_selection)

        self.btn_clear = QPushButton("Clear")
        self.btn_clear.clicked.connect(self.clear_events)

        self.chk_capture_keys = QCheckBox("Capture Keys")
        self.chk_capture_keys.setChecked(True)

        self.lbl_loops = QLabel("Loops:")
        self.spin_loops = QSpinBox()
        self.spin_loops.setRange(0, 9999)
        self.spin_loops.setValue(1)
        self.spin_loops.valueChanged.connect(self._update_estimates)

        layout.addWidget(self.btn_record)
        layout.addWidget(self.btn_play)
        layout.addWidget(self.btn_delete)
        layout.addWidget(self.btn_clear)
        layout.addSpacing(20)
        layout.addWidget(self.chk_capture_keys)
        layout.addStretch()
        layout.addWidget(self.lbl_loops)
        layout.addWidget(self.spin_loops)

        controls_group.setLayout(layout)
        self.main_layout.addWidget(controls_group)

        self.status_label = QLabel("Ready")
        self.statusBar().addWidget(self.status_label)

    # --- DRAG & DROP LOGIC ---

    def handle_row_move(self, source_rows, target_row, insert_mode):
        """
        Calculates the new order based on Drag & Drop menu selection.
        Uses a QTimer to defer the visual refresh, preventing Qt from
        clearing the new rows during its 'drop' cleanup phase.
        """
        # 1. Extract objects (using original list so indices don't shift yet)
        original_list = list(self.engine.events)
        moved_items = []
        for idx in source_rows:
            if idx < len(original_list):
                moved_items.append(original_list[idx])

        # 2. Remove items from the engine list
        for item in moved_items:
            self.engine.events.remove(item)

        # 3. Calculate adjustment for removal
        # If we remove a row ABOVE the target, the target index shifts down.
        adjustment = 0
        for row in source_rows:
            if row < target_row:
                adjustment += 1

        adjusted_target = target_row - adjustment

        # 4. Determine final insertion index
        if insert_mode == 'above':
            insert_idx = adjusted_target
        else:  # 'below'
            insert_idx = adjusted_target + 1

        # Safety clamp
        insert_idx = max(0, min(insert_idx, len(self.engine.events)))

        # 5. Insert items at new position
        for i, item in enumerate(moved_items):
            self.engine.events.insert(insert_idx + i, item)

        # --- THE FIX: DEFER UI UPDATE ---
        def deferred_refresh():
            self.refresh_table()

            # Re-select moved items (UX Polish)
            self.table.clearSelection()
            for i in range(len(moved_items)):
                self.table.selectRow(insert_idx + i)

        # Wait 0ms (pushes this to the end of the event queue)
        QTimer.singleShot(0, deferred_refresh)
    # --- CONTEXT MENU ---

    def open_context_menu(self, position):
        menu = QMenu()

        # Actions
        act_cut = menu.addAction("Cut")
        act_copy = menu.addAction("Copy")
        act_paste = menu.addAction("Paste")
        menu.addSeparator()
        act_flag = menu.addAction("Insert Flag")
        act_wait = menu.addAction("Insert Wait (1s)")
        menu.addSeparator()
        act_dup = menu.addAction("Duplicate")
        act_del = menu.addAction("Delete")

        # Check clipboard ...
        if not hasattr(self, '_clipboard_events') or not self._clipboard_events:
            act_paste.setEnabled(False)

        action = menu.exec_(self.table.viewport().mapToGlobal(position))

        if action == act_cut:
            self.cut_selection()
        elif action == act_copy:
            self.copy_selection()
        elif action == act_paste:
            self.paste_selection()
        elif action == act_flag:
            self.insert_flag()
        elif action == act_wait:
            self.insert_wait()
        elif action == act_dup:
            self.duplicate_selection()
        elif action == act_del:
            self.delete_selection()

    def duplicate_selection(self):
        selected_rows = sorted(set(index.row() for index in self.table.selectedIndexes()))
        if not selected_rows: return

        new_events = []
        insert_base = selected_rows[-1] + 1

        for row in selected_rows:
            item = self.table.item(row, 0)
            if not item: continue
            original_event = item.data(Qt.UserRole)
            if not original_event: continue

            # Deep Copy via Dict
            data = original_event.to_dict()
            new_event = MacroEvent.from_dict(data)
            new_events.append(new_event)

        for i, ev in enumerate(new_events):
            self.engine.events.insert(insert_base + i, ev)

        self.refresh_table()
        self.status_label.setText(f"Duplicated {len(new_events)} events.")

    # --- MAIN LOGIC & BOILERPLATE ---

    def insert_flag(self):
        """Inserts a comment flag and immediately opens it for editing."""
        current_row = self.table.currentRow()

        # If nothing selected, append to end
        if current_row == -1:
            current_row = len(self.engine.events)
        else:
            # Insert *after* the selected row usually feels more natural for flags,
            # but standard "Insert" usually pushes down. Let's push down (Insert At).
            pass

            # Create the Event
        flag = FlagEvent("--- NEW COMMENT ---")
        self.engine.events.insert(current_row, flag)

        # Refresh to render the green span
        self.refresh_table()

        # UX POLISH: Auto-select and Open Editor
        self.table.selectRow(current_row)
        item = self.table.item(current_row, 0)  # Col 0 holds the text
        if item:
            self.table.setCurrentItem(item)  # Focus the item
            self.table.editItem(item)  # Force-open the text editor

    def insert_wait(self):
        """Inserts a 1-second wait event."""
        current_row = self.table.currentRow()
        if current_row == -1:
            current_row = len(self.engine.events)

        # Create Wait Event
        wait_ev = WaitEvent(1.0)
        self.engine.events.insert(current_row, wait_ev)

        self.refresh_table()

        # Select the 'Delay' cell for immediate editing (Column 5)
        self.table.selectRow(current_row)
        item = self.table.item(current_row, 5)  # 5 = Delay column
        if item:
            self.table.setCurrentItem(item)
            self.table.editItem(item)

    def _start_hotkey_listener(self):
        if self.hotkey_listener:
            self.hotkey_listener.stop()
        try:
            self.hotkey_listener = keyboard.GlobalHotKeys({
                self.hotkey_record: self.toggle_recording,
                self.hotkey_play: self.toggle_playback
            })
            self.hotkey_listener.start()
        except ValueError as e:
            self.status_label.setText(f"Error setting hotkeys: {e}")\

    def edit_hotkeys(self):
        dialog = HotkeyDialog(self.hotkey_record, self.hotkey_play, self)
        if dialog.exec_():
            new_rec, new_play = dialog.get_values()
            if new_rec and new_play:
                self.hotkey_record = new_rec
                self.hotkey_play = new_play
                self._start_hotkey_listener()
                self.status_label.setText(f"Hotkeys updated.")
            else:
                QMessageBox.warning(self, "Invalid", "Hotkeys cannot be empty.")

    def closeEvent(self, event):
        if self.hotkey_listener:
            self.hotkey_listener.stop()
        event.accept()

    def toggle_sync(self):
        self.sync_coords = self.act_sync.isChecked()
        self.status_label.setText(f"Sync Coordinates: {self.sync_coords}")

    def toggle_always_on_top(self):
        should_be_top = self.act_always_top.isChecked()
        current_flags = self.windowFlags()
        if should_be_top:
            self.setWindowFlags(current_flags | Qt.WindowStaysOnTopHint)
            self.status_label.setText("Always on Top: ON")
        else:
            self.setWindowFlags(current_flags & ~Qt.WindowStaysOnTopHint)
            self.status_label.setText("Always on Top: OFF")
        self.show()

    def toggle_smart_delete(self):
        self.smart_delete = self.act_smart_del.isChecked()
        self.status_label.setText(f"Smart Delete: {self.smart_delete}")

    def toggle_releases(self):
        self.show_releases = not self.act_hide_rel.isChecked()

        # SAFETY: Disable Drag & Drop if releases are hidden
        self.table.setDragEnabled(self.show_releases)

        self.refresh_table()

    def show_transparency_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Window Transparency")
        layout = QVBoxLayout(dialog)
        lbl = QLabel("Opacity (10% - 100%)")
        slider = QSlider(Qt.Horizontal)
        slider.setRange(10, 100)
        slider.setValue(int(self.windowOpacity() * 100))

        def set_opacity(val):
            self.setWindowOpacity(val / 100.0)

        slider.valueChanged.connect(set_opacity)
        layout.addWidget(lbl)
        layout.addWidget(slider)
        dialog.exec_()

    def save_events(self):
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getSaveFileName(self, "Save Macro", "", "JSON Files (*.json)", options=options)
        if file_name:
            data = [e.to_dict() for e in self.engine.events]
            with open(file_name, 'w') as f:
                json.dump(data, f, indent=4)
            self.status_label.setText(f"Saved to {file_name}")

    def load_events(self):
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(self, "Load Macro", "", "JSON Files (*.json)", options=options)
        if file_name:
            try:
                with open(file_name, 'r') as f:
                    data = json.load(f)
                loaded_events = []
                for item in data:
                    event = MacroEvent.from_dict(item)
                    if event: loaded_events.append(event)
                self.engine.load_events(loaded_events)
                self.refresh_table()
                self.status_label.setText(f"Loaded {len(loaded_events)} events.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load: {e}")

    def delete_selection(self):
        selected_rows = sorted(set(index.row() for index in self.table.selectedIndexes()), reverse=True)
        if not selected_rows: return

        events_to_remove = []

        for row in selected_rows:
            item = self.table.item(row, 0)
            if not item: continue

            event = item.data(Qt.UserRole)
            if not event: continue

            events_to_remove.append(event)

            if self.smart_delete and isinstance(event, MousePressEvent):
                partner = self._find_partner_release(event)
                if partner and partner not in events_to_remove:
                    events_to_remove.append(partner)

        for e in events_to_remove:
            if e in self.engine.events:
                self.engine.events.remove(e)

        self.refresh_table()
        self.status_label.setText(f"Deleted {len(events_to_remove)} event(s).")

    def _find_partner_release(self, press_event):
        try:
            idx = self.engine.events.index(press_event)
            for i in range(idx + 1, len(self.engine.events)):
                next_event = self.engine.events[i]
                if isinstance(next_event, MouseReleaseEvent) and next_event.button == press_event.button:
                    return next_event
        except ValueError:
            pass
        return None

    def on_cell_changed(self, item):
        row = item.row()
        col = item.column()
        val = item.text()

        # Get Event Object (We use column 0 to retrieve the data for all rows)
        type_item = self.table.item(row, 0)
        if not type_item: return
        event = type_item.data(Qt.UserRole)
        if not event: return

        # --- NEW: HANDLE FLAG EDIT ---
        # If this is a flag, the user is editing the description text.
        if isinstance(event, FlagEvent):
            event.text = val
            return  # Flags don't have coords/delays, so we stop here.
        # -----------------------------

        # Standard Logic for Mouse/Key/Wait events
        try:
            if col == 2:
                event.x = int(float(val))
            elif col == 3:
                event.y = int(float(val))
            elif col == 5:
                event.delay = float(val)
                self._update_estimates()
            elif col == 6:
                event.variance = int(float(val))
        except ValueError:
            pass

            # Sync Logic (Only for MousePress)
        if self.sync_coords and isinstance(event, MousePressEvent) and (col == 2 or col == 3):
            self._sync_next_release(event)
            if self.show_releases:
                # Use singleShot to defer the refresh and prevent recursion loops
                QTimer.singleShot(0, self.refresh_table)
    def _sync_next_release(self, press_event):
        try:
            idx = self.engine.events.index(press_event)
            for i in range(idx + 1, len(self.engine.events)):
                next_event = self.engine.events[i]
                if isinstance(next_event, MouseReleaseEvent) and next_event.button == press_event.button:
                    next_event.x = press_event.x
                    next_event.y = press_event.y
                    return
        except ValueError:
            pass

    def _highlight_active_row(self):
        idx = self.engine.current_event_index
        if self._last_highlighted_idx == idx: return

        self.table.blockSignals(True)
        try:
            if self._last_highlighted_idx >= 0 and self._last_highlighted_idx < self.table.rowCount():
                for col in range(self.table.columnCount()):
                    item = self.table.item(self._last_highlighted_idx, col)
                    if item: item.setBackground(QColor(0, 0, 0, 0))

            if idx >= 0 and idx < self.table.rowCount():
                for col in range(self.table.columnCount()):
                    item = self.table.item(idx, col)
                    if item: item.setBackground(QColor(255, 255, 0))
                self.table.scrollToItem(self.table.item(idx, 0))

            self._last_highlighted_idx = idx
        finally:
            self.table.blockSignals(False)

    def _on_tick(self):
        if self.engine.is_playing:
            self.btn_play.setText("Stop")
            self.btn_record.setEnabled(False)
            self.btn_delete.setEnabled(False)

            self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
            self.table.setSelectionMode(QAbstractItemView.NoSelection)
            self.table.setDragEnabled(False)

            self._highlight_active_row()
        else:
            if self.btn_record.text() == "Record":
                self.btn_play.setText("Play")
                self.btn_record.setEnabled(True)
                self.btn_delete.setEnabled(True)

                self.table.setEnabled(True)
                self.table.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed)
                self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
                if self.show_releases:
                    self.table.setDragEnabled(True)

                if self._last_highlighted_idx != -1:
                    self.engine.current_event_index = -1
                    self._highlight_active_row()

        x, y = pyautogui.position()
        self.lbl_mouse_pos.setText(f"Mouse: ({x}, {y})")

    def _update_estimates(self):
        single_loop_time = self.engine.calculate_duration()
        loops = self.spin_loops.value()
        total_time = single_loop_time * loops
        total_str = "Infinite" if loops == 0 else f"{total_time:.2f}s"
        self.lbl_loop_time.setText(f"Loop Time: {single_loop_time:.2f}s")
        self.lbl_total_est.setText(f"Total Est: {total_str}")

    def toggle_recording(self):
        if self.engine.is_playing: return

        if self.btn_record.text() == "Record":
            capture_keys = self.chk_capture_keys.isChecked()
            self.engine.start_recording(capture_keys=capture_keys)
            self.btn_record.setText("Stop Recording")
            self.status_label.setText("Recording... (Press Stop)")
            self.btn_play.setEnabled(False)
            self.btn_delete.setEnabled(False)
        else:
            new_count = self.engine.stop_recording()
            self.btn_record.setText("Record")
            self.status_label.setText(f"Recorded {new_count} events.")
            self.btn_play.setEnabled(True)
            self.btn_delete.setEnabled(True)
            self.refresh_table()

    def toggle_playback(self):
        if self.engine.recorder.mouse_listener: return
        if not self.engine.is_playing:
            loops = self.spin_loops.value()
            self.engine.start_playback(loops)
            self.status_label.setText("Playing...")
        else:
            self.engine.stop_playback()
            self.status_label.setText("Stopped.")

    def clear_events(self):
        self.engine.clear_events()
        self.refresh_table()
        self.status_label.setText("Timeline cleared.")

    def refresh_table(self):
        self.table.blockSignals(True)
        self.table.setRowCount(0)

        for row_idx, event in enumerate(self.engine.events):
            if not self.show_releases:
                if isinstance(event, MouseReleaseEvent): continue
                if isinstance(event, KeyEvent) and event.action == 'release': continue

            row = self.table.rowCount()
            self.table.insertRow(row)

            type_str = event.__class__.__name__.replace("Event", "")
            if isinstance(event, MousePressEvent): type_str = "MouseDown"
            if isinstance(event, MouseReleaseEvent): type_str = "MouseUp"

            type_item = QTableWidgetItem(type_str)
            type_item.setData(Qt.UserRole, event)
            type_item.setFlags(type_item.flags() ^ Qt.ItemIsEditable)
            self.table.setItem(row, 0, type_item)

            action_str = ""
            if hasattr(event, 'button'):
                action_str = event.button
            elif hasattr(event, 'action'):
                action_str = event.action
            self.table.setItem(row, 1, QTableWidgetItem(action_str))

            x_val = str(getattr(event, 'x', ''))
            y_val = str(getattr(event, 'y', ''))
            self.table.setItem(row, 2, QTableWidgetItem(x_val))
            self.table.setItem(row, 3, QTableWidgetItem(y_val))

            btn_key = ""
            if hasattr(event, 'button'):
                btn_key = event.button
            elif hasattr(event, 'key_code'):
                btn_key = str(event.key_code)
            self.table.setItem(row, 4, QTableWidgetItem(btn_key))

            self.table.setItem(row, 5, QTableWidgetItem(f"{getattr(event, 'delay', 0):.2f}"))
            self.table.setItem(row, 6, QTableWidgetItem(str(getattr(event, 'variance', 0))))

        self.table.blockSignals(False)
        self._update_estimates()