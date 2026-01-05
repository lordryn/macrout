
# AutoClicker Application
An advanced auto-clicker application that records and plays back mouse and keyboard events. This application allows users to automate repetitive tasks by capturing input events and replaying them with precision. It features a modern user interface, looping capabilities, statistics display, and customizable hotkeys.

## Table of Contents
- Features
- Installation
- Usage
  - Recording Events
  - Playback Events
  - Looping Options
  - Managing Events
  - Hotkeys
  - Saving and Loading Events
  - User Interface Overview
- Important Notes
- Dependencies
- License

## Features
### Record Mouse and Keyboard Events:
- Capture mouse clicks, movements, and keyboard presses/releases.
- Option to include or exclude keyboard events.

### Playback Events:
- Replay recorded events accurately.
- Supports both mouse and keyboard event playback.

### Looping Capabilities:
- Loop playback based on a set number of loops.
- Loop playback for a specified total duration.
- Real-time countdown display for loops or remaining time.

### Modern User Interface:
- Uses PyQt5 for a sleek and modern GUI.
- Toolbar with essential actions for easy access.
- Menu bar with file and settings options.
- Status bar for displaying messages and statistics.

### Hotkeys:
- Global hotkeys to start/stop recording and playback.
- Customizable hotkeys to suit user preferences.

### Event Management:
- Add, edit, and delete individual events.
- Clear all events from the event list.
- Save and load event sequences to/from JSON files.

### Statistics Display:
- Shows total runtime, loops completed, and average loop time after playback.
- Provides feedback during playback through the status bar.

## Installation
### Clone the Repository:
```bash
git clone https://github.com/lordryn/macrout.git
cd autoclicker
```

### Install Dependencies:
Ensure you have Python 3.x installed. Install required packages using pip:
```bash
pip install pyautogui pynput PyQt5
```
Note: On some systems, you might need to use `pip3` instead of `pip`.

## Usage
### Run the application using the following command:
```bash
python autoclicker.py
```

### Recording Events
#### Start Recording:
- Click the Start Recording button on the toolbar or press the hotkey (Ctrl+Alt+R by default).
- The status bar will display "Recording started."

#### Perform Actions:
- Perform the mouse clicks, movements, and keyboard presses/releases you wish to record.
- If you want to record keyboard events, ensure the "Capture Keys" checkbox is checked.

#### Stop Recording:
- Click the Stop Recording button on the toolbar or press the hotkey again (Ctrl+Alt+R by default).
- The status bar will display "Recording stopped."
- Recorded events will appear in the event table.

### Playback Events
#### Configure Looping Options (Optional):
##### Enable Looping:
- Check the "Loop Playback" checkbox to enable looping.

##### Set Loop Mode:
- Choose between "Number of Loops" or "Total Duration (s)" from the dropdown menu.

##### Set Loop Count/Duration:
- Adjust the spin box to set the number of loops or total duration in seconds.

#### Start Playback:
- Click the Start Playback button on the toolbar or press the hotkey (Ctrl+Alt+P by default).
- The status bar will display "Playback started."
- The Countdown label will display remaining loops or time left during playback.

#### Stop Playback:
- Click the Stop Playback button on the toolbar or press the hotkey again (Ctrl+Alt+P by default).
- The status bar will display "Playback stopped."

#### After Playback:
- The status bar will display statistics:
  - Loops completed.
  - Total runtime.
  - Average loop time.

## Looping Options
### Loop Playback:
Enable this option to repeat the playback automatically.

### Number of Loops:
Select this option to loop playback a specific number of times. Set the desired number in the spin box.

### Total Duration (s):
Select this option to loop playback for a specific total duration. Set the duration in seconds in the spin box.

## Managing Events
### Add Event:
Click the Add Event button to insert a new event into the event table. The default event is a mouse click at position (0, 0) with a 1-second delay.

### Edit Event:
Select an event from the table. Click the Edit Event button to modify the event's properties. Update the event details in the dialog and click OK.

### Delete Event:
Select an event from the table. Click the Delete Event button to remove it from the list.

### Clear Events:
Click the Clear Events button on the toolbar to remove all events from the table. The status bar will display "Events cleared."

## Hotkeys
### Default Hotkeys:
- Start/Stop Recording: Ctrl+Alt+R
- Start/Stop Playback: Ctrl+Alt+P

### Set Custom Hotkeys:
- Go to Settings > Set Hotkeys from the menu bar.
- Enter new hotkey combinations in the dialog.
- Hotkeys should be in a format recognized by pynput (e.g., `<ctrl>+<alt>+r`).
- Click OK to apply changes. The status bar will display "Hotkeys updated."

## Saving and Loading Events
### Save Events:
- Go to File > Save from the menu bar.
- Choose a location and filename to save your events as a JSON file.
- The status bar will display "Events saved."

### Load Events:
- Go to File > Load from the menu bar.
- Select a JSON file containing saved events.
- The event table will populate with the loaded events.
- The status bar will display "Events loaded."

## User Interface Overview
### Toolbar:
Contains buttons for starting/stopping recording, starting/stopping playback, and clearing events. Essential actions are easily accessible.

### Menu Bar:
#### File Menu:
- Save and Load options for managing event files.
- Exit to close the application.

#### Settings Menu:
- Set Hotkeys to customize global hotkeys.

### Event Table:
Displays recorded events in a table format. Columns include Type, Action, X, Y, Button/Key, and Delay.

### Options Panel:
Contains checkboxes and buttons for additional settings.
- "Capture Keys" checkbox to enable/disable keyboard event recording.
- Buttons to add, edit, or delete events.

### Loop and Statistics Panel:
- "Loop Playback" checkbox to enable looping.
- Dropdown to select loop mode (Number of Loops or Total Duration (s)).
- Spin box to set loop count or duration.
- Countdown label to display remaining loops or time.

### Status Bar:
Displays messages and playback statistics.

### Mouse Position Label:
Shows the current mouse position in real-time.

## Important Notes
### Permissions:
On some operating systems, you may need to grant accessibility permissions for the application to control mouse and keyboard events.
For macOS, go to System Preferences > Security & Privacy > Accessibility and add your Python interpreter or application.

### Global Hotkeys:
Hotkeys are global and will work even when the application is not in focus. Choose hotkeys that are unlikely to interfere with other applications to avoid unintended actions.

### Testing:
Test the application in a safe environment to ensure it behaves as expected. Be cautious when automating inputs to prevent unintended actions.

### Performance:
Setting a very high number of loops or a long duration may impact system performance. Monitor resource usage during extensive playback loops.

### Thread Safety:
The application uses threading to prevent the GUI from freezing during playback. UI updates from threads are handled carefully to avoid crashes.

## Dependencies
### Python 3.x
### Required Packages:
- PyQt5: For the graphical user interface.
- pyautogui: To control mouse and keyboard events.
- pynput: To capture mouse and keyboard events and handle global hotkeys.

### Install Packages:
```bash
pip install pyautogui pynput PyQt5
```

## License
This project is released under the MIT License. You are free to use, modify, and distribute this software as per the terms of the license.
