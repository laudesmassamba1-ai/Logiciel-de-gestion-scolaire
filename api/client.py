import time

import httpx

from core import config


class ApiError(Exception):
    pass


def _request(method, path, **kwargs):
    try:
        # Lecture dynamique : l'assistant graphique peut changer l'URL
        # du serveur pendant l'execution (changement de port).
        resp = httpx.request(method, config.API_BASE_URL + path,
                             timeout=config.API_TIMEOUT, **kwargs)
    except httpx.HTTPError as exc:

        return None, f"API hors ligne ({exc.__class__.__name__})"
    try:
        resp.raise_for_status()
    except httpx.HTTPStatusError:
        try:
            detail = resp.json().get("detail", resp.text)
        except ValueError:
            detail = resp.text or f"code {resp.status_code}"
        return None, f"Erreur API {resp.status_code} : {detail}"
    try:
        payload = resp.json()
    except ValueError as exc:
        return None, f"Reponse JSON invalide : {exc}"
    return payload, None


class _CacheDispo:

    _last = 0.0
    _value = None

    @classmethod
    def get(cls, force=False):
        now = time.monotonic()
        if force or cls._last == 0 or now - cls._last > 5:
            payload, err = _request("GET", "/annee_scolaire_active")
            cls._value = err is None
            cls._last = now
        return cls._value


def api_disponible(force=False) -> bool:
    try:
        return bool(_CacheDispo.get(force=force))
    except Exception:
        return False


class ApiClient:


    def total_eleves(self):
        data, err = _request("GET", "/total_eleves")
        if err:
            return None, err
        return data.get("total_eleves"), None

    def total_eleves_par_classe(self, recherche=None):
        data, err = _request("GET", "/total_eleves_par_classe",
                             params={"recherche": recherche})
        if err:
            return None, err
        return data, None

    def eleves(self):
        data, err = _request("GET", "/eleve")
        if err:
            return None, err
        return data.get("eleves", []), None

    def eleves_par_classe(self, classe):
        data, err = _request("GET", f"/eleve/{classe}")
        if err:
            return None, err
        return data.get("eleves", []), None

    def eleve_recherche(self, nom=None, prenom=None):
        data, err = _request("GET", "/eleve_recherche",
                             params={"recherche": nom, "recherche1": prenom})
        if err:
            return None, err
        return data.get("eleve", []), None

    def eleve_total_classe(self):
        data, err = _request("GET", "/eleve_total_classe")
        if err:
            return None, err
        return data.get("eleve_total_classe", []), None

    def ajouter_eleve(self, eleve, paiement):
        data, err = _request("POST", "/eleve",
                             json={"eleve": eleve, "paiement": paiement})
        return data, err

    def modifier_eleve(self, identifiant, donnees):
        return _request("PUT", f"/modifierEleve/{identifiant}", json=donnees)

    def supprimer_eleve(self, identifiant):
        return _request("DELETE", f"/eleve/{identifiant}")

    def eleves_supprimes(self):
        data, err = _request("GET", "/eleve_supprime")
        if err:
            return None, err
        return data.get("eleves_supprimes", []), None

    def restaurer_eleve(self, nom, prenom):
        return _request("PUT", f"/restaurer_eleve/{nom}/{prenom}")

    def parents_par_classe(self, classe):
        data, err = _request("GET", f"/parents_par_classe/{classe}")
        if err:
            return None, err
        return data.get("parents", []), None


    def total_classe(self):
        data, err = _request("GET", "/total_classe")
        if err:
            return None, err
        return data.get("total_classe"), None

    def classes(self):
        data, err = _request("GET", "/classe")
        if err:
            return None, err
        return data.get("classes", []), None

    def classe_par_id(self, identifiant):
        data, err = _request("GET", f"/classe/{identifiant}")
        if err:
            return None, err
        return data.get("classe"), None

    def ajouter_classe(self, nom, cycle_id):
        return _request("POST", "/classe",
                        json={"classe": nom, "cycle_id": cycle_id})

    def modifier_classe(self, identifiant, donnees):
        return _request("PUT", f"/modifierClasse/{identifiant}", json=donnees)

    def supprimer_classe(self, identifiant):
        return _request("DELETE", f"/supprimerClasse/{identifiant}")

    def total_cycle(self):
        data, err = _request("GET", "/total_cycle")
        if err:
            return None, err
        return data.get("total_cycle"), None

    def cycles(self):
        data, err = _request("GET", "/cycle")
        if err:
            return None, err
        return data.get("cycle", []), None

    def cycle_par_id(self, identifiant):
        data, err = _request("GET", f"/cycle/{identifiant}")
        if err:
            return None, err
        return data.get("cycle"), None

    def ajouter_cycle(self, nom):
        return _request("POST", "/cycle", json={"nom": nom})

    def modifier_cycle(self, identifiant, donnees):
        return _request("PUT", f"/modifierCycle/{identifiant}", json=donnees)

    def supprimer_cycle(self, identifiant):
        return _request("DELETE", f"/supprimerCycle/{identifiant}")

    def ajouter_annee_scolaire(self, libelle, date_debut, date_fin, est_active=False):
        return _request("POST", "/ajouter_annee_scolaire", json={
            "libelle": libelle, "date_debut": date_debut,
            "date_fin": date_fin, "est_active": est_active})

    def lister_annees_scolaires(self):
        data, err = _request("GET", "/lister_annees_scolaires")
        if err:
            return None, err
        return data.get("annees_scolaires", []), None

    def annee_scolaire_active(self):
        data, err = _request("GET", "/annee_scolaire_active")
        if err:
            return None, err
        return data.get("annee_scolaire_active"), None


    def tarifs_scolarite(self):
        data, err = _request("GET", "/tarifs-scolarite")
        if err:
            return None, err
        return data.get("tarifs", []), None

    def ajouter_tarif(self, donnees):
        return _request("POST", "/tarifs-scolarite", json=donnees)

    def modifier_tarif(self, tarif_id, donnees):
        return _request("PUT", f"/tarifs-scolarite/{tarif_id}", json=donnees)

    def supprimer_tarif(self, tarif_id):
        return _request("DELETE", f"/tarifs-scolarite/{tarif_id}")

    def tarifs_scolarite_classe(self, classe_id):
        data, err = _request("GET", f"/tarifs-scolarite/classe/{classe_id}")
        if err:
            return None, err
        return data.get("tarifs", []), None

    def total_paiement(self):
        data, err = _request("GET", "/total_paiement")
        if err:
            return None, err
        for cle in ("nombre total de paiements", "total_paiement"):
            if cle in data:
                return data[cle], None
        return None, "Cle 'total_paiement' absente de la reponse"

    def total_montant_paiement(self):
        data, err = _request("GET", "/total_montant_paiement")
        if err:
            return None, err
        return data.get("total_montant_paiement"), None

    def paiements(self):
        data, err = _request("GET", "/paiement")
        if err:
            return None, err
        return data.get("paiement", []), None

    def ajouter_paiement(self, donnees):
        return _request("POST", "/paiement", json=donnees)

    def modifier_paiement(self, identifiant, donnees):
        return _request("PUT", f"/modifierPaiement/{identifiant}", json=donnees)

    def supprimer_paiement(self, identifiant):
        return _request("DELETE", f"/supprimerPaiement/{identifiant}")

    def solde_inscription(self, inscription_id):
        data, err = _request("GET", f"/inscriptions/{inscription_id}/solde")
        if err:
            return None, err
        return data, None

    def suivi_mensuel_inscription(self, inscription_id):
        data, err = _request("GET", f"/inscriptions/{inscription_id}/suivi-mensuel")
        if err:
            return None, err
        return data, None

    def bilan_annee(self, annee_scolaire):
        data, err = _request("GET", f"/paiement/bilan/{annee_scolaire}")
        if err:
            return None, err
        return data.get("paiement", []), None

    def bilan_trimestre(self, trimestre):
        data, err = _request("GET", f"/paiement/bilan/trimestre/{trimestre}")
        if err:
            return None, err
        return data.get("paiement", []), None

    def bilan_type_frais(self, type_frais):
        data, err = _request("GET", f"/paiement/bilan/type_frais/{type_frais}")
        if err:
            return None, err
        return data.get("paiement", []), None

    def bilan_eleve(self, nom, prenom):
        data, err = _request("GET", f"/paiement/bilan/eleve/{nom}/{prenom}")
        if err:
            return None, err
        return data.get("paiement", []), None

    def bilan_classe(self, classe_id):
        data, err = _request("GET", f"/paiement/bilan/classe/{classe_id}")
        if err:
            return None, err
        return data.get("paiement", []), None

    def bilan_mode_paiement(self, mode_paiement):
        data, err = _request("GET", f"/paiement/bilan/mode_paiement/{mode_paiement}")
        if err:
            return None, err
        return data.get("paiement", []), None


    def total_enseignant(self):
        data, err = _request("GET", "/total_enseignant")
        if err:
            return None, err
        return data.get("total_enseignant"), None

    def enseignants(self):
        data, err = _request("GET", "/enseignant")
        if err:
            return None, err
        return data.get("enseignant", []), None

    def enseignant_par_id(self, identifiant):
        data, err = _request("GET", f"/enseignant/{identifiant}")
        if err:
            return None, err
        return data.get("enseignant"), None

    def ajouter_enseignant(self, donnees):
        return _request("POST", "/enseignant", json=donnees)

    def modifier_enseignant(self, identifiant, donnees):
        return _request("PUT", f"/modifierEnseignant/{identifiant}", json=donnees)

    def supprimer_enseignant(self, identifiant):
        return _request("DELETE", f"/supprimerEnseignant/{identifiant}")

    def matieres(self):
        data, err = _request("GET", "/matiere")
        if err:
            return None, err
        return data.get("matieres", []), None

    def matiere_par_id(self, identifiant):
        data, err = _request("GET", f"/matiere/{identifiant}")
        if err:
            return None, err
        return data.get("matiere"), None

    def ajouter_matiere(self, nom):
        return _request("POST", "/matiere", json={"nom": nom})

    def modifier_matiere(self, identifiant, donnees):
        return _request("PUT", f"/modifierMatiere/{identifiant}", json=donnees)

    def supprimer_matiere(self, identifiant):
        return _request("DELETE", f"/supprimerMatiere/{identifiant}")

    def associer_matiere_classe_enseignant(self, classe_id, matiere_id,
                                           enseignant_id, coefficient=1):
        return _request("POST", "/associerMatiereClasseEnseignant", json={
            "classe_id": classe_id, "matiere_id": matiere_id,
            "enseignant_id": enseignant_id, "coefficient": coefficient})

    def programme(self, classe):
        data, err = _request("GET", f"/programme/{classe}")
        if err:
            return None, err
        return data.get("programme", []), None

    def modifier_programme(self, identifiant, donnees):
        return _request("PUT", f"/modifierProgramme/{identifiant}", json=donnees)

    def supprimer_programme(self, identifiant):
        return _request("DELETE", f"/supprimerProgramme/{identifiant}")


    def total_note(self):
        data, err = _request("GET", "/total_note")
        if err:
            return None, err
        return data.get("total_note"), None

    def notes(self):
        data, err = _request("GET", "/note")
        if err:
            return None, err
        return data.get("note", []), None

    def notes_eleve(self, nom, prenom):
        data, err = _request("GET", f"/note/eleve/{nom}/{prenom}")
        if err:
            return None, err
        return data.get("note", []), None

    def ajouter_note(self, donnees):
        return _request("POST", "/note", json=donnees)

    def modifier_note(self, identifiant, donnees):
        return _request("PUT", f"/modifierNote/{identifiant}", json=donnees)

    def supprimer_note(self, identifiant):
        return _request("DELETE", f"/supprimerNote/{identifiant}")

    def moyenne(self, nom, prenom, type_evaluation):
        data, err = _request("GET", f"/moyenne/{nom}/{prenom}/{type_evaluation}")
        if err:
            return None, err
        return data, None

    def bulletin(self, nom, prenom, trimestre):
        data, err = _request("GET", f"/bulletin/{nom}/{prenom}/{trimestre}")
        if err:
            return None, err
        return data, None

    def total_presence(self, classe):
        data, err = _request("GET", f"/total_presence/{classe}")
        if err:
            return None, err
        return data.get("total_presence"), None

    def presence_par_classe(self, classe):
        data, err = _request("GET", f"/presence/{classe}")
        if err:
            return None, err
        return data.get("presence", []), None

    def liste_presence_par_classe(self, classe):
        data, err = _request("GET", f"/liste_de_presence_par_classe/{classe}")
        if err:
            return None, err
        for cle in ("liste de presence par classe", "liste_presence"):
            if cle in data:
                return data[cle], None
        return None, "Cle 'liste de presence par classe' absente de la reponse"

    def ajouter_presence(self, donnees):
        return _request("POST", "/presence", json=donnees)

    def modifier_presence(self, identifiant, donnees):
        return _request("PUT", f"/modifierPresence/{identifiant}", json=donnees)

    def supprimer_presence(self, identifiant):
        return _request("DELETE", f"/supprimerPresence/{identifiant}")


client = ApiClient()
