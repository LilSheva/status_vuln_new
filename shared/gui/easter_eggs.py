"""Easter eggs for the vulnerability analyzer apps."""

from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, Qt, QTimer, Signal


class KonamiDetector(QObject):
    """Detects the Konami code key sequence and emits activated()."""

    activated = Signal()

    _SEQ = [
        Qt.Key.Key_Up, Qt.Key.Key_Up,
        Qt.Key.Key_Down, Qt.Key.Key_Down,
        Qt.Key.Key_Left, Qt.Key.Key_Right,
        Qt.Key.Key_Left, Qt.Key.Key_Right,
        Qt.Key.Key_B, Qt.Key.Key_A,
    ]

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._pos = 0

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.KeyPress:
            if event.key() == self._SEQ[self._pos]:
                self._pos += 1
                if self._pos == len(self._SEQ):
                    self._pos = 0
                    self.activated.emit()
            else:
                self._pos = 0
        return False


class TitleClickDetector(QObject):
    """Emits activated() after N fast clicks on the watched widget."""

    activated = Signal()

    def __init__(self, clicks: int = 7, timeout_ms: int = 2000, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._target = clicks
        self._count = 0
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(timeout_ms)
        self._timer.timeout.connect(self._reset)

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.MouseButtonPress:
            self._count += 1
            self._timer.start()
            if self._count >= self._target:
                self._count = 0
                self._timer.stop()
                self.activated.emit()
        return False

    def _reset(self) -> None:
        self._count = 0
