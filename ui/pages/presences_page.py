from PyQt5.QtCore import Qt, QDate
from PyQt5.QtWidgets import (
    QHBoxLayout, QLabel, QLineEdit, QMessageBox, QComboBox, QPushButton,
    QTableWidgetItem, QVBoxLayout, QWidget, QDateEdit,
)

from repositories import repos
from ui.pages.helpers import (
    _btn, _simple_btn_style, _classe_items, _reload_combo, _make_table,
    _page_header, _kpi_card,
)
from core.config import (
    C_EMPTY_STATE, STYLE_BTN_PRIMARY, STYLE_BTN_ADD,
    C_RED, C_RED_BG, C_RED_BORDER, C_GOLD, C_WARNING,
)


def presences(page, ctx):
    if page.layout() is not None:
        return
    page.setStyleSheet("")
    lay = QVBoxLayout(page)
    lay.setContentsMargins(20, 20, 20, 20)
    lay.setSpacing(16)
    _page_header(lay, "Presences", "Feuille de presence par classe et par jour")

    filtre = QHBoxLayout()
    combo_classe = QComboBox()
    for c in repos.classes():
        combo_classe.addItem(c["nom"], c["id"])
    date_edit = QDateEdit()
    date_edit.setDisplayFormat("dd/MM/yyyy")
    date_edit.setCalendarPopup(True)
    date_edit.setDate(QDate.currentDate())
    btn_charger = QPushButton("Charger")
    btn_charger.setCursor(Qt.PointingHandCursor)
    btn_charger.setStyleSheet(STYLE_BTN_PRIMARY)
    filtre.addWidget(QLabel("Classe :"))
    filtre.addWidget(combo_classe)
    filtre.addWidget(QLabel("Date :"))
    filtre.addWidget(date_edit)
    filtre.addWidget(btn_charger)

    btn_all_present = QPushButton("Tout marquer present")
    btn_all_present.setCursor(Qt.PointingHandCursor)
    btn_all_present.setStyleSheet(STYLE_BTN_ADD)
    btn_all_present.setToolTip("Marquer tous les eleves de la classe comme presents")
    filtre.addWidget(btn_all_present)

    btn_all_absent = QPushButton("Tout marquer absent")
    btn_all_absent.setCursor(Qt.PointingHandCursor)
    btn_all_absent.setStyleSheet(_simple_btn_style(bg=C_RED_BG, fg=C_RED, border=C_RED_BORDER))
    btn_all_absent.setToolTip("Marquer tous les eleves de la classe comme absents")
    filtre.addWidget(btn_all_absent)

    filtre.addStretch(1)
    btn_save = QPushButton("Enregistrer les Presences")
    btn_save.setCursor(Qt.PointingHandCursor)
    btn_save.setStyleSheet(STYLE_BTN_PRIMARY)
    if ctx.can_edit("presences"):
        filtre.addWidget(btn_save)
    lay.addLayout(filtre)

    kpi_lay = QHBoxLayout()
    lbl_presents = _kpi_card("Presents", "0", C_GOLD)
    lbl_absents = _kpi_card("Absents", "0", C_RED)
    lbl_retards = _kpi_card("Retards", "0", C_WARNING)
    for w in (lbl_presents, lbl_absents, lbl_retards):
        kpi_lay.addWidget(w)
    lay.addLayout(kpi_lay)

    from PyQt5.QtWidgets import QTableWidget
    table = _make_table(["Matricule", "Eleve", "Statut", "Motif"])
    table.setEditTriggers(QTableWidget.NoEditTriggers)
    lay.addWidget(table)
    lbl_empty = QLabel("Choisissez une classe et une date")
    lbl_empty.setStyleSheet(f"color: {C_EMPTY_STATE}; padding: 30px;")
    lbl_empty.setAlignment(Qt.AlignCenter)
    lay.addWidget(lbl_empty)

    etats = {}

    def refresh():
        _reload_combo(combo_classe, _classe_items(avec_toutes=False))
        classe_id = combo_classe.currentData()
        date = date_edit.date().toString("yyyy-MM-dd")
        if not classe_id:
            table.setRowCount(0)
            lbl_empty.setVisible(True)
            table.setVisible(False)
            return
        eleves_rows = repos.eleves(classe_id=classe_id)
        pres_rows = {p["eleve_id"]: p for p in repos.presences(classe_id, date)}
        etats.clear()
        table.blockSignals(True)
        table.setRowCount(len(eleves_rows))
        for i, e in enumerate(eleves_rows):
            table.setItem(i, 0, QTableWidgetItem(e["matricule"]))
            table.setItem(i, 1, QTableWidgetItem(f"{e['prenom']} {e['nom']}"))
            pres = pres_rows.get(e["id"])
            statut = pres["statut"] if pres else "Present"
            motif = pres["motif"] or "" if pres else ""
            combo = QComboBox()
            combo.addItems(["Present", "Absent", "Retard"])
            combo.setCurrentText(statut)
            table.setCellWidget(i, 2, combo)
            edit_motif = QLineEdit(motif)
            edit_motif.setPlaceholderText("Motif (si absent)")
            table.setCellWidget(i, 3, edit_motif)
            etats[i] = (e["id"], combo, edit_motif)
        table.blockSignals(False)
        table.resizeColumnsToContents()
        lbl_empty.setVisible(False)
        table.setVisible(True)
        _maj_kpi()

    def _maj_kpi():
        comptes = {"Present": 0, "Absent": 0, "Retard": 0}
        for _eid, combo, _motif in etats.values():
            comptes[combo.currentText()] = comptes.get(combo.currentText(), 0) + 1
        lbl_presents.findChild(QLabel, "kpi_value").setText(str(comptes["Present"]))
        lbl_absents.findChild(QLabel, "kpi_value").setText(str(comptes["Absent"]))
        lbl_retards.findChild(QLabel, "kpi_value").setText(str(comptes["Retard"]))

    def _set_all(statut):
        for _eid, combo, _motif in etats.values():
            combo.blockSignals(True)
            combo.setCurrentText(statut)
            combo.blockSignals(False)
        _maj_kpi()

    def save():
        classe_id = combo_classe.currentData()
        date = date_edit.date().toString("yyyy-MM-dd")
        if not etats:
            QMessageBox.warning(page, "Presences", "Chargez d'abord la feuille de presence.")
            return
        for eleve_id, combo, edit_motif in etats.values():
            repos.save_presence(eleve_id, classe_id, date,
                                combo.currentText(), edit_motif.text().strip())
        QMessageBox.information(page, "Presences", "Presences enregistrees.")
        refresh()

    btn_all_present.clicked.connect(lambda: _set_all("Present"))
    btn_all_absent.clicked.connect(lambda: _set_all("Absent"))
    combo_classe.currentIndexChanged.connect(refresh)
    btn_charger.clicked.connect(refresh)
    btn_save.clicked.connect(save)
    refresh()
    page.refresh = refresh
