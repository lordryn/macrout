# AutoClicker Application

An advanced auto-clicker application that records and plays back mouse and keyboard events. This application allows users to automate repetitive tasks by capturing input events and replaying them with precision. It features a modern user interface, looping capabilities, statistics display, and customizable hotkeys.

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
  - [Recording Events](#recording-events)
  - [Playback Events](#playback-events)
  - [Looping Options](#looping-options)
  - [Managing Events](#managing-events)
  - [Hotkeys](#hotkeys)
  - [Saving and Loading Events](#saving-and-loading-events)
- [User Interface Overview](#user-interface-overview)
- [Important Notes](#important-notes)
- [Dependencies](#dependencies)
- [License](#license)

## Features

- **Record Mouse and Keyboard Events:**
  - Capture mouse clicks, movements, and keyboard presses/releases.
  - Option to include or exclude keyboard events.

- **Playback Events:**
  - Replay recorded events accurately.
  - Supports both mouse and keyboard event playback.

- **Looping Capabilities:**
  - Loop playback based on a set number of loops.
  - Loop playback for a specified total duration.
  - Real-time countdown display for loops or remaining time.

- **Modern User Interface:**
  - Uses PyQt5 for a sleek and modern GUI.
  - Toolbar with essential actions for easy access.
  - Menu bar with file and settings options.
  - Status bar for displaying messages and statistics.

- **Hotkeys:**
  - Global hotkeys to start/stop recording and playback.
  - Customizable hotkeys to suit user preferences.

- **Event Management:**
  - Add, edit, and delete individual events.
  - Clear all events from the event list.
  - Save and load event sequences to/from JSON files.

- **Statistics Display:**
  - Shows total runtime, loops completed, and average loop time after playback.
  - Provides feedback during playback through the status bar.

## Installation

1. **Clone the Repository:**

   ```bash
   git clone https://github.com/yourusername/autoclicker.git
   cd autoclicker
