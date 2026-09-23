from functools import partial

import datetime

from PyQt5.QtCore import QDate
from PyQt5.QtWidgets import (
    QDialog, QDialogButtonBox, QLabel, QLineEdit, QMessageBox,
    QComboBox, QFormLayout, QDateEdit, QVBoxLayout,
)

from repositories import repos
from ui import toast
from ui.pages.helpers import (
    _btn, _simple_btn_style, _money_edit, refuser_si_hors_annee, _actions_cell,
)
from ui.widgets import fmt_money, KPICard
from ui.widgets.page_templates import ListPageTemplate
from resources.design_tokens import Colors
from core.config import (
    STYLE_BTN_PRIMARY, STYLE_BTN_SECONDARY, STYLE_BTN_DANGER,
    C_RED_BG, C_RED, C_RED_BORDER,
)


def caisse(page, ctx):
    if page.layout() is not None:
        return
    tpl = ListPageTemplate(page, "Caisse", "Recettes, depenses et solde")
    peut_editer = ctx.can_edit("caisse")

    search = QLineEdit()
    search.setPlaceholderText("Rechercher (motif, beneficiaire, reference)...")
    search.setMaximumWidth(280)
    combo_type = QComboBox()
    combo_type.addItems(["Toutes les operations", "Recettes uniquement",
                         "Depenses uniquement"])
    now = QDate.currentDate()
    date_start = QDateEdit(now.addDays(-(now.day() - 1)))
    date_end = QDateEdit(now)
    for d in (date_start, date_end):
        d.setFixedWidth(130)
    combo_annee = QComboBox()
    combo_annee.addItem("Annee active", "active")
    combo_annee.addItem("Toutes les annees", None)
    for a in repos.annees_scolaires():
        combo_annee.addItem(a["libelle"], a["libelle"])
    combo_annee.setMaximumWidth(220)
    tpl.ajouter_filtre(search)
    tpl.ajouter_filtre(combo_type)
    tpl.ajouter_filtre(QLabel("Du :"))
    tpl.ajouter_filtre(date_start)
    tpl.ajouter_filtre(QLabel("Au :"))
    tpl.ajouter_filtre(date_end)
    tpl.ajouter_filtre(combo_annee)
    tpl.ajouter_space_filtre()

    kpi = [
        tpl.ajouter_kpi(KPICard("Recettes", "0", Colors.SUCCESS), 0),
        tpl.ajouter_kpi(KPICard("Depenses", "0", Colors.DANGER), 1),
        tpl.ajouter_kpi(KPICard("Solde", "0", Colors.INFO), 2),
    ]
    tpl.table.setColumnCount(8)
    tpl.table.setHorizontalHeaderLabels(
        ["Date", "Reference", "Beneficiaire", "Motif", "Categorie",
         "Recettes", "Depenses", "Actions"])

    btn_recette = _btn("+ Recette",
                       lambda: open_transaction_dialog(page, ctx, "entree",
                                                       on_created=refresh),
                       STYLE_BTN_PRIMARY)
    btn_depense = _btn("+ Depense",
                       lambda: open_transaction_dialog(page, ctx, "sortie",
                                                       on_created=refresh),
                       STYLE_BTN_DANGER)
    btn_export = _btn("Exporter CSV", lambda: export_csv(), STYLE_BTN_SECONDARY)
    btn_export_pdf = _btn("Exporter PDF", lambda: _exporter_pdf(), STYLE_BTN_SECONDARY)
    if peut_editer:
        tpl.header.ajouter_action(btn_recette)
        tpl.header.ajouter_action(btn_depense)
    tpl.header.ajouter_action(btn_export)
    tpl.header.ajouter_action(btn_export_pdf)

    def _exporter_pdf():
        from services import rapports
        rows = getattr(page, "_caisse_rows", [])
        lignes = [[r["date"], r["reference"], r["beneficiaire"] or "-",
                   r["motif"] or "-", r["categorie"] or "-",
                   r["type"] == "entree" and "Recette" or "Depense",
                   fmt_money(r["montant"])] for r in rows]
        if not rapports.export_table_pdf(
                "Caisse : operations",
                f"Periode {filtre_courant['debut']} au "
                f"{filtre_courant['fin']} - le {rapports._date_pdf()}",
                ["Date", "Reference", "Beneficiaire", "Motif", "Categorie",
                 "Type", "Montant"], lignes,
                "rapport_caisse.pdf"):
            toast.info(page, "Rien a exporter : aucune operation sur cette periode.")

    filtre_courant = {"t": None, "recherche": "", "debut": None, "fin": None,
                      "annee": "active"}

    def refresh():
        repos.reconcilier_caisse()
        type_filtre = combo_type.currentText()
        recherche = search.text().strip()
        if type_filtre == "Recettes uniquement":
            t = "entree"
        elif type_filtre == "Depenses uniquement":
            t = "sortie"
        else:
            t = None
        annee_filtre = combo_annee.currentData()
        if annee_filtre == "active":
            active = repos.annee_scolaire_active()
            annee_filtre = active["libelle"] if active else None
        debut = date_start.date().toString("yyyy-MM-dd")
        fin = date_end.date().toString("yyyy-MM-dd")
        filtre_courant.update(t=t, recherche=recherche, debut=debut, fin=fin,
                              annee=annee_filtre)
        rows = repos.transactions(
            type_filtre=t, recherche=recherche,
            date_start=debut, date_end=fin,
            annee=annee_filtre)
        valeurs = []
        total_entrees = 0.0
        total_sorties = 0.0
        for r in rows:
            montant = float(r["montant"] or 0)
            if r["type"] == "entree":
                total_entrees += montant
                rec, dep = fmt_money(montant), ""
            else:
                total_sorties += montant
                rec, dep = "", fmt_money(montant)
            valeurs.append([r["date"], r["reference"], r["beneficiaire"] or "-",
                            r["motif"] or "-", r["categorie"] or "-",
                            rec, dep, ""])
        tpl.remplir(
            valeurs,
            message_vide="Aucune transaction sur la periode selectionnee",
            sous_titre_vide="Elargissez les dates ou changez de filtre.")
        for i, r in enumerate(rows):
            tpl.table.setCellWidget(i, 7, _actions_cell(*(
                (_btn("Supprimer", partial(_delete_transaction, page, ctx, r),
                      _simple_btn_style(bg=C_RED_BG, fg=C_RED, border=C_RED_BORDER)),)
                if peut_editer else ()
            )))

        kpi[0].set_value(fmt_money(total_entrees))
        kpi[1].set_value(fmt_money(total_sorties))
        kpi[2].set_value(fmt_money(total_entrees - total_sorties))
        page._caisse_rows = rows

    def _delete_transaction(parent, ctx, t):
        from ui.pages.helpers import confirmer
        if confirmer(parent, "Supprimer cette transaction ?", "Supprimer"):
            repos.delete_transaction(t["id"])
            refresh()

    def export_csv():
        from PyQt5.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(page, "Exporter CSV",
                                              "transactions.csv", "CSV (*.csv)")
        if not path:
            return
        f = filtre_courant
        repos.export_transactions_csv(
            path, type_filtre=f["t"], recherche=f["recherche"],
            date_start=f["debut"], date_end=f["fin"], annee=f["annee"])
        toast.succes(page, f"Exporte vers {path}")

    search.textChanged.connect(refresh)
    combo_type.currentIndexChanged.connect(refresh)
    combo_annee.currentIndexChanged.connect(refresh)
    date_start.dateChanged.connect(refresh)
    date_end.dateChanged.connect(refresh)

    refresh()
    page.refresh = refresh


def open_transaction_dialog(parent, ctx, type_trans, on_created=None):
    dlg = QDialog(parent)
    dlg.setWindowTitle("Nouvelle Recette" if type_trans == "entree" else "Nouvelle Depense")
    dlg.resize(420, 300)
    dlg.setMinimumSize(360, 240)
    lay = QVBoxLayout(dlg)
    form = QFormLayout()

    motif = QLineEdit()
    motif.setPlaceholderText("Ex: Droits de scolarite, Fournitures...")
    beneficiaire = QLineEdit()
    beneficiaire.setPlaceholderText("Eleve ou fournisseur")
    montant = _money_edit(minimum=1)
    if type_trans == "entree":
        categorie = QComboBox()
        categorie.addItems(["Scolarite", "Inscription", "Tenues", "Autres"])
        mode = QComboBox()
        mode.addItems(["Especes", "Mobile Money (MTN / Moov)", "Cheque / Virement"])
    else:
        categorie = QComboBox()
        categorie.addItems(["Fournitures", "Salaires", "Entretien", "Transport", "Autres"])
        mode = QComboBox()
        mode.addItems(["Especes", "Virement", "Cheque"])

    form.addRow("Motif :", motif)
    form.addRow("Beneficiaire :", beneficiaire)
    form.addRow("Montant :", montant)
    form.addRow("Categorie :", categorie)
    form.addRow("Mode :", mode)
    lay.addLayout(form)
    buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
    btn_ok = buttons.button(QDialogButtonBox.Ok)
    btn_ok.setText("Valider")
    buttons.rejected.connect(dlg.reject)
    lay.addWidget(buttons)

    def valider():
        if montant.value() <= 0:
            QMessageBox.warning(dlg, "Caisse", "Le montant doit etre superieur a 0.")
            return
        if refuser_si_hors_annee(dlg, datetime.date.today().isoformat(),
                                 "La date de l'ecriture (aujourd'hui)"):
            return
        repos.add_transaction(
            type_trans, montant.value(), motif.text().strip() or "Sans motif",
            categorie.currentText(), beneficiaire.text().strip() or "-",
            mode.currentText())
        toast.succes(dlg, "Transaction enregistree.")
        dlg.accept()

    btn_ok.clicked.connect(valider)

    dlg.exec_()
    if dlg.result() == QDialog.Accepted and on_created:
        on_created()
