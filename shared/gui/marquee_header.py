"""Table header that scrolls text when column is too narrow."""

from __future__ import annotations

from PySide6.QtCore import QRect, Qt, QTimer
from PySide6.QtGui import QFontMetrics, QPainter
from PySide6.QtWidgets import QHeaderView, QWidget


class MarqueeHeaderView(QHeaderView):
    """QHeaderView that animates overflowing section text like a ticker."""

    _TICK_MS = 50
    _PAUSE_TICKS = 40
    _PAD = 16

    def __init__(self, orientation: Qt.Orientation, parent: QWidget | None = None) -> None:
        super().__init__(orientation, parent)
        self._offsets: dict[int, int] = {}
        self._pauses: dict[int, int] = {}
        self._active: set[int] = set()
        self._timer = QTimer(self)
        self._timer.setInterval(self._TICK_MS)
        self._timer.timeout.connect(self._tick)

    def paintSection(self, painter: QPainter, rect: QRect, logical_index: int) -> None:
        text = self.model().headerData(logical_index, self.orientation(), Qt.ItemDataRole.DisplayRole)
        if not text:
            super().paintSection(painter, rect, logical_index)
            return

        fm = QFontMetrics(self.font())
        text_w = fm.horizontalAdvance(str(text))
        avail = rect.width() - self._PAD

        if text_w <= avail:
            super().paintSection(painter, rect, logical_index)
            self._active.discard(logical_index)
            return

        self._active.add(logical_index)
        if not self._timer.isActive():
            self._timer.start()

        painter.save()
        painter.setClipRect(rect)

        # Draw header background via style
        opt = self._section_style_option(logical_index, rect)
        self.style().drawControl(self.style().ControlElement.CE_Header, opt, painter, self)

        offset = self._offsets.get(logical_index, 0)
        text_rect = QRect(rect.left() + self._PAD // 2 - offset, rect.top(), text_w + self._PAD, rect.height())
        painter.setPen(painter.pen())
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, str(text))
        painter.restore()

    def _section_style_option(self, index: int, rect: QRect):
        from PySide6.QtWidgets import QStyleOptionHeader

        opt = QStyleOptionHeader()
        self.initStyleOption(opt)
        opt.section = index
        opt.rect = rect
        opt.text = ""
        return opt

    def _tick(self) -> None:
        model = self.model()
        if model is None:
            return
        stale = set()
        for section in list(self._active):
            pause = self._pauses.get(section, 0)
            if pause > 0:
                self._pauses[section] = pause - 1
                continue
            text = model.headerData(section, self.orientation(), Qt.ItemDataRole.DisplayRole)
            if not text:
                stale.add(section)
                continue
            fm = QFontMetrics(self.font())
            text_w = fm.horizontalAdvance(str(text))
            avail = self.sectionSize(section) - self._PAD
            if text_w <= avail:
                stale.add(section)
                continue
            offset = self._offsets.get(section, 0) + 1
            if offset > text_w - avail + self._PAD:
                offset = 0
                self._pauses[section] = self._PAUSE_TICKS
            self._offsets[section] = offset
        self._active -= stale
        for s in stale:
            self._offsets.pop(s, None)
            self._pauses.pop(s, None)
        if not self._active:
            self._timer.stop()
        self.viewport().update()
