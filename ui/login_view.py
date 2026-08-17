from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QLinearGradient, QPainter
from PyQt5.QtWidgets import (
    QDialog, QFrame, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QPushButton, QVBoxLayout,
)

from core.config import APP_NAME, APP_VERSION, C_TEXT_SECONDARY, C_PRIMARY, C_PRIMARY_PRESSED
from services import auth

PRIMARY = C_PRIMARY
PRIMARY_DARK = C_PRIMARY_PRESSED


class _Gradient(QFrame):
    def paintEvent(self, _event):

        painter = QPainter(self)
        grad = QLinearGradient(0, 0, self.width(), self.height())
        grad.setColorAt(0.0, QColor("#065f46"))
        grad.setColorAt(1.0, QColor("#0f766e"))
        painter.fillRect(self.rect(), grad)


class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.user = None
        self.setWindowTitle(f"{APP_NAME} - Connexion")

        self.setFixedSize(700, 540)
        self._build()

    def _build(self):

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        background = _Gradient(self)
        root.addWidget(background)

        background_layout = QVBoxLayout(background)
        background_layout.setContentsMargins(50, 40, 50, 40)

        card = QFrame(background)
        card.setObjectName("loginCard")
        card.setStyleSheet(
            "QFrame#loginCard { background-color: #ffffff; border-radius: 12px; }")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(40, 32, 40, 32)
        card_layout.setSpacing(12)

        title = QLabel("GESTION SCOLAIRE")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(
            "color: #0f172a; font-size: 20px; font-weight: bold;")
        subtitle = QLabel(f"Connexion - v{APP_VERSION}")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("color: #64748b; font-size: 12px;")
        card_layout.addWidget(title)
        card_layout.addWidget(subtitle)

        card_layout.addSpacing(10)


        def row(label, field):
            lay = QVBoxLayout()
            lab = QLabel(label)
            lab.setStyleSheet(f"color: {C_TEXT_SECONDARY}; font-size: 12px; font-weight: bold;")
            field.setStyleSheet("")
            lay.addWidget(lab)
            lay.addWidget(field)
            return lay


        self.input_username = QLineEdit()
        self.input_username.setPlaceholderText("Identifiant")
        self.input_password = QLineEdit()
        self.input_password.setPlaceholderText("Mot de passe")
        self.input_password.setEchoMode(QLineEdit.Password)
        self.input_password.returnPressed.connect(self._do_login)

        card_layout.addLayout(row("Identifiant", self.input_username))
        card_layout.addLayout(row("Mot de passe", self.input_password))


        btn = QPushButton("Se connecter")
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(
            f"QPushButton {{ background-color: {PRIMARY}; color: #ffffff;"
            " border: none; border-radius: 6px; padding: 10px;"
            " font-size: 14px; font-weight: bold; }"
            f"QPushButton:hover {{ background-color: {PRIMARY_DARK}; }}")
        btn.clicked.connect(self._do_login)
        card_layout.addSpacing(6)
        card_layout.addWidget(btn)

        hint = QLabel(
            "Comptes de test:\nadmin / admin123   |   directeur / directeur123   |   gestionnaire / gestionnaire123")
        hint.setStyleSheet("color: #94a3b8; font-size: 11px;")
        hint.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(hint)

        background_layout.addWidget(card)

        self.input_username.setFocus()

    def _do_login(self):

        username = self.input_username.text().strip()
        password = self.input_password.text()
        if not username or not password:
            QMessageBox.warning(self, "Connexion",
                                "Veuillez saisir l'identifiant et le mot de passe.")
            return
        user, error = auth.login(username, password)
        if error:
            QMessageBox.warning(self, "Connexion", error)
            return
        self.user = user
        self.accept()
