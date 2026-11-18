"""Pomodoro state machine: 25-minute focus / short break / long break."""
from __future__ import annotations
import time


class Pomodoro:
    FOCUS_SECONDS = 25 * 60
    SHORT_SECONDS = 5 * 60

    def __init__(self):
        self.mode = 'focus'
        self.total_focus = 0
        self.seconds_left = self.FOCUS_SECONDS
        self.running = False
        self._deadline = 0.0

    @property
    def round_number(self) -> int:
        return (self.total_focus % 4) + 1

    @property
    def cycles_completed(self) -> int:
        return self.total_focus // 4

    def start(self) -> None:
        if not self.running:
            self.running = True
            self._deadline = time.monotonic() + self.seconds_left

    def pause(self) -> None:
        if self.running:
            self.seconds_left = max(0, int(self._deadline - time.monotonic() + 0.999))
            self.running = False

    def reset(self) -> None:
        self.running = False
        self.mode = 'focus'
        self.seconds_left = self.FOCUS_SECONDS
        self.total_focus = 0

    def update(self) -> str | None:
        """Return the new session name on transition, else None.

        Uses elapsed monotonic time, so laptop sleeps and UI delays don't
        cause a stopped/slow timer.
        """
        if not self.running:
            return None
        remaining = self._deadline - time.monotonic()
        if remaining > 0:
            self.seconds_left = int(remaining + 0.999)
            return None
        if self.mode == 'focus':
            self.total_focus += 1
            if self.total_focus % 4 == 0:
                self.mode = 'long break'
                completed_cycles = self.cycles_completed
                self.seconds_left = min(30, 15 + (completed_cycles - 1) * 5) * 60
            else:
                self.mode = 'short break'
                self.seconds_left = self.SHORT_SECONDS
        else:
            self.mode = 'focus'
            self.seconds_left = self.FOCUS_SECONDS
        self._deadline = time.monotonic() + self.seconds_left
        return self.mode

    @property
    def formatted(self) -> str:
        mins, secs = divmod(self.seconds_left, 60)
        return f'{mins:02d}:{secs:02d}'
