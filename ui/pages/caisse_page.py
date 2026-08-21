from functools import partial

from PyQt5.QtCore import Qt, QDate
from PyQt5.QtWidgets import (
    QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QComboBox, QFormLayout, QTableWidgetItem, QVBoxLayout,
    QWidget,
)

from repositories import repos
from ui.loader import apply_ui
from ui.pages.helpers import (
    _btn, _simple_btn_style, _money_edit, _fit_rows,
)
from ui.widgets import fmt_money
from core.config import (
    STYLE_TABLE, STYLE_EMPTY_STATE,
    C_RED_BG, C_RED, C_RED_BORDER,
)


def caisse(page, ctx):
    if page.layout() is not None:
        return
    apply_ui("caisse/caisse.ui", page)
    page.setStyleSheet("")
    _fit_rows(page.table_transactions)
    page.table_transactions.setStyleSheet(STYLE_TABLE)

    if not ctx.can_edit("caisse"):
        page.btn_add_income.setVisible(False)
        page.btn_add_expense.setVisible(False)

    now = QDate.currentDate()
    page.date_start.setDate(now.addDays(-(now.day() - 1)))
    page.date_end.setDate(now)

    lbl_empty = QLabel("Aucune transaction sur la periode selectionnee")
    lbl_empty.setStyleSheet(STYLE_EMPTY_STATE)
    lbl_empty.setAlignment(Qt.AlignCenter)
    page.mainLayout.addWidget(lbl_empty)

    def refresh():
        type_filtre = page.combo_type.currentText()
        recherche = page.search_input.text().strip()
        if type_filtre == "Recettes uniquement":
            t = "entree"
        elif type_filtre == "Depenses uniquement":
            t = "sortie"
        else:
            t = None
        rows = repos.transactions(
            type_filtre=t, recherche=recherche,
            date_start=page.date_start.date().toString("yyyy-MM-dd"),
            date_end=page.date_end.date().toString("yyyy-MM-dd"))
        page.table_transactions.setRowCount(len(rows))
        total_entrees = 0.0
        total_sorties = 0.0
        for i, r in enumerate(rows):
            values = [r["date"], r["reference"], r["beneficiaire"] or "-",
                      r["motif"] or "-", r["categorie"] or "-"]
            for j, val in enumerate(values):
                page.table_transactions.setItem(i, j, QTableWidgetItem(str(val)))
            montant = float(r["montant"] or 0)
            if r["type"] == "entree":
                total_entrees += montant
                page.table_transactions.setItem(i, 5, QTableWidgetItem(fmt_money(montant)))
                page.table_transactions.setItem(i, 6, QTableWidgetItem(""))
            else:
                total_sorties += montant
                page.table_transactions.setItem(i, 5, QTableWidgetItem(""))
                page.table_transactions.setItem(i, 6, QTableWidgetItem(fmt_money(montant)))
            cell = QWidget()
            lay = QHBoxLayout(cell)
            lay.setContentsMargins(2, 2, 2, 2)
            if ctx.can_edit("caisse"):
                lay.addWidget(_btn("Supprimer", partial(_delete_transaction, page, ctx, r),
                                    _simple_btn_style(bg=C_RED_BG, fg=C_RED, border=C_RED_BORDER)))
            page.table_transactions.setCellWidget(i, 7, cell)
        page.table_transactions.resizeColumnsToContents()
        page.table_transactions.horizontalHeader().setStretchLastSection(True)
        page.table_transactions.horizontalHeader().setMinimumSectionSize(80)

        # Totaux coherent avec le filtre affiche.
        page.val_total_incomes.setText(fmt_money(total_entrees))
        page.val_total_expenses.setText(fmt_money(total_sorties))
        page.val_current_balance.setText(fmt_money(total_entrees - total_sorties))

        lbl_empty.setVisible(not rows)
        page.table_transactions.setVisible(bool(rows))

    def _delete_transaction(parent, ctx, t):
        if QMessageBox.question(parent, "Supprimer",
                                "Supprimer cette transaction ?") == QMessageBox.Yes:
            repos.delete_transaction(t["id"])
            refresh()

    page.btn_add_income.clicked.connect(
        lambda: open_transaction_dialog(page, ctx, "entree", on_created=refresh))
    page.btn_add_expense.clicked.connect(
        lambda: open_transaction_dialog(page, ctx, "sortie", on_created=refresh))
    page.btn_apply_filter.clicked.connect(refresh)
    page.search_input.textChanged.connect(refresh)
    page.combo_type.currentIndexChanged.connect(refresh)

    def export_csv():
        from PyQt5.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(page, "Exporter CSV",
                                              "transactions.csv", "CSV (*.csv)")
        if path:
            repos.export_transactions_csv(path)
            QMessageBox.information(page, "Export", f"Exporte vers {path}")

    page.btn_export.clicked.connect(export_csv)

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
        repos.add_transaction(
            type_trans, montant.value(), motif.text().strip() or "Sans motif",
            categorie.currentText(), beneficiaire.text().strip() or "-",
            mode.currentText())
        QMessageBox.information(dlg, "Caisse", "Transaction enregistree.")
        dlg.accept()

    btn_ok.clicked.connect(valider)

    dlg.exec_()
    if dlg.result() == QDialog.Accepted and on_created:
        on_created()
