import sys
import time
import threading
import pyautogui
import json
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QTableWidget, QTableWidgetItem,
    QDialog, QLineEdit, QLabel, QDialogButtonBox, QFileDialog, QCheckBox,
    QMenuBar, QAction, QToolBar, QStatusBar, QHBoxLayout, QMainWindow, QMessageBox, QSpinBox, QComboBox, QSlider,
    QInputDialog
)
from PyQt5.QtGui import QIcon, QColor  # Add QColor for row highlighting
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


class AutoClickerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.initListeners()  # Initialize listeners once
        self.initHotkeys()    # Initialize hotkeys
        self.show()
        self.start_row = 0  # Initialize the active row


    def initUI(self):
        self.setWindowTitle('AutoClicker')
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

        # Labels layout
        labelsLayout = QHBoxLayout()
        self.mousePositionLabel = QLabel("Mouse Position: X=0, Y=0")
        labelsLayout.addWidget(self.mousePositionLabel)

        # Add stretch to push the next label to the right
        labelsLayout.addStretch()

        self.totalTimeLabel = QLabel("Total Estimated Time: 0.00s")
        labelsLayout.addWidget(self.totalTimeLabel)

        self.layout.addLayout(labelsLayout)

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

        # In initUI, where other buttons are set up
        self.setStartButton = QAction(QIcon(), 'Set Start Line', self)
        self.setStartButton.triggered.connect(self.setStartPosition)
        self.toolbar.addAction(self.setStartButton)

        self.playAction = QAction(QIcon(), 'Start Playback', self)
        self.playAction.triggered.connect(self.startPlayback)
        self.toolbar.addAction(self.playAction)

        self.stopAction = QAction(QIcon(), 'Stop Playback', self)
        self.stopAction.triggered.connect(self.stopPlayback)
        self.toolbar.addAction(self.stopAction)

        self.clearAction = QAction(QIcon(), 'Clear Events')
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

        self.insertFlagAction = QAction('Insert Flag', self)
        self.insertFlagAction.triggered.connect(self.insertFlagRow)
        settingsMenu.addAction(self.insertFlagAction)

        hotkeyAction = QAction('Set Hotkeys', self)
        hotkeyAction.triggered.connect(self.setHotkeys)
        settingsMenu.addAction(hotkeyAction)

        self.narrowViewAction = QAction('Narrow View', self, checkable=True)
        self.narrowViewAction.triggered.connect(self.toggleTableView)
        settingsMenu.addAction(self.narrowViewAction)

        self.hideReleasesAction = QAction('Hide Releases', self, checkable=True)
        self.hideReleasesAction.triggered.connect(self.toggleReleaseVisibility)
        settingsMenu.addAction(self.hideReleasesAction)

        self.adjustTransparencyAction = QAction('Adjust Transparency', self)
        self.adjustTransparencyAction.triggered.connect(self.showTransparencyDialog)
        settingsMenu.addAction(self.adjustTransparencyAction)

        self.syncCoordsAction = QAction('Sync Coordinates', self, checkable=True)
        self.syncCoordsAction.setChecked(True)  # Default to enabled
        settingsMenu.addAction(self.syncCoordsAction)

        # Mouse position tracking
        self.mouse_position_timer = QtCore.QTimer()
        self.mouse_position_timer.timeout.connect(self.updateMousePosition)
        self.mouse_position_timer.start(100)

        # Connect the itemChanged signal
        self.table.itemChanged.connect(self.on_table_item_changed)

        # Initialize variables
        self.playback_active = False
        self.playback_thread = None
        self.recording_active = False
        self.last_event_time = None
        self.default_hotkeys()
        self.loop_countdown_timer = None

        self.table.itemChanged.connect(self.updateReleaseCoords)

    def showTransparencyDialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Adjust Transparency")

        layout = QVBoxLayout(dialog)
        label = QLabel("Transparency:")
        layout.addWidget(label)

        # Create a slider for transparency (10% to 100%)
        slider = QSlider(Qt.Horizontal)
        slider.setRange(10, 100)  # Transparency range from 10% to 100%
        slider.setValue(int(self.windowOpacity() * 100))  # Set initial value to current opacity
        slider.valueChanged.connect(self.adjustWindowOpacity)
        layout.addWidget(slider)

        dialog.setLayout(layout)
        dialog.exec_()  # Show dialog as modal

    # Define a separate method to adjust the window opacity
    def adjustWindowOpacity(self, value):
        self.setWindowOpacity(value / 100)

    def toggleTableView(self):
        if self.narrowViewAction.isChecked():
            # Limit table height to approximately show 3 rows for a "narrow" view
            self.table.setFixedHeight(self.table.rowHeight(0) * 2 + self.table.horizontalHeader().height())
            self.statusBar.showMessage("Narrow View enabled")
        else:
            # Reset the table height to its full content size
            self.table.setFixedHeight(self.table.sizeHint().height())
            self.statusBar.showMessage("Full View enabled")

    def toggleReleaseVisibility(self):
        hide_releases = self.hideReleasesAction.isChecked()
        for row in range(self.table.rowCount()):
            action_item = self.table.item(row, 1)  # Column 1 is "Action"
            if action_item and action_item.text() == 'release':
                self.table.setRowHidden(row, hide_releases)

    def setStartPosition(self):
        currentRow = self.table.currentRow()
        if currentRow != -1:
            self.start_row = currentRow
            self.statusBar.showMessage(f'Starting playback from line {self.start_row + 1}')
        else:
            self.statusBar.showMessage('Please select a row to set as the start position')

    def setActiveRow(self, row):
            self.start_row = row
            self.statusBar.showMessage(f'Starting from row {row}')

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
            self.playback_active = False  # Acts as a pause
            self.statusBar.showMessage('Playback paused')
        else:
            self.playback_active = True
            self.startPlayback()  # Resumes playback

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

    def calculate_single_loop_time(self):
        total_time = 0.0
        for i in range(self.table.rowCount()):
            delay_text = self.table.item(i, 5).text()
            try:
                delay = float(delay_text)
                total_time += delay
            except ValueError:
                pass  # Ignore invalid entries
        return total_time

    def record_event(self, event_type, action, x, y, button_key):
        current_time = time.time()
        if self.last_event_time is None:
            delay = 0
        else:
            delay = current_time - self.last_event_time
        self.last_event_time = current_time

        # Block signals to prevent recursive calls
        self.table.blockSignals(True)

        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(event_type))
        self.table.setItem(row, 1, QTableWidgetItem(action))
        self.table.setItem(row, 2, QTableWidgetItem(str(x)))
        self.table.setItem(row, 3, QTableWidgetItem(str(y)))
        self.table.setItem(row, 4, QTableWidgetItem(button_key))
        self.table.setItem(row, 5, QTableWidgetItem(f"{delay:.4f}"))

        # Unblock signals after modifications
        self.table.blockSignals(False)

        self.update_total_time_label()

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

        first_loop = True  # Track if it's the first loop



        while self.playback_active:
            # Update countdown
            if loop_enabled and loop_mode == 'Number of Loops':
                self.countdownLabel.setText(f"Remaining Loops: {self.remaining_loops}")
            elif loop_enabled and loop_mode == 'Total Duration (s)':
                time_left = max(0, int(self.end_time - time.time()))
                self.countdownLabel.setText(f"Time Left: {time_left}s")
                if time_left <= 0:
                    break

            # Use start_row for the first loop only; reset it to 0 afterward
            i = self.start_row if first_loop else 0

            total_events = self.table.rowCount()
            while i < total_events and self.playback_active:
                # Clear previous row highlight to prevent overlap
                for row in range(total_events):
                    for j in range(self.table.columnCount()):
                        self.table.item(row, j).setBackground(QColor('white'))

                # Highlight current row
                for j in range(self.table.columnCount()):
                    self.table.item(i, j).setBackground(QColor('lightblue'))

                # Scroll to the highlighted item
                self.table.scrollToItem(self.table.item(i, 0), QTableWidget.PositionAtCenter)
                QApplication.processEvents()  # Ensure UI updates to show the highlighted row

                # Skip flag rows (identified by "Flag:" text)
                if self.table.item(i, 0) and "Flag:" in self.table.item(i, 0).text():
                    i += 1
                    continue

                # Execute the action on the current row
                event_type = self.table.item(i, 0).text()
                action = self.table.item(i, 1).text()
                x_text = self.table.item(i, 2).text()
                y_text = self.table.item(i, 3).text()
                button_key = self.table.item(i, 4).text()
                delay_text = self.table.item(i, 5).text()

                try:
                    delay = float(delay_text)
                except ValueError:
                    delay = 0  # Default to no delay if invalid
                time.sleep(delay)

                # Perform the mouse or key action
                if event_type == 'Mouse':
                    if x_text and y_text:
                        try:
                            x = int(float(x_text))
                            y = int(float(y_text))
                        except ValueError:
                            x, y = pyautogui.position()
                    else:
                        x, y = pyautogui.position()
                    if action == 'press':
                        pyautogui.moveTo(x, y)
                        pyautogui.mouseDown(button=button_key)
                    elif action == 'release':
                        pyautogui.moveTo(x, y)
                        pyautogui.mouseUp(button=button_key)
                    elif action == 'click':
                        pyautogui.moveTo(x, y)
                        pyautogui.click(button=button_key)
                elif event_type == 'Key':
                    key = button_key
                    if action == 'press':
                        pyautogui.keyDown(key)
                    elif action == 'release':
                        pyautogui.keyUp(key)
                    elif action == 'click':
                        pyautogui.press(key)

                # Wait briefly to give the UI time to reset before next action
                QApplication.processEvents()  # Refresh UI after each iteration
                time.sleep(0.05)  # Small delay to ensure visibility

                i += 1

            loops_completed += 1

            # Reset start_row to 0 after the first loop completes
            if first_loop:
                first_loop = False

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
        # Block signals to prevent recursive calls
        self.table.blockSignals(True)

        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem('Mouse'))
        self.table.setItem(row, 1, QTableWidgetItem('click'))
        self.table.setItem(row, 2, QTableWidgetItem('0'))
        self.table.setItem(row, 3, QTableWidgetItem('0'))
        self.table.setItem(row, 4, QTableWidgetItem('left'))
        self.table.setItem(row, 5, QTableWidgetItem('1.00'))

        # Unblock signals after modifications
        self.table.blockSignals(False)

        self.update_total_time_label()

    def deleteClick(self):
        currentRow = self.table.currentRow()
        if currentRow > -1:
            # Block signals to prevent recursive calls
            self.table.blockSignals(True)

            self.table.removeRow(currentRow)

            # Unblock signals after modifications
            self.table.blockSignals(False)

            self.update_total_time_label()

    def clearEvents(self):
        # Block signals to prevent recursive calls
        self.table.blockSignals(True)

        self.table.setRowCount(0)
        self.statusBar.showMessage('Events cleared')

        # Unblock signals after modifications
        self.table.blockSignals(False)

        self.update_total_time_label()

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

                # Block signals to prevent recursive calls
                self.table.blockSignals(True)

                self.table.setItem(currentRow, 0, QTableWidgetItem(event_type))
                self.table.setItem(currentRow, 1, QTableWidgetItem(action))
                self.table.setItem(currentRow, 2, QTableWidgetItem(x))
                self.table.setItem(currentRow, 3, QTableWidgetItem(y))
                self.table.setItem(currentRow, 4, QTableWidgetItem(button_key))
                self.table.setItem(currentRow, 5, QTableWidgetItem(delay))

                # Unblock signals after modifications
                self.table.blockSignals(False)

                self.update_total_time_label()

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
            try:
                with open(fileName, 'w') as file:
                    json.dump(clicks, file, indent=4)
                self.statusBar.showMessage('Events saved')
            except Exception as e:
                QMessageBox.critical(self, 'Error', f'Failed to save events: {str(e)}')

    def loadClicks(self):
        options = QFileDialog.Options()
        fileName, _ = QFileDialog.getOpenFileName(
            self, "Load Events", "", "JSON Files (*.json);;All Files (*)", options=options
        )
        if fileName:
            try:
                with open(fileName, 'r') as file:
                    clicks = json.load(file)
                    self.table.setRowCount(0)  # Clear the table before loading new clicks

                    # Block signals to prevent recursive calls
                    self.table.blockSignals(True)

                    for click in clicks:
                        # Validate click data
                        event_type = click.get('type', 'Mouse')
                        action = click.get('action', 'click')
                        x = click.get('x', '0')
                        y = click.get('y', '0')
                        button_key = click.get('button_key', 'left')
                        delay = click.get('delay', '0.00')

                        # Validate numerical values
                        try:
                            x = float(x)
                        except ValueError:
                            x = 0.0
                        try:
                            y = float(y)
                        except ValueError:
                            y = 0.0
                        try:
                            delay = float(delay)
                        except ValueError:
                            delay = 0.0

                        row = self.table.rowCount()
                        self.table.insertRow(row)
                        self.table.setItem(row, 0, QTableWidgetItem(event_type))
                        self.table.setItem(row, 1, QTableWidgetItem(action))
                        self.table.setItem(row, 2, QTableWidgetItem(str(x)))
                        self.table.setItem(row, 3, QTableWidgetItem(str(y)))
                        self.table.setItem(row, 4, QTableWidgetItem(button_key))
                        self.table.setItem(row, 5, QTableWidgetItem(f"{delay:.4f}"))

                    # Unblock signals after modifications
                    self.table.blockSignals(False)

                self.statusBar.showMessage('Events loaded')
                self.update_total_time_label()
            except Exception as e:
                QMessageBox.critical(self, 'Error', f'Failed to load events: {str(e)}')
                # Ensure signals are unblocked even if an error occurs
                self.table.blockSignals(False)

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

    def on_table_item_changed(self, item):
        # Only read data; do not modify the table to avoid recursive calls
        self.update_total_time_label()

    def calculate_total_estimated_time(self):
        total_time = 0.0
        for i in range(self.table.rowCount()):
            delay_text = self.table.item(i, 5).text()
            try:
                delay = float(delay_text)
                total_time += delay
            except ValueError:
                pass  # Ignore invalid entries
        return total_time

    def updateReleaseCoords(self, item):
        # Check if the "Sync Coordinates" feature is enabled
        if not self.syncCoordsAction.isChecked():
            return  # Exit if synchronization is disabled

        row = item.row()
        col = item.column()

        # Check if the edited row is a "press" action and the edited column is a coordinate
        if self.table.item(row, 0).text() == "Mouse" and self.table.item(row, 1).text() == "press" and col in [2, 3]:
            # Get the updated coordinates
            x_text = self.table.item(row, 2).text()
            y_text = self.table.item(row, 3).text()

            # Find the corresponding "release" action in subsequent rows
            for i in range(row + 1, self.table.rowCount()):
                if self.table.item(i, 0).text() == "Mouse" and self.table.item(i, 1).text() == "release":
                    # Update the release action's coordinates
                    self.table.item(i, 2).setText(x_text)
                    self.table.item(i, 3).setText(y_text)
                    break  # Stop after finding the first matching release action

    def insertFlagRow(self):
        current_row = self.table.currentRow()
        insert_row = current_row + 1 if current_row != -1 else self.table.rowCount()

        # Insert the flag row
        self.table.insertRow(insert_row)

        flag_item = QTableWidgetItem("Flag: Description Here")
        flag_item.setFlags(flag_item.flags() & ~Qt.ItemIsEditable)
        flag_item.setForeground(QColor("green"))
        font = flag_item.font()
        font.setItalic(True)
        flag_item.setFont(font)

        self.table.setItem(insert_row, 0, flag_item)
        self.table.setSpan(insert_row, 0, 1, self.table.columnCount())

    def update_total_time_label(self):
        total_time = self.calculate_total_estimated_time()
        self.totalTimeLabel.setText(f"Total Estimated Time: {total_time:.2f}s")

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
    ex = AutoClickerApp()
    try:
        sys.exit(app.exec_())
    except Exception as e:
        print(f"An error occurred: {e}")
