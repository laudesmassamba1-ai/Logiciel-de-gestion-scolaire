import math

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont, QPainter, QPen
from PyQt5.QtWidgets import QSizePolicy, QWidget


from core.config import (
    C_ACCENT_VIOLET, C_BLUE, C_RED, C_WARNING, C_GREEN,
    C_BORDER_STRONG, C_TEXT_MUTED, C_TEXT_LIGHT, C_TEXT, C_CARD,
    C_EMPTY_STATE, lire_composant,
)

CHART_COLORS = [
    C_ACCENT_VIOLET, C_BLUE, C_GREEN, C_WARNING, C_RED,
    C_TEXT_LIGHT, C_BORDER_STRONG, C_TEXT_MUTED,
]

def _color(i):
    return QColor(CHART_COLORS[i % len(CHART_COLORS)])


def _font(point_size, bold=False):
    """QFont doux et antialiase (net y compris en petites tailles)."""
    f = QFont()
    f.setPointSize(point_size)
    f.setBold(bold)
    f.setStyleStrategy(QFont.PreferAntialias)
    return f


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
        # Composant themable "statistiques" : couleurs cibles des graphiques.
        self.comp_stat = lire_composant("statistiques")
        self.grille_col = QColor(self.comp_stat.get("grille", C_EMPTY_STATE))

    def _couleur(self, i, premiere=None):
        """Couleur de paletete; la 1ere est remplacable par le composant."""
        pal = CHART_COLORS[:]
        if premiere:
            pal[0] = premiere
        return QColor(pal[i % len(pal)])

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
        painter.setPen(QColor(C_TEXT))
        font = _font(10, bold=True)
        painter.setFont(font)
        painter.drawText(6, 4, self.width() - 12, 26, Qt.AlignLeft, self.titre)
        return 26

    def _draw_empty(self, painter, y, hauteur):
        painter.setPen(QColor(C_EMPTY_STATE))
        font = _font(9)
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

        if not self.labels or not self.values:
            self._draw_empty(painter, y0, max(h - y0, 60))
            painter.end()
            return

        min_val = min(0.0, min(self.values))
        max_val = max(self.values)
        if max_val < 0:
            max_val = 0.0
        span = max_val - min_val
        if span <= 0:
            span = 1.0
        n = len(self.labels)
        pad = 36
        chart_top = y0 + 26
        chart_bottom = h - 32
        chart_h = chart_bottom - chart_top
        if chart_h < 40:
            chart_h = 40
        bar_w = min(80.0, max(6.0, (w - pad * 2) / n * 0.55))
        gap = (w - pad * 2) / n
        zero_y = chart_top + (max_val / span) * chart_h

        font = _font(8)
        painter.setFont(font)
        fm = painter.fontMetrics()

        grid_steps = min(5, max(1, int(round(max_val / max(1, max_val / 5)))))
        for s in range(0, grid_steps + 1):
            gy = chart_bottom - (s / grid_steps) * chart_h
            painter.setPen(QPen(self.grille_col, 1, Qt.DashLine))
            painter.drawLine(pad - 4, int(gy), int(w - pad + 4), int(gy))
            val_label = f"{int(s / grid_steps * max_val):,}".replace(",", " ")
            painter.setPen(QColor(C_TEXT_MUTED))
            small_font = _font(7)
            painter.setFont(small_font)
            painter.drawText(2, int(gy) - 3, pad - 8, 14, Qt.AlignRight, val_label)
            painter.setFont(font)

        painter.setPen(QPen(self.grille_col, 1))
        painter.drawLine(pad - 4, int(chart_bottom), int(w - pad + 4), int(chart_bottom))

        for i, (label, value) in enumerate(zip(self.labels, self.values)):
            x = pad + i * gap + (gap - bar_w) / 2
            v = float(value)
            if v >= 0:
                bar_h = (v / span) * chart_h
                y = zero_y - bar_h
            else:
                bar_h = (-v / span) * chart_h
                y = zero_y
            painter.setBrush(self._couleur(i, self.comp_stat.get("barres")))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(int(x), int(y), int(bar_w), int(bar_h), 3, 3)

            painter.setPen(QColor(C_TEXT_MUTED))
            slot_w = max(6.0, gap * 0.96)
            label_texte = fm.elidedText(str(label), Qt.ElideRight, int(slot_w))
            painter.drawText(int(x) - int(slot_w) // 2, chart_bottom + 4,
                             int(slot_w), 18, Qt.AlignHCenter, label_texte)

            if v != 0:
                texte = f"{v:,.0f}".replace(",", " ")
                text_w = fm.horizontalAdvance(texte)
                if v > 0 and text_w <= int(bar_w) - 2 and y - 14 >= y0:
                    painter.drawText(int(x), int(y) - 14, int(bar_w), 16,
                                     Qt.AlignHCenter, texte)
                elif text_w <= int(bar_w) - 4 and bar_h >= 18:
                    painter.setPen(QColor(C_CARD))
                    painter.drawText(int(x), int(y) + 2, int(bar_w), 16,
                                     Qt.AlignHCenter, texte)
                elif v < 0 and text_w <= int(bar_w) - 2 and y + bar_h + 18 <= chart_bottom:
                    painter.drawText(int(x), int(y + bar_h) + 2, int(bar_w), 16,
                                     Qt.AlignHCenter, texte)
            painter.setPen(QColor(C_TEXT_MUTED))

        if min_val < 0:
            painter.setPen(QPen(self.grille_col, 1, Qt.DashLine))
            painter.drawLine(pad, int(zero_y), int(w - pad), int(zero_y))
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

        font = _font(8)
        painter.setFont(font)
        fm = painter.fontMetrics()

        texte_leg = [f"{label}  ({value / total * 100:.0f}%)"
                     for label, value in zip(self.labels, self.values)]
        leg_necessaire = max(fm.horizontalAdvance(t) for t in texte_leg) + 24
        legend_w = max(110, min(int(w * 0.45), leg_necessaire))
        pie_area = w - legend_w - 8
        if pie_area < 70:
            pie_area = 70
            legend_w = max(60, w - pie_area - 8)
            pie_area = max(50, w - legend_w - 8)
        center_x = max(pie_area // 2, 50)
        center_y = y0 + (h - y0) // 2
        radius = min(pie_area, h - y0) // 2 - 12
        if radius < 10:
            radius = 10

        start_angle = 0
        for i, value in enumerate(self.values):
            span_angle = (value / total) * 360 * 16
            painter.setBrush(self._couleur(i, self.comp_stat.get("secteurs")))
            painter.setPen(QPen(QColor(C_CARD), 2))
            painter.drawPie(center_x - radius, center_y - radius,
                            radius * 2, radius * 2,
                            int(start_angle), int(span_angle))
            start_angle += span_angle

        legend_x = pie_area + 8
        row_h = max(16, int((h - y0 - 8) / len(self.labels)) if len(self.labels) else 16)
        texte_w = int(legend_w) - 20
        y = y0 + 6
        for i, texte in enumerate(texte_leg):
            painter.setPen(Qt.NoPen)
            painter.setBrush(self._couleur(i, self.comp_stat.get("secteurs")))
            painter.drawRoundedRect(int(legend_x), int(y) + 2, 10, 10, 2, 2)
            painter.setPen(QColor(C_TEXT))
            elide = fm.elidedText(texte, Qt.ElideRight, texte_w)
            painter.drawText(int(legend_x) + 16, int(y), texte_w, 15,
                             Qt.AlignLeft | Qt.AlignVCenter, elide)
            y += row_h
        painter.end()


class SimpleLineChart(_BaseChart):
    """Courbes multi-series : UNE LIGNE COLOREE PAR SERIE.

    ``set_series([(nom, [v1, v2, ...]), ...], labels)``
    - chaque serie a sa propre couleur (CHART_COLORS) ;
    - grille horizontale, valeurs min/max, legende avec point par serie ;
    - lecture type « tresorerie / encaissements sur 12 mois ».
    """

    def __init__(self, parent=None, titre=""):
        super().__init__(parent, titre)
        self.series = []
        self.setMinimumHeight(180)

    def set_series(self, series, labels=None):

        self.series = [
            (nom, [float(v) if v is not None else 0.0 for v in valeurs])
            for nom, valeurs in series]
        if labels is not None:
            self.labels = list(labels)
        self.update()

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        y0 = self._draw_titre(painter, h)

        if not self.series or not self.labels:
            self._draw_empty(painter, y0, max(h - y0, 60))
            painter.end()
            return

        font = _font(8)
        painter.setFont(font)
        fm = painter.fontMetrics()

        flat = [v for _, vals in self.series for v in vals]
        if not flat:
            self._draw_empty(painter, y0, max(h - y0, 60))
            painter.end()
            return
        vmin = min(flat)
        vmax = max(flat)
        if vmax - vmin <= 0:
            vmax = vmin + 1
        pad = (vmax - vmin) * 0.08
        vmin -= pad
        vmax += pad
        span = vmax - vmin
        if span <= 0:
            span = 1.0

        nb_points = max(len(vals) for _, vals in self.series)
        n_legende = len(self.series)

        left = 48
        right = 10
        top = y0 + 14
        legend_h = (n_legende * 16 + 8) if n_legende > 1 else 26
        bottom = h - 30 - legend_h
        if bottom - top < 60:
            bottom = top + 60
        step_x = (w - left - right) / max(nb_points - 1, 1)

        def _x(i):
            return left + i * step_x

        def _y(v):
            return bottom - (v - vmin) / span * (bottom - top)

        # Grille horizontale (4 divisions) + valeurs.
        for i in range(5):
            gy = top + (bottom - top) * i / 4
            val = vmax - (vmax - vmin) * i / 4
            pen = QPen(self.grille_col if i in (0, 4)
                       else self.grille_col.lighter(160), 1)
            pen.setStyle(Qt.SolidLine if i in (0, 4) else Qt.DashLine)
            painter.setPen(pen)
            painter.drawLine(int(left), int(gy), int(w - right), int(gy))
            painter.setPen(QColor(C_TEXT_MUTED))
            texte = f"{val:,.0f}".replace(",", " ")
            painter.drawText(2, int(gy) - 7, left - 8, 14,
                             Qt.AlignRight, texte)

        # Axe X : echantillonne au plus 10 etiquettes sans chevauchement.
        pas = 1
        while nb_points / pas > 10:
            pas += 1
        for ix in range(nb_points):
            if ix % pas != 0 and ix != nb_points - 1:
                continue
            label_i = ix if ix < len(self.labels) else len(self.labels) - 1
            label = str(self.labels[label_i])
            slot = step_x * pas * 0.98
            elide = fm.elidedText(label, Qt.ElideRight, int(max(slot, 24)))
            painter.setPen(QColor(C_TEXT_MUTED))
            painter.drawText(int(_x(ix) - slot / 2), int(bottom) + 5,
                             int(slot), 16, Qt.AlignHCenter, elide)

        # Une polyline coloriee par serie, traits renforces pour la lecture.
        for i, (nom, vals) in enumerate(self.series):
            couleur = self._couleur(i, self.comp_stat.get("courbe"))
            for j in range(len(vals) - 1):
                x1, y1 = _x(j), _y(vals[j])
                x2, y2 = _x(j + 1), _y(vals[j + 1])
                pen = QPen(couleur, 3 if i == 0 else 2)
                pen.setCapStyle(Qt.RoundCap)
                painter.setPen(pen)
                painter.drawLine(int(x1), int(y1), int(x2), int(y2))
            for j, v in enumerate(vals):
                x, y = _x(j), _y(v)
                painter.setPen(Qt.NoPen)
                painter.setBrush(couleur)
                painter.drawEllipse(int(x) - 3, int(y) - 3, 6, 6)

        # Legende : pastille + nom + dernier point.
        if n_legende > 1:
            ly = (h - legend_h) + 4
            ligne_max = (w - left - right) / n_legende
            for i, (nom, vals) in enumerate(self.series):
                x = left + i * ligne_max
                couleur = self._couleur(i, self.comp_stat.get("courbe"))
                painter.setPen(Qt.NoPen)
                painter.setBrush(couleur)
                painter.drawRoundedRect(int(x), int(ly), 10, 10, 3, 3)
                painter.setPen(QColor(C_TEXT))
                dernier = vals[-1] if vals else 0.0
                t_leg = f"{nom} : {dernier:,.0f}".replace(",", " ")
                elide = fm.elidedText(t_leg, Qt.ElideRight,
                                      int(ligne_max - 14))
                painter.drawText(int(x) + 14, int(ly), int(ligne_max - 14),
                                 14, Qt.AlignLeft, elide)
        else:
            ly = h - legend_h + 4
            painter.setPen(QColor(C_TEXT_MUTED))
            dernier = self.series[0][1][-1] if self.series[0][1] else 0.0
            painter.drawText(int(left), int(ly), w - left - right, 14,
                             Qt.AlignRight,
                             f"Dernier point : {dernier:,.0f}".replace(",", " "))
        painter.end()
