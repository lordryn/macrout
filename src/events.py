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
            return ClickEvent(data['x'], data['y'], data['button'], data['delay'], data.get('variance', 0), data.get('delay_variance', 0.0))
        elif data['type'] == 'mouse_down':
            return MousePressEvent(data['x'], data['y'], data['button'], data['delay'], data.get('delay_variance', 0.0))
        elif data['type'] == 'mouse_up':
            return MouseReleaseEvent(data['x'], data['y'], data['button'], data['delay'], data.get('delay_variance', 0.0))
        elif data['type'] == 'key':
            return KeyEvent(data['key_code'], data['action'], data['delay'], data.get('delay_variance', 0.0))
        elif data['type'] == 'wait':
            return WaitEvent(data['duration'], data.get('delay_variance', 0.0))
        # --- NEW FLAG TYPE ---
        elif data['type'] == 'flag':
            return FlagEvent(data['text'])
        return None

# --- ATOMIC EVENTS ---

class MousePressEvent(MacroEvent):
    def __init__(self, x, y, button='left', delay=0.1, delay_variance=0.0):
        self.x = int(x)
        self.y = int(y)
        self.button = button
        self.delay = float(delay)
        self.delay_variance = float(delay_variance)

    def execute(self):
        actual_delay = self.delay
        if getattr(self, 'delay_variance', 0) > 0: actual_delay = max(0, self.delay + random.uniform(-self.delay_variance, self.delay_variance))
        if actual_delay > 0: time.sleep(actual_delay)
        pyautogui.moveTo(self.x, self.y)
        pyautogui.mouseDown(button=self.button)

    def to_dict(self):
        return {'type': 'mouse_down', 'x': self.x, 'y': self.y, 'button': self.button, 'delay': self.delay, 'delay_variance': self.delay_variance}

class MouseReleaseEvent(MacroEvent):
    def __init__(self, x, y, button='left', delay=0.1, delay_variance=0.0):
        self.x = int(x)
        self.y = int(y)
        self.button = button
        self.delay = float(delay)
        self.delay_variance = float(delay_variance)

    def execute(self):
        actual_delay = self.delay
        if getattr(self, 'delay_variance', 0) > 0: actual_delay = max(0, self.delay + random.uniform(-self.delay_variance, self.delay_variance))
        if actual_delay > 0: time.sleep(actual_delay)
        pyautogui.moveTo(self.x, self.y)
        pyautogui.mouseUp(button=self.button)

    def to_dict(self):
        return {'type': 'mouse_up', 'x': self.x, 'y': self.y, 'button': self.button, 'delay': self.delay, 'delay_variance': self.delay_variance}

# --- LEGACY / COMPOSITE EVENTS ---

class ClickEvent(MacroEvent):
    def __init__(self, x, y, button='left', delay=0.1, variance=0, delay_variance=0.0):
        self.x = int(x)
        self.y = int(y)
        self.button = button
        self.delay = float(delay)
        self.variance = int(variance)
        self.delay_variance = float(delay_variance)

    def execute(self):
        actual_delay = self.delay
        if getattr(self, 'delay_variance', 0) > 0: actual_delay = max(0, self.delay + random.uniform(-self.delay_variance, self.delay_variance))
        if actual_delay > 0: time.sleep(actual_delay)
        tx, ty = self.x, self.y
        if self.variance > 0:
            tx += random.randint(-self.variance, self.variance)
            ty += random.randint(-self.variance, self.variance)
        pyautogui.click(x=tx, y=ty, button=self.button)

    def to_dict(self):
        return {'type': 'click', 'x': self.x, 'y': self.y, 'button': self.button, 'delay': self.delay, 'variance': self.variance, 'delay_variance': self.delay_variance}

class KeyEvent(MacroEvent):
    def __init__(self, key_code, action='press', delay=0.1, delay_variance=0.0):
        self.key_code = key_code
        self.action = action
        self.delay = float(delay)
        self.delay_variance = float(delay_variance)

    def execute(self):
        actual_delay = self.delay
        if getattr(self, 'delay_variance', 0) > 0: actual_delay = max(0, self.delay + random.uniform(-self.delay_variance, self.delay_variance))
        if actual_delay > 0: time.sleep(actual_delay)
        if self.action == 'press': pyautogui.keyDown(self.key_code)
        elif self.action == 'release': pyautogui.keyUp(self.key_code)

    def to_dict(self):
        return {'type': 'key', 'key_code': str(self.key_code), 'action': self.action, 'delay': self.delay, 'delay_variance': self.delay_variance}

class WaitEvent(MacroEvent):
    def __init__(self, duration, delay_variance=0.0):
        self.duration = float(duration)
        self.delay_variance = float(delay_variance)

    @property
    def delay(self):
        return self.duration

    @delay.setter
    def delay(self, value):
        self.duration = value

    def execute(self):
        actual_delay = self.duration
        if getattr(self, 'delay_variance', 0) > 0: actual_delay = max(0, self.duration + random.uniform(-self.delay_variance, self.delay_variance))
        if actual_delay > 0: time.sleep(actual_delay)

    def to_dict(self):
        return {'type': 'wait', 'duration': self.duration, 'delay_variance': self.delay_variance}

# --- NEW: FLAG EVENT ---
class FlagEvent(MacroEvent):
    def __init__(self, text="--- Comment ---"):
        self.text = text
    def execute(self):
        pass # Do nothing
    def to_dict(self):
        return {'type': 'flag', 'text': self.text}