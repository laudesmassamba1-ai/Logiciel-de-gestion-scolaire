"""Interface de la mise a jour (boite de dialogue, telechargement, install).

Reutilisable depuis le check automatique au lancement (main.py) et depuis
le bouton manuel de la page Parametres.
"""

from PyQt5.QtWidgets import QMessageBox, QProgressDialog

from core.config import APP_VERSION
from services import updater
from ui.workers import run_async


def _proposer(parent, infos, titre="Mise a jour disponible"):
    """Demande oui/non puis, si oui, telecharge et installe."""
    if not infos:
        return
    if updater.blocage_obligatoire(infos):
        libelle = ("Une mise a jour OBLIGATOIRE est disponible "
                   f"sur le serveur de l'ecole : v{infos['version_texte']}.\n\n"
                   "Vous devez la telecharger pour continuer a travailler.\n"
                   "L'application se fermera le temps de l'installation.")
        boite = QMessageBox(QMessageBox.Information, titre, libelle,
                            QMessageBox.Ok, parent)
        boite.exec_()
    else:
        source = ("le serveur de l'ecole"
                  if infos.get("source") == "serveur"
                  else "les releases GitHub")
        libelle = (f"Une nouvelle version est disponible : "
                   f"v{infos['version_texte']} (la version actuelle est "
                   f"v{APP_VERSION}).\n\n"
                   f"Elle est publiee sur {source}.\n"
                   "Voulez-vous la telecharger et l'installer maintenant ?")
        boite = QMessageBox(QMessageBox.Question, titre, libelle,
                            QMessageBox.Yes | QMessageBox.No, parent)
        boite.setDefaultButton(QMessageBox.Yes)
        reponse = boite.exec_()
        if reponse != QMessageBox.Yes:
            return

    _telecharger_et_installer(parent, infos)


def _telecharger_et_installer(parent, infos):
    progression = QProgressDialog(
        "Telechargement de la mise a jour en cours...", "", 0, 0, parent)
    progression.setWindowTitle("Mise a jour")
    progression.setCancelButton(None)
    progression.setWindowModality(2)  # ApplicationModal
    progression.setMinimumDuration(0)
    progression.show()
    # Petite pause pour que la boite se dessine avant le travail long.
    from PyQt5.QtCore import QTimer
    QTimer.singleShot(300, lambda: _lancer_telechargement(parent, infos, progression))


def _lancer_telechargement(parent, infos, progression):
    def _tache():
        return updater.telecharger(infos)

    def _fini(resultat):
        try:
            progression.close()
        except RuntimeError:
            pass
        chemin, erreur = resultat
        try:
            if erreur or not chemin:
                QMessageBox.warning(
                    parent, "Mise a jour",
                    f"{erreur or 'Telechargement impossible.'}")
                return
            action, message = updater.installer(chemin, infos)
            if action == "fermer":
                QMessageBox.information(
                    parent, "Mise a jour",
                    f"{message}\n\nUne fois l'installation terminee, la "
                    "nouvelle version sera active.")
                parent.close()
            elif action == "fait":
                QMessageBox.information(parent, "Mise a jour", message)
            else:
                QMessageBox.warning(parent, "Mise a jour", message)
        except RuntimeError:
            pass

    run_async(_tache, _fini)


def verifier_au_demarrage(parent):
    """Check silencieux : ne fait rien si rien/indisponible."""
    def _tache():
        try:
            return updater.verifier_mise_a_jour()
        except Exception:
            return None

    def _fini(infos):
        try:
            if infos:
                _proposer(parent, infos)
        except RuntimeError:
            pass

    run_async(_tache, _fini)


def verifier_manuel(parent):
    """Bouton 'Verifier les mises a jour' de la page Parametres."""
    def _tache():
        try:
            return updater.verifier_mise_a_jour()
        except Exception:
            return None

    def _fini(infos):
        try:
            if infos:
                _proposer(parent, infos)
            else:
                QMessageBox.information(
                    parent, "Mise a jour",
                    "Aucune mise a jour disponible (ou pas de connexion "
                    "Internet / serveur injoignable).")
        except RuntimeError:
            pass

    run_async(_tache, _fini)