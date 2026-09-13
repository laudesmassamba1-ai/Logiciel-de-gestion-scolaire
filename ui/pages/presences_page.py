from PyQt5.QtCore import Qt, QDate
from PyQt5.QtWidgets import (
    QLabel, QLineEdit, QMessageBox, QComboBox, QPushButton, QDateEdit,
    QTableWidgetItem,
)

from repositories import repos
from ui import toast
from ui.pages.helpers import (
    _simple_btn_style, _classe_items, _reload_combo,
    refuser_si_hors_annee,
)
from ui.widgets import KPICard
from ui.widgets.page_templates import ListPageTemplate
from resources.design_tokens import Colors
from core.config import (
    STYLE_BTN_PRIMARY, STYLE_BTN_ADD,
    C_RED, C_RED_BG, C_RED_BORDER,
)


def presences(page, ctx):
    if page.layout() is not None:
        return
    tpl = ListPageTemplate(page, "Presences",
                           "Feuille de presence par classe et par jour")
    peut_editer = ctx.can_edit("presences")

    combo_classe = QComboBox()
    date_edit = QDateEdit()
    date_edit.setDisplayFormat("dd/MM/yyyy")
    date_edit.setCalendarPopup(True)
    date_edit.setDate(QDate.currentDate())
    btn_charger = QPushButton("Charger")
    btn_charger.setCursor(Qt.PointingHandCursor)
    btn_charger.setStyleSheet(STYLE_BTN_PRIMARY)
    tpl.ajouter_filtre(QLabel("Classe :"))
    tpl.ajouter_filtre(combo_classe)
    tpl.ajouter_filtre(QLabel("Date :"))
    tpl.ajouter_filtre(date_edit)
    tpl.ajouter_filtre(btn_charger)

    btn_all_present = QPushButton("Tout marquer present")
    btn_all_present.setCursor(Qt.PointingHandCursor)
    btn_all_present.setStyleSheet(STYLE_BTN_ADD)
    btn_all_present.setToolTip(
        "Marquer tous les eleves de la classe comme presents")
    tpl.ajouter_filtre(btn_all_present)
    btn_all_absent = QPushButton("Tout marquer absent")
    btn_all_absent.setCursor(Qt.PointingHandCursor)
    btn_all_absent.setStyleSheet(
        _simple_btn_style(bg=C_RED_BG, fg=C_RED, border=C_RED_BORDER))
    btn_all_absent.setToolTip(
        "Marquer tous les eleves de la classe comme absents")
    tpl.ajouter_filtre(btn_all_absent)
    tpl.ajouter_space_filtre()

    kpi = [
        tpl.ajouter_kpi(KPICard("Presents", "0", Colors.PRIMARY), 0),
        tpl.ajouter_kpi(KPICard("Absents", "0", Colors.DANGER), 1),
        tpl.ajouter_kpi(KPICard("Retards", "0", Colors.WARNING), 2),
    ]
    tpl.table.setColumnCount(4)
    tpl.table.setHorizontalHeaderLabels(
        ["Matricule", "Eleve", "Statut", "Motif"])

    btn_save = QPushButton("Enregistrer les Presences")
    btn_save.setCursor(Qt.PointingHandCursor)
    btn_save.setStyleSheet(STYLE_BTN_PRIMARY)
    if peut_editer:
        tpl.header.ajouter_action(btn_save)

    etats = {}
    charge = {"cle": None}

    def _montrer_vide(message):
        tpl.vide.set_message(message, "")
        tpl.pile.setCurrentWidget(tpl.vide)

    def refresh():
        _reload_combo(combo_classe, _classe_items(avec_toutes=False))
        classe_id = combo_classe.currentData()
        date = date_edit.date().toString("yyyy-MM-dd")
        etats.clear()
        charge["cle"] = None
        if not classe_id:
            _montrer_vide("Choisissez une classe et une date")
            _maj_kpi()
            return
        eleves_rows = repos.eleves(classe_id=classe_id)
        if not eleves_rows:
            _montrer_vide("Aucun eleve dans cette classe")
            _maj_kpi()
            return
        pres_rows = {p["eleve_id"]: p for p in repos.presences(classe_id, date)}
        tpl.table.setRowCount(len(eleves_rows))
        for i, e in enumerate(eleves_rows):
            tpl.table.setItem(i, 0, QTableWidgetItem(e["matricule"]))
            tpl.table.setItem(i, 1, QTableWidgetItem(f"{e['prenom']} {e['nom']}"))
            pres = pres_rows.get(e["id"])
            statut = pres["statut"] if pres else "Present"
            motif = (pres.get("motif") or "") if pres else ""
            combo = QComboBox()
            combo.addItems(["Present", "Absent", "Retard"])
            combo.setCurrentText(statut)
            tpl.table.setCellWidget(i, 2, combo)
            edit_motif = QLineEdit(motif)
            edit_motif.setPlaceholderText("Motif (si absent)")
            tpl.table.setCellWidget(i, 3, edit_motif)
            etats[i] = (e["id"], combo, edit_motif)
        charge["cle"] = (classe_id, date)
        tpl.table.refresh_height()
        tpl.pile.setCurrentWidget(tpl.table)
        _maj_kpi()

    def _maj_kpi():
        comptes = {"Present": 0, "Absent": 0, "Retard": 0}
        for _eid, combo, _motif in etats.values():
            comptes[combo.currentText()] = comptes.get(combo.currentText(), 0) + 1
        kpi[0].set_value(str(comptes["Present"]))
        kpi[1].set_value(str(comptes["Absent"]))
        kpi[2].set_value(str(comptes["Retard"]))

    def _set_all(statut):
        for _eid, combo, _motif in etats.values():
            combo.blockSignals(True)
            combo.setCurrentText(statut)
            combo.blockSignals(False)
        _maj_kpi()

    def save():
        classe_id = combo_classe.currentData()
        date = date_edit.date().toString("yyyy-MM-dd")
        if not etats or charge["cle"] is None:
            QMessageBox.warning(page, "Presences",
                                "Chargez d'abord la feuille de presence.")
            return
        if refuser_si_hors_annee(page, date, "La date de presence"):
            return
        if charge["cle"] != (classe_id, date):
            QMessageBox.warning(
                page, "Selection modifiee",
                "La classe ou la date a change depuis le chargement. "
                "Cliquez 'Charger' pour recharger la feuille avant "
                "d'enregistrer : evite d'ecrire les statuts affiches "
                "sous une autre date.")
            return
        for eleve_id, combo, edit_motif in etats.values():
            repos.save_presence(eleve_id, classe_id, date,
                                combo.currentText(), edit_motif.text().strip())
        toast.succes(page, "Presences enregistrees.")
        refresh()

    btn_all_present.clicked.connect(lambda: _set_all("Present"))
    btn_all_absent.clicked.connect(lambda: _set_all("Absent"))
    combo_classe.currentIndexChanged.connect(refresh)
    date_edit.dateChanged.connect(refresh)
    btn_charger.clicked.connect(refresh)
    btn_save.clicked.connect(save)
    refresh()
    page.refresh = refresh
