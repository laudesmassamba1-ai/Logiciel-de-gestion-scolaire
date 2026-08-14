"""Fabrication des pages et dialogues metier.

Chaque fabrique recoit un widget vide (PageContext) et le remplit :
- applique le fichier .ui correspondant
- cree les controleurs (signaux + donnees)
- expose une methode refresh() appelee lors de la navigation
"""
import datetime
from functools import partial
from pathlib import Path

from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QBrush, QColor
from PyQt5.QtWidgets import (
    QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QMessageBox, QPushButton, QTableWidgetItem, QVBoxLayout, QComboBox,
    QDoubleSpinBox, QCheckBox, QFormLayout, QWidget,
)

from config import JOURS, CRENEAUX, PERIODES, ROLE_LABELS
from database.db import hash_password
from models import repos
from services import api, auth, reports
from services.auth import RoleAuthorizer
from views.loader import apply_ui
from views.widgets import SimpleBarChart, SimplePieChart, fmt_money

# ---------------------------------------------------------------------------
# Contexte commun
# ---------------------------------------------------------------------------


class PageContext:
    def __init__(self, user, navigate):
        self.user = user
        self.role = user["role"]
        self.role_label = ROLE_LABELS.get(self.role, self.role)
        self.authorizer = RoleAuthorizer(self.role)
        self.navigate = navigate

    def can_edit(self, page):
        return self.authorizer.can_edit(page)


# ---------------------------------------------------------------------------
# Utilitaires
# ---------------------------------------------------------------------------


def _btn(text, callback, style=None):
    b = QPushButton(text)
    b.setCursor(Qt.PointingHandCursor)
    b.setMaximumHeight(28)
    if style:
        b.setStyleSheet(style)
    b.clicked.connect(callback)
    return b


def _simple_btn_style(bg="#f1f5f9", fg="#334155", border="#cbd5e1"):
    return (f"background-color: {bg}; color: {fg}; border: 1px solid {border};"
            " border-radius: 4px; padding: 3px 8px; font-size: 10px;")


def _money_edit(value=0, minimum=0, maximum=100000000):
    spin = QDoubleSpinBox()
    spin.setRange(minimum, maximum)
    spin.setDecimals(0)
    spin.setValue(value)
    spin.setPrefix("")
    spin.setSuffix(" FCFA")
    return spin


def _today_fr():
    jours = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
    mois = ["Janvier", "Fevrier", "Mars", "Avril", "Mai", "Juin",
            "Juillet", "Aout", "Septembre", "Octobre", "Novembre", "Decembre"]
    d = datetime.date.today()
    return f"{jours[d.weekday()]} {d.day} {mois[d.month - 1]} {d.year}"


def _fill_combos(combo, items, clear_first=True):
    if clear_first:
        combo.clear()
    for item in items:
        combo.addItem(item)


# ---------------------------------------------------------------------------
# Dashboard Admin
# ---------------------------------------------------------------------------


def dashboard_admin(page, ctx):
    apply_ui("dashboards/dashboard_admin.ui", page)

    def refresh():
        comptes = repos.utilisateurs()
        actifs = [c for c in comptes if c["actif"]]
        inactifs = [c for c in comptes if not c["actif"]]
        directeurs = [c for c in actifs if c["role"] == "directeur"]
        gestionnaires = [c for c in actifs if c["role"] == "gestionnaire"]
        page.lbl_kpi1_valeur.setText(str(len(actifs)))
        page.lbl_kpi2_valeur.setText(str(len(directeurs)))
        page.lbl_kpi3_valeur.setText(str(len(gestionnaires)))
        page.lbl_kpi4_valeur.setText(str(len(inactifs)))
        logs = auth.derniere_connexions()
        page.list_dernieres_connexions.clear()
        for log in logs:
            page.list_dernieres_connexions.addItem(
                f"{log['date_connexion']}  -  {log['nom_complet']} ({log['role']})")
        page.lbl_activite_empty.setVisible(not logs)

    page.btn_quick_nouveau_compte.clicked.connect(
        lambda: open_compte_dialog(page, ctx))
    page.btn_goto_comptes.clicked.connect(lambda: ctx.navigate("comptes"))
    page.btn_reset_password.clicked.connect(
        lambda: open_reset_password_dialog(page, ctx))

    refresh()
    page.refresh = refresh


# ---------------------------------------------------------------------------
# Dashboard Directeur
# ---------------------------------------------------------------------------


def dashboard_directeur(page, ctx):
    apply_ui("dashboards/dashboard_directeur.ui", page)

    def refresh():
        masse = repos.masse_salariale()
        enseignants = repos.enseignants()
        page.vk1_val.setText(fmt_money(masse))

        nb_ens_api, _ = api.client.total_enseignant()
        page.vk2_val.setText(
            f"{nb_ens_api} Enseignants" if nb_ens_api is not None
            else f"{len(enseignants)} Enseignants")
        page.vk3_val.setText("0 En Attente")

        frais = float(repos.parametres().get("frais_scolarite", "25000") or 0)
        _, _, solde = repos.caisse_totals()
        total_eleves = repos.stats_dashboard()["total_eleves"]
        encaisse_api, _ = api.client.total_montant_paiement()
        if encaisse_api is not None:
            solde = float(encaisse_api)
        attendu = frais * total_eleves
        taux = min(100.0, solde / attendu * 100) if attendu else 0.0
        page.vk4_val.setText(f"{taux:.1f} %")

        charts = _directeur_charts()
        chart_fin = SimpleBarChart(titre="Tresorerie sur 6 mois")
        chart_fin.set_data(charts["fin_labels"], charts["fin_values"])
        chart_scol = SimpleBarChart(titre="Effectifs par classe")
        chart_scol.set_data(charts["scol_labels"], charts["scol_values"])
        _replace_layout(page.layout_chart_finances, chart_fin)
        _replace_layout(page.layout_chart_scolarite, chart_scol)

        try:
            fonctions = {}
            src = repos.personnel()
            if not src:
                enseignants_api, _ = api.client.enseignants()
                src = enseignants_api or []
            for p in src:
                f = p.get("fonction") or p.get("statut") or "Autre"
                fonctions[f] = fonctions.get(f, 0) + 1
            if fonctions and hasattr(page, "layout_chart_personnel"):
                chart_perso = SimplePieChart(titre="Repartition du personnel")
                chart_perso.set_data(list(fonctions.keys())[:6],
                                     list(fonctions.values())[:6])
                _replace_layout(page.layout_chart_personnel, chart_perso)
        except Exception:
            pass

        classes = repos.classes()
        sans_titulaire = [c for c in classes if not c.get("titulaire")]
        page.table_validations.setRowCount(len(sans_titulaire))
        for i, c in enumerate(sans_titulaire):
            items = ["Direction", "Affectation titulaire", f"Classe {c['nom']}",
                     c.get("created_at") or "-", "A affecter"]
            for j, val in enumerate(items):
                page.table_validations.setItem(i, j, QTableWidgetItem(str(val)))
        page.table_validations.resizeColumnsToContents()

    def goto_classes(row=None, _col=None):
        ctx.navigate("classes")

    page.table_validations.cellDoubleClicked.connect(goto_classes)
    page.table_validations.setToolTip(
        "Double-cliquez pour ouvrir la page Classes et affecter un titulaire")

    page.btn_goto_personnel.clicked.connect(lambda: ctx.navigate("personnel"))
    page.btn_act_recrutement.clicked.connect(
        lambda: open_personnel_dialog(page, ctx))
    page.btn_act_paie.clicked.connect(lambda: reports.paie())
    page.btn_act_rapport_rh.clicked.connect(lambda: reports.rapport_rh())
    page.btn_act_auditer_caisse.clicked.connect(lambda: ctx.navigate("caisse"))

    refresh()
    page.refresh = refresh


def _directeur_charts():
    rows = repos.transactions()
    months = {}
    for r in rows:
        key = r["date"][:7]
        months.setdefault(key, 0)
        months[key] += r["montant"] if r["type"] == "entree" else -r["montant"]
    today = datetime.date.today()
    labels, values = [], []
    for i in range(5, -1, -1):
        d = today - datetime.timedelta(days=30 * i)
        key = d.strftime("%Y-%m")
        labels.append(d.strftime("%b"))
        values.append(int(months.get(key, 0)))
    classes = repos.classes()
    scol_labels = [c["nom"][:10] for c in classes[:6]]
    scol_values = [c["effectif"] for c in classes[:6]]
    return {"fin_labels": labels, "fin_values": values,
            "scol_labels": scol_labels, "scol_values": scol_values}


def _replace_layout(layout, widget):
    while layout.count():
        item = layout.takeAt(0)
        w = item.widget()
        if w:
            w.deleteLater()
    layout.addWidget(widget)


# ---------------------------------------------------------------------------
# Dashboard Gestionnaire
# ---------------------------------------------------------------------------


def dashboard_gestionnaire(page, ctx):
    apply_ui("dashboards/dashboard_gestionnaire.ui", page)

    def refresh():
        page.lbl_date.setText(_today_fr())
        stats = repos.stats_dashboard()
        total_api, _ = api.client.total_eleves()
        page.lbl_kpi1_valeur.setText(
            str(total_api) if total_api is not None else str(stats["total_eleves"]))
        page.lbl_kpi2_valeur.setText(str(stats["inscriptions_jour"]))
        enc_api, _ = api.client.total_montant_paiement()
        encaisse = float(enc_api) if enc_api is not None else stats["encaissements_jour"]
        page.lbl_kpi3_valeur.setText(fmt_money(encaisse))
        page.lbl_kpi4_valeur.setText(str(stats["dossiers_incomplets"]))

        actifs = repos.transactions(recherche="")[:8]
        page.list_activite_recente.clear()
        for t in actifs:
            sens = "+" if t["type"] == "entree" else "-"
            page.list_activite_recente.addItem(
                f"{t['date']}  {t['motif']}  {sens}{fmt_money(t['montant'])}")
        page.lbl_activite_empty.setVisible(not actifs)

        incomplets = repos.eleves()
        incomplets = [e for e in incomplets
                      if not (e["check_acte"] and e["check_photos"] and e["check_bulletin"])]
        page.list_dossiers_incomplets.clear()
        for e in incomplets[:8]:
            manque = []
            if not e["check_acte"]:
                manque.append("acte")
            if not e["check_photos"]:
                manque.append("photos")
            if not e["check_bulletin"]:
                manque.append("bulletin")
            page.list_dossiers_incomplets.addItem(
                f"{e['prenom']} {e['nom']}  - manque: {', '.join(manque)}")

        try:
            statuts = {}
            eleves_api, _ = api.client.eleve_recherche()
            source = eleves_api if eleves_api else repos.eleves()
            for e in source:
                s = e.get("statut") or "inconnu"
                statuts[s] = statuts.get(s, 0) + 1
            if statuts and hasattr(page, "layout_chart_statuts"):
                chart = SimplePieChart(titre="Repartition des eleves par statut")
                chart.set_data(list(statuts.keys()), list(statuts.values()))
                _replace_layout(page.layout_chart_statuts, chart)
        except Exception:
            pass

    page.btn_quick_inscrire.clicked.connect(
        lambda: open_inscription_dialog(page, ctx))
    page.btn_quick_recette.clicked.connect(
        lambda: open_transaction_dialog(page, ctx, "entree"))
    page.btn_quick_depense.clicked.connect(
        lambda: open_transaction_dialog(page, ctx, "sortie"))
    page.btn_quick_certificat.clicked.connect(
        lambda: open_certificat_dialog(page))

    refresh()
    page.refresh = refresh


# ---------------------------------------------------------------------------
# Eleves
# ---------------------------------------------------------------------------


def eleves(page, ctx):
    apply_ui("eleves/eleves.ui", page)

    def fill():
        classe_id = page.combo_classe.currentData()
        statut = page.combo_statut.currentText()
        recherche = page.search_eleve.text().strip()
        rows = repos.eleves(classe_id=classe_id, statut=statut, recherche=recherche)
        page.table_eleves.setRowCount(len(rows))
        for i, e in enumerate(rows):
            values = [e["matricule"], f"{e['prenom']} {e['nom']}",
                      e["classe_nom"] or "-", e["sexe"] or "-",
                      e["date_naissance"] or "-", e["tuteur_tel"] or "-", e["statut"]]
            for j, val in enumerate(values):
                page.table_eleves.setItem(i, j, QTableWidgetItem(str(val)))
            cell = QWidget()
            lay = QHBoxLayout(cell)
            lay.setContentsMargins(2, 2, 2, 2)
            lay.addWidget(_btn("Modifier",
                               partial(open_inscription_dialog, page, ctx, e),
                               _simple_btn_style(bg="#eff6ff", fg="#1d4ed8", border="#bfdbfe")))
            lay.addWidget(_btn("Supprimer",
                               partial(_delete_eleve, page, ctx, e),
                               _simple_btn_style(bg="#fef2f2", fg="#dc2626", border="#fecaca")))
            page.table_eleves.setCellWidget(i, 7, cell)
        page._rows = rows
        page.table_eleves.resizeColumnsToContents()
        page.lbl_empty_state.setVisible(not rows)
        page.table_eleves.setVisible(bool(rows))

        eleves_all = repos.eleves(classe_id=classe_id)
        page.v1_val.setText(str(len(eleves_all)))
        page.v2_val.setText(str(len([e for e in eleves_all if e["statut"] == "Pre-inscrit"])))
        page.v3_val.setText(str(len([e for e in eleves_all if e["statut"] == "Inscrit"])))
        page.v4_val.setText(str(len([e for e in eleves_all if e["statut"] == "Inactif"])))

        if classe_id:
            page.lbl_page_subtitle.setText(
                f"Effectifs et suivis scolaires - classe {page.combo_classe.currentText()}")
        else:
            page.lbl_page_subtitle.setText(
                "Effectifs de toute l'ecole - filtrez par classe pour plus de lisibilite")

    def _delete_eleve(parent, ctx, eleve):
        if QMessageBox.question(parent, "Supprimer",
                                f"Supprimer l'eleve {eleve['prenom']} {eleve['nom']} ?") \
                == QMessageBox.Yes:
            repos.delete_eleve(eleve["id"])
            fill()

    def populate_class_combo():
        page.combo_classe.clear()
        page.combo_classe.addItem("Toutes les classes", None)
        for c in repos.classes():
            page.combo_classe.addItem(c["nom"], c["id"])
        if page.combo_classe.count() > 1:
            page.combo_classe.setCurrentIndex(1)

    populate_class_combo()
    page.btn_add_eleve.clicked.connect(lambda: open_inscription_dialog(page, ctx))
    page.btn_apply_filter_eleves.clicked.connect(fill)
    page.search_eleve.textChanged.connect(fill)
    page.combo_classe.currentIndexChanged.connect(fill)
    page.combo_statut.currentIndexChanged.connect(fill)
    page.btn_export_eleves.clicked.connect(
        lambda: reports.export_eleves_csv(getattr(page, "_rows", [])))

    def double_clicked(row, _col):
        if 0 <= row < len(getattr(page, "_rows", [])):
            open_inscription_dialog(page, ctx, page._rows[row])

    page.table_eleves.cellDoubleClicked.connect(double_clicked)
    page.table_eleves.setToolTip("Double-cliquez sur une ligne pour modifier le dossier")

    fill()
    page.refresh = fill


# ---------------------------------------------------------------------------
# Inscription (eleve)
# ---------------------------------------------------------------------------


def open_inscription_dialog(parent, ctx, eleve=None):
    dlg = QDialog(parent)
    dlg.setWindowTitle("Dossier d'Inscription")
    dlg.resize(1000, 780)
    apply_ui("eleves/inscription.ui", dlg)

    # Apercu du matricule (nouveaux) + recherche pour les reinscriptions
    lbl_matricule = QLabel()
    lbl_matricule.setStyleSheet(
        "color: #047857; font-weight: bold; font-size: 13px;")
    dlg.horizontalLayout_Header.addWidget(lbl_matricule)

    reins_row = QHBoxLayout()
    dlg.horizontalLayout_Header.addLayout(reins_row)
    input_reins = QLineEdit()
    input_reins.setPlaceholderText("Matricule (reinscription)")
    input_reins.setFixedWidth(160)
    btn_reins = _btn("Rechercher",
                     lambda: _load_reins(),
                     _simple_btn_style(bg="#eff6ff", fg="#1d4ed8", border="#bfdbfe"))
    reins_row.addWidget(input_reins)
    reins_row.addWidget(btn_reins)

    def update_matricule():
        if not eleve:
            lbl_matricule.setText(f"Matricule : {repos.next_matricule()}")
        else:
            lbl_matricule.setText(f"Matricule : {eleve['matricule']}")

    def _load_reins():
        found = repos.eleve_by_matricule(input_reins.text().strip())
        if not found:
            QMessageBox.warning(dlg, "Reinscription",
                                f"Aucun eleve trouve avec le matricule {input_reins.text().strip()}.")
            return
        _fill_from(found)
        dlg.radio_new.setChecked(False)
        dlg.radio_reins.setChecked(True)
        lbl_matricule.setText(f"Reinscription de {found['prenom']} {found['nom']}")
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
            "statut": "Inscrit" if dlg.radio_reins.isChecked() else "Pre-inscrit",
        }
        if eleve:
            data["matricule"] = eleve["matricule"]
            repos.update_eleve(eleve["id"], data)
            QMessageBox.information(dlg, "Inscription",
                                    f"Dossier de {prenom} {nom} mis a jour.")
        else:
            new_id = repos.add_eleve(data)
            montant = _parse_money(dlg.input_montant_verse.text())
            if montant and montant > 0:
                mode = dlg.combo_mode_reglement.currentText().split(":")[-1].strip()
                reference = repos.add_transaction(
                    "entree", montant, "Droits de scolarite - inscription",
                    "Inscription", f"{prenom} {nom}",
                    mode if mode and mode != "Especes" else "Especes")
                if QMessageBox.question(
                        dlg, "Inscription",
                        f"Eleve inscrit. Matricule : {data['matricule']}\n"
                        f"{fmt_money(montant)} encaisse.\nImprimer le recu ?") \
                        == QMessageBox.Yes:
                    reports.recu_paiement(
                        {"prenom": prenom, "nom": nom, "matricule": data["matricule"]},
                        montant, mode, reference)
            else:
                QMessageBox.information(
                    dlg, "Inscription",
                    f"Eleve inscrit. Matricule : {data['matricule']}")
        dlg.accept()

    dlg.btn_save.clicked.connect(save)
    dlg.btn_cancel.clicked.connect(dlg.reject)
    dlg.exec_()


def _parse_money(text):
    try:
        return float(text.replace(" ", "").replace(",", "").replace("FCFA", "").strip())
    except (TypeError, ValueError):
        return 0.0


# ---------------------------------------------------------------------------
# Classes
# ---------------------------------------------------------------------------


def classes(page, ctx):
    apply_ui("classes/classes.ui", page)

    def fill():
        recherche = page.input_search_classe.text().strip().lower()
        niveau = page.combo_filter_niveau.currentText()
        rows = repos.classes()
        if recherche:
            rows = [c for c in rows if recherche in c["nom"].lower()]
        if niveau != "Tous les niveaux":
            rows = [c for c in rows if c["niveau"] == niveau]
        page.table_classes.setRowCount(len(rows))
        for i, c in enumerate(rows):
            effectif = c["effectif"]
            capacite = c["capacite"]
            values = [c["nom"], c["niveau"] or "-", effectif, capacite,
                      c["titulaire"] or "-", c["salle"] or "-"]
            for j, val in enumerate(values):
                item = QTableWidgetItem(str(val))
                if j == 2 and capacite and effectif >= capacite:
                    item.setForeground(QBrush(QColor("#b91c1c")))
                    item.setToolTip("Classe complete")
                page.table_classes.setItem(i, j, item)
            cell = QWidget()
            lay = QHBoxLayout(cell)
            lay.setContentsMargins(2, 2, 2, 2)
            lay.addWidget(_btn("Modifier", partial(open_classe_dialog, page, ctx, c),
                               _simple_btn_style(bg="#eff6ff", fg="#1d4ed8", border="#bfdbfe")))
            lay.addWidget(_btn("Supprimer", partial(_delete_classe, page, ctx, c),
                               _simple_btn_style(bg="#fef2f2", fg="#dc2626", border="#fecaca")))
            page.table_classes.setCellWidget(i, 6, cell)
        page._classe_rows = rows
        page.table_classes.resizeColumnsToContents()
        page.lbl_empty_state_classes.setVisible(not rows)
        page.table_classes.setVisible(bool(rows))

        all_rows = repos.classes()
        page.lbl_kpi1_valeur.setText(str(len(all_rows)))
        page.lbl_kpi2_valeur.setText(str(sum(c["effectif"] for c in all_rows)))
        page.lbl_kpi3_valeur.setText(str(len([c for c in all_rows if c["effectif"] >= c["capacite"]])))
        page.lbl_kpi4_valeur.setText(str(len([c for c in all_rows if not c.get("titulaire")])))

    def _delete_classe(parent, ctx, c):
        if QMessageBox.question(parent, "Supprimer",
                                f"Supprimer la classe {c['nom']} et ses eleves ?") \
                == QMessageBox.Yes:
            repos.delete_classe(c["id"])
            fill()

    niveaux = sorted({c["niveau"] for c in repos.classes() if c.get("niveau")})
    _fill_combos(page.combo_filter_niveau, ["Tous les niveaux"] + niveaux)

    page.btn_add_classe.clicked.connect(lambda: open_classe_dialog(page, ctx))
    page.btn_apply_filter_classe.clicked.connect(fill)
    page.input_search_classe.textChanged.connect(fill)
    page.combo_filter_niveau.currentIndexChanged.connect(fill)

    def double_clicked(row, _col):
        if 0 <= row < len(getattr(page, "_classe_rows", [])):
            open_classe_dialog(page, ctx, page._classe_rows[row])

    page.table_classes.cellDoubleClicked.connect(double_clicked)
    page.table_classes.setToolTip("Double-cliquez sur une ligne pour modifier la classe")

    fill()
    page.refresh = fill


def open_classe_dialog(parent, ctx, classe=None, on_created=None):
    dlg = QDialog(parent)
    dlg.setWindowTitle("Nouvelle Classe" if not classe else "Modifier la Classe")
    dlg.resize(460, 480)
    apply_ui("classes/classe_dialog.ui", dlg)

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

    def save():
        nom = dlg.input_nom_classe.text().strip()
        if not nom:
            QMessageBox.warning(dlg, "Classe", "Le nom de la classe est obligatoire.")
            return
        titulaire = dlg.combo_titulaire.currentData()
        if classe:
            repos.update_classe(classe["id"], nom, dlg.combo_niveau.currentText(),
                                dlg.input_capacite.value(), dlg.input_salle.text().strip(),
                                titulaire)
        else:
            repos.add_classe(nom, dlg.combo_niveau.currentText(),
                             dlg.input_capacite.value(), dlg.input_salle.text().strip(),
                             titulaire)
        if on_created:
            on_created()
        dlg.accept()

    dlg.btn_save.clicked.connect(save)
    dlg.btn_cancel.clicked.connect(dlg.reject)
    dlg.exec_()


# ---------------------------------------------------------------------------
# Notes et bulletins
# ---------------------------------------------------------------------------


def notes(page, ctx):
    apply_ui("notes/notes.ui", page)

    _fill_combos(page.combo_classe, [])
    for c in repos.classes():
        page.combo_classe.addItem(c["nom"], c["id"])
    _fill_combos(page.combo_matiere, [])
    for m in repos.matieres():
        page.combo_matiere.addItem(m["nom"], m["id"])
    _fill_combos(page.combo_periode, list(PERIODES))

    def _refresh_matieres(select_id=None):
        page.combo_matiere.blockSignals(True)
        page.combo_matiere.clear()
        for m in repos.matieres():
            page.combo_matiere.addItem(m["nom"], m["id"])
        if select_id is not None:
            idx = page.combo_matiere.findData(select_id)
            if idx >= 0:
                page.combo_matiere.setCurrentIndex(idx)
        page.combo_matiere.blockSignals(False)

    def add_matiere():
        from PyQt5.QtWidgets import QDialog, QFormLayout, QLineEdit, QDialogButtonBox
        dlg = QDialog(page)
        dlg.setWindowTitle("Nouvelle matiere")
        dlg.resize(360, 130)
        lay = QVBoxLayout(dlg)
        form = QFormLayout()
        nom = QLineEdit()
        form.addRow("Nom de la matiere :", nom)
        lay.addLayout(form)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        lay.addWidget(btns)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        if dlg.exec_() == QDialog.Accepted and nom.text().strip():
            repos.add_matiere(nom.text().strip())
            _refresh_matieres()
            page.lbl_notes_status.setText(f"Matiere '{nom.text().strip()}' ajoutee")

    btn_add_matiere = _btn("+ Matiere", add_matiere,
                           _simple_btn_style(bg="#ecfdf5", fg="#047857",
                                             border="#a7f3d0"))
    page.headerLayout.addWidget(btn_add_matiere)

    if not ctx.can_edit("notes"):
        page.btn_save_notes.setVisible(False)

    def recompute_row(row):
        d1 = _cell_float(page.table_notes.item(row, 2))
        d2 = _cell_float(page.table_notes.item(row, 3))
        comp = _cell_float(page.table_notes.item(row, 4))
        if d1 is None and d2 is None and comp is None:
            page.table_notes.setItem(row, 5, QTableWidgetItem(""))
            page.table_notes.setItem(row, 6, QTableWidgetItem(""))
            return
        moyenne = round(((d1 or 0) + (d2 or 0) + 2 * (comp or 0)) / 4, 2)
        page.table_notes.setItem(row, 5, QTableWidgetItem(f"{moyenne:.2f}"))
        page.table_notes.setItem(row, 6, QTableWidgetItem(_appreciation(moyenne)))

    def _cell_float(item):
        if not item or not item.text().strip():
            return None
        try:
            return float(item.text().replace(",", "."))
        except ValueError:
            return None

    def on_item_changed(item):
        if item.column() in (2, 3, 4):
            texte = item.text().replace(",", ".")
            if texte.strip():
                try:
                    val = float(texte)
                    if val < 0 or val > 20:
                        page.table_notes.blockSignals(True)
                        item.setText(f"{max(0.0, min(20.0, val)):.1f}")
                        page.table_notes.blockSignals(False)
                except ValueError:
                    page.table_notes.blockSignals(True)
                    item.setText("")
                    page.table_notes.blockSignals(False)
            recompute_row(item.row())
            page.lbl_notes_status.setText("Modifications en attente")

    page.table_notes.itemChanged.connect(on_item_changed)

    def load_classe():
        classe_id = page.combo_classe.currentData()
        matiere_id = page.combo_matiere.currentData()
        periode = page.combo_periode.currentText()
        if not classe_id or not matiere_id:
            QMessageBox.warning(page, "Notes",
                                "Choisissez une classe et une matiere.")
            return
        eleves_rows = repos.eleves(classe_id=classe_id)
        notes_rows = repos.notes_for(classe_id, matiere_id, periode)
        notes_map = {n["eleve_id"]: n for n in notes_rows}
        page.table_notes.blockSignals(True)
        page.table_notes.setRowCount(len(eleves_rows))
        for i, e in enumerate(eleves_rows):
            page.table_notes.setItem(i, 0, QTableWidgetItem(e["matricule"]))
            page.table_notes.setItem(i, 1, QTableWidgetItem(f"{e['prenom']} {e['nom']}"))
            note = notes_map.get(e["id"])
            for j, key in ((2, "devoir1"), (3, "devoir2"), (4, "composition")):
                val = note[key] if note and note[key] is not None else ""
                page.table_notes.setItem(i, j, QTableWidgetItem("" if val == "" else str(val)))
            recompute_row(i)
        page.table_notes.blockSignals(False)
        page.lbl_notes_status.setText(f"{len(eleves_rows)} eleves charges")
        page.table_notes.resizeColumnsToContents()

    def save_notes():
        classe_id = page.combo_classe.currentData()
        matiere_id = page.combo_matiere.currentData()
        periode = page.combo_periode.currentText()
        if not classe_id or not matiere_id:
            return
        eleves_rows = repos.eleves(classe_id=classe_id)
        saved = 0
        for i, e in enumerate(eleves_rows):
            d1 = _cell_float(page.table_notes.item(i, 2))
            d2 = _cell_float(page.table_notes.item(i, 3))
            comp = _cell_float(page.table_notes.item(i, 4))
            if d1 is None and d2 is None and comp is None:
                continue
            repos.save_note(e["id"], matiere_id, periode, d1, d2, comp)
            saved += 1
        page.lbl_notes_status.setText(f"{saved} notes enregistrees")
        QMessageBox.information(page, "Notes", f"{saved} notes enregistrees.")

    page.btn_charger_classe.clicked.connect(load_classe)
    page.btn_save_notes.clicked.connect(save_notes)

    def bulletins():
        classe_id = page.combo_classe.currentData()
        if not classe_id:
            QMessageBox.warning(page, "Bulletins", "Choisissez une classe.")
            return
        reports.bulletins(classe_id, page.combo_periode.currentText())

    page.btn_generer_bulletins.clicked.connect(bulletins)
    page.table_notes.setRowCount(0)
    page.refresh = load_classe


def _appreciation(moyenne):
    if moyenne >= 16:
        return "Excellent"
    if moyenne >= 14:
        return "Tres bien"
    if moyenne >= 12:
        return "Bien"
    if moyenne >= 10:
        return "Assez bien"
    if moyenne >= 8:
        return "Passable"
    return "Insuffisant"


# ---------------------------------------------------------------------------
# Planning
# ---------------------------------------------------------------------------

class PlanningCellDialog(QDialog):
    def __init__(self, parent, jour, creneau, matieres, current=None):
        super().__init__(parent)
        self.setWindowTitle(f"{jour} - {creneau}")
        self.resize(320, 120)
        lay = QVBoxLayout(self)
        form = QFormLayout()
        self.combo = QComboBox()
        self.combo.addItem("-- Libre --", None)
        for m in matieres:
            self.combo.addItem(m["nom"], m["nom"])
        self.salle = QLineEdit()
        self.salle.setPlaceholderText("Salle")
        if current:
            matiere = current.get("matiere")
            if matiere:
                idx = self.combo.findData(matiere)
                if idx >= 0:
                    self.combo.setCurrentIndex(idx)
            self.salle.setText(current.get("salle") or "")
        form.addRow("Matiere :", self.combo)
        form.addRow("Salle :", self.salle)
        lay.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        lay.addWidget(buttons)

    def values(self):
        return self.combo.currentData(), self.salle.text().strip()


def planning(page, ctx):
    apply_ui("planning/planning.ui", page)
    _fill_combos(page.combo_classe_planning, [])
    for c in repos.classes():
        page.combo_classe_planning.addItem(c["nom"], c["id"])

    editing = {"on": False}

    def refresh():
        classe_id = page.combo_classe_planning.currentData()
        page.table_planning.clearContents()
        if not classe_id:
            page.lbl_empty_state_planning.setVisible(True)
            page.table_planning.setVisible(False)
            return
        page.lbl_empty_state_planning.setVisible(False)
        page.table_planning.setVisible(True)
        grid = repos.planning_for(classe_id)
        for row in range(8):
            creneau = page.table_planning.verticalHeaderItem(row).text() if \
                page.table_planning.verticalHeaderItem(row) else CRENEAUX[row]
            for col in range(6):
                jour = page.table_planning.horizontalHeaderItem(col).text()
                entree = grid.get((jour, creneau))
                if entree:
                    texte = entree["matiere"] or ""
                    if entree.get("salle"):
                        texte += f" ({entree['salle']})"
                    page.table_planning.setItem(row, col, QTableWidgetItem(texte))

    def toggle_edit():
        if editing["on"]:
            _finish_edit()
        else:
            _start_edit()

    def _start_edit():
        if not page.combo_classe_planning.currentData():
            QMessageBox.warning(page, "Planning", "Choisissez d'abord une classe.")
            return
        editing["on"] = True
        page.btn_edit_planning.setText("Enregistrer le Planning")
        page.btn_edit_planning.setStyleSheet(
            "background-color: #047857; color: white; border: none; border-radius: 6px;"
            " padding: 10px 16px; font-weight: bold;")

    def _finish_edit():
        classe_id = page.combo_classe_planning.currentData()
        entries = []
        for row in range(8):
            creneau = page.table_planning.verticalHeaderItem(row).text() if \
                page.table_planning.verticalHeaderItem(row) else CRENEAUX[row]
            if "Pause" in creneau:
                continue
            for col in range(6):
                jour = page.table_planning.horizontalHeaderItem(col).text()
                item = page.table_planning.item(row, col)
                matiere = salle = None
                if item and item.text().strip():
                    texte = item.text()
                    if "(" in texte:
                        matiere = texte.split("(")[0].strip()
                        salle = texte.split("(")[1].rstrip(")").strip()
                    else:
                        matiere = texte
                    entries.append((jour, creneau, matiere, salle))
        repos.save_planning(classe_id, entries)
        editing["on"] = False
        page.btn_edit_planning.setText("Modifier")
        page.btn_edit_planning.setStyleSheet(
            "background-color: #ffffff; color: #334155; border: 1px solid #cbd5e1;"
            " border-radius: 6px; padding: 10px 16px; font-weight: bold;")
        QMessageBox.information(page, "Planning", "Emploi du temps enregistre.")
        refresh()

    def cell_double_clicked(row, col):
        if not editing["on"]:
            return
        creneau = page.table_planning.verticalHeaderItem(row).text() if \
            page.table_planning.verticalHeaderItem(row) else CRENEAUX[row]
        if "Pause" in creneau:
            return
        jour = page.table_planning.horizontalHeaderItem(col).text()
        current = {"matiere": None, "salle": None}
        item = page.table_planning.item(row, col)
        if item and item.text().strip():
            texte = item.text()
            current["matiere"] = texte.split("(")[0].strip()
            current["salle"] = texte.split("(")[1].rstrip(")").strip() if "(" in texte else None
        dlg = PlanningCellDialog(page, jour, creneau, repos.matieres(), current)
        if dlg.exec_() == QDialog.Accepted:
            matiere, salle = dlg.values()
            texte = matiere if matiere else ""
            if matiere and salle:
                texte += f" ({salle})"
            page.table_planning.setItem(row, col, QTableWidgetItem(texte))

    def print_planning():
        classe_id = page.combo_classe_planning.currentData()
        classe = repos.classe_by_id(classe_id) if classe_id else None
        if not classe:
            QMessageBox.warning(page, "Planning", "Choisissez une classe.")
            return
        reports.planning(classe)

    page.btn_edit_planning.clicked.connect(toggle_edit)
    page.table_planning.cellDoubleClicked.connect(cell_double_clicked)
    page.btn_print_planning.clicked.connect(print_planning)
    page.combo_classe_planning.currentIndexChanged.connect(refresh)

    refresh()
    page.refresh = refresh


# ---------------------------------------------------------------------------
# Caisse
# ---------------------------------------------------------------------------


def caisse(page, ctx):
    apply_ui("caisse/caisse.ui", page)

    if not ctx.can_edit("caisse"):
        page.btn_add_income.setVisible(False)
        page.btn_add_expense.setVisible(False)

    now = QDate.currentDate()
    page.date_start.setDate(now.addDays(-(now.day() - 1)))
    page.date_end.setDate(now)

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
        for i, r in enumerate(rows):
            values = [r["date"], r["reference"], r["beneficiaire"] or "-",
                      r["motif"] or "-", r["categorie"] or "-"]
            for j, val in enumerate(values):
                page.table_transactions.setItem(i, j, QTableWidgetItem(str(val)))
            montant = r["montant"]
            if r["type"] == "entree":
                page.table_transactions.setItem(i, 5, QTableWidgetItem(fmt_money(montant)))
                page.table_transactions.setItem(i, 6, QTableWidgetItem(""))
            else:
                page.table_transactions.setItem(i, 5, QTableWidgetItem(""))
                page.table_transactions.setItem(i, 6, QTableWidgetItem(fmt_money(montant)))
            cell = QWidget()
            lay = QHBoxLayout(cell)
            lay.setContentsMargins(2, 2, 2, 2)
            lay.addWidget(_btn("Supprimer", partial(_delete_transaction, page, ctx, r),
                               _simple_btn_style(bg="#fef2f2", fg="#dc2626", border="#fecaca")))
            page.table_transactions.setCellWidget(i, 7, cell)
        page.table_transactions.resizeColumnsToContents()

        entree, sortie, solde = repos.caisse_totals()
        page.val_total_incomes.setText(fmt_money(entree))
        page.val_total_expenses.setText(fmt_money(sortie))
        page.val_current_balance.setText(fmt_money(solde))

    def _delete_transaction(parent, ctx, t):
        if QMessageBox.question(parent, "Supprimer",
                                "Supprimer cette transaction ?") == QMessageBox.Yes:
            repos.delete_transaction(t["id"])
            refresh()

    page.btn_add_income.clicked.connect(
        lambda: open_transaction_dialog(page, ctx, "entree"))
    page.btn_add_expense.clicked.connect(
        lambda: open_transaction_dialog(page, ctx, "sortie"))
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


def open_transaction_dialog(parent, ctx, type_trans):
    dlg = QDialog(parent)
    dlg.setWindowTitle("Nouvelle Recette" if type_trans == "entree" else "Nouvelle Depense")
    dlg.resize(420, 300)
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
    buttons.button(QDialogButtonBox.Ok).setText("Valider")
    buttons.accepted.connect(dlg.accept)
    buttons.rejected.connect(dlg.reject)
    lay.addWidget(buttons)

    if dlg.exec_() == QDialog.Accepted:
        if montant.value() <= 0:
            QMessageBox.warning(dlg, "Caisse", "Le montant doit etre superieur a 0.")
            return
        repos.add_transaction(
            type_trans, montant.value(), motif.text().strip() or "Sans motif",
            categorie.currentText(), beneficiaire.text().strip() or "-",
            mode.currentText())
        QMessageBox.information(dlg, "Caisse", "Transaction enregistree.")


# ---------------------------------------------------------------------------
# Comptes
# ---------------------------------------------------------------------------


def comptes(page, ctx):
    apply_ui("comptes/comptes.ui", page)

    def refresh():
        role = page.combo_filter_role.currentText()
        recherche = page.input_search_compte.text().strip()
        rows = repos.utilisateurs(role=role, recherche=recherche)
        page.table_comptes.setRowCount(len(rows))
        for i, u in enumerate(rows):
            values = [u["nom_complet"], u["email"] or "-",
                      ROLE_LABELS.get(u["role"], u["role"]),
                      "Actif" if u["actif"] else "Inactif", u["created_at"][:10]]
            for j, val in enumerate(values):
                page.table_comptes.setItem(i, j, QTableWidgetItem(str(val)))
            cell = QWidget()
            lay = QHBoxLayout(cell)
            lay.setContentsMargins(2, 2, 2, 2)
            lay.addWidget(_btn("Activer" if not u["actif"] else "Desactiver",
                               partial(_toggle, page, ctx, u),
                               _simple_btn_style(bg="#ecfdf5", fg="#059669", border="#a7f3d0")))
            lay.addWidget(_btn("Mdp", partial(_reset_pwd, page, ctx, u),
                               _simple_btn_style(bg="#fffbeb", fg="#b45309", border="#fde68a")))
            lay.addWidget(_btn("Supprimer", partial(_delete_compte, page, ctx, u),
                               _simple_btn_style(bg="#fef2f2", fg="#dc2626", border="#fecaca")))
            page.table_comptes.setCellWidget(i, 5, cell)
        page.table_comptes.resizeColumnsToContents()
        page.lbl_empty_state_comptes.setVisible(not rows)
        page.table_comptes.setVisible(bool(rows))

        all_rows = repos.utilisateurs()
        actifs = [u for u in all_rows if u["actif"]]
        page.lbl_kpi1_valeur.setText(str(len(actifs)))
        page.lbl_kpi2_valeur.setText(str(len([u for u in actifs if u["role"] == "directeur"])))
        page.lbl_kpi3_valeur.setText(str(len([u for u in actifs if u["role"] == "gestionnaire"])))
        page.lbl_kpi4_valeur.setText(str(len([u for u in all_rows if not u["actif"]])))

    def _toggle(parent, ctx, u):
        repos.toggle_compte(u["id"], not u["actif"])
        refresh()

    def _reset_pwd(parent, ctx, u):
        new_pwd = auth.random_password()
        if QMessageBox.question(parent, "Reinitialisation",
                                f"Reinitialiser le mot de passe de {u['nom_complet']} ?\n"
                                f"Le nouveau mot de passe sera : {new_pwd}") == QMessageBox.Yes:
            repos.reset_password(u["id"], hash_password(new_pwd))
            QMessageBox.information(parent, "Reinitialisation",
                                    f"Nouveau mot de passe : {new_pwd}")

    def _delete_compte(parent, ctx, u):
        if QMessageBox.question(parent, "Supprimer",
                                f"Supprimer le compte de {u['nom_complet']} ?") \
                == QMessageBox.Yes:
            repos.delete_compte(u["id"])
            refresh()

    page.btn_add_compte.clicked.connect(lambda: open_compte_dialog(page, ctx))
    page.btn_apply_filter_compte.clicked.connect(refresh)
    page.input_search_compte.textChanged.connect(refresh)
    page.combo_filter_role.currentIndexChanged.connect(refresh)

    refresh()
    page.refresh = refresh


def open_compte_dialog(parent, ctx, compte=None):
    dlg = QDialog(parent)
    dlg.setWindowTitle("Nouveau Compte")
    dlg.resize(440, 520)
    apply_ui("comptes/compte_dialog.ui", dlg)
    if compte:
        dlg.lbl_dialog_title.setText("Modifier le Compte")
        dlg.input_nom_compte.setText(compte["nom_complet"])
        dlg.input_email_compte.setText(compte["email"] or "")
        dlg.input_telephone_compte.setText(compte["telephone"] or "")
        idx = dlg.combo_role_compte.findText(
            ROLE_LABELS.get(compte["role"], "").title() or
            compte["role"].capitalize())
        if idx >= 0:
            dlg.combo_role_compte.setCurrentIndex(idx)
        dlg.check_compte_actif.setChecked(bool(compte["actif"]))
        dlg.btn_save.setText("Enregistrer")

    def save():
        nom = dlg.input_nom_compte.text().strip()
        email = dlg.input_email_compte.text().strip()
        if not nom or not email:
            QMessageBox.warning(dlg, "Compte",
                                "Le nom complet et l'email sont obligatoires.")
            return
        role = dlg.combo_role_compte.currentText().lower()
        telephone = dlg.input_telephone_compte.text().strip()
        actif = dlg.check_compte_actif.isChecked()
        if compte:
            repos.update_compte(compte["id"], nom, email, telephone, role, actif)
            QMessageBox.information(dlg, "Compte", "Compte mis a jour.")
        else:
            password = auth.random_password()
            repos.add_compte(nom, email, telephone, role,
                             hash_password(password), actif)
            QMessageBox.information(
                dlg, "Compte",
                f"Compte cree pour {nom}.\nIdentifiant : {email.split('@')[0]}"
                f"\nMot de passe temporaire : {password}")
        dlg.accept()

    dlg.btn_save.clicked.connect(save)
    dlg.btn_cancel.clicked.connect(dlg.reject)
    dlg.exec_()


def open_change_password_dialog(parent, user):
    dlg = QDialog(parent)
    dlg.setWindowTitle("Changer mon mot de passe")
    dlg.resize(380, 200)
    lay = QVBoxLayout(dlg)
    form = QFormLayout()
    old = QLineEdit()
    old.setEchoMode(QLineEdit.Password)
    new = QLineEdit()
    new.setEchoMode(QLineEdit.Password)
    confirm = QLineEdit()
    confirm.setEchoMode(QLineEdit.Password)
    form.addRow("Ancien mot de passe :", old)
    form.addRow("Nouveau mot de passe :", new)
    form.addRow("Confirmer :", confirm)
    lay.addLayout(form)
    buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
    buttons.accepted.connect(dlg.accept)
    buttons.rejected.connect(dlg.reject)
    lay.addWidget(buttons)
    if dlg.exec_() == QDialog.Accepted:
        if not new.text() or new.text() != confirm.text():
            QMessageBox.warning(dlg, "Mot de passe",
                                "Les nouveaux mots de passe ne correspondent pas.")
            return
        ok, message = auth.change_password(user["id"], old.text(), new.text())
        QMessageBox.information(dlg, "Mot de passe", message)


def open_reset_password_dialog(parent, ctx):
    dlg = QDialog(parent)
    dlg.setWindowTitle("Reinitialiser un mot de passe")
    dlg.resize(400, 180)
    lay = QVBoxLayout(dlg)
    form = QFormLayout()
    combo = QComboBox()
    for u in repos.utilisateurs():
        if u["role"] != "admin":
            combo.addItem(f"{u['nom_complet']} ({u['role']})", u["id"])
    new_pwd = QLineEdit(auth.random_password())
    form.addRow("Compte :", combo)
    form.addRow("Nouveau mot de passe :", new_pwd)
    lay.addLayout(form)
    buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
    buttons.accepted.connect(dlg.accept)
    buttons.rejected.connect(dlg.reject)
    lay.addWidget(buttons)
    if dlg.exec_() == QDialog.Accepted:
        if not new_pwd.text().strip():
            QMessageBox.warning(dlg, "Mot de passe", "Mot de passe vide.")
            return
        repos.reset_password(combo.currentData(), hash_password(new_pwd.text()))
        QMessageBox.information(dlg, "Mot de passe", "Mot de passe reinitialise.")


# ---------------------------------------------------------------------------
# Personnel (module RH)
# ---------------------------------------------------------------------------


def personnel(page, ctx):
    page.setStyleSheet("background-color: #f8fafc;")
    lay = QVBoxLayout(page)
    lay.setContentsMargins(20, 20, 20, 20)
    lay.setSpacing(16)

    header = QVBoxLayout()
    titre = QLabel("Personnel & RH")
    titre.setStyleSheet("font-size: 24px; font-weight: bold; color: #0f172a;")
    sub = QLabel("Enseignants, administration et salaires")
    sub.setStyleSheet("color: #64748b; font-size: 13px;")
    header.addWidget(titre)
    header.addWidget(sub)
    lay.addLayout(header)

    top = QHBoxLayout()
    search = QLineEdit()
    search.setPlaceholderText("Rechercher un membre du personnel...")
    top.addWidget(search)
    top.addStretch(1)
    btn_add = _btn("+ Nouvel Employe",
                   lambda: open_personnel_dialog(page, ctx),
                   "background-color: #047857; color: white; border: none; border-radius: 6px;"
                   " padding: 10px 16px; font-weight: bold;")
    top.addWidget(btn_add)
    lay.addLayout(top)

    from PyQt5.QtWidgets import QTableWidget
    table = QTableWidget(0, 6)
    table.setHorizontalHeaderLabels(
        ["Nom complet", "Fonction", "Telephone", "Email", "Salaire", "Actions"])
    table.setEditTriggers(QTableWidget.NoEditTriggers)
    table.setSelectionBehavior(QTableWidget.SelectRows)
    table.setAlternatingRowColors(True)
    table.verticalHeader().setVisible(False)
    table.setStyleSheet(
        "QTableWidget { background: #ffffff; border: 1px solid #e2e8f0;"
        " border-radius: 8px; gridline-color: #f1f5f9; }"
        "QHeaderView::section { background: #f8fafc; font-weight: bold;"
        " padding: 8px; border: none; }")
    lay.addWidget(table)

    def fill():
        rows = repos.personnel(search.text().strip())
        table.setRowCount(len(rows))
        for i, p in enumerate(rows):
            values = [p["nom_complet"], p["fonction"] or "-", p["telephone"] or "-",
                      p["email"] or "-", fmt_money(p["salaire"])]
            for j, val in enumerate(values):
                table.setItem(i, j, QTableWidgetItem(str(val)))
            cell = QWidget()
            cl = QHBoxLayout(cell)
            cl.setContentsMargins(2, 2, 2, 2)
            cl.addWidget(_btn("Modifier", partial(open_personnel_dialog, page, ctx, p),
                              _simple_btn_style(bg="#eff6ff", fg="#1d4ed8", border="#bfdbfe")))
            cl.addWidget(_btn("Supprimer", partial(_delete, page, ctx, p),
                              _simple_btn_style(bg="#fef2f2", fg="#dc2626", border="#fecaca")))
            table.setCellWidget(i, 5, cell)
        table.resizeColumnsToContents()

    def _delete(parent, ctx, p):
        if QMessageBox.question(parent, "Personnel",
                                f"Supprimer {p['nom_complet']} ?") == QMessageBox.Yes:
            repos.delete_personnel(p["id"])
            fill()

    search.textChanged.connect(fill)
    fill()
    page.refresh = fill


def open_personnel_dialog(parent, ctx, employe=None):
    dlg = QDialog(parent)
    dlg.setWindowTitle("Nouvel Employe" if not employe else "Modifier Employe")
    dlg.resize(400, 260)
    lay = QVBoxLayout(dlg)
    form = QFormLayout()
    nom = QLineEdit()
    fonction = QLineEdit()
    fonction.setPlaceholderText("Ex: Enseignant Mathematiques")
    tel = QLineEdit()
    email = QLineEdit()
    salaire = _money_edit()
    statut = QComboBox()
    statut.addItems(["Contrat", "CDI", "Vacataire", "Stage"])
    form.addRow("Nom complet :", nom)
    form.addRow("Fonction :", fonction)
    form.addRow("Telephone :", tel)
    form.addRow("Email :", email)
    form.addRow("Salaire :", salaire)
    form.addRow("Statut :", statut)
    lay.addLayout(form)
    buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
    buttons.accepted.connect(dlg.accept)
    buttons.rejected.connect(dlg.reject)
    lay.addWidget(buttons)
    if employe:
        nom.setText(employe["nom_complet"])
        fonction.setText(employe["fonction"] or "")
        tel.setText(employe["telephone"] or "")
        email.setText(employe["email"] or "")
        salaire.setValue(employe["salaire"] or 0)
        idx = statut.findText(employe["statut"] or "Contrat")
        if idx >= 0:
            statut.setCurrentIndex(idx)
    if dlg.exec_() == QDialog.Accepted:
        if not nom.text().strip():
            QMessageBox.warning(dlg, "Personnel", "Le nom est obligatoire.")
            return
        data = (nom.text().strip(), fonction.text().strip(), tel.text().strip(),
                email.text().strip(), salaire.value(), statut.currentText())
        if employe:
            repos.update_personnel(employe["id"], *data)
        else:
            repos.add_personnel(*data)


# ---------------------------------------------------------------------------
# Certificat
# ---------------------------------------------------------------------------


def open_certificat_dialog(parent):
    dlg = QDialog(parent)
    dlg.setWindowTitle("Certificat de scolarite")
    dlg.resize(420, 160)
    lay = QVBoxLayout(dlg)
    form = QFormLayout()
    combo_classe = QComboBox()
    combo_classe.addItem("Toutes les classes", None)
    for c in repos.classes():
        combo_classe.addItem(c["nom"], c["id"])
    combo = QComboBox()

    def fill_eleves():
        combo.clear()
        for e in repos.eleves(classe_id=combo_classe.currentData()):
            combo.addItem(f"{e['prenom']} {e['nom']} ({e['matricule']})", e["id"])

    combo_classe.currentIndexChanged.connect(fill_eleves)
    form.addRow("Classe :", combo_classe)
    form.addRow("Eleve :", combo)
    fill_eleves()
    lay.addLayout(form)
    buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
    buttons.button(QDialogButtonBox.Ok).setText("Generer")
    buttons.accepted.connect(dlg.accept)
    buttons.rejected.connect(dlg.reject)
    lay.addWidget(buttons)
    if dlg.exec_() == QDialog.Accepted:
        eleve = repos.eleve_by_id(combo.currentData())
        if eleve:
            eleve["classe_nom"] = ""
            classe = repos.classe_by_id(eleve["classe_id"]) if eleve["classe_id"] else None
            if classe:
                eleve["classe_nom"] = classe["nom"]
            reports.certificat_scolarite(eleve, repos.parametres())


# ---------------------------------------------------------------------------
# Parametres
# ---------------------------------------------------------------------------


def parametres(page, ctx):
    apply_ui("parametres/parametres.ui", page)

    images = {"bandeau_haut": None, "bandeau_bas": None, "signature": None}
    upload_map = {"bandeau_haut": page.btn_upload1,
                  "bandeau_bas": page.btn_upload2,
                  "signature": page.btn_upload3}

    def load():
        params = repos.parametres()
        page.input_signer_name.setText(params.get("signataire_nom", ""))
        page.input_signer_title.setText(params.get("signataire_titre", ""))
        page.input_city.setText(params.get("ville", ""))
        page.input_country.setText(params.get("pays", ""))
        page.lbl_progression.setText("Progression de la configuration: 100%")

    def upload(key):
        from PyQt5.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(
            page, "Choisir une image", "", "Images (*.png *.jpg *.jpeg)")
        if path:
            images[key] = path
            page.lbl_status.setText(f"{key} choisi : {path.split('/')[-1]}")

    for key, btn in upload_map.items():
        btn.clicked.connect(partial(upload, key))

    def save():
        repos.set_parametre("signataire_nom", page.input_signer_name.text().strip())
        repos.set_parametre("signataire_titre", page.input_signer_title.text().strip())
        repos.set_parametre("ville", page.input_city.text().strip())
        repos.set_parametre("pays", page.input_country.text().strip())
        for key, path in images.items():
            if path:
                import shutil
                dest = __import__("config").DOCS_DIR / f"{key}_{datetime.date.today():%Y%m%d}{Path(path).suffix}"
                shutil.copy2(path, dest)
                repos.set_parametre(key, str(dest))
        page.lbl_status.setText("Configuration mise a jour.")
        QMessageBox.information(page, "Parametres", "Configuration enregistree.")

    def delete_config():
        if QMessageBox.question(page, "Parametres",
                                "Supprimer la configuration ?") == QMessageBox.Yes:
            repos.delete_parametres()
            load()
            page.lbl_status.setText("Configuration supprimee.")

    page.btn_update.clicked.connect(save)
    page.btn_delete.clicked.connect(delete_config)

    load()
    page.refresh = load
