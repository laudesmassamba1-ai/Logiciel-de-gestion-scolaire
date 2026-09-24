from functools import partial

import datetime

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QMessageBox,
    QComboBox, QFormLayout, QPushButton, QTabWidget, QVBoxLayout, QWidget,
    QStackedWidget,
)

from repositories import repos
from ui import toast
from ui.pages.helpers import (
    _btn, _simple_btn_style, _money_edit, _classe_items, _reload_combo,
    _add_btn, refuser_si_hors_annee, _actions_cell,
)
from ui.widgets import fmt_money, KPICard, DataTable, EmptyState
from resources.design_tokens import Colors
from core.config import (
    PERIODES, STYLE_BTN_PRIMARY, STYLE_BTN_SECONDARY, C_BLUE, C_BLUE_LIGHT,
    C_BLUE_BORDER, C_RED, C_RED_BG, C_RED_BORDER, lire_composant,
    MODES_PAIEMENT,
)


def paiements(page, ctx):
    if page.layout() is not None:
        return
    from ui.widgets import PageHeader
    lay = QVBoxLayout(page)
    lay.setContentsMargins(20, 20, 20, 20)
    lay.setSpacing(16)
    lay.addWidget(PageHeader(
        "Paiements, Suivi & Bilans",
        "Encaissements, suivi mensuel des eleves et bilans"))

    tabs = QTabWidget()
    lay.addWidget(tabs, 1)
    peut_editer = ctx.can_edit("paiements")

    def _annee_options(combo):
        combo.clear()
        combo.addItem("Toutes les annees", None)
        for a in repos.annees_scolaires():
            combo.addItem(a["libelle"], a["libelle"])

    TYPES_FRAIS = ["Scolarite", "Inscription", "Tenues", "Transport", "Cantine", "Autres"]
    MODES = list(MODES_PAIEMENT)

    def _mode_options(combo):
        combo.clear()
        combo.addItem("Tous les modes", None)
        for m in MODES:
            combo.addItem(m, m)

    # ---------------- Onglet Paiements ----------------
    onglet_paiements = QWidget()
    lay_p = QVBoxLayout(onglet_paiements)
    filtre_p = QHBoxLayout()
    combo_classe_p = QComboBox()
    combo_classe_p.addItem("Toutes les classes", None)
    for c in repos.classes():
        combo_classe_p.addItem(c["nom"], c["id"])
    combo_type_p = QComboBox()
    combo_type_p.addItem("Tous les types", None)
    for t in TYPES_FRAIS:
        combo_type_p.addItem(t, t)
    combo_mode_p = QComboBox()
    _mode_options(combo_mode_p)
    filtre_p.addWidget(QLabel("Classe :"))
    filtre_p.addWidget(combo_classe_p)
    filtre_p.addWidget(QLabel("Type :"))
    filtre_p.addWidget(combo_type_p)
    filtre_p.addWidget(QLabel("Mode :"))
    filtre_p.addWidget(combo_mode_p)
    filtre_p.addStretch(1)
    btn_add_paiement = _add_btn(
        "+ Nouveau Paiement",
        lambda: open_paiement_dialog(page, ctx, refresh_p))
    btn_pdf_p = _btn("Exporter PDF", lambda: _exporter_pdf_p(), STYLE_BTN_SECONDARY)
    if peut_editer:
        filtre_p.addWidget(btn_add_paiement)
    filtre_p.addWidget(btn_pdf_p)
    lay_p.addLayout(filtre_p)

    def _exporter_pdf_p():
        from services import rapports
        rows = getattr(page, "_paiements_rows", [])
        lignes = [[p["date_paiement"], p["matricule"],
                   f"{p['prenom']} {p['nom']}", p["classe_nom"] or "-",
                   p["type_frais"] or "-", p["mode_reglement"] or "-",
                   fmt_money(p["montant"])] for p in rows]
        if not rapports.export_table_pdf(
                "Paiements",
                f"Filtres actuels - le {rapports._date_pdf()}",
                ["Date", "Matricule", "Eleve", "Classe", "Type frais",
                 "Mode", "Montant"], lignes, "rapport_paiements.pdf"):
            toast.info(page, "Rien a exporter : aucun paiement dans ce filtre.")

    kpi_p = QHBoxLayout()
    kpi_p_nb = KPICard("Nombre de paiements", "0")
    kpi_p_total = KPICard("Montant total", "0", Colors.INFO)
    kpi_p.addWidget(kpi_p_nb)
    kpi_p.addWidget(kpi_p_total)
    lay_p.addLayout(kpi_p)

    table_p = DataTable()
    table_p.setColumnCount(9)
    table_p.setHorizontalHeaderLabels(
        ["Date", "Matricule", "Eleve", "Classe", "Type frais",
         "Montant", "Mode", "Trimestre", "Actions"])
    vide_p = EmptyState(
        "Aucun paiement enregistre",
        "Enregistrez un paiement via le bouton ci-dessus.")
    pile_p = QStackedWidget()
    pile_p.addWidget(table_p)
    pile_p.addWidget(vide_p)
    lay_p.addWidget(pile_p, 1)

    def refresh_p():
        repos.reconcilier_caisse()
        _reload_combo(combo_classe_p, _classe_items())
        rows = repos.paiements(
            classe_id=combo_classe_p.currentData(),
            type_frais=combo_type_p.currentData() or None,
            mode=combo_mode_p.currentData() or None)
        valeurs = [[p["date_paiement"], p["matricule"],
                    f"{p['prenom']} {p['nom']}", p["classe_nom"] or "-",
                    p["type_frais"] or "-", fmt_money(p["montant"]),
                    p["mode_reglement"] or "-", p["trimestre"] or "-", ""]
                   for p in rows]
        table_p.remplir(valeurs)
        for i, p in enumerate(rows):
            table_p.setCellWidget(i, 8, _actions_cell(*(
                (_btn("Supprimer", partial(_delete_paiement, page, ctx, p),
                      _simple_btn_style(bg=C_RED_BG, fg=C_RED, border=C_RED_BORDER)),)
                if peut_editer else ()
            )))
        pile_p.setCurrentWidget(vide_p if not rows else table_p)
        kpi_p_nb.set_value(str(len(rows)))
        kpi_p_total.set_value(
            fmt_money(sum(float(p["montant"]) for p in rows)))
        page._paiements_rows = rows

    def _delete_paiement(parent, ctx, p):
        from ui.pages.helpers import confirmer
        if confirmer(parent, "Supprimer ce paiement ?", "Paiement"):
            repos.delete_paiement(p["id"])
            refresh_p()

    combo_classe_p.currentIndexChanged.connect(refresh_p)
    combo_type_p.currentIndexChanged.connect(refresh_p)
    combo_mode_p.currentIndexChanged.connect(refresh_p)
    tabs.addTab(onglet_paiements, "Paiements")

    # ---------------- Onglet Suivi Eleve ----------------
    onglet_suivi = QWidget()
    lay_s = QVBoxLayout(onglet_suivi)
    suivi_row = QHBoxLayout()
    combo_classe_s = QComboBox()
    combo_classe_s.addItem("Toutes les classes", None)
    for c in repos.classes():
        combo_classe_s.addItem(c["nom"], c["id"])
    combo_eleve_s = QComboBox()
    suivi_row.addWidget(QLabel("Classe :"))
    suivi_row.addWidget(combo_classe_s)
    suivi_row.addWidget(QLabel("Eleve :"))
    suivi_row.addWidget(combo_eleve_s, 1)
    lay_s.addLayout(suivi_row)

    solde_lay = QHBoxLayout()
    lbl_attendu = KPICard("Total attendu", "0", Colors.INFO)
    lbl_paye = KPICard("Total paye", "0", Colors.PRIMARY)
    lbl_solde = KPICard("Solde restant", "0", Colors.DANGER)
    for w in (lbl_attendu, lbl_paye, lbl_solde):
        solde_lay.addWidget(w)
    lay_s.addLayout(solde_lay)

    table_suivi = DataTable()
    table_suivi.setColumnCount(3)
    table_suivi.setHorizontalHeaderLabels(["Mois", "Attendu", "Paye"])
    vide_suivi = EmptyState(
        "Selectionnez un eleve pour afficher son suivi mensuel", "")
    pile_s = QStackedWidget()
    pile_s.addWidget(table_suivi)
    pile_s.addWidget(vide_suivi)
    lay_s.addWidget(pile_s, 1)

    def fill_eleves():
        combo_eleve_s.blockSignals(True)
        combo_eleve_s.clear()
        for e in repos.eleves(classe_id=combo_classe_s.currentData()):
            combo_eleve_s.addItem(f"{e['prenom']} {e['nom']} ({e['matricule']})", e["id"])
        combo_eleve_s.blockSignals(False)
        refresh_suivi()

    def refresh_suivi():
        eleve_id = combo_eleve_s.currentData()
        if not eleve_id:
            table_suivi.setRowCount(0)
            for w in (lbl_attendu, lbl_paye, lbl_solde):
                w.set_value(fmt_money(0))
            vide_suivi.set_message(
                "Selectionnez un eleve pour afficher son suivi mensuel", "")
            pile_s.setCurrentWidget(vide_suivi)
            return
        active = repos.annee_scolaire_active()
        annee = active["libelle"] if active else ""
        solde = repos.solde_eleve(eleve_id, annee)
        lbl_attendu.set_value(fmt_money(solde["attendu"]))
        lbl_paye.set_value(fmt_money(solde["paye"]))
        lbl_solde.set_value(fmt_money(solde["solde"]))
        suivi = repos.suivi_mensuel(eleve_id, annee)
        valeurs = [[m["mois"], fmt_money(m["attendu"]), fmt_money(m["paye"])]
                   for m in suivi]
        table_suivi.remplir(valeurs)
        # Composant themable "statuts" : teinte du montant paye.
        coul_p = lire_composant("statuts")
        for i, m in enumerate(suivi):
            cell = table_suivi.item(i, 2)
            if cell is not None:
                from PyQt5.QtGui import QColor
                regle = float(m.get("paye") or 0) >= float(m.get("attendu") or 0)
                cell.setForeground(QColor(coul_p["paye"] if regle else coul_p["du"]))
        if not suivi:
            vide_suivi.set_message(
                "Aucun paiement enregistre pour cet eleve sur l'annee active", "")
        pile_s.setCurrentWidget(vide_suivi if not suivi else table_suivi)

    combo_classe_s.currentIndexChanged.connect(fill_eleves)
    combo_eleve_s.currentIndexChanged.connect(refresh_suivi)
    fill_eleves()
    tabs.addTab(onglet_suivi, "Suivi Eleve")

    # ---------------- Onglet Bilans ----------------
    onglet_bilans = QWidget()
    lay_b = QVBoxLayout(onglet_bilans)
    filtre_b = QHBoxLayout()
    combo_annee_b = QComboBox()
    _annee_options(combo_annee_b)
    combo_trimestre_b = QComboBox()
    combo_trimestre_b.addItem("Tous les trimestres", None)
    for p in PERIODES:
        combo_trimestre_b.addItem(p, p)
    combo_type_b = QComboBox()
    combo_type_b.addItem("Tous les types", None)
    for t in TYPES_FRAIS:
        combo_type_b.addItem(t, t)
    combo_classe_b = QComboBox()
    combo_classe_b.addItem("Toutes les classes", None)
    for c in repos.classes():
        combo_classe_b.addItem(c["nom"], c["id"])
    combo_mode_b = QComboBox()
    _mode_options(combo_mode_b)
    filtre_b.addWidget(QLabel("Annee :"))
    filtre_b.addWidget(combo_annee_b)
    filtre_b.addWidget(QLabel("Trimestre :"))
    filtre_b.addWidget(combo_trimestre_b)
    filtre_b.addWidget(QLabel("Type :"))
    filtre_b.addWidget(combo_type_b)
    filtre_b.addWidget(QLabel("Classe :"))
    filtre_b.addWidget(combo_classe_b)
    filtre_b.addWidget(QLabel("Mode :"))
    filtre_b.addWidget(combo_mode_b)

    btn_bilan = QPushButton("Generer le Bilan")
    btn_bilan.setCursor(Qt.PointingHandCursor)
    btn_bilan.setStyleSheet(STYLE_BTN_PRIMARY)
    filtre_b.addWidget(btn_bilan)
    lay_b.addLayout(filtre_b)
    lbl_bilan_total = QLabel(f"Total : {fmt_money(0)}")
    lbl_bilan_total.setStyleSheet(
        f"font-size: 18px; font-weight: bold; color: {Colors.PRIMARY};")
    lay_b.addWidget(lbl_bilan_total)

    table_b = DataTable()
    table_b.setColumnCount(8)
    table_b.setHorizontalHeaderLabels(
        ["Date", "Matricule", "Eleve", "Classe", "Type frais",
         "Montant", "Mode", "Trimestre"])
    vide_b = EmptyState(
        "Aucun paiement ne correspond a ces criteres",
        "Modifiez les filtres ou le trimestre pour voir d'autres encaissements.")
    pile_b = QStackedWidget()
    pile_b.addWidget(table_b)
    pile_b.addWidget(vide_b)
    lay_b.addWidget(pile_b, 1)

    def refresh_b():
        _reload_combo(combo_annee_b,
                      [("Toutes les annees", None)] +
                      [(a["libelle"], a["libelle"]) for a in repos.annees_scolaires()])
        _reload_combo(combo_classe_b, _classe_items())
        rows = repos.paiements(
            annee_scolaire=combo_annee_b.currentData() or None,
            trimestre=combo_trimestre_b.currentData() or None,
            type_frais=combo_type_b.currentData() or None,
            classe_id=combo_classe_b.currentData(),
            mode=combo_mode_b.currentData() or None)
        valeurs = [[p["date_paiement"], p["matricule"],
                    f"{p['prenom']} {p['nom']}", p["classe_nom"] or "-",
                    p["type_frais"] or "-", fmt_money(p["montant"]),
                    p["mode_reglement"] or "-", p["trimestre"] or "-"]
                   for p in rows]
        table_b.remplir(valeurs)
        pile_b.setCurrentWidget(vide_b if not rows else table_b)
        lbl_bilan_total.setText(
            f"Total : {fmt_money(sum(float(p['montant']) for p in rows))}")

    btn_bilan.clicked.connect(refresh_b)
    combo_annee_b.currentIndexChanged.connect(refresh_b)
    combo_trimestre_b.currentIndexChanged.connect(refresh_b)
    combo_type_b.currentIndexChanged.connect(refresh_b)
    combo_classe_b.currentIndexChanged.connect(refresh_b)
    combo_mode_b.currentIndexChanged.connect(refresh_b)
    tabs.addTab(onglet_bilans, "Bilans")

    def page_refresh():
        _reload_combo(combo_classe_p, _classe_items())
        _reload_combo(combo_classe_s, _classe_items())
        _reload_combo(combo_classe_b, _classe_items())
        fill_eleves()
        refresh_p()
        refresh_b()

    refresh_p()
    refresh_b()
    page.refresh = page_refresh


def open_paiement_dialog(parent, ctx, on_created):
    dlg = QDialog(parent)
    dlg.setWindowTitle("Nouveau Paiement")
    dlg.resize(460, 320)
    dlg.setMinimumSize(400, 260)
    lay = QVBoxLayout(dlg)
    form = QFormLayout()
    combo_classe = QComboBox()
    for c in repos.classes():
        combo_classe.addItem(c["nom"], c["id"])
    combo_eleve = QComboBox()
    combo_type = QComboBox()
    combo_type.addItems(["Scolarite", "Inscription", "Tenues", "Transport", "Cantine", "Autres"])
    combo_mode = QComboBox()
    combo_mode.addItems(list(MODES_PAIEMENT))
    combo_trimestre = QComboBox()
    combo_trimestre.addItem("-- Aucun --", "")
    for p in PERIODES:
        combo_trimestre.addItem(p, p)
    montant = _money_edit(minimum=1)
    form.addRow("Classe :", combo_classe)
    form.addRow("Eleve :", combo_eleve)
    form.addRow("Montant :", montant)
    form.addRow("Type de frais :", combo_type)
    form.addRow("Mode de reglement :", combo_mode)
    form.addRow("Trimestre :", combo_trimestre)
    lay.addLayout(form)
    buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
    buttons.button(QDialogButtonBox.Ok).setText("Valider")
    buttons.accepted.connect(dlg.accept)
    buttons.rejected.connect(dlg.reject)
    lay.addWidget(buttons)

    def fill_eleves():
        combo_eleve.clear()
        for e in repos.eleves(classe_id=combo_classe.currentData()):
            combo_eleve.addItem(f"{e['prenom']} {e['nom']} ({e['matricule']})", e["id"])

    combo_classe.currentIndexChanged.connect(fill_eleves)
    fill_eleves()

    def valider():
        eleve_id = combo_eleve.currentData()
        if not eleve_id:
            QMessageBox.warning(dlg, "Paiement", "Selectionnez un eleve.")
            return
        if montant.value() <= 0:
            QMessageBox.warning(dlg, "Paiement", "Le montant doit etre superieur a 0.")
            return
        active = repos.annee_scolaire_active()
        annee = active["libelle"] if active else ""
        if refuser_si_hors_annee(dlg, datetime.date.today().isoformat(),
                                 "La date du paiement (aujourd'hui)"):
            return
        solde = repos.solde_eleve(eleve_id, annee)
        if montant.value() > float(solde["solde"]):
            from ui.pages.helpers import confirmer
            if not confirmer(
                    dlg,
                    f"Le solde restant de cet eleve est de "
                    f"{fmt_money(solde['solde'])} : ce paiement depasse le montant "
                    "attendu (trop-percu possible).\nEnregistrer quand meme ?",
                    "Sur-paiement"):
                return
        repos.add_paiement(eleve_id, montant.value(), combo_mode.currentText(),
                           combo_type.currentText(), annee,
                           combo_trimestre.currentData() or "")
        toast.succes(dlg, f"{fmt_money(montant.value())} encaisse.")
        dlg.accept()

    try:
        buttons.accepted.disconnect()
    except TypeError:
        pass
    buttons.accepted.connect(valider)

    dlg.exec_()
    if dlg.result() == QDialog.Accepted and on_created:
        on_created()
