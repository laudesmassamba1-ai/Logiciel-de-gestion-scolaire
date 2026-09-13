from functools import partial

import sqlite3

from PyQt5.QtCore import Qt, QDate
from PyQt5.QtWidgets import (
    QDialog, QDialogButtonBox, QLabel, QLineEdit, QMessageBox,
    QCheckBox, QFormLayout, QTabWidget, QVBoxLayout,
    QComboBox, QDateEdit, QWidget, QStackedWidget,
)

from repositories import repos
from ui import toast
from ui.pages.helpers import (
    _btn, _simple_btn_style, _add_btn, _actions_cell,
)
from ui.widgets import DataTable, EmptyState
from core.config import (
    C_BLUE, C_BLUE_LIGHT, C_BLUE_BORDER, C_GOLD, C_GOLD_BG, C_GOLD_BORDER,
    C_RED, C_RED_BG, C_RED_BORDER,
)


def cycles_annees(page, ctx):
    if page.layout() is not None:
        return
    from ui.widgets import PageHeader
    lay = QVBoxLayout(page)
    lay.setContentsMargins(20, 20, 20, 20)
    lay.setSpacing(16)
    lay.addWidget(PageHeader(
        "Cycles & Annees Scolaires",
        "Cycles pedagogiques et annees scolaires de l'établissement"))

    tabs = QTabWidget()
    lay.addWidget(tabs, 1)
    peut_editer = ctx.can_edit("cycles")

    # ---- Onglet Cycles
    onglet_cycles = QWidget()
    lay_c = QVBoxLayout(onglet_cycles)
    table_cycles = DataTable()
    table_cycles.setColumnCount(3)
    table_cycles.setHorizontalHeaderLabels(["Nom", "Description", "Actions"])
    vide_cycles = EmptyState("Aucun cycle enregistre",
                             "Ajoutez un cycle via le bouton ci-dessus.")
    pile_c = QStackedWidget()
    pile_c.addWidget(table_cycles)
    pile_c.addWidget(vide_cycles)
    lay_c.addWidget(pile_c, 1)

    def fill_cycles():
        rows = repos.cycles()
        valeurs = [[c["nom"], c["description"] or "-", ""] for c in rows]
        table_cycles.remplir(valeurs)
        for i, c in enumerate(rows):
            table_cycles.setCellWidget(i, 2, _actions_cell(
                _btn("Modifier", partial(open_cycle_dialog, page, ctx, c, fill_cycles),
                     _simple_btn_style(bg=C_BLUE_LIGHT, fg=C_BLUE, border=C_BLUE_BORDER)),
                _btn("Supprimer", partial(_delete_cycle, page, ctx, c),
                     _simple_btn_style(bg=C_RED_BG, fg=C_RED, border=C_RED_BORDER))))
        pile_c.setCurrentWidget(vide_cycles if not rows else table_cycles)

    def _delete_cycle(parent, ctx, c):
        from ui.pages.helpers import confirmer
        if confirmer(
                parent,
                f"Supprimer le cycle {c['nom']} ?\n\n"
                "Attention : les classes rattachees a ce cycle seront "
                "egalement supprimees (avec leurs eleves).",
                "Cycle"):
            repos.delete_cycle(c["id"])
            toast.succes(parent, "Cycle supprime.")
            fill_cycles()

    btn_add_cycle = _add_btn(
        "+ Nouveau Cycle", lambda: open_cycle_dialog(page, ctx, None, fill_cycles))
    lay_c.addWidget(btn_add_cycle, 0, Qt.AlignRight)
    if not peut_editer:
        btn_add_cycle.setVisible(False)

    tabs.addTab(onglet_cycles, "Cycles")

    # ---- Onglet Annees Scolaires
    onglet_annees = QWidget()
    lay_a = QVBoxLayout(onglet_annees)
    table_annees = DataTable()
    table_annees.setColumnCount(5)
    table_annees.setHorizontalHeaderLabels(
        ["Libelle", "Debut", "Fin", "Active", "Actions"])
    vide_annees = EmptyState(
        "Aucune annee scolaire enregistree",
        "Ajoutez une annee scolaire via le bouton ci-dessus.")
    pile_a = QStackedWidget()
    pile_a.addWidget(table_annees)
    pile_a.addWidget(vide_annees)
    lay_a.addWidget(pile_a, 1)

    def fill_annees():
        rows = repos.annees_scolaires()
        valeurs = [[a["libelle"], a["date_debut"] or "-", a["date_fin"] or "-",
                    "Oui" if a["est_active"] else "Non", ""] for a in rows]
        table_annees.remplir(valeurs)
        for i, a in enumerate(rows):
            cell = _actions_cell(*(
                (_btn("Activer", partial(_set_active, page, ctx, a),
                      _simple_btn_style(bg=C_GOLD_BG, fg=C_GOLD, border=C_GOLD_BORDER)),)
                if not a["est_active"] and peut_editer else ()
            ) + (
                (_btn("Supprimer", partial(_delete_annee, page, ctx, a),
                      _simple_btn_style(bg=C_RED_BG, fg=C_RED, border=C_RED_BORDER)),)
                if not a["est_active"] else ()
            ))
            table_annees.setCellWidget(i, 4, cell)
        pile_a.setCurrentWidget(vide_annees if not rows else table_annees)

    def _set_active(parent, ctx, a):
        repos.set_annee_active(a["id"])
        toast.succes(parent, f"{a['libelle']} est maintenant l'annee active.")
        fill_annees()

    def _delete_annee(parent, ctx, a):
        from ui.pages.helpers import confirmer
        if confirmer(parent, f"Supprimer l'annee {a['libelle']} ?", "Annee"):
            repos.delete_annee_scolaire(a["id"])
            toast.succes(parent, "Annee scolaire supprimee.")
            fill_annees()

    btn_add_annee = _add_btn(
        "+ Nouvelle Annee", lambda: open_annee_dialog(page, ctx, None, fill_annees))
    lay_a.addWidget(btn_add_annee, 0, Qt.AlignRight)
    if not peut_editer:
        btn_add_annee.setVisible(False)

    tabs.addTab(onglet_annees, "Annees Scolaires")

    fill_cycles()
    fill_annees()
    page.refresh = lambda: (fill_cycles(), fill_annees())


def open_cycle_dialog(parent, ctx, cycle=None, on_created=None):
    dlg = QDialog(parent)
    dlg.setWindowTitle("Nouveau Cycle" if not cycle else "Modifier le Cycle")
    dlg.resize(420, 200)
    dlg.setMinimumSize(360, 170)
    lay = QVBoxLayout(dlg)
    form = QFormLayout()
    nom = QLineEdit()
    description = QLineEdit()
    if cycle:
        nom.setText(cycle["nom"])
        description.setText(cycle["description"] or "")
    form.addRow("Nom :", nom)
    form.addRow("Description :", description)
    lay.addLayout(form)
    buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
    buttons.rejected.connect(dlg.reject)
    lay.addWidget(buttons)

    def valider():
        if not nom.text().strip():
            QMessageBox.warning(dlg, "Cycle", "Le nom du cycle est obligatoire.")
            return
        try:
            if cycle:
                repos.update_cycle(cycle["id"], nom.text().strip(), description.text().strip())
            else:
                repos.add_cycle(nom.text().strip(), description.text().strip())
        except sqlite3.IntegrityError:
            QMessageBox.warning(dlg, "Cycle",
                                f"Un cycle nomme '{nom.text().strip()}' existe "
                                "deja. Choisissez un autre nom.")
            return
        toast.succes(dlg, "Cycle enregistre.")
        if on_created:
            on_created()
        dlg.accept()

    buttons.accepted.connect(valider)
    dlg.exec_()


def open_annee_dialog(parent, ctx, annee=None, on_created=None):
    dlg = QDialog(parent)
    dlg.setWindowTitle("Nouvelle Annee Scolaire" if not annee else "Modifier l'Annee Scolaire")
    dlg.resize(420, 260)
    dlg.setMinimumSize(360, 220)
    lay = QVBoxLayout(dlg)
    form = QFormLayout()
    libelle = QLineEdit()
    libelle.setPlaceholderText("Ex: 2025-2026")
    debut = QDateEdit()
    debut.setDisplayFormat("dd/MM/yyyy")
    debut.setCalendarPopup(True)
    fin = QDateEdit()
    fin.setDisplayFormat("dd/MM/yyyy")
    fin.setCalendarPopup(True)
    active = QCheckBox("Annee scolaire active")
    if annee:
        libelle.setText(annee["libelle"])
        if annee["date_debut"]:
            debut.setDate(QDate.fromString(annee["date_debut"], "yyyy-MM-dd"))
        if annee["date_fin"]:
            fin.setDate(QDate.fromString(annee["date_fin"], "yyyy-MM-dd"))
        active.setChecked(bool(annee["est_active"]))
    form.addRow("Libelle :", libelle)
    form.addRow("Date de debut :", debut)
    form.addRow("Date de fin :", fin)
    lay.addLayout(form)
    lay.addWidget(active)
    buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
    buttons.rejected.connect(dlg.reject)
    lay.addWidget(buttons)

    def valider():
        if not libelle.text().strip():
            QMessageBox.warning(dlg, "Annee", "Le libelle est obligatoire.")
            return
        d, f = debut.date(), fin.date()
        if f <= d:
            QMessageBox.warning(dlg, "Annee",
                                "La date de fin doit etre posterieure a la "
                                "date de debut.")
            return
        # Anti-chevauchement : deux annees scolaires ne peuvent pas se
        # recouvrir, sinon les gardes de dates deviennent ambigues.
        d_iso, f_iso = d.toString("yyyy-MM-dd"), f.toString("yyyy-MM-dd")
        for a in repos.annees_scolaires():
            if annee and a["id"] == annee["id"]:
                continue
            a_debut = a.get("date_debut") or "0000-01-01"
            a_fin = a.get("date_fin") or "9999-12-31"
            if d_iso <= a_fin and a_debut <= f_iso:
                QMessageBox.warning(
                    dlg, "Annee",
                    f"Les dates saisies chevauchent l'annee {a['libelle']} "
                    f"({a_debut} → {a_fin}).\n"
                    "Deux annees scolaires ne peuvent pas se recouvrir.")
                return
        try:
            if annee:
                repos.update_annee_scolaire(annee["id"], libelle.text().strip(),
                                            d.toString("yyyy-MM-dd"),
                                            f.toString("yyyy-MM-dd"),
                                            active.isChecked())
                if active.isChecked():
                    repos.set_annee_active(annee["id"])
            else:
                new_id = repos.add_annee_scolaire(
                    libelle.text().strip(),
                    d.toString("yyyy-MM-dd"),
                    f.toString("yyyy-MM-dd"),
                    active.isChecked())
                if active.isChecked():
                    repos.set_annee_active(new_id)
        except sqlite3.IntegrityError:
            QMessageBox.warning(dlg, "Annee",
                                f"Une annee '{libelle.text().strip()}' existe "
                                "deja. Choisissez un autre libelle.")
            return
        toast.succes(dlg, "Annee scolaire enregistree.")
        if on_created:
            on_created()
        dlg.accept()

    buttons.accepted.connect(valider)
    dlg.exec_()
