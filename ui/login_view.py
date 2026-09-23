from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QComboBox, QDialog, QFrame, QGraphicsDropShadowEffect, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget,
)
from PyQt5.QtGui import QColor

from core.config import (
    APP_NAME, APP_VERSION, ROLE_LABELS,
    C_INK, C_TEXT, C_TEXT_MUTED, C_TEXT_SECONDARY, C_TEXT_LIGHT, C_CARD,
    C_BG_SOFT, C_BORDER, C_BORDER_STRONG, C_PRIMARY, C_PRIMARY_HOVER,
    C_FOCUS_RING, C_RED, C_GREEN, C_GREEN_BG, C_AURORA,
    STYLE_AUTH_EMBLEME, STYLE_AUTH_BTN, STYLE_AUTH_FIELD_LABEL,
)
from database.db import hash_password
from services.auth import AuthService
from ui import motion


def _style_zone():
    return (
        f"QWidget#zoneChamp {{ background: {C_CARD};"
        f" border: 1px solid {C_BORDER_STRONG}; border-radius: 12px; }}"
        f"QWidget#zoneChamp:hover {{ border: 1px solid {C_TEXT_MUTED}; }}"
        f"QWidget#zoneChamp[etat='focus'] {{ border: 2px solid {C_FOCUS_RING}; }}"
        f"QWidget#zoneChamp QLineEdit {{ background: transparent; border: none;"
        f" padding: 10px 14px; font-size: 14px; color: {C_TEXT}; }}"
        f"QWidget#zoneChamp QPushButton {{ background: transparent;"
        f" border: none; color: {C_PRIMARY}; font-size: 12px; font-weight: 700;"
        f" padding: 0 12px; }}"
        f"QWidget#zoneChamp QPushButton:hover {{ color: {C_PRIMARY_HOVER}; "
        f" text-decoration: underline; }}"
    )


class _ZoneChamp(QWidget):
    """Zone de saisie moderne : fond blanc, bord arrondi, anneau de focus or.

    Les champs pleins largeur (login, configuration) partagent ce style au
    lieu de lignes de code dupliquees avec des couleurs figees.
    """

    def __init__(self, field):
        super().__init__()
        self.setObjectName("zoneChamp")
        self.setProperty("etat", "normal")
        self.setStyleSheet(_style_zone())
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(field, 1)
        self._field = field
        field.installEventFilter(self)

    def eventFilter(self, source, event):
        from PyQt5.QtCore import QEvent
        if source is self._field and event.type() == QEvent.FocusIn:
            self.setProperty("etat", "focus")
            self.style().unpolish(self)
            self.style().polish(self)
        elif source is self._field and event.type() == QEvent.FocusOut:
            self.setProperty("etat", "normal")
            self.style().unpolish(self)
            self.style().polish(self)
        return super().eventFilter(source, event)


class _ChampMdp(_ZoneChamp):
    """Champ mot de passe avec bouton Afficher / Masquer integre."""

    def __init__(self, on_retour=None):
        field = QLineEdit()
        field.setPlaceholderText("Mot de passe")
        field.setEchoMode(QLineEdit.Password)
        super().__init__(field)
        self.field = field
        self.bouton = QPushButton("Afficher")
        self.bouton.setCursor(Qt.PointingHandCursor)
        self.bouton.setFocusPolicy(Qt.NoFocus)
        self.bouton.clicked.connect(self._basculer)
        self.layout().addWidget(self.bouton)
        if on_retour is not None:
            field.returnPressed.connect(on_retour)

    def _basculer(self):
        visible = self.field.echoMode() == QLineEdit.Normal
        self.field.setEchoMode(QLineEdit.Password if visible else QLineEdit.Normal)
        self.bouton.setText("Masquer" if visible else "Afficher")


def _bloc_erreur(parent):
    lbl = QLabel("")
    lbl.setAlignment(Qt.AlignCenter)
    lbl.setStyleSheet(
        f"color: {C_RED}; font-size: 12px; font-weight: 600;")
    lbl.setWordWrap(True)
    lbl.hide()
    return lbl


def _bouton_principal(texte, connecte):
    btn = QPushButton(texte)
    btn.setCursor(Qt.PointingHandCursor)
    btn.setMinimumHeight(48)
    btn.setStyleSheet(STYLE_AUTH_BTN)
    btn.clicked.connect(connecte)
    return btn


def _champ_simple(placeholder):
    field = QLineEdit()
    field.setPlaceholderText(placeholder)
    return field


class _EcranAuth(QDialog):
    """Coquille commune des ecrans de connexion / premiere configuration :
    fond clair, carte centree avec ombre portee, marque, pied de page
    presentant la version et l'etat de synchronisation."""

    LARGEUR = 480

    def __init__(self, titre, sous_titre, parent=None):
        super().__init__(parent)
        self._anime = False
        self.setWindowTitle(f"{APP_NAME} - {titre}")
        self.setMinimumSize(440, self._hauteur() - 60)
        self.resize(self.LARGEUR, self._hauteur())
        self.setSizeGripEnabled(True)
        self.titre = titre
        self.sous_titre = sous_titre
        self._construire()
        self.card.setStyleSheet(
            f"QFrame#authCarte {{ background: {C_CARD};"
            f" border: 1px solid {C_BORDER}; border-radius: 16px; }}")

    def _hauteur(self):
        raise NotImplementedError

    def _construire(self):
        racine = QVBoxLayout(self)
        racine.setContentsMargins(0, 0, 0, 0)
        racine.setSpacing(0)
        self.setStyleSheet(f"QDialog {{ {C_AURORA} }}")

        fond = QVBoxLayout()
        fond.setContentsMargins(0, 28, 0, 20)
        fond.setSpacing(0)

        carte = QFrame()
        carte.setObjectName("authCarte")
        ombre = QGraphicsDropShadowEffect(carte)
        ombre.setBlurRadius(48)
        ombre.setOffset(0, 14)
        ombre.setColor(QColor(15, 18, 28, 55))
        carte.setGraphicsEffect(ombre)

        v = QVBoxLayout(carte)
        v.setContentsMargins(40, 22, 40, 20)
        v.setSpacing(10)

        embleme = QLabel("GS")
        embleme.setFixedSize(60, 60)
        embleme.setAlignment(Qt.AlignCenter)
        embleme.setStyleSheet(STYLE_AUTH_EMBLEME)
        v.addWidget(embleme, 0, Qt.AlignCenter)
        v.addSpacing(2)

        marque = QLabel("GESTION  SCOLAIRE")
        marque.setAlignment(Qt.AlignCenter)
        marque.setStyleSheet(
            f"color: {C_PRIMARY}; font-size: 12px; font-weight: 800;"
            " letter-spacing: 3px;")
        v.addWidget(marque)

        trait = QFrame()
        trait.setFixedSize(40, 3)
        trait.setStyleSheet(
            f"background: {C_PRIMARY}; border: none; border-radius: 2px;")
        v.addWidget(trait, 0, Qt.AlignCenter)
        v.addSpacing(6)

        titre = QLabel(self.titre)
        titre.setAlignment(Qt.AlignCenter)
        titre.setStyleSheet(
            f"color: {C_INK}; font-size: 24px; font-weight: 800;")
        v.addWidget(titre)

        sous = QLabel(self.sous_titre)
        sous.setAlignment(Qt.AlignCenter)
        sous.setWordWrap(True)
        sous.setStyleSheet(f"color: {C_TEXT_MUTED}; font-size: 13px;")
        v.addWidget(sous)
        v.addSpacing(8)

        self._corps = QVBoxLayout()
        self._corps.setSpacing(8)
        v.addLayout(self._corps)

        self.lbl_note = _bloc_erreur(self)
        v.addWidget(self.lbl_note)

        v.addSpacing(4)
        self._pied()

        fond.addWidget(carte)
        racine.addLayout(fond, 1)
        self.card = carte
        self._animer()

    def _ajuster_hauteur(self):
        """Ajuste la fenetre au contenu reel sans jamais depasser l'ecran
        disponible : ni compression des espacements, ni fenetre plus haute
        que l'ecran."""
        from PyQt5.QtWidgets import QApplication
        besoin = self.sizeHint().height()
        dispo = QApplication.primaryScreen().availableGeometry().height() - 40
        hauteur = max(440, min(besoin, dispo))
        self.setMinimumSize(440, max(440, min(self._hauteur() - 60, dispo)))
        self.resize(self.LARGEUR, hauteur)

    def _pied(self):
        from PyQt5.QtWidgets import QHBoxLayout

        ligne = QHBoxLayout()
        ligne.setContentsMargins(8, 0, 8, 0)
        ligne.setSpacing(8)

        version = QLabel(f"v{APP_VERSION}")
        version.setStyleSheet(f"color: {C_TEXT_LIGHT}; font-size: 11px;")
        ligne.addWidget(version)
        ligne.addStretch(1)

        chip = QLabel(self._mode_texte())
        chip.setStyleSheet(
            f"background: {self._mode_couleurs()[0]}; color: {self._mode_couleurs()[1]};"
            " border-radius: 12px; padding: 3px 10px; font-size: 11px;"
            " font-weight: 700;")
        ligne.addWidget(chip)
        self._pied_layout = ligne
        lay = self.layout()
        if lay is not None:
            lay.addLayout(ligne)

    @staticmethod
    def _mode_texte():
        from core import network
        return ("Synchronisation multi-postes activee"
                if network.sync_active()
                else "Mode autonome (un seul poste)")

    @staticmethod
    def _mode_couleurs():
        from core import network
        if network.sync_active():
            return (C_GREEN_BG, C_GREEN)
        return (C_BG_SOFT, C_TEXT_LIGHT)

    def _animer(self):
        if self._anime:
            return
        self._anime = True
        motion.fade_in(self, duree=300)

    def showEvent(self, event):
        super().showEvent(event)
        if hasattr(self, "card"):
            motion.pop_in(self.card, duree=380)


class LoginDialog(_EcranAuth):
    """Ecran de connexion : identifiant (username ou email) + mot de passe."""

    def __init__(self, parent=None):
        super().__init__("Connexion", "Accedez a votre espace.", parent)
        self.user = None
        self._construire_corps()

    def _hauteur(self):
        return 540

    def _construire_corps(self):
        ligne = QLabel("Identifiant")
        ligne.setStyleSheet(
            STYLE_AUTH_FIELD_LABEL)
        self._corps.addWidget(ligne)

        self.input_identifiant = _champ_simple("Nom d'utilisateur ou email")
        self.input_identifiant.returnPressed.connect(lambda: self.input_mdp.setFocus())
        self._corps.addWidget(_ZoneChamp(self.input_identifiant))

        ligne2 = QLabel("Mot de passe")
        ligne2.setStyleSheet(
            STYLE_AUTH_FIELD_LABEL)
        self._corps.addWidget(ligne2)

        self.input_mdp = _ChampMdp(on_retour=self._do_login)
        self._corps.addWidget(self.input_mdp)

        btn = _bouton_principal("Se connecter", self._do_login)
        self._corps.addWidget(btn)
        self.input_identifiant.setFocus()
        self.lbl_note.hide()
        self._ajuster_hauteur()

    def _do_login(self):
        identifiant = self.input_identifiant.text().strip()
        password = self.input_mdp.field.text()
        if not identifiant or not password:
            self._afficher_erreur(
                "Veuillez saisir votre identifiant et votre mot de passe.")
            return
        user, erreur = AuthService().login(identifiant, password)
        if user is None:
            self._afficher_erreur(
                erreur or "Identifiant ou mot de passe incorrect.")
            self.input_mdp.field.clear()
            self.input_mdp.field.setFocus()
            return
        AuthService().save_session(user["id"])
        self.user = user
        self.accept()

    def _afficher_erreur(self, texte):
        self.lbl_note.setText(texte)
        self.lbl_note.show()


class FirstSetupDialog(_EcranAuth):
    """Premiere configuration : creation du premier compte administrateur.

    Affiche en direct l'identifiant generé (nom -> nom.prenom) pour que la
    personne sache des maintenant comment se connecter par la suite.
    """

    def __init__(self, parent=None):
        super().__init__(
            "Bienvenue", "Creez le premier compte pour commencer.", parent)
        self.user = None
        self._construire_corps()

    def _hauteur(self):
        return 700

    def _construire_corps(self):
        def champ(placeholder):
            return _champ_simple(placeholder)

        def label(texte):
            lbl = QLabel(texte)
            lbl.setStyleSheet(
                STYLE_AUTH_FIELD_LABEL)
            return lbl

        self._corps.addWidget(label("Nom complet"))
        self.input_nom = champ("Ex : Marie Ngoma")
        self.input_nom.returnPressed.connect(lambda: self.input_password.setFocus())
        self._corps.addWidget(_ZoneChamp(self.input_nom))
        self.input_nom.textChanged.connect(self._maj_apercu_identifiant)

        self.lbl_identifiant = QLabel("")
        self.lbl_identifiant.setStyleSheet(
            f"color: {C_TEXT_MUTED}; font-size: 11px; padding: 0 4px;")
        self._corps.addWidget(self.lbl_identifiant)

        self._corps.addWidget(label("Role"))
        self.combo_role = QComboBox()
        for role_key in ("directeur", "gestionnaire"):
            self.combo_role.addItem(ROLE_LABELS[role_key], role_key)
        self._corps.addWidget(self.combo_role)

        self._corps.addWidget(label("Mot de passe"))
        self.input_password = _ChampMdp(
            on_retour=lambda: self.input_confirm.setFocus())
        self._corps.addWidget(self.input_password)

        self._corps.addWidget(label("Confirmer le mot de passe"))
        self.input_confirm = _ChampMdp(on_retour=self._do_create)
        self._corps.addWidget(self.input_confirm)

        btn = _bouton_principal("Creer mon compte", self._do_create)
        self._corps.addWidget(btn)
        self.input_nom.setFocus()
        self._ajuster_hauteur()

    def _maj_apercu_identifiant(self, nom):
        identifiant = self._generer_identifiant(nom)
        if identifiant:
            self.lbl_identifiant.setText(
                f"Votre identifiant sera :  {identifiant}")
        else:
            self.lbl_identifiant.setText("")

    @staticmethod
    def _generer_identifiant(nom):
        base = nom.lower().replace(" ", ".").replace("'", "")
        return base or ""

    def _do_create(self):
        from database import db

        nom = self.input_nom.text().strip()
        password = self.input_password.field.text()
        confirm = self.input_confirm.field.text()
        role = self.combo_role.currentData()

        if not nom:
            self._afficher_erreur("Le nom complet est obligatoire.")
            return
        if not password or len(password) < 4:
            self._afficher_erreur(
                "Le mot de passe doit contenir au moins 4 caracteres.")
            return
        if password != confirm:
            self._afficher_erreur("Les mots de passe ne correspondent pas.")
            return

        base_username = self._generer_identifiant(nom)
        if not base_username:
            self._afficher_erreur(
                "Le nom doit contenir au moins une lettre.")
            return
        username = base_username
        compteur = 1
        while db.query_one("SELECT id FROM utilisateurs WHERE username = ?",
                           (username,)):
            username = f"{base_username}{compteur}"
            compteur += 1

        user_id = db.execute(
            """INSERT INTO utilisateurs
               (nom_complet, username, password, role, actif)
               VALUES (?, ?, ?, ?, 1)""",
            (nom, username, hash_password(password), role))

        user = db.query_one("SELECT * FROM utilisateurs WHERE id = ?", (user_id,))
        if user is None:
            self._afficher_erreur(
                "Impossible d'enregistrer le compte. Reessayez.")
            return
        db.execute(
            "INSERT INTO connexions (utilisateur_id) VALUES (?)", (user_id,))
        self._pousser_premier_compte(nom, username, password, role)
        self.user = user
        self.accept()

    def _pousser_premier_compte(self, nom, username, password, role):
        """Pousse le premier compte vers le serveur partage (si disponible)
        pour qu'il soit utilisable sur tous les postes de l'etablissement.

        Silencieux : en mode autonome (aucun serveur) rien n'est envoyé.
        """
        from core import network
        if not network.sync_active():
            return
        try:
            from core.config import API_BASE_URL
            from api import client
            client.ApiClient().ajouter_compte_serveur(
                nom, username, password, role,
                email=f"{username}@ecole.ci" if "@" not in username else username)
        except Exception:
            pass  # le compte reste local ; le pull des comptes alignera plus tard

    def _afficher_erreur(self, texte):
        self.lbl_note.setText(texte)
        self.lbl_note.show()