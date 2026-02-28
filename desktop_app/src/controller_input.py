"""Xbox/PS controller input reader using pygame."""
import time
import pygame
from PySide6.QtCore import QThread, Signal


class ControllerInput(QThread):
    steering_changed = Signal(float)       # -1.0 to 1.0
    throttle_changed = Signal(float)       # 0.0 to 1.0
    brake_changed = Signal(float)          # 0.0 to 1.0
    controller_status = Signal(str)        # Status text for UI

    DEADZONE = 0.05
    POLL_RATE_HZ = 100

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = False

    def stop(self):
        self._running = False
        self.wait(2000)

    @staticmethod
    def _apply_deadzone(value: float, dz: float) -> float:
        if abs(value) < dz:
            return 0.0
        sign = 1.0 if value > 0 else -1.0
        return sign * (abs(value) - dz) / (1.0 - dz)

    def run(self):
        self._running = True
        pygame.init()
        pygame.joystick.init()

        joystick = None
        last_steering = 0.0

        while self._running:
            # --- Detect controller ---
            if joystick is None:
                pygame.joystick.quit()
                pygame.joystick.init()
                if pygame.joystick.get_count() > 0:
                    joystick = pygame.joystick.Joystick(0)
                    joystick.init()
                    name = joystick.get_name()
                    self.controller_status.emit(f"Controller: {name}")
                else:
                    self.controller_status.emit("No controller")
                    time.sleep(1.0)
                    continue

            try:
                pygame.event.pump()

                # Left stick X axis → steering
                raw_x = joystick.get_axis(0)
                steering = self._apply_deadzone(raw_x, self.DEADZONE)
                if abs(steering - last_steering) > 0.001:
                    last_steering = steering
                    self.steering_changed.emit(steering)

                # Triggers → throttle/brake (axis 4 = right trigger, axis 5 = left trigger on Xbox)
                # Triggers are typically -1 (released) to 1 (pressed)
                num_axes = joystick.get_numaxes()
                if num_axes > 5:
                    rt = (joystick.get_axis(5) + 1.0) / 2.0  # 0..1
                    lt = (joystick.get_axis(4) + 1.0) / 2.0
                    self.throttle_changed.emit(max(0.0, min(1.0, rt)))
                    self.brake_changed.emit(max(0.0, min(1.0, lt)))

            except pygame.error:
                joystick = None
                self.controller_status.emit("Controller lost")
                time.sleep(0.5)
                continue

            time.sleep(1.0 / self.POLL_RATE_HZ)

        pygame.joystick.quit()
        pygame.quit()
