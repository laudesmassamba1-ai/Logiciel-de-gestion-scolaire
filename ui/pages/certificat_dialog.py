from PyQt5.QtWidgets import (
    QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QComboBox, QFormLayout,
    QVBoxLayout, QMessageBox,
)

from repositories import repos
from services import reports


def open_certificat_dialog(parent):
    dlg = QDialog(parent)
    dlg.setWindowTitle("Certificat de scolarite")
    dlg.resize(420, 160)
    dlg.setMinimumSize(360, 130)
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
            try:
                reports.certificat_scolarite(eleve, repos.parametres())
                QMessageBox.information(parent, "Certificat", "Certificat genere avec succes.")
            except Exception as exc:
                QMessageBox.warning(parent, "Certificat", f"Erreur : {exc}")
