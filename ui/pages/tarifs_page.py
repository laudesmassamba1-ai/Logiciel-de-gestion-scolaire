from functools import partial

from PyQt5.QtWidgets import (
    QDialog, QDialogButtonBox, QLabel, QLineEdit, QMessageBox,
    QComboBox, QFormLayout, QVBoxLayout,
)

from repositories import repos
from ui import toast
from ui.pages.helpers import (
    _btn, _simple_btn_style, _money_edit, _classe_items, _reload_combo,
    _add_btn, _actions_cell,
)
from ui.widgets import fmt_money, KPICard
from ui.widgets.page_templates import ListPageTemplate
from resources.design_tokens import Colors
from core.config import (
    C_BLUE, C_BLUE_LIGHT, C_BLUE_BORDER, C_RED, C_RED_BG, C_RED_BORDER,
)


def tarifs(page, ctx):
    if page.layout() is not None:
        return
    tpl = ListPageTemplate(page, "Tarifs & Scolarite",
                           "Montants des frais par classe et par type")
    peut_editer = ctx.can_edit("tarifs")

    combo_classe = QComboBox()
    combo_classe.addItem("Toutes les classes", None)
    tpl.ajouter_filtre(QLabel("Classe :"))
    tpl.ajouter_filtre(combo_classe)
    tpl.ajouter_space_filtre()

    kpi = [
        tpl.ajouter_kpi(KPICard("Nombre de tarifs", "0"), 0),
        tpl.ajouter_kpi(KPICard("Montant moyen", "0", Colors.INFO), 1),
        tpl.ajouter_kpi(KPICard("Tarif minimum", "0", Colors.WARNING), 2),
        tpl.ajouter_kpi(KPICard("Tarif maximum", "0", Colors.DANGER), 3),
    ]
    tpl.table.setColumnCount(5)
    tpl.table.setHorizontalHeaderLabels(
        ["Classe", "Type de frais", "Montant", "Annee scolaire", "Actions"])

    btn_add_tarif = _add_btn(
        "+ Nouveau Tarif", lambda: open_tarif_dialog(page, ctx, refresh))
    if peut_editer:
        tpl.header.ajouter_action(btn_add_tarif)

    def refresh():
        _reload_combo(combo_classe, _classe_items())
        rows = repos.tarifs(classe_id=combo_classe.currentData())
        valeurs = [[t["classe_nom"] or "-", t["type_frais"],
                    fmt_money(t["montant"]), t["annee_scolaire"] or "-", ""]
                   for t in rows]
        tpl.remplir(
            valeurs,
            message_vide="Aucun tarif enregistre",
            sous_titre_vide="Creez le premier tarif de scolarite pour cette "
                            "annee scolaire.")
        for i, t in enumerate(rows):
            tpl.table.setCellWidget(i, 4, _actions_cell(*(
                (
                    _btn("Modifier", partial(open_tarif_dialog, page, ctx, refresh, t),
                         _simple_btn_style(bg=C_BLUE_LIGHT, fg=C_BLUE, border=C_BLUE_BORDER)),
                    _btn("Supprimer", partial(_delete_tarif, page, ctx, t),
                         _simple_btn_style(bg=C_RED_BG, fg=C_RED, border=C_RED_BORDER)),
                ) if peut_editer else ()
            )))
        nul = fmt_money(0)
        if rows:
            montants = [float(t["montant"]) for t in rows]
            kpi[0].set_value(str(len(rows)))
            kpi[1].set_value(fmt_money(sum(montants) / len(montants)))
            kpi[2].set_value(fmt_money(min(montants)))
            kpi[3].set_value(fmt_money(max(montants)))
        else:
            for carte in kpi:
                carte.set_value(nul if carte is not kpi[0] else "0")

    def _delete_tarif(parent, ctx, t):
        from ui.pages.helpers import confirmer
        if confirmer(
                parent,
                f"Supprimer le tarif {t['type_frais']} ({t['classe_nom']}) ?\n\n"
                "Attention : les calculs de solde scolarite des eleves de "
                "cette classe seront modifies (frais attendus reduits).",
                "Tarif"):
            repos.delete_tarif(t["id"])
            toast.succes(parent, "Tarif supprime.")
            refresh()

    combo_classe.currentIndexChanged.connect(refresh)
    refresh()
    page.refresh = refresh


def open_tarif_dialog(parent, ctx, on_created, tarif=None):
    dlg = QDialog(parent)
    dlg.setWindowTitle("Nouveau Tarif" if not tarif else "Modifier le Tarif")
    dlg.resize(440, 260)
    dlg.setMinimumSize(380, 220)
    lay = QVBoxLayout(dlg)
    form = QFormLayout()
    combo_classe = QComboBox()
    for c in repos.classes():
        combo_classe.addItem(c["nom"], c["id"])
    type_frais = QComboBox()
    type_frais.setEditable(True)
    type_frais.addItems(["Scolarite", "Inscription", "Tenues", "Transport", "Cantine", "Autres"])
    montant = _money_edit(minimum=1)
    annee = QLineEdit()
    active = repos.annee_scolaire_active()
    annee.setText(active["libelle"] if active else "")
    if tarif:
        idx = combo_classe.findData(tarif["classe_id"])
        if idx >= 0:
            combo_classe.setCurrentIndex(idx)
        idx = type_frais.findText(tarif["type_frais"])
        if idx >= 0:
            type_frais.setCurrentIndex(idx)
        else:
            type_frais.setEditText(tarif["type_frais"])
        montant.setValue(float(tarif["montant"]))
        annee.setText(tarif["annee_scolaire"] or "")
    form.addRow("Classe :", combo_classe)
    form.addRow("Type de frais :", type_frais)
    form.addRow("Montant :", montant)
    form.addRow("Annee scolaire :", annee)
    lay.addLayout(form)
    buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
    btn_ok = buttons.button(QDialogButtonBox.Ok)
    btn_ok.setText("Valider")
    buttons.rejected.connect(dlg.reject)
    lay.addWidget(buttons)

    def valider():
        if combo_classe.currentData() is None:
            QMessageBox.warning(dlg, "Tarif", "Selectionnez une classe.")
            return
        if montant.value() <= 0:
            QMessageBox.warning(dlg, "Tarif", "Le montant doit etre superieur a 0.")
            return
        libelle_type = type_frais.currentText().strip()
        if not libelle_type:
            QMessageBox.warning(dlg, "Tarif", "Le type de frais est obligatoire.")
            return
        # Anti-doublon : meme classe + type + annee deja tarifé.
        # Le doublon n'est supprime qu'APRES l'enregistrement reussi du
        # nouveau tarif : jamais de perte si la validation echoue ensuite.
        doublon_id = None
        existants = repos.tarifs(classe_id=combo_classe.currentData())
        for t in existants:
            meme = (t["type_frais"].lower() == libelle_type.lower()
                    and (t["annee_scolaire"] or "") == annee.text().strip()
                    and (not tarif or t["id"] != tarif["id"]))
            if meme:
                from ui.pages.helpers import confirmer
                if not confirmer(
                        dlg,
                        "Un tarif identique existe deja pour cette classe, ce type "
                        "et cette annee. Le remplacer ?",
                        "Tarif"):
                    return
                doublon_id = t["id"]
                break
        if tarif:
            repos.update_tarif(tarif["id"], combo_classe.currentData(),
                               libelle_type, montant.value(), annee.text().strip())
        else:
            repos.add_tarif(combo_classe.currentData(), libelle_type,
                            montant.value(), annee.text().strip())
        if doublon_id is not None:
            repos.delete_tarif(doublon_id)
        toast.succes(dlg, "Tarif enregistre.")
        dlg.accept()

    btn_ok.clicked.connect(valider)

    dlg.exec_()
    if dlg.result() == QDialog.Accepted and on_created:
        on_created()
