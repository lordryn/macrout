import sys
import json
import pyautogui
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QPushButton,
    QLabel, QSpinBox, QHeaderView, QAbstractItemView,
    QCheckBox, QGroupBox, QAction, QFileDialog, QMessageBox,
    QMenuBar, QSlider, QDialog, QLineEdit, QDialogButtonBox
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor

from pynput import keyboard

from src.engine import MacroEngine
from src.events import (
    MacroEvent, ClickEvent, KeyEvent, WaitEvent,
    MousePressEvent, MouseReleaseEvent
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
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(7)
        self.setHorizontalHeaderLabels(["Type", "Action", "X", "Y", "Button/Key", "Delay", "Variance"])
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)  # Allow multiple selection
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setViewportMargins(0, 0, 0, 0)
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setDropIndicatorShown(True)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Macrout 2.0 - Automation IDE")
        self.resize(1000, 650)

        self.engine = MacroEngine()

        # View Settings
        self.show_releases = True
        self.sync_coords = True
        self.smart_delete = True  # Default to paired deletion

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

        self.act_sync = QAction('Sync Coordinates', self, checkable=True)
        self.act_sync.setChecked(True)
        self.act_sync.triggered.connect(self.toggle_sync)
        settings_menu.addAction(self.act_sync)

        # Smart Delete Toggle
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
        self.main_layout.addWidget(self.table)

    def _setup_controls(self):
        controls_group = QGroupBox("Controls")
        layout = QHBoxLayout()

        self.btn_record = QPushButton("Record")
        self.btn_record.clicked.connect(self.toggle_recording)

        self.btn_play = QPushButton("Play")
        self.btn_play.clicked.connect(self.toggle_playback)

        self.btn_delete = QPushButton("Delete")  # <--- NEW BUTTON
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
        layout.addWidget(self.btn_delete)  # Added to layout
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

    # --- HOTKEYS ---

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
            self.status_label.setText(f"Error setting hotkeys: {e}")

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

    # --- MENU ACTIONS ---

    def toggle_sync(self):
        self.sync_coords = self.act_sync.isChecked()
        self.status_label.setText(f"Sync Coordinates: {self.sync_coords}")

    def toggle_smart_delete(self):
        self.smart_delete = self.act_smart_del.isChecked()
        self.status_label.setText(f"Smart Delete: {self.smart_delete}")

    def toggle_releases(self):
        self.show_releases = not self.act_hide_rel.isChecked()
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

    # --- DELETION LOGIC ---

    def delete_selection(self):
        selected_rows = sorted(set(index.row() for index in self.table.selectedIndexes()), reverse=True)
        if not selected_rows:
            return

        events_to_remove = []

        for row in selected_rows:
            item = self.table.item(row, 0)
            if not item: continue

            event = item.data(Qt.UserRole)
            if not event: continue

            events_to_remove.append(event)

            # SMART DELETE: If removing a Press, find and remove its Release
            if self.smart_delete and isinstance(event, MousePressEvent):
                partner = self._find_partner_release(event)
                if partner and partner not in events_to_remove:
                    events_to_remove.append(partner)

        # Remove from engine
        for e in events_to_remove:
            if e in self.engine.events:
                self.engine.events.remove(e)

        self.refresh_table()
        self.status_label.setText(f"Deleted {len(events_to_remove)} event(s).")

    def _find_partner_release(self, press_event):
        """Finds the next MouseRelease matching the press_event."""
        try:
            idx = self.engine.events.index(press_event)
            for i in range(idx + 1, len(self.engine.events)):
                next_event = self.engine.events[i]
                if isinstance(next_event, MouseReleaseEvent) and next_event.button == press_event.button:
                    return next_event
        except ValueError:
            pass
        return None

    # --- CELL EDIT & SYNC LOGIC ---

    def on_cell_changed(self, item):
        row = item.row()
        col = item.column()
        val = item.text()

        type_item = self.table.item(row, 0)
        if not type_item: return
        event = type_item.data(Qt.UserRole)
        if not event: return

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

        if self.sync_coords and isinstance(event, MousePressEvent) and (col == 2 or col == 3):
            self._sync_next_release(event)
            if self.show_releases:
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

            # --- HIGHLIGHTING & TICK ---

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
            self.btn_delete.setEnabled(False)  # Disable delete during play

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
                self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)  # Allow Multi-select
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
            self._sync_table_to_engine()
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

    def _sync_table_to_engine(self):
        if not self.show_releases: return
        new_events = []
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item:
                event = item.data(Qt.UserRole)
                if event: new_events.append(event)
        if new_events:
            self.engine.events = new_events
        self._update_estimates()