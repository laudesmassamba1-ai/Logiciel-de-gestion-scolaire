"""Assistant graphique de connexion multi-postes.

Remplace TOUTE manipulation de terminal : le directeur clique sur un
bouton, le serveur integre demarre en mode SQLite (base = simple
fichier), et l'adresse a saisir sur les autres postes s'affiche.
"""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QCheckBox, QDialog, QGroupBox, QHBoxLayout, QLabel, QMessageBox,
    QSpinBox, QVBoxLayout, QWidget,
)

from core import network
from core.config import (
    C_BORDER, C_RED, C_RED_BG, C_RED_BORDER, C_TEXT, C_TEXT_MUTED,
    C_GOLD, C_GOLD_BG, C_GOLD_BORDER, C_GOLD_PRESSED,
    STYLE_BTN_PRIMARY,
)
from services import serveur_local
from ui.pages.helpers import _btn, _simple_btn_style


class AssistantServeur(QDialog):

    def __init__(self, parent=None, apres_changement=None):
        super().__init__(parent)
        self._apres_changement = apres_changement
        self.setWindowTitle("Connecter plusieurs postes")
        self.setMinimumWidth(560)

        racine = QVBoxLayout(self)
        racine.setSpacing(12)

        intro = QLabel(
            "Ce choix permet à plusieurs ordinateurs de l'école de partager "
            "les mêmes données (élèves, notes, paiements…).\n"
            "Aucune installation technique n'est nécessaire : tout est géré "
            "ici, en un clic.")
        intro.setWordWrap(True)
        intro.setStyleSheet(f"color: {C_TEXT}; font-size: 13px;")
        racine.addWidget(intro)

        # ---- Etat actuel -----------------------------------------------
        groupe_etat = QGroupBox("Etat actuel")
        groupe_etat.setStyleSheet(self._style_groupe())
        lay_etat = QVBoxLayout(groupe_etat)
        self.lbl_etat = QLabel()
        self.lbl_etat.setWordWrap(True)
        lay_etat.addWidget(self.lbl_etat)
        racine.addWidget(groupe_etat)

        # ---- Actions ----------------------------------------------------
        groupe_actions = QGroupBox("Que voulez-vous faire ?")
        groupe_actions.setStyleSheet(self._style_groupe())
        lay_actions = QVBoxLayout(groupe_actions)

        ligne_port = QHBoxLayout()
        lbl_port = QLabel("Port du serveur :")
        self.spin_port = QSpinBox()
        self.spin_port.setRange(1024, 65535)
        self.spin_port.setValue(serveur_local.port_configure())
        self.spin_port.setFixedWidth(100)
        ligne_port.addWidget(lbl_port)
        ligne_port.addWidget(self.spin_port)
        ligne_port.addStretch()
        lay_actions.addLayout(ligne_port)

        self.btn_activer = _btn(
            "Activer la connexion entre les postes",
            self.activer, STYLE_BTN_PRIMARY, max_h=44)
        lay_actions.addWidget(self.btn_activer)

        style_danger = _simple_btn_style(C_RED_BG, C_RED, C_RED_BORDER)
        self.btn_arreter = _btn(
            "Revenir au mode « un seul poste »",
            self.desactiver, style_danger, max_h=40)
        lay_actions.addWidget(self.btn_arreter)
        racine.addWidget(groupe_actions)

        # ---- Options de demarrage automatique ---------------------------
        groupe_auto = QGroupBox("Demarrage automatique")
        groupe_auto.setStyleSheet(self._style_groupe())
        lay_auto = QVBoxLayout(groupe_auto)

        self.chk_serveur_auto = QCheckBox(
            "Demarrer automatiquement le serveur quand l'application demarre")
        self.chk_serveur_auto.setStyleSheet(f"color: {C_TEXT}; font-size: 12px;")
        self.chk_serveur_auto.stateChanged.connect(self._on_serveur_auto_changed)
        lay_auto.addWidget(self.chk_serveur_auto)

        self.chk_app_auto = QCheckBox(
            "Lancer l'application automatiquement au demarrage de l'ordinateur")
        self.chk_app_auto.setStyleSheet(f"color: {C_TEXT}; font-size: 12px;")
        self.chk_app_auto.stateChanged.connect(self._on_app_auto_changed)
        lay_auto.addWidget(self.chk_app_auto)

        racine.addWidget(groupe_auto)

        # ---- Informations utiles ---------------------------------------
        self.groupe_infos = QGroupBox("Informations de connexion")
        self.groupe_infos.setStyleSheet(self._style_groupe())
        self.lay_infos = QVBoxLayout(self.groupe_infos)
        racine.addWidget(self.groupe_infos)

        btn_fermer = _btn("Fermer", self.accept, _simple_btn_style(),
                          max_h=36)
        racine.addWidget(btn_fermer, alignment=Qt.AlignRight)

        self.rafraichir()

    # ------------------------------------------------------------------

    @staticmethod
    def _style_groupe():
        return (f"QGroupBox {{ font-weight: bold; color: {C_TEXT}; "
                f"border: 1px solid {C_BORDER}; border-radius: 8px; "
                "padding: 12px; margin-top: 8px; }")

    def rafraichir(self):
        actif = network.sync_active()
        # Sonde courte : ne JAMAIS bloquer l'interface 15s.
        joignable = serveur_local.api_joignable(delai=1.2) if actif else False

        if actif and joignable:
            self.lbl_etat.setText(
                "La connexion entre les postes est ACTIVE et fonctionne.")
            self.lbl_etat.setStyleSheet("color: #166534; font-size: 13px;")
        elif actif:
            self.lbl_etat.setText(
                "La synchronisation est activée mais le serveur ne répond "
                "pas encore (démarrage en cours ou arrêté).")
            self.lbl_etat.setStyleSheet(f"color: {C_RED}; font-size: 13px;")
        else:
            self.lbl_etat.setText(
                "Mode « un seul poste » : les données restent sur cet "
                "ordinateur uniquement.")
            self.lbl_etat.setStyleSheet(f"color: {C_TEXT_MUTED}; font-size: 13px;")

        self.btn_activer.setEnabled(True)
        self.btn_arreter.setEnabled(actif)

        # Chargement de l'etat des options de demarrage automatique
        from core.config import lire_config_sync
        cfg = lire_config_sync()
        self.chk_serveur_auto.blockSignals(True)
        self.chk_serveur_auto.setChecked(bool(cfg.get("serveur_auto", False)))
        self.chk_serveur_auto.setEnabled(actif)
        self.chk_serveur_auto.blockSignals(False)

        from services.demarrage import est_auto_demarrage
        self.chk_app_auto.blockSignals(True)
        self.chk_app_auto.setChecked(est_auto_demarrage())
        self.chk_app_auto.blockSignals(False)

        # Infos reconstruites a chaque affichage
        while self.lay_infos.count():
            item = self.lay_infos.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        port = serveur_local.port_configure()
        infos = [
            ("Adresse pour les AUTRES postes", serveur_local.adresse_locale(port)),
            ("Adresse sur ce poste", f"http://127.0.0.1:{port}"),
        ]
        for titre, valeur in infos:
            ligne = QLabel(f"<b>{titre} :</b> {valeur}")
            ligne.setTextInteractionFlags(Qt.TextSelectableByMouse)
            ligne.setStyleSheet(f"color: {C_TEXT}; font-size: 13px;")
            self.lay_infos.addWidget(ligne)

        note = QLabel(
            "Sur chaque autre ordinateur, ouvrez l'application puis saisissez "
            "cette adresse dans Paramètres → Synchronisation.\n"
            "Le serveur doit rester allumé sur ce poste pour que les autres "
            "voient les données.")
        note.setWordWrap(True)
        note.setStyleSheet(f"color: {C_TEXT_MUTED}; font-size: 12px;")
        self.lay_infos.addWidget(note)

    # ------------------------------------------------------------------

    def activer(self):
        port = self.spin_port.value()
        self.btn_activer.setEnabled(False)
        self.btn_activer.setText("Démarrage en cours…")
        from PyQt5.QtWidgets import QApplication
        QApplication.processEvents()

        from core.config import ecrire_config_sync
        serveur_auto = self.chk_serveur_auto.isChecked()
        ecrire_config_sync(port=port, api_url=f"http://127.0.0.1:{port}",
                           serveur_auto=serveur_auto)
        _, message = serveur_local.demarrer_serveur(port, serveur_auto=serveur_auto)
        # Etat reel apres tentative (le serveur peut trainer a demarrer ;
        # le worker de synchro le detectera plus tard dans ce cas).
        # Si demarrer_serveur a deja echoue (paquets manquants, port occupe),
        # pas besoin d'attendre 2s de sonde inutile.
        if not serveur_local.serveur_disponible():
            en_ligne = False
        else:
            en_ligne = serveur_local.api_joignable(port, delai=2.0)
        network.set_sync_active(en_ligne)
        ecrire_config_sync(sync_active=en_ligne)

        self.btn_activer.setText("Activer la connexion entre les postes")
        self.btn_activer.setEnabled(True)
        self.rafraichir()

        boite = QMessageBox(self)
        boite.setWindowTitle("Connexion multi-postes")
        # en_ligne : etat reel mesure apres la tentative de demarrage
        # (l'ancien code utilisait une variable `ok` jamais definie ->
        # NameError a chaque activation).
        if en_ligne:
            boite.setIcon(QMessageBox.Information)
            boite.setText(message)
        else:
            boite.setIcon(QMessageBox.Warning)
            boite.setText(message)
        boite.exec_()

        if en_ligne and self._apres_changement:
            self._apres_changement()

    def desactiver(self):
        reponse = QMessageBox.question(
            self, "Confirmation",
            "Revenir au mode « un seul poste » ?\n\n"
            "Les données de CETTE machine sont conservées ; les autres "
            "postes ne pourront plus les consulter.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reponse != QMessageBox.Yes:
            return
        _, message = serveur_local.arreter_serveur()
        network.set_sync_active(False)
        from core.config import ecrire_config_sync
        ecrire_config_sync(sync_active=False, serveur_auto=False, pid=None)
        self.chk_serveur_auto.setChecked(False)
        self.rafraichir()
        QMessageBox.information(self, "Mode autonome", message)
        if self._apres_changement:
            self._apres_changement()

    def _on_serveur_auto_changed(self, state):
        from core.config import ecrire_config_sync
        ecrire_config_sync(serveur_auto=bool(state))

    def _on_app_auto_changed(self, state):
        if state:
            from services.demarrage import activer_auto_demarrage
            if not activer_auto_demarrage():
                QMessageBox.warning(
                    self, "Demarrage automatique",
                    "Impossible d'activer le lancement automatique de "
                    "l'application. Creez un raccourci dans le dossier "
                    "de demarrage de votre systeme.")
                self.chk_app_auto.blockSignals(True)
                self.chk_app_auto.setChecked(False)
                self.chk_app_auto.blockSignals(False)
        else:
            from services.demarrage import desactiver_auto_demarrage
            desactiver_auto_demarrage()


def ouvrir_assistant(parent=None, apres_changement=None):
    """Point d'entree pratique (badge, parametres)."""
    dialogue = AssistantServeur(parent, apres_changement)
    dialogue.exec_()
