from functools import partial

import datetime

from PyQt5.QtCore import QDate
from PyQt5.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QComboBox,
)

from repositories import repos
from services import reports
from ui import toast
from ui.loader import apply_ui
from ui.pages.helpers import (
    _btn, _simple_btn_style, _classe_items, _reload_combo,
    _parse_money, refuser_si_hors_annee, _actions_cell, _adapter_hauteur,
)
from ui.widgets import KPICard, fmt_money
from ui.widgets.page_templates import ListPageTemplate
from core.config import (
    C_GOLD, C_BLUE, C_BLUE_LIGHT, C_BLUE_BORDER, C_RED, C_RED_BG,
    C_RED_BORDER, STYLE_BTN_PRIMARY, STYLE_BTN_SECONDARY,
)
from resources.design_tokens import Colors


def eleves(page, ctx):
    if page.layout() is not None:
        return
    tpl = ListPageTemplate(
        page, "Eleves",
        "Effectifs de toute l'ecole - filtrez par classe pour plus de lisibilite")

    search = QLineEdit()
    search.setPlaceholderText("Rechercher (nom, prenom, matricule)...")
    search.setMaximumWidth(360)
    combo_classe = QComboBox()
    combo_statut = QComboBox()
    combo_statut.addItems(["Tous les statuts", "Inscrit", "Pre-inscrit", "Inactif"])
    tpl.ajouter_filtre(search)
    tpl.ajouter_filtre(combo_classe)
    tpl.ajouter_filtre(combo_statut)
    tpl.ajouter_space_filtre()

    kpi = [
        tpl.ajouter_kpi(KPICard("Total eleves", "0", Colors.PRIMARY), 0),
        tpl.ajouter_kpi(KPICard("Pre-inscrits", "0", Colors.WARNING), 1),
        tpl.ajouter_kpi(KPICard("Inscrits", "0", Colors.INFO), 2),
        tpl.ajouter_kpi(KPICard("Inactifs", "0", Colors.DANGER), 3),
    ]
    tpl.table.setColumnCount(8)
    tpl.table.setHorizontalHeaderLabels(
        ["Matricule", "Nom complet", "Classe", "Sexe", "Naissance",
         "Tel tuteur", "Statut", "Actions"])

    def _ouvrir_inscription(eleve=None):
        open_inscription_dialog(page, ctx, eleve)
        fill()

    def _delete_eleve(parent, ctx, eleve):
        from ui.pages.helpers import confirmer
        if confirmer(
                parent,
                f"Supprimer l'élève {eleve['prenom']} {eleve['nom']} ?\n\n"
                "Attention : ses notes, presences et paiements seront "
                "également supprimés.",
                "Supprimer"):
            repos.delete_eleve(eleve["id"])
            fill()

    def fill():
        _reload_combo(combo_classe, _classe_items())
        classe_id = combo_classe.currentData()
        statut = combo_statut.currentText()
        recherche = search.text().strip()
        rows = repos.eleves(classe_id=classe_id, statut=statut, recherche=recherche)
        valeurs = [[e["matricule"], f"{e['prenom']} {e['nom']}",
                    e["classe_nom"] or "-", e["sexe"] or "-",
                    e["date_naissance"] or "-", e["tuteur_tel"] or "-",
                    e["statut"], ""] for e in rows]
        tpl.remplir(
            valeurs,
            message_vide="Aucun eleve trouve",
            sous_titre_vide="Modifiez votre recherche ou changez de filtre.")
        for i, e in enumerate(rows):
            tpl.table.setCellWidget(i, 7, _actions_cell(
                _btn("Modifier", partial(open_inscription_dialog, page, ctx, e),
                     _simple_btn_style(bg=C_BLUE_LIGHT, fg=C_BLUE, border=C_BLUE_BORDER)),
                _btn("Supprimer", partial(_delete_eleve, page, ctx, e),
                     _simple_btn_style(bg=C_RED_BG, fg=C_RED, border=C_RED_BORDER))))
        page._rows = rows

        eleves_all = repos.eleves(classe_id=classe_id)
        kpi[0].set_value(len(eleves_all))
        kpi[1].set_value(len([e for e in eleves_all if e["statut"] == "Pre-inscrit"]))
        kpi[2].set_value(len([e for e in eleves_all if e["statut"] == "Inscrit"]))
        kpi[3].set_value(len([e for e in eleves_all if e["statut"] == "Inactif"]))

        if classe_id:
            tpl.header.set_sous_titre(
                f"Effectifs et suivis scolaires - classe {combo_classe.currentText()}")
        else:
            tpl.header.set_sous_titre(
                "Effectifs de toute l'école - filtrez par classe pour plus de lisibilite")

    btn_add = _btn("+ Nouvel Eleve", lambda: _ouvrir_inscription(), STYLE_BTN_PRIMARY)
    tpl.header.ajouter_action(btn_add)
    btn_export = _btn("Exporter CSV",
                      lambda: reports.export_eleves_csv(getattr(page, "_rows", [])),
                      STYLE_BTN_SECONDARY)
    tpl.header.ajouter_action(btn_export)

    def populate_class_combo():
        combo_classe.clear()
        combo_classe.addItem("Toutes les classes", None)
        for c in repos.classes():
            combo_classe.addItem(c["nom"], c["id"])
        if combo_classe.count() > 1:
            combo_classe.setCurrentIndex(1)

    populate_class_combo()

    search.textChanged.connect(fill)
    combo_classe.currentIndexChanged.connect(fill)
    combo_statut.currentIndexChanged.connect(fill)

    def double_clicked(row, _col):
        if 0 <= row < len(getattr(page, "_rows", [])):
            _ouvrir_inscription(page._rows[row])

    tpl.table.cellDoubleClicked.connect(double_clicked)
    tpl.table.setToolTip("Double-cliquez sur une ligne pour modifier le dossier")

    fill()
    page.refresh = fill


def open_inscription_dialog(parent, ctx, eleve=None):
    dlg = QDialog(parent)
    dlg.setWindowTitle("Dossier d'Inscription")
    dlg.resize(1000, 780)
    dlg.setMinimumSize(800, 600)
    apply_ui("eleves/inscription.ui", dlg)

    lbl_matricule = QLabel()
    lbl_matricule.setStyleSheet(
        f"color: {C_GOLD}; font-weight: bold; font-size: 13px;")
    dlg.horizontalLayout_Header.addWidget(lbl_matricule)

    reins_row = QHBoxLayout()
    dlg.horizontalLayout_Header.addLayout(reins_row)
    input_reins = QLineEdit()
    input_reins.setPlaceholderText("Matricule (reinscription)")
    input_reins.setFixedWidth(160)
    btn_reins = _btn("Rechercher",
                     lambda: _load_reins(),
                      _simple_btn_style(bg=C_BLUE_LIGHT, fg=C_BLUE, border=C_BLUE_BORDER))
    reins_row.addWidget(input_reins)
    reins_row.addWidget(btn_reins)

    def update_matricule():
        if not eleve:
            lbl_matricule.setText(f"Matricule : {repos.next_matricule()}")
        else:
            lbl_matricule.setText(f"Matricule : {eleve['matricule']}")

    # Dossier charge via la recherche de reinscription : dans ce cas on
    # MET A JOUR l'eleve existant au lieu de creer un doublon.
    reins_source = {"eleve": None}

    def _load_reins():
        found = repos.eleve_by_matricule(input_reins.text().strip())
        if not found:
            QMessageBox.warning(dlg, "Reinscription",
                                f"Aucun eleve trouve avec le matricule {input_reins.text().strip()}.")
            return
        reins_source["eleve"] = found
        _fill_from(found)
        dlg.radio_new.setChecked(False)
        dlg.radio_reins.setChecked(True)
        lbl_matricule.setText(f"Reinscription de {found['prenom']} {found['nom']} "
                              f"({found['matricule']})")
        input_reins.setEnabled(False)
        btn_reins.setEnabled(False)

    def _fill_from(source):
        dlg.input_nom.setText(source["nom"])
        dlg.input_prenom.setText(source["prenom"])
        sexe = f"Sexe : {source['sexe']}" if source["sexe"] else "Sexe : Masculin"
        idx = dlg.combo_sexe.findText(sexe)
        if idx >= 0:
            dlg.combo_sexe.setCurrentIndex(idx)
        if source["date_naissance"]:
            dlg.date_naissance.setDate(
                QDate.fromString(source["date_naissance"], "yyyy-MM-dd"))
        dlg.input_lieu_naiss.setText(source["lieu_naissance"] or "")
        dlg.input_ecole_provenance.setText(source["ecole_provenance"] or "")
        dlg.input_pere_nom.setText(source["pere_nom"] or "")
        dlg.input_pere_tel.setText(source["pere_tel"] or "")
        dlg.input_mere_nom.setText(source["mere_nom"] or "")
        dlg.input_mere_tel.setText(source["mere_tel"] or "")
        dlg.input_tuteur_nom.setText(source["tuteur_nom"] or "")
        dlg.input_tuteur_tel.setText(source["tuteur_tel"] or "")
        dlg.input_adresse_famille.setText(source["adresse"] or "")
        idx = dlg.combo_classe.findData(source["classe_id"])
        if idx >= 0:
            dlg.combo_classe.setCurrentIndex(idx)

    def on_radio():
        is_reins = dlg.radio_reins.isChecked()
        input_reins.setEnabled(is_reins)
        btn_reins.setEnabled(is_reins)

    if eleve:
        dlg.setWindowTitle(f"Modifier - {eleve['prenom']} {eleve['nom']}")
        dlg.radio_new.setChecked(eleve["statut"] != "Pre-inscrit")
        dlg.radio_reins.setChecked(eleve["statut"] == "Pre-inscrit")
        dlg.input_nom.setText(eleve["nom"])
        dlg.input_prenom.setText(eleve["prenom"])
        sexe = f"Sexe : {eleve['sexe']}" if eleve["sexe"] else "Sexe : Masculin"
        idx = dlg.combo_sexe.findText(sexe)
        if idx >= 0:
            dlg.combo_sexe.setCurrentIndex(idx)
        if eleve["date_naissance"]:
            dlg.date_naissance.setDate(QDate.fromString(eleve["date_naissance"], "yyyy-MM-dd"))
        dlg.input_lieu_naiss.setText(eleve["lieu_naissance"] or "")
        dlg.input_ecole_provenance.setText(eleve["ecole_provenance"] or "")
        dlg.input_pere_nom.setText(eleve["pere_nom"] or "")
        dlg.input_pere_tel.setText(eleve["pere_tel"] or "")
        dlg.input_mere_nom.setText(eleve["mere_nom"] or "")
        dlg.input_mere_tel.setText(eleve["mere_tel"] or "")
        dlg.input_tuteur_nom.setText(eleve["tuteur_nom"] or "")
        dlg.input_tuteur_tel.setText(eleve["tuteur_tel"] or "")
        dlg.input_adresse_famille.setText(eleve["adresse"] or "")
        dlg.check_acte.setChecked(bool(eleve["check_acte"]))
        dlg.check_photos.setChecked(bool(eleve["check_photos"]))
        dlg.check_bulletin.setChecked(bool(eleve["check_bulletin"]))
        dlg.input_montant_verse.setEnabled(False)
        dlg.combo_mode_reglement.setEnabled(False)
        dlg.btn_save.setText("Enregistrer les Modifications")
        input_reins.setEnabled(False)
        btn_reins.setEnabled(False)

    def refresh_classes(select_id=None):
        dlg.combo_classe.clear()
        for c in repos.classes():
            dlg.combo_classe.addItem(c["nom"], c["id"])
        if select_id is not None:
            idx = dlg.combo_classe.findData(select_id)
            if idx >= 0:
                dlg.combo_classe.setCurrentIndex(idx)

    refresh_classes(eleve["classe_id"] if eleve else None)

    def add_classe():
        from ui.pages.classes_page import open_classe_dialog
        open_classe_dialog(dlg, ctx, on_created=refresh_classes)

    dlg.btn_add_classe.clicked.connect(add_classe)
    dlg.radio_new.toggled.connect(lambda _: on_radio())
    dlg.radio_reins.toggled.connect(lambda _: on_radio())
    on_radio()
    update_matricule()


    def save():
        nom = dlg.input_nom.text().strip()
        prenom = dlg.input_prenom.text().strip()
        if not nom or not prenom:
            QMessageBox.warning(dlg, "Inscription",
                                "Le nom et le prenom sont obligatoires.")
            return
        classe_id = dlg.combo_classe.currentData()
        if not classe_id:
            QMessageBox.warning(dlg, "Inscription",
                                "Selectionnez une classe (ou creez-en une).")
            return
        source = reins_source["eleve"]
        # Nouvelle inscription ou reinscription : l'ecriture date d'aujourd'hui,
        # elle doit tomber dans l'annee scolaire active.
        if not eleve and refuser_si_hors_annee(
                dlg, datetime.date.today().isoformat(),
                "La date d'inscription (aujourd'hui)"):
            return
        sexe = dlg.combo_sexe.currentText().split(":")[-1].strip()
        data = {
            "nom": nom, "prenom": prenom, "sexe": sexe,
            "date_naissance": dlg.date_naissance.date().toString("yyyy-MM-dd"),
            "lieu_naissance": dlg.input_lieu_naiss.text().strip(),
            "classe_id": classe_id,
            "ecole_provenance": dlg.input_ecole_provenance.text().strip(),
            "pere_nom": dlg.input_pere_nom.text().strip(),
            "pere_tel": dlg.input_pere_tel.text().strip(),
            "mere_nom": dlg.input_mere_nom.text().strip(),
            "mere_tel": dlg.input_mere_tel.text().strip(),
            "tuteur_nom": dlg.input_tuteur_nom.text().strip(),
            "tuteur_tel": dlg.input_tuteur_tel.text().strip(),
            "adresse": dlg.input_adresse_famille.text().strip(),
            "check_acte": 1 if dlg.check_acte.isChecked() else 0,
            "check_photos": 1 if dlg.check_photos.isChecked() else 0,
            "check_bulletin": 1 if dlg.check_bulletin.isChecked() else 0,
        }
        # Statut : la reinscription est explicite ; sinon on preserve le
        # statut existant en edition, ou on applique le choix en creation.
        if source:
            data["statut"] = "Inscrit"
            # Reinscription ne veut PAS dire redoublement : on preserve le
            # flag existant (seul un avis pedagogique le change).
            data["redoublant"] = source.get("redoublant", 0)
            data["matricule"] = source["matricule"]
        elif eleve:
            data["statut"] = ("Inscrit" if dlg.radio_reins.isChecked()
                              and eleve["statut"] != "Inscrit"
                              else eleve["statut"])
            data["redoublant"] = eleve["redoublant"]
            data["matricule"] = eleve["matricule"]
        else:
            data["statut"] = "Inscrit" if dlg.radio_reins.isChecked() else "Pre-inscrit"
            data["redoublant"] = 0

        def _encaisser_si_montant(matricule):
            montant = _parse_money(dlg.input_montant_verse.text())
            if not montant or montant <= 0:
                return
            mode = dlg.combo_mode_reglement.currentText().split(":")[-1].strip()
            reference = repos.add_transaction(
                "entree", montant, "Droits de scolarite - inscription",
                "Inscription", f"{prenom} {nom}",
                mode if mode and mode != "Especes" else "Especes")
            from ui.pages.helpers import confirmer
            if confirmer(
                    dlg,
                    f"{fmt_money(montant)} encaisse.\nImprimer le recu ?",
                    "Inscription"):
                reports.recu_paiement(
                    {"prenom": prenom, "nom": nom, "matricule": matricule},
                    montant, mode, reference)

        if eleve:
            repos.update_eleve(eleve["id"], data)
            toast.succes(dlg, f"Dossier de {prenom} {nom} mis a jour.")
        elif source:
            # Reinscription : mise a jour du dossier EXISTANT (pas de doublon)
            repos.update_eleve(source["id"], data)
            _encaisser_si_montant(source["matricule"])
            toast.succes(dlg,
                         f"{prenom} {nom} reinscrit. Matricule : {source['matricule']}")
        else:
            new_id = repos.add_eleve(data)
            _encaisser_si_montant(data["matricule"])
            if not (dlg.input_montant_verse.text() or "").strip() or \
                    _parse_money(dlg.input_montant_verse.text()) <= 0:
                toast.succes(dlg, f"Eleve inscrit. Matricule : {data['matricule']}")
        dlg.accept()

    dlg.btn_save.clicked.connect(save)
    dlg.btn_cancel.clicked.connect(dlg.reject)
    _adapter_hauteur(dlg)
    dlg.exec_()
