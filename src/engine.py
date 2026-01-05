import threading
import time
from pynput import mouse, keyboard
from src.events import ClickEvent, KeyEvent, WaitEvent, MousePressEvent, MouseReleaseEvent
from PyQt5.QtGui import QColor
import threading
import time
from pynput import mouse, keyboard
from src.events import (
    ClickEvent, KeyEvent, WaitEvent,
    MousePressEvent, MouseReleaseEvent
)


class MacroRecorder:
    def __init__(self):
        self.mouse_listener = None
        self.key_listener = None
        self.recorded_events = []
        self.last_time = 0
        self.capture_keys = True

    def start(self, capture_keys=True):
        """Start listening. capture_keys determines if we record keyboard."""
        self.recorded_events = []
        self.last_time = time.time()
        self.capture_keys = capture_keys

        # Start Listeners
        self.mouse_listener = mouse.Listener(on_click=self._on_click)
        self.mouse_listener.start()

        if self.capture_keys:
            self.key_listener = keyboard.Listener(on_press=self._on_press, on_release=self._on_release)
            self.key_listener.start()

    def stop(self):
        if self.mouse_listener:
            self.mouse_listener.stop()
            self.mouse_listener = None

        if self.key_listener:
            self.key_listener.stop()
            self.key_listener = None

        return self.recorded_events

    def _get_delay(self):
        now = time.time()
        delay = now - self.last_time
        self.last_time = now
        return max(0, delay)

    def _on_click(self, x, y, button, pressed):
        delay = self._get_delay()
        btn_str = str(button).split('.')[-1]

        if pressed:
            # Create a PRESS event
            event = MousePressEvent(x, y, btn_str, delay=delay)
            self.recorded_events.append(event)
        else:
            # Create a RELEASE event
            event = MouseReleaseEvent(x, y, btn_str, delay=delay)
            self.recorded_events.append(event)

    def _on_press(self, key):
        if not self.capture_keys: return
        delay = self._get_delay()
        key_str = self._format_key(key)
        self.recorded_events.append(KeyEvent(key_str, 'press', delay))

    def _on_release(self, key):
        if not self.capture_keys: return
        delay = self._get_delay()
        key_str = self._format_key(key)
        self.recorded_events.append(KeyEvent(key_str, 'release', delay))

    def _format_key(self, key):
        try:
            return key.char
        except AttributeError:
            return str(key).split('.')[-1]

    def _highlight_active_row(self):
        """Highlights the row currently being executed by the engine."""
        idx = self.engine.current_event_index

        # Optimization: Don't redraw if the index hasn't changed
        if hasattr(self, '_last_highlighted_idx') and self._last_highlighted_idx == idx:
            return

        # 1. Clear previous highlight
        if hasattr(self, '_last_highlighted_idx') and self._last_highlighted_idx >= 0:
            # Check if row still exists (in case of weird edge cases)
            if self._last_highlighted_idx < self.table.rowCount():
                for col in range(self.table.columnCount()):
                    item = self.table.item(self._last_highlighted_idx, col)
                    if item: item.setBackground(QColor(0, 0, 0, 0))  # Transparent/Reset

        # 2. Apply new highlight (Light Blue)
        if idx >= 0 and idx < self.table.rowCount():
            for col in range(self.table.columnCount()):
                item = self.table.item(idx, col)
                if item: item.setBackground(QColor(173, 216, 230))  # Cyan-ish blue

            # Auto-scroll to keep the active row in view
            self.table.scrollToItem(self.table.item(idx, 0))

        self._last_highlighted_idx = idx

class MacroEngine:
    def __init__(self):
        self.events = []
        self.recorder = MacroRecorder()
        self.is_playing = False
        self.playback_thread = None
        self._stop_signal = threading.Event()

        # Track where we are for UI highlighting
        self.current_event_index = -1
        self.current_loop_index = 0

    def calculate_duration(self):
        total = 0.0
        for e in self.events:
            total += getattr(e, 'delay', 0)
        return total

    # --- Management ---
    def add_event(self, event):
        self.events.append(event)

    def clear_events(self):
        self.events = []
        self.current_event_index = -1

    def load_events(self, event_list):
        self.events = event_list

    # --- Recording ---
    def start_recording(self, capture_keys=True):
        self.recorder.start(capture_keys=capture_keys)

    def stop_recording(self):
        new_events = self.recorder.stop()
        self.events.extend(new_events)
        return len(new_events)

    # --- Playback ---
    def start_playback(self, loops=1):
        if self.is_playing: return
        self.is_playing = True
        self._stop_signal.clear()
        self.playback_thread = threading.Thread(target=self._playback_worker, args=(loops,), daemon=True)
        self.playback_thread.start()

    def stop_playback(self):
        self.is_playing = False
        self._stop_signal.set()

    def _playback_worker(self, loops):
        self.current_loop_index = 0

        while self.current_loop_index < loops or loops == 0:
            if self._stop_signal.is_set(): break

            # Reset index at start of loop
            self.current_event_index = -1

            for idx, event in enumerate(self.events):
                if self._stop_signal.is_set(): break

                # UPDATE INDEX FOR UI
                self.current_event_index = idx

                try:
                    event.execute()
                except Exception as e:
                    print(f"Error executing event: {e}")

            self.current_loop_index += 1
            time.sleep(0.01)  # Tiny sleep to prevent CPU hogging between loops

        self.is_playing = False
        self.current_event_index = -1  # Reset when done
