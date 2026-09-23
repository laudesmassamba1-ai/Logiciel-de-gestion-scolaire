"""Reseau des postes — qui est connecte au serveur de l'ecole.

Tableau de bord des connexions (vue directeur/gestionnaire) :
- affiliation de CE poste (nom, role hote/client, version, systeme, code
  de l'ecole, adresse du serveur, etat de la synchro) ;
- liste des postes connus du serveur (battement de coeur `POST /present`) :
  adresse, systeme, version, en ligne / hors ligne, derniere activite ;
- actions : tester la connexion (latencer), synchroniser maintenant,
  actualiser, copier le code de l'ecole, ouvrir l'assistant reseau.

Les donnees viennent du serveur (`GET /postes`) : c'est la source de
verite partagee entre tous les postes de l'ecole.
"""

import datetime
import time

from PyQt5.QtWidgets import (
    QApplication, QFormLayout, QFrame, QHBoxLayout, QLabel, QMessageBox,
    QStackedWidget, QVBoxLayout,
)

from api.client import _request
from core import network
from core import config as _config
from core.config import (
    APP_VERSION, C_BORDER, C_CARD, C_PRIMARY, C_PRIMARY_LIGHT, C_BLUE_BORDER,
    C_GREEN, C_GREEN_BG, C_RED, C_TEXT_MUTED,
    C_TEXT_SECONDARY, STYLE_CARD, code_ecole, est_hote,
)
from services import poste
from ui import toast
from ui.workers import run_async
from ui.pages.helpers import _btn, _simple_btn_style
from ui.widgets import DataTable, EmptyState, PageHeader

SEUIL_EN_LIGNE = 120


class _CarteData(QFrame):
    """Petite carte KPI (« Apple minimal ») avec valeur et libelle pilotables."""

    def __init__(self, libelle, valeur="-", couleur=C_PRIMARY):
        super().__init__()
        self.setMaximumHeight(92)
        self.setStyleSheet(
            f"QFrame {{ background: {C_CARD}; border: 1px solid {C_BORDER};"
            " border-radius: 16px; }")
        v = QVBoxLayout(self)
        v.setContentsMargins(16, 8, 16, 8)
        v.setSpacing(4)
        self._valeur = QLabel(str(valeur))
        self._valeur.setStyleSheet(
            f"font-size: 22px; font-weight: 800; color: {couleur};")
        lab = QLabel(libelle)
        lab.setStyleSheet(
            f"font-size: 11px; color: {C_TEXT_MUTED}; font-weight: 600;")
        v.addWidget(self._valeur)
        v.addWidget(lab)

    def set_valeur(self, valeur):
        self._valeur.setText(str(valeur))

    def set_couleur(self, couleur):
        self._valeur.setStyleSheet(
            f"font-size: 22px; font-weight: 800; color: {couleur};")


def _age_humain(secondes):
    if secondes is None:
        return "-"
    if secondes < 60:
        return "a l'instant"
    if secondes < 3600:
        return f"il y a {secondes // 60} min"
    if secondes < 86400:
        return f"il y a {secondes // 3600} h"
    jours = secondes // 86400
    return f"il y a {jours} j"


def _derniere_activite(horodatage):
    if not horodatage:
        return "-"
    try:
        valeur = datetime.datetime.strptime(str(horodatage)[:19],
                                            "%Y-%m-%d %H:%M:%S")
        return valeur.strftime("%d/%m/%Y %H:%M")
    except ValueError:
        return str(horodatage)


def reseau(page, ctx):
    if page.layout() is not None:
        return

    lay = QVBoxLayout(page)
    lay.setContentsMargins(20, 20, 20, 20)
    lay.setSpacing(14)

    titre = PageHeader(
        "Reseau des postes",
        "Postes connectes au serveur de l'ecole, etat des connexions "
        "et affiliation de ce poste.")
    lay.addWidget(titre)

    kpi_en_ligne = _CarteData("Postes en ligne", "-", C_GREEN)
    kpi_etat = _CarteData("Etat du serveur", "-", C_PRIMARY)
    kpi_version = _CarteData("Version de l'app", APP_VERSION, C_PRIMARY)
    kpi_code = _CarteData("Code de l'ecole", code_ecole() or "-", C_PRIMARY)

    cartes = QHBoxLayout()
    cartes.setSpacing(12)
    for carte in (kpi_en_ligne, kpi_etat, kpi_version, kpi_code):
        cartes.addWidget(carte, 1)
    lay.addLayout(cartes)

    ident = poste.identite_poste()
    hote = est_hote()
    if not network.sync_active():
        role = "Mode autonome (synchronisation desactivee)"
        couleur_role = C_TEXT_MUTED
    elif hote:
        role = "Hote : serveur de l'ecole"
        couleur_role = C_PRIMARY
    else:
        role = "Poste du reseau (client connecte)"
        couleur_role = C_GREEN

    cadre_info = QFrame()
    cadre_info.setStyleSheet(STYLE_CARD)
    form = QFormLayout(cadre_info)
    form.setContentsMargins(16, 12, 16, 12)
    form.setSpacing(8)

    def _ligne_stat(texte, style):
        lbl = QLabel(texte)
        lbl.setStyleSheet(style)
        return lbl

    style_cle = f"color: {C_TEXT_MUTED}; font-size: 12px; font-weight: 600;"
    style_valeur = f"color: {C_TEXT_SECONDARY}; font-size: 12px;"
    form.addRow("Nom du poste",
                _ligne_stat(f"{ident['nom_poste']}"
                            " (ce poste)", style_valeur))
    form.addRow("Role dans le reseau", _ligne_stat(role, style_valeur))
    form.addRow("Systeme",
                _ligne_stat(ident.get("systeme", "-") or "-", style_valeur))
    form.addRow("Adresse du serveur",
                _ligne_stat(_config.API_BASE_URL, style_valeur))
    lay.addWidget(cadre_info)

    table = DataTable()
    table.setColumnCount(6)
    table.setHorizontalHeaderLabels(
        ["Poste", "Adresse IP", "Version", "Systeme", "Statut",
         "Derniere activite"])
    vide = EmptyState("Aucun poste connu",
                      "Les postes de l'ecole apparaitront ici des qu'ils "
                      "seront connectes.")
    pile = QStackedWidget()
    pile.addWidget(table)
    pile.addWidget(vide)
    lay.addWidget(pile, 1)

    rows = []

    def _charger_postes():
        data, err = _request("GET", "/postes")
        if err:
            return {"postes": []}, err
        return data, None

    def _afficher(resultat):
        data, err = resultat
        if err:
            macro = ("Serveur injoignable" if network.sync_active()
                     else "Synchronisation desactivee")
            kpi_en_ligne.set_valeur("-")
            kpi_etat.set_valeur(macro)
            kpi_etat.set_couleur(C_RED)
            vide.set_message("Serveur injoignable",
                             "Le serveur de l'ecole ne repond pas "
                             "(GS_API_URL).")
            pile.setCurrentWidget(vide)
            rows.clear()
            return
        postes = data.get("postes", [])
        now = time.monotonic()
        en_ligne = 0
        for p in postes:
            age = p.get("age_secondes")
            if age is not None and age < SEUIL_EN_LIGNE:
                en_ligne += 1
        kpi_en_ligne.set_valeur(f"{en_ligne} / {len(postes)}")
        kpi_etat.set_valeur("En ligne")
        kpi_etat.set_couleur(C_GREEN)

        valeurs = []
        for p in postes:
            ce_poste = p.get("uuid_poste") == ident["uuid_poste"]
            suffixe = " (hote)" if p.get("est_hote") else " (client)"
            nom = p.get("nom_poste") or "(poste sans nom)"
            if ce_poste:
                nom += " - ce poste"
            valeurs.append([
                nom + suffixe,
                p.get("adresse_ip") or "-",
                p.get("version_app") or "-",
                p.get("systeme") or "-",
                "",
                _age_humain(p.get("age_secondes"))])
        table.remplir(valeurs)
        for i, p in enumerate(postes):
            age = p.get("age_secondes")
            en_ligne_i = age is not None and age < SEUIL_EN_LIGNE
            if en_ligne_i:
                texte, fg, bg = "En ligne", C_GREEN, C_GREEN_BG
            else:
                texte, fg, bg = "Hors ligne", C_TEXT_MUTED, "transparent"
            lbl = QLabel(f"{texte}")
            lbl.setStyleSheet(
                f"color: {fg}; background: {bg}; border-radius: 8px;"
                " padding: 2px 8px; font-size: 11px; font-weight: 700;")
            lbl.setToolTip(
                "Vu pour la derniere fois : "
                f"{_derniere_activite(p.get('derniere_seen'))}")
            table.setCellWidget(i, 4, lbl)
        pile.setCurrentWidget(vide if not postes else table)
        table.horizontalHeader().setStretchLastSection(True)

    def rafraichir():
        nonlocal rows
        run_async(_charger_postes, _afficher)

    def _tester_connexion():
        depart = time.monotonic()
        data, err = _request("GET", "/ping")
        duree = (time.monotonic() - depart) * 1000
        if err:
            toast.erreur(page, f"Connexion impossible : {err}")
            return
        toast.succes(page, f"Le serveur de l'ecole repond en "
                            f"{duree:.0f} ms (code d'ecole : "
                            f"{code_ecole() or 'non defini'}).")

    def _synchroniser():
        from services.sync_service import synchroniser_maintenant

        def _fait(resultat):
            if resultat.get("erreurs"):
                toast.erreur(
                    page, "; ".join(resultat["erreurs"][:3]))
            else:
                total = (resultat.get("structure", 0)
                         + resultat.get("donnees", 0)
                         + resultat.get("comptes", 0)
                         + resultat.get("envoyes", 0))
                toast.succes(
                    page, f"Synchronisation terminee ({total} elements).")
            rafraichir()

        run_async(synchroniser_maintenant, _fait)

    def _copier_code():
        code = code_ecole()
        if not code:
            QMessageBox.warning(page, "Code de l'ecole",
                                "Aucun code d'ecole n'est defini sur ce "
                                "poste. Passez par l'assistant reseau.")
            return
        QApplication.clipboard().setText(code)
        toast.succes(page, "Code de l'ecole copie dans le presse-papiers.")

    def _configurer():
        if not ctx.authorizer.can_edit("parametres"):
            QMessageBox.information(
                page, "Configuration reseau",
                "Seul le directeur peut modifier la connexion entre "
                "les postes.")
            return
        from ui.assistant_serveur import ouvrir_assistant
        ouvrir_assistant(page, apres_changement=rafraichir)

    actions = QHBoxLayout()
    actions.setSpacing(10)
    actions.addWidget(_btn("Tester la connexion", _tester_connexion,
                           _simple_btn_style(bg=C_PRIMARY_LIGHT, fg=C_PRIMARY,
                                             border=C_BLUE_BORDER)))
    actions.addWidget(_btn("Synchroniser maintenant", _synchroniser,
                           _simple_btn_style(bg=C_PRIMARY_LIGHT, fg=C_PRIMARY,
                                             border=C_BLUE_BORDER)))
    actions.addWidget(_btn("Copier le code ecole", _copier_code,
                           _simple_btn_style(bg=C_CARD, fg=C_TEXT_SECONDARY,
                                             border=C_BORDER)))
    actions.addStretch(1)
    actions.addWidget(_btn("Configurer le reseau...", _configurer,
                           _simple_btn_style(bg=C_CARD, fg=C_TEXT_SECONDARY,
                                             border=C_BORDER)))
    actions.addWidget(_btn("Actualiser", rafraichir,
                           _simple_btn_style(bg=C_CARD, fg=C_TEXT_SECONDARY,
                                             border=C_BORDER)))
    lay.addLayout(actions)

    rafraichir()
    page.refresh = rafraichir