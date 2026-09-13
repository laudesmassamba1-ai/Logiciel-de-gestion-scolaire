from PyQt5.QtWidgets import (
    QDialog, QDialogButtonBox, QLabel, QComboBox, QFormLayout,
    QVBoxLayout, QMessageBox,
)

from repositories import repos
from services import reports
from ui import toast


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
    btn_ok = buttons.button(QDialogButtonBox.Ok)
    btn_ok.setText("Generer")
    buttons.rejected.connect(dlg.reject)
    lay.addWidget(buttons)

    def valider():
        if combo.currentData() is None:
            QMessageBox.warning(dlg, "Certificat",
                                "Selectionnez un eleve (aucun eleve dans cette selection).")
            return
        dlg.accept()

    btn_ok.clicked.connect(valider)

    dlg.exec_()
    if dlg.result() == QDialog.Accepted:
        eleve = repos.eleve_by_id(combo.currentData())
        if eleve:
            eleve["classe_nom"] = "-"
            classe = repos.classe_by_id(eleve["classe_id"]) if eleve["classe_id"] else None
            if classe:
                eleve["classe_nom"] = classe["nom"]
            try:
                reports.certificat_scolarite(eleve, repos.parametres())
                toast.succes(parent, "Certificat genere avec succes.")
            except Exception as exc:
                QMessageBox.warning(parent, "Certificat", f"Erreur : {exc}")
