from functools import partial

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog, QDialogButtonBox, QLabel, QLineEdit, QMessageBox,
    QFormLayout, QStackedWidget, QTextEdit, QVBoxLayout,
)

from repositories import repos
from ui import toast
from ui.pages.helpers import (
    _btn, _simple_btn_style, _add_btn, _actions_cell, confirmer,
)
from ui.widgets import DataTable, EmptyState, PageHeader
from core.config import (
    C_BLUE, C_BLUE_LIGHT, C_BLUE_BORDER, C_RED, C_RED_BG, C_RED_BORDER,
)


def _utilisateur_id(ctx):
    return ctx.user.get("id", 0)


def _extrait(contenu):
    une_ligne = (contenu or "").strip().replace("\n", " ")
    return une_ligne[:70] + ("..." if len(une_ligne) > 70 else "")


def bloc_notes(page, ctx):
    if page.layout() is not None:
        return
    uid = _utilisateur_id(ctx)
    lay = QVBoxLayout(page)
    lay.setContentsMargins(20, 20, 20, 20)
    lay.setSpacing(16)
    lay.addWidget(PageHeader(
        "Bloc Notes",
        "Notes personnelles conservees sur ce poste"))

    table = DataTable()
    table.setColumnCount(4)
    table.setHorizontalHeaderLabels(["Titre", "Modifie le", "Extrait", "Actions"])
    vide = EmptyState("Aucune note",
                      "Ajoutez votre premiere note via le bouton ci-dessus.")
    pile = QStackedWidget()
    pile.addWidget(table)
    pile.addWidget(vide)
    lay.addWidget(pile, 1)

    def fill():
        rows = repos.blocnote.notes(uid)
        valeurs = [[n["titre"], n["modifie_le"] or "-", _extrait(n["contenu"]), ""]
                   for n in rows]
        table.remplir(valeurs)
        for i, n in enumerate(rows):
            table.setCellWidget(i, 3, _actions_cell(
                _btn("Ouvrir", partial(open_note_dialog, page, ctx, n, fill),
                     _simple_btn_style(bg=C_BLUE_LIGHT, fg=C_BLUE, border=C_BLUE_BORDER)),
                _btn("Supprimer", partial(_delete_note, page, n, fill),
                     _simple_btn_style(bg=C_RED_BG, fg=C_RED, border=C_RED_BORDER))))
        pile.setCurrentWidget(vide if not rows else table)
        table.horizontalHeader().setStretchLastSection(True)

    def _delete_note(parent, n, on_done):
        if confirmer(parent, f"Supprimer la note « {n['titre']} » ?", "Bloc Notes"):
            repos.blocnote.supprimer(n["id"])
            toast.succes(parent, "Note supprimee.")
            on_done()

    btn_add = _add_btn("+ Nouvelle Note",
                       lambda: open_note_dialog(page, ctx, None, fill))
    lay.addWidget(btn_add, 0, Qt.AlignRight)

    fill()
    page.refresh = fill


def open_note_dialog(parent, ctx, note=None, on_saved=None):
    dlg = QDialog(parent)
    dlg.setWindowTitle("Nouvelle Note" if not note else "Modifier la Note")
    dlg.setMinimumSize(560, 420)
    lay = QVBoxLayout(dlg)

    form = QFormLayout()
    titre = QLineEdit()
    contenu = QTextEdit()
    contenu.setPlaceholderText("Votre note...")
    if note:
        titre.setText(note["titre"])
        contenu.setPlainText(note["contenu"] or "")
    form.addRow("Titre :", titre)
    lay.addLayout(form)
    lay.addWidget(QLabel("Note :"))
    lay.addWidget(contenu, 1)

    buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
    buttons.rejected.connect(dlg.reject)
    lay.addWidget(buttons)

    def _enregistrer():
        nom = titre.text().strip()
        if not nom:
            QMessageBox.warning(dlg, "Titre manquant",
                                "Donnez un titre a la note.")
            return
        contenu_texte = contenu.toPlainText().strip()
        if note is None:
            repos.blocnote.ajouter(_utilisateur_id(ctx), nom, contenu_texte)
            toast.succes(dlg, "Note creee.")
        else:
            repos.blocnote.modifier(note["id"], nom, contenu_texte)
            toast.succes(dlg, "Note modifiee.")
        dlg.accept()
        if on_saved:
            on_saved()

    buttons.accepted.connect(_enregistrer)
    dlg.exec_()