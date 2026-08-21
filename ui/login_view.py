from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QLinearGradient, QPainter
from PyQt5.QtWidgets import (
    QDialog, QFrame, QLabel, QLineEdit, QMessageBox,
    QPushButton, QVBoxLayout, QComboBox,
)

from core.config import APP_NAME, APP_VERSION, ROLE_LABELS, C_TEXT, C_TEXT_MUTED, C_TEXT_SECONDARY, C_CARD, C_BORDER_STRONG, C_PRIMARY, C_PRIMARY_PRESSED, C_GOLD, C_GOLD_PRESSED
from database.db import hash_password
from services.auth import AuthService

PRIMARY = C_PRIMARY
PRIMARY_DARK = C_PRIMARY_PRESSED


class _Gradient(QFrame):
    def paintEvent(self, _event):
        painter = QPainter(self)
        grad = QLinearGradient(0, 0, self.width(), self.height())
        grad.setColorAt(0.0, QColor(C_GOLD))
        grad.setColorAt(1.0, QColor(C_GOLD_PRESSED))
        painter.fillRect(self.rect(), grad)


class LoginDialog(QDialog):
    """Ecran de connexion : identifiant (username ou email) + mot de passe."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.user = None
        self.setWindowTitle(f"{APP_NAME} - Connexion")
        self.setFixedSize(700, 480)
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        background = _Gradient(self)
        root.addWidget(background)

        background_layout = QVBoxLayout(background)
        background_layout.setContentsMargins(50, 30, 50, 30)

        card = QFrame(background)
        card.setObjectName("loginCard")
        card.setStyleSheet(
            f"QFrame#loginCard {{ background-color: {C_CARD}; border-radius: 12px; }}")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(40, 28, 40, 28)
        card_layout.setSpacing(12)

        title = QLabel("GESTION SCOLAIRE")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(f"color: {C_TEXT}; font-size: 22px; font-weight: bold;")
        subtitle = QLabel(f"Connexion a votre espace - version {APP_VERSION}")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet(f"color: {C_TEXT_MUTED}; font-size: 12px;")
        card_layout.addWidget(title)
        card_layout.addWidget(subtitle)

        card_layout.addSpacing(6)

        def row(label_text, field):
            lay = QVBoxLayout()
            lab = QLabel(label_text)
            lab.setStyleSheet(f"color: {C_TEXT_SECONDARY}; font-size: 12px; font-weight: bold;")
            field.setStyleSheet(
                f"QLineEdit {{ border: 1px solid {C_BORDER_STRONG}; border-radius: 8px;"
                " padding: 8px 12px; font-size: 13px; }")
            field.setMinimumHeight(36)
            lay.addWidget(lab)
            lay.addWidget(field)
            return lay

        self.input_identifiant = QLineEdit()
        self.input_identifiant.setPlaceholderText("Nom d'utilisateur ou email")

        self.input_password = QLineEdit()
        self.input_password.setPlaceholderText("Mot de passe")
        self.input_password.setEchoMode(QLineEdit.Password)
        self.input_password.returnPressed.connect(self._do_login)

        card_layout.addLayout(row("Identifiant", self.input_identifiant))
        card_layout.addLayout(row("Mot de passe", self.input_password))

        self.lbl_erreur = QLabel("")
        self.lbl_erreur.setAlignment(Qt.AlignCenter)
        self.lbl_erreur.setStyleSheet("color: #B91C1C; font-size: 12px; font-weight: bold;")
        self.lbl_erreur.setWordWrap(True)
        card_layout.addWidget(self.lbl_erreur)

        btn = QPushButton("Se connecter")
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(
            f"QPushButton {{ background-color: {PRIMARY}; color: {C_CARD};"
            " border: none; border-radius: 6px; padding: 10px;"
            " font-size: 14px; font-weight: bold; min-height: 38px; }"
            f"QPushButton:hover {{ background-color: {PRIMARY_DARK}; }}")
        btn.clicked.connect(self._do_login)
        card_layout.addWidget(btn)

        background_layout.addWidget(card)
        self.input_identifiant.setFocus()

    def _do_login(self):
        identifiant = self.input_identifiant.text().strip()
        password = self.input_password.text()
        if not identifiant or not password:
            self.lbl_erreur.setText("Veuillez saisir votre identifiant et votre mot de passe.")
            return
        user, erreur = AuthService().login(identifiant, password)
        if user is None:
            self.lbl_erreur.setText(erreur or "Identifiant ou mot de passe incorrect.")
            self.input_password.clear()
            self.input_password.setFocus()
            return
        AuthService().save_session(user["id"])
        self.user = user
        self.accept()


class FirstSetupDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.user = None
        self.setWindowTitle(f"{APP_NAME} - Premiere configuration")
        self.setFixedSize(700, 480)
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        background = _Gradient(self)
        root.addWidget(background)

        background_layout = QVBoxLayout(background)
        background_layout.setContentsMargins(50, 30, 50, 30)

        card = QFrame(background)
        card.setObjectName("loginCard")
        card.setStyleSheet(
            f"QFrame#loginCard {{ background-color: {C_CARD}; border-radius: 12px; }}")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(40, 28, 40, 28)
        card_layout.setSpacing(12)

        title = QLabel("GESTION SCOLAIRE")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(f"color: {C_TEXT}; font-size: 22px; font-weight: bold;")
        subtitle = QLabel("Premiere configuration")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet(f"color: {C_TEXT_MUTED}; font-size: 12px;")
        card_layout.addWidget(title)
        card_layout.addWidget(subtitle)

        card_layout.addSpacing(6)

        def row(label_text, field):
            lay = QVBoxLayout()
            lab = QLabel(label_text)
            lab.setStyleSheet(f"color: {C_TEXT_SECONDARY}; font-size: 12px; font-weight: bold;")
            field.setStyleSheet(
                f"QLineEdit {{ border: 1px solid {C_BORDER_STRONG}; border-radius: 8px;"
                " padding: 8px 12px; font-size: 13px; }")
            field.setMinimumHeight(36)
            lay.addWidget(lab)
            lay.addWidget(field)
            return lay

        self.input_nom = QLineEdit()
        self.input_nom.setPlaceholderText("Nom et prenom")

        self.combo_role = QComboBox()
        self.combo_role.setStyleSheet(
            f"QComboBox {{ border: 1px solid {C_BORDER_STRONG}; border-radius: 8px;"
            " padding: 8px 12px; font-size: 13px; background-color: white; }")
        self.combo_role.setMinimumHeight(36)
        for role_key in ("directeur", "gestionnaire"):
            self.combo_role.addItem(ROLE_LABELS[role_key], role_key)

        self.input_password = QLineEdit()
        self.input_password.setPlaceholderText("Mot de passe")
        self.input_password.setEchoMode(QLineEdit.Password)

        self.input_confirm = QLineEdit()
        self.input_confirm.setPlaceholderText("Confirmez le mot de passe")
        self.input_confirm.setEchoMode(QLineEdit.Password)
        self.input_confirm.returnPressed.connect(self._do_create)

        card_layout.addLayout(row("Nom complet", self.input_nom))

        role_lay = QVBoxLayout()
        role_lab = QLabel("Role :")
        role_lab.setStyleSheet(f"color: {C_TEXT_SECONDARY}; font-size: 12px; font-weight: bold;")
        role_lay.addWidget(role_lab)
        role_lay.addWidget(self.combo_role)
        card_layout.addLayout(role_lay)

        card_layout.addLayout(row("Mot de passe", self.input_password))
        card_layout.addLayout(row("Confirmer", self.input_confirm))

        card_layout.addSpacing(4)

        btn = QPushButton("Creer mon compte")
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(
            f"QPushButton {{ background-color: {PRIMARY}; color: {C_CARD};"
            " border: none; border-radius: 6px; padding: 10px;"
            " font-size: 14px; font-weight: bold; min-height: 38px; }"
            f"QPushButton:hover {{ background-color: {PRIMARY_DARK}; }}")
        btn.clicked.connect(self._do_create)
        card_layout.addWidget(btn)

        background_layout.addWidget(card)
        self.input_nom.setFocus()

    def _do_create(self):
        from database import db

        nom = self.input_nom.text().strip()
        password = self.input_password.text()
        confirm = self.input_confirm.text()
        role = self.combo_role.currentData()

        if not nom:
            QMessageBox.warning(self, "Creation", "Le nom complet est obligatoire.")
            return
        if not password or len(password) < 4:
            QMessageBox.warning(self, "Creation",
                                "Le mot de passe doit contenir au moins 4 caracteres.")
            return
        if password != confirm:
            QMessageBox.warning(self, "Creation",
                                "Les mots de passe ne correspondent pas.")
            return

        base_username = nom.lower().replace(" ", ".").replace("'", "")
        username = base_username
        counter = 1
        while db.query_one("SELECT id FROM utilisateurs WHERE username = ?",
                           (username,)):
            username = f"{base_username}{counter}"
            counter += 1

        user_id = db.execute(
            """INSERT INTO utilisateurs
               (nom_complet, username, password, role, actif)
               VALUES (?, ?, ?, ?, 1)""",
            (nom, username, hash_password(password), role))

        user = db.query_one("SELECT * FROM utilisateurs WHERE id = ?", (user_id,))
        db.execute(
            "INSERT INTO connexions (utilisateur_id) VALUES (?)", (user_id,))
        self.user = user
        self.accept()
