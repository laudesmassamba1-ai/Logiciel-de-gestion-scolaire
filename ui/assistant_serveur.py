"""Assistant graphique de connexion multi-postes.

Remplace TOUTE manipulation de terminal : le directeur clique sur un
bouton, le serveur integre demarre en mode SQLite (base = simple
fichier), et l'adresse a saisir sur les autres postes s'affiche.

Presentation moderne : carte statut, adresse copiable en un clic,
feedback inline (aucune boite modale apres action).
"""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication, QCheckBox, QDialog, QFrame, QGraphicsDropShadowEffect,
    QHBoxLayout, QLabel, QLineEdit, QPushButton, QScrollArea, QSpinBox,
    QVBoxLayout, QWidget,
)
from PyQt5.QtGui import QColor

from core import network
from core.config import (
    C_CARD, C_BORDER, C_BG, C_INK, C_TEXT, C_TEXT_MUTED, C_TEXT_SECONDARY,
    C_RED, C_RED_BG, C_RED_BORDER, C_PRIMARY, C_PRIMARY_HOVER,
    C_GOLD_BG, C_GOLD_BORDER, C_GOLD_PRESSED,
    STYLE_BTN_PRIMARY,
)
from services import serveur_local
from ui.pages.helpers import _btn, _simple_btn_style, confirmer


def _carte():
    """Frame blanche arrondie avec ombre legere."""
    carte = QFrame()
    carte.setObjectName("serveurCarte")
    carte.setStyleSheet(
        f"QFrame#serveurCarte {{ background: {C_CARD};"
        f" border: 1px solid {C_BORDER}; border-radius: 14px; }}")
    return carte


def _titre_carte(texte):
    lbl = QLabel(texte)
    lbl.setStyleSheet(
        f"color: {C_TEXT_SECONDARY}; font-size: 12px; font-weight: 700;"
        " letter-spacing: 0.2px;")
    return lbl


def _chip(texte, bg, fg):
    lbl = QLabel(texte)
    lbl.setStyleSheet(
        f"background: {bg}; color: {fg}; border-radius: 12px;"
        " padding: 6px 14px; font-size: 12px; font-weight: 800;")
    lbl.setAlignment(Qt.AlignCenter)
    return lbl


class AssistantServeur(QDialog):

    def __init__(self, parent=None, apres_changement=None):
        super().__init__(parent)
        self._apres_changement = apres_changement
        self._scan_thread = None
        self.setWindowTitle("Connexion entre plusieurs postes")
        self.setMinimumSize(620, 520)
        self.resize(720, 640)
        self.setSizeGripEnabled(True)
        self.setStyleSheet(f"QDialog {{ background-color: {C_BG}; }}")

        enveloppe = QVBoxLayout(self)
        enveloppe.setContentsMargins(0, 0, 0, 0)
        enveloppe.setSpacing(0)

        conteneur = QWidget()
        racine = QVBoxLayout(conteneur)
        racine.setContentsMargins(24, 20, 24, 20)
        racine.setSpacing(12)
        self.racine = racine

        self._construire_entete(racine)
        self._construire_statut(racine)
        self._construire_connexion_client(racine)
        self._construire_adresse(racine)
        self._construire_actions(racine)
        self._construire_options(racine)
        self._construire_feedback(racine)
        self._construire_pied(racine)

        defile = QScrollArea()
        defile.setWidgetResizable(True)
        defile.setWidget(conteneur)
        defile.setFrameShape(QFrame.NoFrame)
        defile.setStyleSheet(
            f"QScrollArea {{ background: {C_BG}; border: none; }}"
            "QScrollBar:vertical { background: transparent; width: 10px; }"
            "QScrollBar::handle:vertical { background: #C9C9D4;"
            " border-radius: 5px; min-height: 30px; }"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical"
            " { height: 0; }")
        enveloppe.addWidget(defile)

        self.rafraichir()

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def _construire_entete(self, racine):
        ligne = QHBoxLayout()
        ligne.setSpacing(12)

        titre = QLabel("Connexion entre les postes")
        titre.setStyleSheet(
            f"color: {C_INK}; font-size: 17px; font-weight: 800;")
        ligne.addWidget(titre)
        ligne.addStretch(1)

        self.pilule = _chip("...", C_GOLD_BG, C_GOLD_PRESSED)
        ligne.addWidget(self.pilule)
        racine.addLayout(ligne)

        sous = QLabel(
            "Plusieurs ordinateurs de l'ecole partagent les memes donnees "
            "(eleves, notes, paiements...). Tout est gere ici, sans "
            "manipulation technique.")
        sous.setWordWrap(True)
        sous.setStyleSheet(f"color: {C_TEXT_MUTED}; font-size: 12px;")
        racine.addWidget(sous)

    def _construire_statut(self, racine):
        carte = _carte()
        lay = QVBoxLayout(carte)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(6)
        lay.addWidget(_titre_carte("Etat actuel"))
        self.lbl_etat = QLabel()
        self.lbl_etat.setWordWrap(True)
        self.lbl_etat.setStyleSheet(f"color: {C_TEXT}; font-size: 13px;")
        lay.addWidget(self.lbl_etat)
        racine.addWidget(carte)

    def _construire_adresse(self, racine):
        carte = _carte()
        lay = QVBoxLayout(carte)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(6)
        lay.addWidget(_titre_carte("Adresse pour les AUTRES postes"))

        ligne = QHBoxLayout()
        ligne.setSpacing(8)
        self.lbl_adresse = QLabel("Activez la connexion pour obtenir l'adresse.")
        self.lbl_adresse.setStyleSheet(
            f"background: {C_BG}; border: 1px solid {C_BORDER};"
            " border-radius: 12px; padding: 10px 14px; color: #20202A;"
            " font-family: 'DejaVu Sans Mono', monospace; font-size: 12px;")
        self.lbl_adresse.setTextInteractionFlags(Qt.TextSelectableByMouse)
        ligne.addWidget(self.lbl_adresse, 1)

        self.btn_copier = QPushButton("Copier")
        self.btn_copier.setCursor(Qt.PointingHandCursor)
        self.btn_copier.setMinimumHeight(38)
        self.btn_copier.setStyleSheet(
            f"QPushButton {{ background: {C_GOLD_BG}; color: {C_GOLD_PRESSED};"
            f" border: 1px solid {C_GOLD_BORDER}; border-radius: 12px;"
            " padding: 0 18px; font-weight: 700; font-size: 12px; }"
            "QPushButton:hover { background-color: #F7EECF; }")
        self.btn_copier.clicked.connect(self._copier_adresse)
        ligne.addWidget(self.btn_copier)
        lay.addLayout(ligne)

        self.lbl_adresse_local = QLabel("")
        self.lbl_adresse_local.setStyleSheet(
            f"color: {C_TEXT_MUTED}; font-size: 11px;")
        lay.addWidget(self.lbl_adresse_local)

        self._carte_adresse = carte
        racine.addWidget(carte)

    def _construire_connexion_client(self, racine):
        """Carte pour connecter ce poste a un PC serveur distant."""
        carte = _carte()
        lay = QVBoxLayout(carte)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(8)
        lay.addWidget(_titre_carte("Se connecter au PC serveur de l'ecole"))

        self.lbl_client_mode = QLabel(
            "Ce poste peut se connecter a un autre ordinateur qui "
            "héberge les donnees partagees (eleves, notes, paiements...).")
        self.lbl_client_mode.setStyleSheet(
            f"color: {C_TEXT_MUTED}; font-size: 12px;")
        self.lbl_client_mode.setWordWrap(True)
        lay.addWidget(self.lbl_client_mode)

        ligne_adr = QHBoxLayout()
        ligne_adr.setSpacing(8)
        lbl_serveur = QLabel("Adresse du serveur :")
        lbl_serveur.setStyleSheet(
            f"color: {C_TEXT_SECONDARY}; font-size: 13px;")
        self.input_adresse_serveur = QLineEdit()
        self.input_adresse_serveur.setPlaceholderText(
            "http://192.168.1.100:8000")
        self.input_adresse_serveur.setMinimumHeight(38)
        ligne_adr.addWidget(lbl_serveur)
        ligne_adr.addWidget(self.input_adresse_serveur, 1)

        self.btn_scan = QPushButton("Scanner")
        self.btn_scan.setCursor(Qt.PointingHandCursor)
        self.btn_scan.setMinimumHeight(38)
        self.btn_scan.setFixedWidth(90)
        self.btn_scan.setStyleSheet(
            f"QPushButton {{ background: {C_RED_BG}; color: {C_RED};"
            " border: 1px solid #E8C3C3; border-radius: 12px;"
            " padding: 0 12px; font-weight: 700; font-size: 12px; }"
            f"QPushButton:hover {{ background: {C_RED}22; }}"
            "QPushButton:disabled { opacity: 0.5; }")
        self.btn_scan.clicked.connect(self._scanner_reseau)
        ligne_adr.addWidget(self.btn_scan)

        self.btn_connecter = QPushButton("Connecter")
        self.btn_connecter.setCursor(Qt.PointingHandCursor)
        self.btn_connecter.setMinimumHeight(38)
        self.btn_connecter.setStyleSheet(STYLE_BTN_PRIMARY)
        self.btn_connecter.clicked.connect(self._connecter_client)
        ligne_adr.addWidget(self.btn_connecter)
        lay.addLayout(ligne_adr)

        self.btn_deconnecter = _btn(
            "Revenir au mode autonome (pas de serveur distant)",
            self._deconnecter_client,
            _simple_btn_style(C_RED_BG, C_RED, C_RED_BORDER), max_h=40)
        lay.addWidget(self.btn_deconnecter)

        self.lbl_client_statut = QLabel("")
        self.lbl_client_statut.setStyleSheet(
            f"color: {C_TEXT_SECONDARY}; font-size: 12px; padding: 2px 4px;")
        lay.addWidget(self.lbl_client_statut)

        self._carte_client = carte
        racine.addWidget(carte)

    def _construire_actions(self, racine):
        carte = _carte()
        lay = QVBoxLayout(carte)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(10)
        lay.addWidget(_titre_carte("Activer ou arreter la connexion"))

        ligne_port = QHBoxLayout()
        ligne_port.setSpacing(10)
        lbl_port = QLabel("Port du serveur :")
        lbl_port.setStyleSheet(f"color: {C_TEXT_SECONDARY}; font-size: 13px;")
        self.spin_port = QSpinBox()
        self.spin_port.setRange(1024, 65535)
        self.spin_port.setValue(serveur_local.port_configure())
        self.spin_port.setFixedWidth(110)
        self.spin_port.setMinimumHeight(38)
        ligne_port.addWidget(lbl_port)
        ligne_port.addWidget(self.spin_port)
        ligne_port.addStretch(1)
        lay.addLayout(ligne_port)

        self.btn_activer = _btn(
            "Activer la connexion multi-postes",
            self.activer, STYLE_BTN_PRIMARY, max_h=44)
        lay.addWidget(self.btn_activer)

        self.btn_hotspot = _btn(
            "Creer le reseau WiFi de l'ecole (hotspot)",
            self.creer_hotspot, _simple_btn_style(
                C_GOLD_BG, C_GOLD_PRESSED, C_GOLD_BORDER), max_h=40)
        self.btn_hotspot.setEnabled(False)
        lay.addWidget(self.btn_hotspot)

        style_danger = _simple_btn_style(C_RED_BG, C_RED, C_RED_BORDER)
        self.btn_arreter = _btn(
            "Revenir au mode « un seul poste »",
            self.desactiver, style_danger, max_h=40)
        lay.addWidget(self.btn_arreter)

        racine.addWidget(carte)

    def _construire_options(self, racine):
        carte = _carte()
        lay = QVBoxLayout(carte)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(8)
        lay.addWidget(_titre_carte("Demarrage automatique"))

        self.chk_serveur_auto = QCheckBox(
            "Demarrer le serveur en meme temps que l'application")
        self.chk_serveur_auto.setStyleSheet(f"color: {C_TEXT}; font-size: 12px;")
        self.chk_serveur_auto.stateChanged.connect(self._on_serveur_auto_changed)
        lay.addWidget(self.chk_serveur_auto)

        self.chk_app_auto = QCheckBox(
            "Lancer l'application au demarrage de l'ordinateur")
        self.chk_app_auto.setStyleSheet(f"color: {C_TEXT}; font-size: 12px;")
        self.chk_app_auto.stateChanged.connect(self._on_app_auto_changed)
        lay.addWidget(self.chk_app_auto)

        racine.addWidget(carte)

    def _construire_feedback(self, racine):
        self.lbl_feedback = QLabel("")
        self.lbl_feedback.setWordWrap(True)
        self.lbl_feedback.setStyleSheet(
            f"color: {C_TEXT_SECONDARY}; font-size: 12px; padding: 2px 4px;")
        self.lbl_feedback.hide()
        racine.addWidget(self.lbl_feedback)

    def _construire_pied(self, racine):
        ligne = QHBoxLayout()
        ligne.addStretch(1)
        btn_fermer = _btn("Fermer", self.accept, _simple_btn_style(), max_h=36)
        ligne.addWidget(btn_fermer)
        racine.addLayout(ligne)

    # ------------------------------------------------------------------
    # Etat
    # ------------------------------------------------------------------

    def _feedback(self, texte, erreur=False):
        self.lbl_feedback.setStyleSheet(
            f"background: {'#FDECEC' if erreur else '#FFF8E1'};"
            f" color: {C_RED if erreur else '#8A6410'};"
            " border-radius: 12px; padding: 10px 14px; font-size: 12px;"
            " font-weight: 600;")
        self.lbl_feedback.setText(texte)
        self.lbl_feedback.show()

    def _copier_adresse(self):
        adresse = self.lbl_adresse.text().strip()
        if not adresse or adresse.startswith("Activez"):
            return
        QApplication.clipboard().setText(adresse)
        self.btn_copier.setText("Copie !")
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(1200, lambda: self.btn_copier.setText("Copier"))

    def rafraichir(self):
        from core.config import API_BASE_URL, est_hote, ecrire_config_sync, lire_config_sync

        est_hote_mode = est_hote()
        actif = network.sync_active()
        joignable = serveur_local.api_joignable(delai=1.2) if actif else False

        # --- Afficher le bon mode (hote / client) ---
        self._carte_adresse.setVisible(est_hote_mode)
        self._carte_client.setVisible(not est_hote_mode)
        # L'avatar "serveur" est toujours visible dans les options

        if actif and joignable:
            self.pilule.setText("Connecte")
            self.pilule.setStyleSheet(
                "background: #E4F6E9; color: #1B7A3D; border-radius: 12px;"
                " padding: 6px 14px; font-size: 12px; font-weight: 800;")
            if est_hote_mode:
                self.lbl_etat.setText(
                    "Ce poste est le serveur et fonctionne : "
                    "les autres postes peuvent partager les donnees.")
            else:
                self.lbl_etat.setText(
                    "Ce poste est connecte au serveur de l'ecole.")
            self.lbl_etat.setStyleSheet("color: #166534; font-size: 13px;")
        elif actif:
            self.pilule.setText("Serveur injoignable")
            self.pilule.setStyleSheet(
                f"background: {C_RED_BG}; color: {C_RED}; border-radius: 12px;"
                " padding: 6px 14px; font-size: 12px; font-weight: 800;")
            if est_hote_mode:
                self.lbl_etat.setText(
                    "La synchronisation est activee mais le serveur ne repond "
                    "pas encore (demarrage en cours ou arrete).")
            else:
                self.lbl_etat.setText(
                    "La connexion au serveur distant ne repond pas. "
                    "Verifiez l'adresse et que le serveur est en marche.")
            self.lbl_etat.setStyleSheet(f"color: {C_RED}; font-size: 13px;")
        else:
            self.pilule.setText("Mode autonome")
            self.pilule.setStyleSheet(
                "background: #F1F1F5; color: #8A8A93; border-radius: 12px;"
                " padding: 6px 14px; font-size: 12px; font-weight: 800;")
            self.lbl_etat.setText(
                "Les donnees restent sur cet ordinateur uniquement. "
                "Activez la connexion pour partager avec les autres postes.")
            self.lbl_etat.setStyleSheet(
                f"color: {C_TEXT_MUTED}; font-size: 13px;")

        self.btn_activer.setEnabled(not actif and est_hote_mode)
        self.btn_arreter.setEnabled(actif and est_hote_mode)

        from services import hotspot
        self.btn_hotspot.setEnabled(
            est_hote_mode and hotspot.nmcli_disponible())
        if est_hote_mode and hotspot.nmcli_disponible() \
                and hotspot.hotspot_actif():
            self.btn_hotspot.setText("Arreter le reseau WiFi de l'ecole")
        else:
            self.btn_hotspot.setText("Creer le reseau WiFi de l'ecole (hotspot)")

        # --- Carte adresse (mode hote) ---
        port = serveur_local.port_configure()
        if actif and est_hote_mode:
            self.lbl_adresse.setText(serveur_local.adresse_locale(port))
            self.lbl_adresse_local.setText(
                f"Sur ce poste :  http://127.0.0.1:{port}")
            self.btn_copier.setEnabled(True)
        elif est_hote_mode:
            self.lbl_adresse.setText(
                "Activez la connexion pour obtenir l'adresse.")
            self.lbl_adresse_local.setText("")
            self.btn_copier.setEnabled(False)

        # --- Carte client ---
        if not est_hote_mode:
            # En mode client, on affiche l'adresse actuellement utilisee
            self.input_adresse_serveur.setText(
                API_BASE_URL if API_BASE_URL != "http://127.0.0.1:8000" else "")
            if actif:
                self.lbl_client_statut.setText(
                    f"Connecte a : {API_BASE_URL}")
                self.btn_connecter.setEnabled(False)
                self.btn_deconnecter.setEnabled(True)
                self.btn_deconnecter.show()
            else:
                self.lbl_client_statut.setText("")
                self.btn_connecter.setEnabled(True)
                self.btn_deconnecter.hide()

        # --- Options ---
        cfg = lire_config_sync()
        self.chk_serveur_auto.blockSignals(True)
        self.chk_serveur_auto.setChecked(bool(cfg.get("serveur_auto", False)))
        self.chk_serveur_auto.blockSignals(False)

        from services.demarrage import est_auto_demarrage
        self.chk_app_auto.blockSignals(True)
        self.chk_app_auto.setChecked(est_auto_demarrage())
        self.chk_app_auto.blockSignals(False)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def activer(self):
        """Active la connexion multi-postes. Le demarrage du serveur et la
        verrification de disponibilite s'executent hors du thread GUI."""
        port = self.spin_port.value()
        self.btn_activer.setEnabled(False)
        self.btn_activer.setText("Demarrage en cours...")
        QApplication.processEvents()

        from core.config import ecrire_config_sync
        serveur_auto = self.chk_serveur_auto.isChecked()
        ecrire_config_sync(port=port, api_url=f"http://127.0.0.1:{port}",
                           serveur_auto=serveur_auto)

        from ui.workers import run_async

        def _tache():
            _, message = serveur_local.demarrer_serveur(
                port, serveur_auto=serveur_auto)
            if not serveur_local.serveur_disponible():
                return False, message
            return (serveur_local.api_joignable(port, delai=2.0), message)

        def _fini(resultat):
            en_ligne, message = (resultat if isinstance(resultat, tuple)
                                 else (False, str(resultat)))
            network.set_sync_active(en_ligne)
            ecrire_config_sync(sync_active=en_ligne)
            adresse = serveur_local.adresse_locale(port)
            if en_ligne:
                self._feedback(
                    f"Connexion activee.\n"
                    f"Sur chaque autre poste, saisissez cette adresse : {adresse}")
            else:
                self._feedback(message, erreur=True)
            self.btn_activer.setText("Activer la connexion multi-postes")
            self.btn_activer.setEnabled(True)
            self.rafraichir()
            if en_ligne and self._apres_changement:
                self._apres_changement()

        run_async(_tache, _fini)

    def desactiver(self):
        if not confirmer(
                self,
                "Revenir au mode « un seul poste » ?\n\n"
                "Les donnees de CETTE machine sont conservees ; les autres "
                "postes ne pourront plus les consulter.",
                "Confirmation"):
            return
        _, message = serveur_local.arreter_serveur()
        network.set_sync_active(False)
        from core.config import ecrire_config_sync
        ecrire_config_sync(sync_active=False, serveur_auto=False, pid=None)
        self.chk_serveur_auto.setChecked(False)
        self._feedback(message)
        self.rafraichir()
        if self._apres_changement:
            self._apres_changement()

    # ------------------------------------------------------------------
    # Point d'acces WiFi de l'ecole (hotspot)
    # ------------------------------------------------------------------

    def creer_hotspot(self):
        """Cree (ou arrete) le reseau WiFi de l'ecole sur ce PC hote."""
        from services import hotspot
        if hotspot.hotspot_actif():
            hotspot.arreter_hotspot()
            self._feedback(
                "Reseau WiFi de l'ecole arrete.\n"
                "La carte WiFi reprend ses connexions habituelles.")
            self.rafraichir()
            return

        self.btn_hotspot.setEnabled(False)
        self.btn_hotspot.setText("Creation du reseau WiFi...")
        QApplication.processEvents()

        from ui.workers import run_async

        def _tache():
            try:
                return ("ok", hotspot.creer_hotspot())
            except hotspot.HotspotError as exc:
                return ("err", str(exc))
            except Exception as exc:
                return ("err", f"Erreur inattendue : {exc}")

        def _fini(resultat):
            statut = resultat[0] if isinstance(resultat, tuple) else "err"
            if statut != "ok":
                self._feedback(
                    resultat[1] if isinstance(resultat, tuple) else str(resultat),
                    erreur=True)
                self.rafraichir()
                return
            infos = resultat[1]
            adresse = hotspot.adresse_passerelle()
            port = self.spin_port.value() if hasattr(self, "spin_port") \
                else serveur_local.port_configure()
            partage = "Internet sera PARTAGE" if infos.get("partage") else (
                "pas d'Internet sur ce reseau (reseau local uniquement)")
            if adresse:
                adresse_texte = (
                    f"\nPostes clients — adresse : http://{adresse}:{port}")
            else:
                adresse_texte = (
                    "\nAdresse a verifier apres activation de la connexion.")

            self._feedback(
                f"Reseau WiFi cree : « {infos['ssid']} »\n"
                f"Mot de passe : {infos['mot_de_passe']}\n\n"
                f"{partage}.{adresse_texte}")
            self.btn_hotspot.setText("Arreter le reseau WiFi de l'ecole")
            self.btn_hotspot.setEnabled(True)

        run_async(_tache, _fini)

    # ------------------------------------------------------------------
    # Mode client : connexion a un PC serveur distant
    # ------------------------------------------------------------------

    def _connecter_client(self):
        """Connecte ce poste au serveur distant (poste client)."""
        adresse = self.input_adresse_serveur.text().strip()
        if not adresse:
            self._feedback(
                "Saisissez l'adresse du PC serveur (ex: "
                "http://192.168.1.100:8000).", erreur=True)
            return
        if not adresse.startswith("http"):
            adresse = "http://" + adresse
            self.input_adresse_serveur.setText(adresse)

        self.btn_connecter.setEnabled(False)
        self.btn_connecter.setText("Test en cours...")
        QApplication.processEvents()

        # Test de connectivite : on interroge une route simple
        import httpx
        try:
            rep = httpx.get(adresse + "/annee_scolaire_active", timeout=3.0)
            ok = rep.status_code < 500
        except Exception:
            ok = False

        if not ok:
            self._feedback(
                f"Impossible de joindre le serveur {adresse}.\n"
                "Verifiez l'adresse et que le serveur est demarre.",
                erreur=True)
            self.btn_connecter.setText("Connecter")
            self.btn_connecter.setEnabled(True)
            return

        # Succes : on enregistre l'adresse et on active la synchro
        from core import config
        from core.config import ecrire_config_sync
        ecrire_config_sync(
            api_url=adresse, sync_active=True, serveur_auto=False, pid=None)
        # Mettre a jour l'URL en memoire pour les appels immediats
        config.API_BASE_URL = adresse
        network.set_sync_active(True)

        self._feedback(
            f"Connecte au serveur {adresse}.\n"
            "Les donnees (eleves, notes, paiements) seront synchronisees "
            "automatiquement.")
        self.btn_connecter.setText("Connecter")
        self.btn_connecter.setEnabled(True)
        self.rafraichir()
        if self._apres_changement:
            self._apres_changement()

    def _deconnecter_client(self):
        """Deconnecte ce poste du serveur distant et revient en mode autonome."""
        from core import config
        from core.config import ecrire_config_sync
        ecrire_config_sync(sync_active=False, serveur_auto=False, pid=None)
        network.set_sync_active(False)
        self._feedback("Deconnecte du serveur. Ce poste fonctionne en mode autonome.")
        self.rafraichir()
        if self._apres_changement:
            self._apres_changement()

    def _scanner_reseau(self):
        """Lance la decouverte du serveur de l'ecole sur le reseau local."""
        self.btn_scan.setEnabled(False)
        self.btn_scan.setText("...")
        self._feedback("Recherche du serveur sur le reseau local (5 secondes)...")
        QApplication.processEvents()

        from PyQt5.QtCore import QThread, pyqtSignal

        class _ScanThread(QThread):
            termine = pyqtSignal(list)
            def run(self):
                from services.discovery import trouver_serveur
                resultats = trouver_serveur(duree=5.0)
                self.termine.emit(resultats)

        self._scan_thread = _ScanThread(self)
        self._scan_thread.termine.connect(self._sur_scan_termine)
        self._scan_thread.start()

    def closeEvent(self, event):
        """Ferme proprement : attend la fin du scan reseau en cours pour
        ne jamais detruire le QThread pendant qu'il tourne."""
        if self._scan_thread is not None and self._scan_thread.isRunning():
            self._scan_thread.terminate()
            self._scan_thread.wait(1500)
        super().closeEvent(event)

    def _sur_scan_termine(self, resultats):
        self.btn_scan.setText("Scanner")
        self.btn_scan.setEnabled(True)
        if not resultats:
            self._feedback(
                "Aucun serveur trouve sur le reseau.\n"
                "Assurez-vous que le PC serveur est demarre et connecte "
                "au meme reseau WiFi.", erreur=True)
            return
        srv = resultats[0]
        adresse = f"http://{srv['ip']}:{srv['port']}"
        self.input_adresse_serveur.setText(adresse)
        self._feedback(
            f"Serveur trouve : {adresse}\n"
            "Cliquez sur Connecter pour vous y connecter.")

    def _on_serveur_auto_changed(self, state):
        from core.config import ecrire_config_sync
        ecrire_config_sync(serveur_auto=bool(state))

    def _on_app_auto_changed(self, state):
        from PyQt5.QtWidgets import QMessageBox
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