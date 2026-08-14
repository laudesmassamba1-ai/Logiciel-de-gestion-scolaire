import math

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont, QPainter, QPen
from PyQt5.QtWidgets import QSizePolicy, QWidget


CHART_COLORS = [
    "#047857", "#2563eb", "#d97706", "#dc2626",
    "#8b5cf6", "#ec4899", "#0891b2", "#65a30d",
]

def _color(i):
    return QColor(CHART_COLORS[i % len(CHART_COLORS)])


def fmt_money(montant) -> str:
    try:
        return f"{float(montant):,.0f}".replace(",", " ") + " FCFA"
    except (TypeError, ValueError):
        return "0 FCFA"


def fmt_money_short(montant) -> str:
    return fmt_money(montant).replace(" FCFA", "")


class _BaseChart(QWidget):

    def __init__(self, parent=None, titre=""):
        super().__init__(parent)
        self.titre = titre
        self.labels = []
        self.values = []
        self.setMinimumHeight(200)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_data(self, labels, values, titre=None):

        self.labels = list(labels)
        self.values = [float(v) if v is not None else 0.0 for v in values]
        if titre:
            self.titre = titre
        self.update()

    def set_titre(self, titre):
        self.titre = titre
        self.update()

    def _draw_titre(self, painter, h):
        if not self.titre:
            return 0
        painter.setPen(QColor("#0f172a"))
        font = QFont()
        font.setPointSize(10)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(6, 4, self.width() - 12, 26, Qt.AlignLeft, self.titre)
        return 26

    def _draw_empty(self, painter, y, hauteur):
        painter.setPen(QColor("#94a3b8"))
        font = QFont()
        font.setPointSize(9)
        painter.setFont(font)
        painter.drawText(6, y, self.width() - 12, hauteur,
                         Qt.AlignCenter, "Aucune donnee a afficher")


class SimpleBarChart(_BaseChart):

    def __init__(self, parent=None, titre=""):
        super().__init__(parent, titre)
        self.setMinimumHeight(180)

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        y0 = self._draw_titre(painter, h)

        if not self.labels or not self.values or max(self.values) <= 0:
            self._draw_empty(painter, y0, max(h - y0, 60))
            painter.end()
            return

        max_val = max(self.values) or 1
        n = len(self.labels)
        pad = 10
        chart_top = y0 + 20
        chart_bottom = h - 26
        chart_h = chart_bottom - chart_top
        if chart_h < 40:
            chart_h = 40
        bar_w = max(6.0, (w - pad * 2) / n * 0.55)
        gap = (w - pad * 2) / n


        for i, (label, value) in enumerate(zip(self.labels, self.values)):
            x = pad + i * gap + (gap - bar_w) / 2
            bar_h = (value / max_val) * (chart_h - 10)
            y = chart_top + (chart_h - 10) - bar_h
            painter.setBrush(_color(i))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(int(x), int(y), int(bar_w), int(bar_h), 4, 4)
            painter.setPen(QColor("#475569"))
            font = QFont()
            font.setPointSize(8)
            painter.setFont(font)
            painter.drawText(int(x) - 4, int(y) - 12, int(bar_w) + 8, 14,
                             Qt.AlignHCenter, f"{value:,.0f}".replace(",", " "))
            painter.drawText(int(x) - 4, chart_bottom + 2, int(bar_w) + 8, 18,
                             Qt.AlignHCenter, str(label))
        painter.end()


class SimplePieChart(_BaseChart):

    def __init__(self, parent=None, titre=""):
        super().__init__(parent, titre)
        self.setMinimumHeight(200)

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        y0 = self._draw_titre(painter, h)

        if not self.labels or not self.values or sum(self.values) <= 0:
            self._draw_empty(painter, y0, max(h - y0, 60))
            painter.end()
            return

        total = sum(self.values)
        legend_w = int(w * 0.32)
        if legend_w < 120:
            legend_w = 120
        pie_area = w - legend_w - 8
        center_x = pie_area // 2
        center_y = y0 + (h - y0) // 2
        radius = min(pie_area, h - y0) // 2 - 12
        if radius < 10:
            radius = 10


        start_angle = 0
        for i, value in enumerate(self.values):
            span_angle = (value / total) * 360 * 16
            painter.setBrush(_color(i))
            painter.setPen(QPen(QColor("#ffffff"), 2))
            painter.drawPie(center_x - radius, center_y - radius,
                            radius * 2, radius * 2,
                            int(start_angle), int(span_angle))
            start_angle += span_angle

        font = QFont()
        font.setPointSize(8)
        painter.setFont(font)
        legend_x = pie_area + 8
        row_h = max(18, int((h - y0 - 8) / len(self.labels)) if len(self.labels) else 18)
        if row_h < 16:
            row_h = 16

        y = y0 + 6
        for i, (label, value) in enumerate(zip(self.labels, self.values)):
            pct = (value / total) * 100
            painter.setPen(Qt.NoPen)
            painter.setBrush(_color(i))
            painter.drawRoundedRect(int(legend_x), int(y) + 2, 10, 10, 2, 2)
            painter.setPen(QColor("#0f172a"))
            painter.drawText(int(legend_x) + 16, int(y) - 2,
                             max(int(legend_w) - 22, 40), 16,
                             Qt.AlignLeft | Qt.AlignVCenter,
                             f"{label}  ({pct:.0f}%)")
            y += row_h
        painter.end()
