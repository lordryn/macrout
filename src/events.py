import time
import random
import pyautogui
from pynput.keyboard import Key

# Safety: Fail-safe to stop mouse from going crazy.
pyautogui.FAILSAFE = True


class MacroEvent:
    def execute(self):
        raise NotImplementedError

    def to_dict(self):
        raise NotImplementedError

    @staticmethod
    def from_dict(data):
        if data['type'] == 'click':
            return ClickEvent(data['x'], data['y'], data['button'], data['delay'], data.get('variance', 0))
        elif data['type'] == 'mouse_down':
            return MousePressEvent(data['x'], data['y'], data['button'], data['delay'])
        elif data['type'] == 'mouse_up':
            return MouseReleaseEvent(data['x'], data['y'], data['button'], data['delay'])
        elif data['type'] == 'key':
            return KeyEvent(data['key_code'], data['action'], data['delay'])
        elif data['type'] == 'wait':
            return WaitEvent(data['duration'])
        return None


# --- ATOMIC EVENTS (Press vs Release) ---

class MousePressEvent(MacroEvent):
    def __init__(self, x, y, button='left', delay=0.1):
        self.x = int(x)
        self.y = int(y)
        self.button = button
        self.delay = float(delay)

    def execute(self):
        # FIX: Sleep BEFORE action to preserve timing gaps
        if self.delay > 0: time.sleep(self.delay)

        pyautogui.moveTo(self.x, self.y)
        pyautogui.mouseDown(button=self.button)

    def to_dict(self):
        return {'type': 'mouse_down', 'x': self.x, 'y': self.y, 'button': self.button, 'delay': self.delay}

    def __str__(self):
        return f"Mouse DOWN ({self.button})"


class MouseReleaseEvent(MacroEvent):
    def __init__(self, x, y, button='left', delay=0.1):
        self.x = int(x)
        self.y = int(y)
        self.button = button
        self.delay = float(delay)

    def execute(self):
        # FIX: Sleep BEFORE action (crucial for holding buttons down)
        if self.delay > 0: time.sleep(self.delay)

        pyautogui.moveTo(self.x, self.y)
        pyautogui.mouseUp(button=self.button)

    def to_dict(self):
        return {'type': 'mouse_up', 'x': self.x, 'y': self.y, 'button': self.button, 'delay': self.delay}

    def __str__(self):
        return f"Mouse UP ({self.button})"


# --- LEGACY / COMPOSITE EVENTS ---

class ClickEvent(MacroEvent):
    def __init__(self, x, y, button='left', delay=0.1, variance=0):
        self.x = int(x)
        self.y = int(y)
        self.button = button
        self.delay = float(delay)
        self.variance = int(variance)

    def execute(self):
        # FIX: Sleep BEFORE action
        if self.delay > 0: time.sleep(self.delay)

        tx, ty = self.x, self.y
        if self.variance > 0:
            tx += random.randint(-self.variance, self.variance)
            ty += random.randint(-self.variance, self.variance)
        pyautogui.click(x=tx, y=ty, button=self.button)

    def to_dict(self):
        return {'type': 'click', 'x': self.x, 'y': self.y, 'button': self.button, 'delay': self.delay,
                'variance': self.variance}

    def __str__(self):
        return f"Click {self.button.upper()} (Atomic)"


class KeyEvent(MacroEvent):
    def __init__(self, key_code, action='press', delay=0.1):
        self.key_code = key_code
        self.action = action
        self.delay = float(delay)

    def execute(self):
        # FIX: Sleep BEFORE action
        if self.delay > 0: time.sleep(self.delay)

        if self.action == 'press':
            pyautogui.keyDown(self.key_code)
        elif self.action == 'release':
            pyautogui.keyUp(self.key_code)

    def to_dict(self):
        return {'type': 'key', 'key_code': str(self.key_code), 'action': self.action, 'delay': self.delay}

    def __str__(self):
        return f"Key {self.action.upper()}: {self.key_code}"


class WaitEvent(MacroEvent):
    def __init__(self, duration):
        self.duration = float(duration)

    def execute(self):
        time.sleep(self.duration)

    def to_dict(self):
        return {'type': 'wait', 'duration': self.duration}

    def __str__(self):
        return f"Wait {self.duration}s"