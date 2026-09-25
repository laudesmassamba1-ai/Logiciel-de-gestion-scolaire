from functools import partial

from PyQt5.QtGui import QBrush, QColor
from PyQt5.QtWidgets import (
    QDialog, QLabel, QLineEdit, QMessageBox, QComboBox,
)

from repositories import repos
from ui import toast
from ui.loader import apply_ui
from core.config import (
    C_RED, C_BLUE, C_BLUE_LIGHT, C_BLUE_BORDER, C_RED_BG, C_RED_BORDER,
    C_TEXT_SECONDARY, STYLE_BTN_PRIMARY, STYLE_BTN_SECONDARY,
)
from ui.pages.helpers import (
    _btn, _simple_btn_style, _classe_items, _reload_combo, _actions_cell,
    _adapter_hauteur, _fond_aurora_dialog,
)
from ui.widgets import KPICard
from ui.widgets.page_templates import ListPageTemplate
from resources.design_tokens import Colors


def classes(page, ctx):
    if page.layout() is not None:
        return
    tpl = ListPageTemplate(page, "Classes")

    search = QLineEdit()
    search.setPlaceholderText("Rechercher une classe...")
    search.setMaximumWidth(360)
    combo_niveau = QComboBox()
    tpl.ajouter_filtre(search)
    tpl.ajouter_filtre(combo_niveau)
    tpl.ajouter_space_filtre()

    kpi = [
        tpl.ajouter_kpi(KPICard("Total classes", "0", Colors.PRIMARY), 0),
        tpl.ajouter_kpi(KPICard("Effectif total", "0", Colors.INFO), 1),
        tpl.ajouter_kpi(KPICard("Classes completes", "0", Colors.WARNING), 2),
        tpl.ajouter_kpi(KPICard("Sans titulaire", "0", Colors.DANGER), 3),
    ]
    tpl.table.setColumnCount(8)
    tpl.table.setHorizontalHeaderLabels(
        ["Classe", "Niveau", "Effectif", "Capacite", "Titulaire",
         "Salle", "Cycle", "Actions"])

    def _ouvrir_dialog(classe=None):
        open_classe_dialog(page, ctx, classe)
        fill()

    def _delete_classe(parent, ctx, c):
        from ui.pages.helpers import confirmer
        if confirmer(
                parent,
                f"Supprimer la classe {c['nom']} ?\n\n"
                "Attention : ses eleves ainsi que leurs notes, presences et "
                "paiements, le planning et les tarifs associes seront "
                "egalement supprimes.",
                "Supprimer"):
            repos.delete_classe(c["id"])
            toast.succes(parent, f"Classe {c['nom']} supprimee.")
            fill()

    def fill():
        _reload_combo(
            combo_niveau,
            [("Tous les niveaux", None)] +
            [(n, n) for n in sorted({c["niveau"] for c in repos.classes()
                                     if c.get("niveau")})])
        recherche = search.text().strip().lower()
        niveau = combo_niveau.currentData()
        all_rows = repos.classes()
        rows = all_rows
        if recherche:
            rows = [c for c in rows if recherche in c["nom"].lower()]
        if niveau:
            rows = [c for c in rows if c["niveau"] == niveau]
        valeurs = []
        for c in rows:
            valeurs.append([c["nom"], c["niveau"] or "-", c["effectif"],
                            c["capacite"], c["titulaire"] or "-",
                            c["salle"] or "-", c.get("cycle_nom") or "-", ""])
        tpl.remplir(
            valeurs,
            message_vide="Aucune classe")
        for i, c in enumerate(rows):
            item = tpl.table.item(i, 2)
            if c["capacite"] and c["effectif"] >= c["capacite"]:
                item.setForeground(QBrush(QColor(C_RED)))
                item.setToolTip("Classe complete")
            tpl.table.setCellWidget(i, 7, _actions_cell(
                _btn("Modifier", partial(open_classe_dialog, page, ctx, c),
                     _simple_btn_style(bg=C_BLUE_LIGHT, fg=C_BLUE, border=C_BLUE_BORDER)),
                _btn("Supprimer", partial(_delete_classe, page, ctx, c),
                     _simple_btn_style(bg=C_RED_BG, fg=C_RED, border=C_RED_BORDER))))
        page._classe_rows = rows

        kpi[0].set_value(len(all_rows))
        kpi[1].set_value(sum(c["effectif"] for c in all_rows))
        kpi[2].set_value(len([c for c in all_rows
                              if c["capacite"] and c["effectif"] >= c["capacite"]]))
        kpi[3].set_value(len([c for c in all_rows if not c.get("titulaire")]))

    btn_add = _btn("+ Nouvelle Classe", lambda: _ouvrir_dialog(), STYLE_BTN_PRIMARY)
    tpl.header.ajouter_action(btn_add)
    btn_pdf = _btn("Exporter PDF", lambda: _exporter_pdf(), STYLE_BTN_SECONDARY)
    tpl.header.ajouter_action(btn_pdf)

    def _exporter_pdf():
        from services import rapports
        rows = getattr(page, "_classe_rows", [])
        lignes = [[c["nom"], c["niveau"] or "-", c["effectif"],
                   c["capacite"], c["titulaire"] or "-",
                   c["salle"] or "-", c.get("cycle_nom") or "-"]
                  for c in rows]
        if not rapports.export_table_pdf(
                "Classes et effectifs",
                f"Filtres actuels - le {rapports._date_pdf()}",
                ["Classe", "Niveau", "Effectif", "Capacite", "Titulaire",
                 "Salle", "Cycle"], lignes,
                "rapport_classes.pdf"):
            toast.info(page, "Rien a exporter : aucune classe dans ce filtre.")

    search.textChanged.connect(fill)
    combo_niveau.currentIndexChanged.connect(fill)

    def double_clicked(row, _col):
        if 0 <= row < len(getattr(page, "_classe_rows", [])):
            _ouvrir_dialog(page._classe_rows[row])

    tpl.table.cellDoubleClicked.connect(double_clicked)
    tpl.table.setToolTip("Double-cliquez sur une ligne pour modifier la classe")

    fill()
    page.refresh = fill


def open_classe_dialog(parent, ctx, classe=None, on_created=None):
    dlg = QDialog(parent)
    dlg.setWindowTitle("Nouvelle Classe" if not classe else "Modifier la Classe")
    dlg.resize(460, 480)
    dlg.setMinimumSize(380, 400)
    apply_ui("classes/classe_dialog.ui", dlg)
    # Boutons themes par les tokens (le .ui garde des hex figes) :
    # le theme personnalise du configurateur s'applique aussi ici.
    dlg.btn_save.setStyleSheet(STYLE_BTN_PRIMARY)
    dlg.btn_cancel.setStyleSheet(STYLE_BTN_SECONDARY)
    _fond_aurora_dialog(dlg)

    combo_cycle = QComboBox()
    combo_cycle.addItem("-- Sans cycle --", None)
    for cyc in repos.cycles():
        combo_cycle.addItem(cyc["nom"], cyc["id"])
    lbl_cycle = QLabel("Cycle :")
    lbl_cycle.setStyleSheet(f"color: {C_TEXT_SECONDARY}; font-weight: bold; font-size: 12px;")
    dlg.mainLayout.insertWidget(5, lbl_cycle)
    dlg.mainLayout.insertWidget(6, combo_cycle)

    personnel = repos.personnel()
    dlg.combo_titulaire.clear()
    dlg.combo_titulaire.addItem("-- A affecter plus tard --", None)
    for p in personnel:
        dlg.combo_titulaire.addItem(p["nom_complet"], p["nom_complet"])

    if classe:
        dlg.lbl_dialog_title.setText("Modifier la Classe")
        dlg.input_nom_classe.setText(classe["nom"])
        idx = dlg.combo_niveau.findText(classe["niveau"]) if classe["niveau"] else -1
        if idx >= 0:
            dlg.combo_niveau.setCurrentIndex(idx)
        dlg.input_capacite.setValue(classe["capacite"] or 50)
        dlg.input_salle.setText(classe["salle"] or "")
        if classe.get("titulaire"):
            idx = dlg.combo_titulaire.findData(classe["titulaire"])
            if idx >= 0:
                dlg.combo_titulaire.setCurrentIndex(idx)
        idx = combo_cycle.findData(classe.get("cycle_id"))
        if idx >= 0:
            combo_cycle.setCurrentIndex(idx)

    def save():
        nom = dlg.input_nom_classe.text().strip()
        if not nom:
            QMessageBox.warning(dlg, "Classe", "Le nom de la classe est obligatoire.")
            return
        titulaire = dlg.combo_titulaire.currentData()
        if classe:
            repos.update_classe(classe["id"], nom, dlg.combo_niveau.currentText(),
                                dlg.input_capacite.value(), dlg.input_salle.text().strip(),
                                titulaire, combo_cycle.currentData())
        else:
            repos.add_classe(nom, dlg.combo_niveau.currentText(),
                             dlg.input_capacite.value(), dlg.input_salle.text().strip(),
                             titulaire, combo_cycle.currentData())
        if on_created:
            on_created()
        toast.succes(dlg, f"Classe {nom} enregistree.")
        dlg.accept()

    dlg.btn_save.clicked.connect(save)
    dlg.btn_cancel.clicked.connect(dlg.reject)
    _adapter_hauteur(dlg)
    dlg.exec_()
