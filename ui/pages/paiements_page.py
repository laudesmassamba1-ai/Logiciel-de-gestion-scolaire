from functools import partial

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QComboBox, QFormLayout, QPushButton, QTabWidget, QTableWidgetItem, QVBoxLayout,
    QWidget,
)

from repositories import repos
from ui.pages.helpers import (
    _btn, _simple_btn_style, _money_edit, _classe_items, _reload_combo,
    _add_btn, _kpi_card, _make_table, _page_header,
)
from ui.widgets import fmt_money
from core.config import PERIODES, C_EMPTY_STATE, STYLE_BTN_PRIMARY, C_BLUE, C_BLUE_LIGHT, C_BLUE_BORDER, C_GOLD, C_RED, C_RED_BG, C_RED_BORDER


def paiements(page, ctx):
    if page.layout() is not None:
        return
    page.setStyleSheet("")
    lay = QVBoxLayout(page)
    lay.setContentsMargins(20, 20, 20, 20)
    lay.setSpacing(16)
    _page_header(lay, "Paiements, Suivi & Bilans",
                 "Encaissements, suivi mensuel des eleves et bilans")

    tabs = QTabWidget()
    lay.addWidget(tabs)

    def _annee_options(combo):
        combo.clear()
        combo.addItem("Toutes les annees", None)
        for a in repos.annees_scolaires():
            combo.addItem(a["libelle"], a["libelle"])

    def _mode_options(combo):
        combo.addItem("Tous les modes", None)
        combo.addItems(["Especes", "Mobile Money (MTN / Moov)", "Cheque / Virement"])

    onglet_paiements = QWidget()
    lay_p = QVBoxLayout(onglet_paiements)
    filtre_p = QHBoxLayout()
    combo_classe_p = QComboBox()
    combo_classe_p.addItem("Toutes les classes", None)
    for c in repos.classes():
        combo_classe_p.addItem(c["nom"], c["id"])
    combo_type_p = QComboBox()
    combo_type_p.addItem("Tous les types", None)
    combo_type_p.addItems(["Scolarite", "Inscription", "Tenues", "Transport", "Cantine", "Autres"])
    combo_mode_p = QComboBox()
    _mode_options(combo_mode_p)
    filtre_p.addWidget(QLabel("Classe :"))
    filtre_p.addWidget(combo_classe_p)
    filtre_p.addWidget(QLabel("Type :"))
    filtre_p.addWidget(combo_type_p)
    filtre_p.addWidget(QLabel("Mode :"))
    filtre_p.addWidget(combo_mode_p)
    filtre_p.addStretch(1)
    btn_add_paiement = _add_btn("+ Nouveau Paiement", lambda: open_paiement_dialog(page, ctx, refresh_p))
    if ctx.can_edit("paiements"):
        filtre_p.addWidget(btn_add_paiement)
    lay_p.addLayout(filtre_p)

    kpi_p = QHBoxLayout()
    lbl_p_nb = _kpi_card("Nombre de paiements", "0")
    lbl_p_total = _kpi_card("Montant total", "0 FCFA", C_BLUE)
    for w in (lbl_p_nb, lbl_p_total):
        kpi_p.addWidget(w)
    lay_p.addLayout(kpi_p)

    table_p = _make_table(["Date", "Matricule", "Eleve", "Classe", "Type frais",
                           "Montant", "Mode", "Trimestre", "Actions"])
    lay_p.addWidget(table_p)
    lbl_empty_p = QLabel("Aucun paiement enregistre")
    lbl_empty_p.setStyleSheet(f"color: {C_EMPTY_STATE}; padding: 30px;")
    lbl_empty_p.setAlignment(Qt.AlignCenter)
    lay_p.addWidget(lbl_empty_p)

    def refresh_p():
        _reload_combo(combo_classe_p, _classe_items())
        rows = repos.paiements(
            classe_id=combo_classe_p.currentData(),
            type_frais=combo_type_p.currentData() or None,
            mode=combo_mode_p.currentData() or None)
        table_p.setRowCount(len(rows))
        for i, p in enumerate(rows):
            values = [p["date_paiement"], p["matricule"], f"{p['prenom']} {p['nom']}",
                      p["classe_nom"] or "-", p["type_frais"] or "-",
                      fmt_money(p["montant"]), p["mode_reglement"] or "-",
                      p["trimestre"] or "-"]
            for j, val in enumerate(values):
                table_p.setItem(i, j, QTableWidgetItem(str(val)))
            cell = QWidget()
            cl = QHBoxLayout(cell)
            cl.setContentsMargins(2, 2, 2, 2)
            if ctx.can_edit("paiements"):
                cl.addWidget(_btn("Supprimer", partial(_delete_paiement, page, ctx, p),
                                   _simple_btn_style(bg=C_RED_BG, fg=C_RED, border=C_RED_BORDER)))
            table_p.setCellWidget(i, 8, cell)
        table_p.resizeColumnsToContents()
        lbl_empty_p.setVisible(not rows)
        table_p.setVisible(bool(rows))
        lbl_p_nb.findChild(QLabel, "kpi_value").setText(str(len(rows)))
        lbl_p_total.findChild(QLabel, "kpi_value").setText(
            fmt_money(sum(float(p["montant"]) for p in rows)))

    def _delete_paiement(parent, ctx, p):
        if QMessageBox.question(parent, "Paiement",
                                "Supprimer ce paiement ?") == QMessageBox.Yes:
            repos.delete_paiement(p["id"])
            refresh_p()

    combo_classe_p.currentIndexChanged.connect(refresh_p)
    combo_type_p.currentIndexChanged.connect(refresh_p)
    combo_mode_p.currentIndexChanged.connect(refresh_p)
    tabs.addTab(onglet_paiements, "Paiements")

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
    lbl_attendu = _kpi_card("Total attendu", "0 FCFA", C_BLUE)
    lbl_paye = _kpi_card("Total paye", "0 FCFA", C_GOLD)
    lbl_solde = _kpi_card("Solde restant", "0 FCFA", C_RED)
    for w in (lbl_attendu, lbl_paye, lbl_solde):
        solde_lay.addWidget(w)
    lay_s.addLayout(solde_lay)

    table_suivi = _make_table(["Mois", "Attendu", "Paye"])
    lay_s.addWidget(table_suivi)

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
                w.findChild(QLabel, "kpi_value").setText("0 FCFA")
            return
        active = repos.annee_scolaire_active()
        annee = active["libelle"] if active else ""
        solde = repos.solde_eleve(eleve_id, annee)
        lbl_attendu.findChild(QLabel, "kpi_value").setText(fmt_money(solde["attendu"]))
        lbl_paye.findChild(QLabel, "kpi_value").setText(fmt_money(solde["paye"]))
        lbl_solde.findChild(QLabel, "kpi_value").setText(fmt_money(solde["solde"]))
        suivi = repos.suivi_mensuel(eleve_id, annee)
        table_suivi.setRowCount(len(suivi))
        for i, m in enumerate(suivi):
            table_suivi.setItem(i, 0, QTableWidgetItem(m["mois"]))
            table_suivi.setItem(i, 1, QTableWidgetItem(fmt_money(m["attendu"])))
            table_suivi.setItem(i, 2, QTableWidgetItem(fmt_money(m["paye"])))
        table_suivi.resizeColumnsToContents()

    combo_classe_s.currentIndexChanged.connect(fill_eleves)
    combo_eleve_s.currentIndexChanged.connect(refresh_suivi)
    fill_eleves()
    tabs.addTab(onglet_suivi, "Suivi Eleve")

    onglet_bilans = QWidget()
    lay_b = QVBoxLayout(onglet_bilans)
    filtre_b = QHBoxLayout()
    combo_annee_b = QComboBox()
    _annee_options(combo_annee_b)
    combo_trimestre_b = QComboBox()
    combo_trimestre_b.addItem("Tous les trimestres", None)
    combo_trimestre_b.addItems(list(PERIODES))
    combo_type_b = QComboBox()
    combo_type_b.addItem("Tous les types", None)
    combo_type_b.addItems(["Scolarite", "Inscription", "Tenues", "Transport", "Cantine", "Autres"])
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
    lay_b.addLayout(filtre_b)

    btn_bilan = QPushButton("Generer le Bilan")
    btn_bilan.setCursor(Qt.PointingHandCursor)
    btn_bilan.setStyleSheet(STYLE_BTN_PRIMARY)
    filtre_b.addWidget(btn_bilan)
    lbl_bilan_total = QLabel("Total : 0 FCFA")
    lbl_bilan_total.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {C_GOLD};")
    lay_b.addWidget(lbl_bilan_total)

    table_b = _make_table(["Date", "Matricule", "Eleve", "Classe", "Type frais",
                           "Montant", "Mode", "Trimestre"])
    lay_b.addWidget(table_b)

    def refresh_b():
        _reload_combo(combo_annee_b, [(a["libelle"], a["libelle"]) for a in repos.annees_scolaires()])
        _reload_combo(combo_classe_b, _classe_items())
        rows = repos.paiements(
            annee_scolaire=combo_annee_b.currentData() or None,
            trimestre=combo_trimestre_b.currentData() or None,
            type_frais=combo_type_b.currentData() or None,
            classe_id=combo_classe_b.currentData(),
            mode=combo_mode_b.currentData() or None)
        table_b.setRowCount(len(rows))
        for i, p in enumerate(rows):
            values = [p["date_paiement"], p["matricule"], f"{p['prenom']} {p['nom']}",
                      p["classe_nom"] or "-", p["type_frais"] or "-",
                      fmt_money(p["montant"]), p["mode_reglement"] or "-",
                      p["trimestre"] or "-"]
            for j, val in enumerate(values):
                table_b.setItem(i, j, QTableWidgetItem(str(val)))
        table_b.resizeColumnsToContents()
        lbl_bilan_total.setText(f"Total : {fmt_money(sum(float(p['montant']) for p in rows))}")

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
    combo_classe.addItem("Toutes les classes", None)
    for c in repos.classes():
        combo_classe.addItem(c["nom"], c["id"])
    combo_eleve = QComboBox()
    combo_type = QComboBox()
    combo_type.addItems(["Scolarite", "Inscription", "Tenues", "Transport", "Cantine", "Autres"])
    combo_mode = QComboBox()
    combo_mode.addItems(["Especes", "Mobile Money (MTN / Moov)", "Cheque / Virement"])
    combo_trimestre = QComboBox()
    combo_trimestre.addItem("-- Aucun --", "")
    combo_trimestre.addItems(list(PERIODES))
    montant = _money_edit(minimum=1)
    form.addRow("Classe :", combo_classe)
    form.addRow("Eleve :", combo_eleve)
    form.addRow("Montant :", montant)
    form.addRow("Type de frais :", combo_type)
    form.addRow("Mode de reglement :", combo_mode)
    form.addRow("Trimestre :", combo_trimestre)
    lay.addLayout(form)
    buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
    buttons.accepted.connect(dlg.accept)
    buttons.rejected.connect(dlg.reject)
    lay.addWidget(buttons)

    def fill_eleves():
        combo_eleve.clear()
        for e in repos.eleves(classe_id=combo_classe.currentData()):
            combo_eleve.addItem(f"{e['prenom']} {e['nom']} ({e['matricule']})", e["id"])

    combo_classe.currentIndexChanged.connect(fill_eleves)
    fill_eleves()

    if dlg.exec_() == QDialog.Accepted:
        eleve_id = combo_eleve.currentData()
        if not eleve_id or montant.value() <= 0:
            QMessageBox.warning(dlg, "Paiement", "Selectionnez un eleve et un montant valide.")
            return
        active = repos.annee_scolaire_active()
        annee = active["libelle"] if active else ""
        repos.add_paiement(eleve_id, montant.value(), combo_mode.currentText(),
                           combo_type.currentText(), annee, combo_trimestre.currentData())
        QMessageBox.information(dlg, "Paiement",
                                f"{fmt_money(montant.value())} encaisse.")
        if on_created:
            on_created()
