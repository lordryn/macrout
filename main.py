import sys
import time
import threading
import pyautogui
import json
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QTableWidget, QTableWidgetItem,
    QDialog, QLineEdit, QLabel, QDialogButtonBox, QFileDialog, QCheckBox,
    QMenuBar, QAction, QToolBar, QStatusBar, QHBoxLayout, QMainWindow, QMessageBox, QSpinBox, QComboBox
)
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, QTimer
from PyQt5 import QtCore

from pynput import keyboard
from pynput.mouse import Listener as MouseListener
from pynput.keyboard import Listener as KeyboardListener

class EditDialog(QDialog):
    def __init__(self, event_type, action, x, y, button_key, delay):
        super().__init__()
        self.setWindowTitle('Edit Event')
        self.layout = QVBoxLayout(self)

        self.typeEdit = QLineEdit(event_type)
        self.layout.addWidget(QLabel('Type:'))
        self.layout.addWidget(self.typeEdit)

        self.actionEdit = QLineEdit(action)
        self.layout.addWidget(QLabel('Action:'))
        self.layout.addWidget(self.actionEdit)

        self.xEdit = QLineEdit(str(x))
        self.layout.addWidget(QLabel('X:'))
        self.layout.addWidget(self.xEdit)

        self.yEdit = QLineEdit(str(y))
        self.layout.addWidget(QLabel('Y:'))
        self.layout.addWidget(self.yEdit)

        self.buttonKeyEdit = QLineEdit(button_key)
        self.layout.addWidget(QLabel('Button/Key:'))
        self.layout.addWidget(self.buttonKeyEdit)

        self.delayEdit = QLineEdit(delay)
        self.layout.addWidget(QLabel('Delay (s):'))
        self.layout.addWidget(self.delayEdit)

        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        self.layout.addWidget(self.buttons)

    def getValues(self):
        return (
            self.typeEdit.text(), self.actionEdit.text(), self.xEdit.text(),
            self.yEdit.text(), self.buttonKeyEdit.text(), self.delayEdit.text()
        )

class MacroutApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.initListeners()  # Initialize listeners once
        self.initHotkeys()    # Initialize hotkeys
        self.show()

    def initUI(self):
        self.setWindowTitle('Macrout')
        self.setWindowFlags(Qt.WindowStaysOnTopHint)
        self.setWindowOpacity(0.9)  # Adjusted for better visibility

        # Central widget
        centralWidget = QWidget()
        self.setCentralWidget(centralWidget)
        self.layout = QVBoxLayout(centralWidget)

        # Table
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(['Type', 'Action', 'X', 'Y', 'Button/Key', 'Delay'])
        self.layout.addWidget(self.table)

        # Mouse position label
        self.mousePositionLabel = QLabel("Mouse Position: X=0, Y=0")
        self.layout.addWidget(self.mousePositionLabel)

        # Loop and statistics
        loopStatsLayout = QHBoxLayout()

        self.loopCheckbox = QCheckBox('Loop Playback')
        self.loopCheckbox.setChecked(False)
        loopStatsLayout.addWidget(self.loopCheckbox)

        self.loopModeCombo = QComboBox()
        self.loopModeCombo.addItems(['Number of Loops', 'Total Duration (s)'])
        loopStatsLayout.addWidget(self.loopModeCombo)

        self.loopCountSpin = QSpinBox()
        self.loopCountSpin.setRange(1, 1000000)
        self.loopCountSpin.setValue(1)
        loopStatsLayout.addWidget(self.loopCountSpin)

        self.countdownLabel = QLabel('Countdown: N/A')
        loopStatsLayout.addWidget(self.countdownLabel)

        self.layout.addLayout(loopStatsLayout)

        # Toolbar
        self.toolbar = QToolBar("Main Toolbar")
        self.addToolBar(self.toolbar)

        # Buttons on toolbar
        self.recordAction = QAction(QIcon(), 'Start Recording', self)
        self.recordAction.triggered.connect(self.toggleRecording)
        self.toolbar.addAction(self.recordAction)

        self.playAction = QAction(QIcon(), 'Start Playback', self)
        self.playAction.triggered.connect(self.startPlayback)
        self.toolbar.addAction(self.playAction)

        self.stopAction = QAction(QIcon(), 'Stop Playback', self)
        self.stopAction.triggered.connect(self.stopPlayback)
        self.toolbar.addAction(self.stopAction)

        self.clearAction = QAction(QIcon(), 'Clear Events', self)
        self.clearAction.triggered.connect(self.clearEvents)
        self.toolbar.addAction(self.clearAction)

        # Checkboxes and buttons
        optionsLayout = QHBoxLayout()
        self.captureKeysCheckbox = QCheckBox('Capture Keys')
        optionsLayout.addWidget(self.captureKeysCheckbox)
        self.captureKeysCheckbox.setChecked(False)

        self.addButton = QPushButton('Add Event')
        self.addButton.clicked.connect(self.addClick)
        optionsLayout.addWidget(self.addButton)

        self.editButton = QPushButton('Edit Event')
        self.editButton.clicked.connect(self.editClick)
        optionsLayout.addWidget(self.editButton)

        self.deleteButton = QPushButton('Delete Event')
        self.deleteButton.clicked.connect(self.deleteClick)
        optionsLayout.addWidget(self.deleteButton)

        self.layout.addLayout(optionsLayout)

        # Status bar
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)

        # Menu bar
        self.menuBar = QMenuBar()
        self.setMenuBar(self.menuBar)

        # File menu
        fileMenu = self.menuBar.addMenu('File')

        saveAction = QAction('Save', self)
        saveAction.triggered.connect(self.saveClicks)
        fileMenu.addAction(saveAction)

        loadAction = QAction('Load', self)
        loadAction.triggered.connect(self.loadClicks)
        fileMenu.addAction(loadAction)

        exitAction = QAction('Exit', self)
        exitAction.triggered.connect(self.close)
        fileMenu.addAction(exitAction)

        # Settings menu
        settingsMenu = self.menuBar.addMenu('Settings')

        hotkeyAction = QAction('Set Hotkeys', self)
        hotkeyAction.triggered.connect(self.setHotkeys)
        settingsMenu.addAction(hotkeyAction)

        # Mouse position tracking
        self.mouse_position_timer = QtCore.QTimer()
        self.mouse_position_timer.timeout.connect(self.updateMousePosition)
        self.mouse_position_timer.start(100)

        # Initialize variables
        self.playback_active = False
        self.playback_thread = None
        self.recording_active = False
        self.last_event_time = None
        self.default_hotkeys()
        self.loop_countdown_timer = None

    def default_hotkeys(self):
        # Default hotkeys
        self.start_stop_recording_hotkey = '<ctrl>+<alt>+r'
        self.start_stop_playback_hotkey = '<ctrl>+<alt>+p'

    def initListeners(self):
        # Start listeners once
        self.mouse_listener = MouseListener(on_click=self.on_click)
        self.mouse_listener.start()

        self.keyboard_listener = KeyboardListener(on_press=self.on_press, on_release=self.on_release)
        self.keyboard_listener.start()

    def initHotkeys(self):
        # Set up global hotkeys
        self.hotkey_listener = keyboard.GlobalHotKeys({
            self.start_stop_recording_hotkey: self.toggleRecording,
            self.start_stop_playback_hotkey: self.togglePlayback
        })
        self.hotkey_listener.start()

    def togglePlayback(self):
        if self.playback_active:
            self.stopPlayback()
        else:
            self.startPlayback()

    def updateMousePosition(self):
        x, y = pyautogui.position()
        self.mousePositionLabel.setText(f"Mouse Position: X={x}, Y={y}")

    def toggleRecording(self):
        if not self.recording_active:
            self.startRecording()
        else:
            self.stopRecording()

    def startRecording(self):
        self.recording_active = True
        self.recordAction.setText('Stop Recording')
        self.statusBar.showMessage('Recording started')
        self.last_event_time = time.time()

    def stopRecording(self):
        self.recording_active = False
        self.recordAction.setText('Start Recording')
        self.statusBar.showMessage('Recording stopped')

    # Mouse event handler
    def on_click(self, x, y, button, pressed):
        if self.recording_active:
            action = 'press' if pressed else 'release'
            self.record_event('Mouse', action, x, y, str(button).replace('Button.', '').lower())

    # Keyboard event handlers
    def on_press(self, key):
        if self.recording_active and self.captureKeysCheckbox.isChecked():
            try:
                key_str = key.char
            except AttributeError:
                key_str = str(key).replace('Key.', '')
            self.record_event('Key', 'press', '', '', key_str)

    def on_release(self, key):
        if self.recording_active and self.captureKeysCheckbox.isChecked():
            try:
                key_str = key.char
            except AttributeError:
                key_str = str(key).replace('Key.', '')
            self.record_event('Key', 'release', '', '', key_str)

    def record_event(self, event_type, action, x, y, button_key):
        current_time = time.time()
        if self.last_event_time is None:
            delay = 0
        else:
            delay = current_time - self.last_event_time
        self.last_event_time = current_time

        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(event_type))
        self.table.setItem(row, 1, QTableWidgetItem(action))
        self.table.setItem(row, 2, QTableWidgetItem(str(x)))
        self.table.setItem(row, 3, QTableWidgetItem(str(y)))
        self.table.setItem(row, 4, QTableWidgetItem(button_key))
        self.table.setItem(row, 5, QTableWidgetItem(f"{delay:.4f}"))

    def playbackClicks(self):
        self.playback_active = True
        self.statusBar.showMessage('Playback started')
        loop_enabled = self.loopCheckbox.isChecked()
        loop_mode = self.loopModeCombo.currentText()
        loop_count = self.loopCountSpin.value()

        if loop_enabled:
            if loop_mode == 'Number of Loops':
                total_loops = loop_count
                loop_duration = None
            else:
                total_loops = None
                loop_duration = loop_count  # Here, loop_count represents duration in seconds
        else:
            total_loops = 1
            loop_duration = None

        start_time = time.time()
        loops_completed = 0
        single_loop_time = self.calculate_single_loop_time()

        # Initialize countdown
        if loop_enabled and loop_mode == 'Number of Loops':
            self.remaining_loops = total_loops
        elif loop_enabled and loop_mode == 'Total Duration (s)':
            self.end_time = start_time + loop_duration
        else:
            self.remaining_loops = 1

        while self.playback_active:
            # Update countdown
            if loop_enabled and loop_mode == 'Number of Loops':
                self.countdownLabel.setText(f"Remaining Loops: {self.remaining_loops}")
            elif loop_enabled and loop_mode == 'Total Duration (s)':
                time_left = max(0, int(self.end_time - time.time()))
                self.countdownLabel.setText(f"Time Left: {time_left}s")
                if time_left <= 0:
                    break

            i = 0
            total_events = self.table.rowCount()
            while i < total_events and self.playback_active:
                event_type = self.table.item(i, 0).text()
                action = self.table.item(i, 1).text()
                x_text = self.table.item(i, 2).text()
                y_text = self.table.item(i, 3).text()
                button_key = self.table.item(i, 4).text()
                delay_text = self.table.item(i, 5).text()

                delay = float(delay_text)
                time.sleep(delay)

                if event_type == 'Mouse':
                    if x_text and y_text:
                        x = int(float(x_text))
                        y = int(float(y_text))
                    else:
                        x, y = pyautogui.position()
                    if action == 'press':
                        pyautogui.moveTo(x, y)
                        pyautogui.mouseDown(button=button_key)
                    elif action == 'release':
                        pyautogui.moveTo(x, y)
                        pyautogui.mouseUp(button=button_key)
                elif event_type == 'Key':
                    key = button_key
                    if action == 'press':
                        pyautogui.keyDown(key)
                    elif action == 'release':
                        pyautogui.keyUp(key)
                i += 1

            loops_completed += 1

            if loop_enabled:
                if loop_mode == 'Number of Loops':
                    self.remaining_loops -= 1
                    if self.remaining_loops <= 0:
                        break
                elif loop_mode == 'Total Duration (s)':
                    if time.time() >= self.end_time:
                        break
            else:
                break  # Only one loop needed when looping is disabled

        total_runtime = time.time() - start_time
        loops_per_second = loops_completed / total_runtime if total_runtime > 0 else 0

        # Display statistics
        stats_message = (
            f"Playback finished. Loops completed: {loops_completed}, "
            f"Total runtime: {total_runtime:.2f}s, "
            f"Average loop time: {single_loop_time:.2f}s"
        )
        self.statusBar.showMessage(stats_message)
        self.countdownLabel.setText('Countdown: N/A')
        self.playback_active = False

    def calculate_single_loop_time(self):
        total_time = 0.0
        for i in range(self.table.rowCount()):
            delay_text = self.table.item(i, 5).text()
            delay = float(delay_text)
            total_time += delay
        return total_time

    def startPlayback(self):
        if self.table.rowCount() == 0:
            QMessageBox.warning(self, 'No Events', 'No events to playback.')
            return
        if self.playback_thread is None or not self.playback_thread.is_alive():
            self.playback_thread = threading.Thread(target=self.playbackClicks)
            self.playback_thread.start()

    def stopPlayback(self):
        self.playback_active = False
        self.statusBar.showMessage('Playback stopped')

    def addClick(self):
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem('Mouse'))
        self.table.setItem(row, 1, QTableWidgetItem('click'))
        self.table.setItem(row, 2, QTableWidgetItem('0'))
        self.table.setItem(row, 3, QTableWidgetItem('0'))
        self.table.setItem(row, 4, QTableWidgetItem('left'))
        self.table.setItem(row, 5, QTableWidgetItem('1.00'))

    def deleteClick(self):
        currentRow = self.table.currentRow()
        if currentRow > -1:
            self.table.removeRow(currentRow)

    def clearEvents(self):
        self.table.setRowCount(0)
        self.statusBar.showMessage('Events cleared')

    def editClick(self):
        currentRow = self.table.currentRow()
        if currentRow > -1:
            event_type = self.table.item(currentRow, 0).text()
            action = self.table.item(currentRow, 1).text()
            x = self.table.item(currentRow, 2).text()
            y = self.table.item(currentRow, 3).text()
            button_key = self.table.item(currentRow, 4).text()
            delay = self.table.item(currentRow, 5).text()

            dialog = EditDialog(event_type, action, x, y, button_key, delay)
            if dialog.exec():
                event_type, action, x, y, button_key, delay = dialog.getValues()
                self.table.setItem(currentRow, 0, QTableWidgetItem(event_type))
                self.table.setItem(currentRow, 1, QTableWidgetItem(action))
                self.table.setItem(currentRow, 2, QTableWidgetItem(x))
                self.table.setItem(currentRow, 3, QTableWidgetItem(y))
                self.table.setItem(currentRow, 4, QTableWidgetItem(button_key))
                self.table.setItem(currentRow, 5, QTableWidgetItem(delay))

    def saveClicks(self):
        options = QFileDialog.Options()
        fileName, _ = QFileDialog.getSaveFileName(
            self, "Save Events", "", "JSON Files (*.json);;All Files (*)", options=options
        )
        if fileName:
            clicks = []
            for row in range(self.table.rowCount()):
                event_type = self.table.item(row, 0).text()
                action = self.table.item(row, 1).text()
                x = self.table.item(row, 2).text()
                y = self.table.item(row, 3).text()
                button_key = self.table.item(row, 4).text()
                delay = self.table.item(row, 5).text()
                clicks.append({
                    "type": event_type,
                    "action": action,
                    "x": x,
                    "y": y,
                    "button_key": button_key,
                    "delay": delay
                })
            with open(fileName, 'w') as file:
                json.dump(clicks, file, indent=4)
            self.statusBar.showMessage('Events saved')

    def loadClicks(self):
        options = QFileDialog.Options()
        fileName, _ = QFileDialog.getOpenFileName(
            self, "Load Events", "", "JSON Files (*.json);;All Files (*)", options=options
        )
        if fileName:
            with open(fileName, 'r') as file:
                clicks = json.load(file)
                self.table.setRowCount(0)  # Clear the table before loading new clicks
                for click in clicks:
                    row = self.table.rowCount()
                    self.table.insertRow(row)
                    self.table.setItem(row, 0, QTableWidgetItem(click['type']))
                    self.table.setItem(row, 1, QTableWidgetItem(click['action']))
                    self.table.setItem(row, 2, QTableWidgetItem(click['x']))
                    self.table.setItem(row, 3, QTableWidgetItem(click['y']))
                    self.table.setItem(row, 4, QTableWidgetItem(click['button_key']))
                    self.table.setItem(row, 5, QTableWidgetItem(click['delay']))
            self.statusBar.showMessage('Events loaded')

    def setHotkeys(self):
        # Dialog to set hotkeys
        dialog = QDialog(self)
        dialog.setWindowTitle('Set Hotkeys')
        layout = QVBoxLayout(dialog)

        recordLabel = QLabel('Start/Stop Recording Hotkey:')
        self.recordHotkeyEdit = QLineEdit(self.start_stop_recording_hotkey)
        layout.addWidget(recordLabel)
        layout.addWidget(self.recordHotkeyEdit)

        playbackLabel = QLabel('Start/Stop Playback Hotkey:')
        self.playbackHotkeyEdit = QLineEdit(self.start_stop_playback_hotkey)
        layout.addWidget(playbackLabel)
        layout.addWidget(self.playbackHotkeyEdit)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, dialog)
        buttons.accepted.connect(lambda: self.updateHotkeys(dialog))
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        dialog.exec_()

    def updateHotkeys(self, dialog):
        # Unregister previous hotkeys
        self.hotkey_listener.stop()

        self.start_stop_recording_hotkey = self.recordHotkeyEdit.text()
        self.start_stop_playback_hotkey = self.playbackHotkeyEdit.text()

        # Reinitialize hotkeys
        self.initHotkeys()
        dialog.accept()
        self.statusBar.showMessage('Hotkeys updated')

    def closeEvent(self, event):
        # Stop listeners when application closes
        self.mouse_listener.stop()
        self.keyboard_listener.stop()
        self.hotkey_listener.stop()
        self.mouse_listener.join()
        self.keyboard_listener.join()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = MacroutApp()
    sys.exit(app.exec_())
