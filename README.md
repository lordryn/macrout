# Macrout 2.0: The Automation IDE

Macrout is a powerful, open-source automation tool designed to be more than just a "tape recorder" for your mouse. It is an **Automation Non-Linear Editor (NLE)** that treats input events as editable objects, allowing for precise tuning, logic adjustment, and robust playback.

Built with **Python** and **PyQt5**, Macrout 2.0 introduces a fully Object-Oriented backend, separating the recording logic from the playback engine for maximum stability and extensibility.

---

## ✨ Key Features

### 🧠 Intelligent Event Engine

Unlike basic clickers that play back a flat recording, Macrout treats every action as a discrete object.

- **Atomic Precision**  
  Clicks are split into `MouseDown` and `MouseUp` events, allowing hold durations to be tuned down to the millisecond.

- **Smart Delete**  
  Automatically detects and removes paired events. Deleting a "Press" can also remove the matching "Release" to prevent stuck keys.

---

### 👁️ Visual Execution Tracking

- **Live Highlighting**  
  The UI highlights the exact line of execution in real time, making complex loops easy to debug.

- **Live Dashboard**  
  Real-time tracking of mouse coordinates, loop counts, and estimated total runtime.

---

### 🛠️ Editor Tools

- **Sync Coordinates**  
  Editing the X/Y position of a `MouseDown` event automatically updates the matching `MouseUp` event further down the timeline.

- **Humanization (Variance)**  
  Built-in jitter support adds random pixel offsets to clicks to simulate human behavior and reduce bot detection.

- **Global Hotkeys**  
  Start/Stop recording and playback from any application using customizable keyboard shortcuts.

---

## 📦 Installation

### 1. Clone the Repository

```bash
git clone https://github.com/lordryn/macrout.git
cd macrout
```

### 2. Install Dependencies

Macrout relies on `pynput` for low-level input hooks and `PyQt5` for the graphical interface.

```bash
pip install -r requirements.txt
```

### 3. Run the Application

```bash
python main.py
```

---

## 🎮 Usage Guide

### 1. Recording

1. Click **Record** or press `<Ctrl> + <Alt> + R`.
2. Perform your actions. Macrout captures mouse presses/releases and keystrokes.
3. Press the hotkey again to stop recording.

---

### 2. Editing

- **Modify Events**  
  Double-click any cell in the table to edit coordinates, delays, or variance values.

- **Sync Mode**  
  Ensure **Sync Coordinates** is enabled in the Settings menu. Editing a mouse press position will automatically update the corresponding release.

- **Delete**  
  Select one or more rows and click **Delete**. With **Smart Delete** enabled, paired events are removed together.

---

### 3. Playback

1. Set the number of **Loops** (`0` for infinite).
2. Click **Play** or press `<Ctrl> + <Alt> + P`.
3. The table locks and visually tracks execution.
4. Move the mouse to the **top-left corner of the screen** to trigger the fail-safe emergency stop.

---

## 🗺️ Roadmap & Vision

Macrout 2.0 is the foundation for a broader vision of **"Automation as Code."** Planned future enhancements include:

- **🏷️ Event Tagging**  
  Rename events (e.g., "Click Left" → "Open Inventory") for readability and maintainability.

- **📸 Visual Thumbnails**  
  Capture small screenshots around the cursor during recording to display as event thumbnails.

- **🖱️ Context Menus**  
  Right-click actions such as *Duplicate Row*, *Randomize Delay*, or *Insert Wait*.

- **⇄ Drag & Drop**  
  Full drag-and-drop timeline reordering (currently experimental).

