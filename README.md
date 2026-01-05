# Macrout 2.1: The Automation IDE

Macrout is a powerful, open-source automation tool designed to be more than just a "tape recorder" for your mouse. It is an **Automation Non-Linear Editor (NLE)** that treats input events as editable objects, allowing for precise tuning, logic adjustment, and robust playback.

Built with **Python** and **PyQt5**, Macrout 2.1 features a modular Object-Oriented architecture, separating the recording logic from the playback engine for maximum stability.

---

## ✨ New in v2.1

### 📑 Organization Flags

Long macros are hard to read. Macrout 2.1 introduces **Flags**—non-executable comment rows that span the entire table. Use them to label sections of your macro (e.g., *"--- BOSS PHASE ---"* or *"--- INVENTORY SORT ---"*).

### 🖱️ Safe Drag & Drop

Reordering events is now safer and more precise. Dragging rows triggers a context menu asking whether to **Insert Above** or **Insert Below** the target, preventing accidental overwrites or UI glitches common in standard list widgets.

### 📋 Context Power Tools

A robust right-click menu provides full IDE-like control:

* **Cut / Copy / Paste** – Move events reliably between sections.
* **Duplicate** – Quickly clone complex event chains.
* **Insert Wait** – Manually add pause events without recording them.

---

## 🔑 Core Features

### 🧠 Intelligent Event Engine

Unlike basic clickers that play back a flat recording, Macrout treats every action as a discrete object.

* **Atomic Precision**
  Clicks are split into `MouseDown` and `MouseUp` events, allowing hold durations to be tuned down to the millisecond.

* **Smart Delete**
  Deleting a `Press` event automatically detects and removes the matching `Release` to prevent stuck keys.

---

### 👁️ Visual Execution Tracking

* **Live Highlighting**
  The UI highlights the exact line of execution in real time, functioning as a visual debugger.

* **Live Dashboard**
  Real-time tracking of mouse coordinates, loop counts, and estimated total runtime.

---

### 🛠️ Editor Tools

* **Sync Coordinates**
  Editing the X/Y position of a `MouseDown` automatically updates the matching `MouseUp`.

* **Humanization (Variance)**
  Built-in jitter support adds random pixel offsets to clicks to simulate human behavior.

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

### 2. Editing & Organizing

* **Reorder**
  Drag rows to a new position and select **Insert Above** or **Insert Below** from the popup menu.

* **Add Comments (Flags)**
  Right-click and select **Insert Flag**. The row turns green; type your note in the first column.

* **Modify**
  Double-click any editable cell (coordinates, delay, variance) to make changes. The **Type** column is locked for safety on standard events.

---

### 3. Playback

1. Set the number of **Loops** (`0` for infinite).
2. Click **Play** or press `<Ctrl> + <Alt> + P`.
3. The interface locks to prevent editing during execution.
4. **Emergency Stop:** Move the mouse to the top-left corner of the screen to trigger the fail-safe.

---

## 🗺️ Roadmap

Macrout is evolving from a script into a platform. Planned enhancements include:

* **📸 Visual Thumbnails**
  Capture small screenshots around the cursor during recording to display as event thumbnails.

* **💾 Project Files**
  Save and load macros with relative paths and metadata descriptions.

* **🖼️ Image Recognition**
  Conditional logic such as *"Wait until Image X appears on screen"*.
