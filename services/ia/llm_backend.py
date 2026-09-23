"""Backend LLM optionnel pour Charo — connecte a ollama quand disponible.

Quand ollama tourne avec un modele (ex: phi3, llama3), Charo peut
deleguer certaines taches de comprehension du langage naturel pour
produire des reponses plus fluides, contextuelles et reflexivees.

Quand ollama n'est pas disponible, tout fonctionne en mode dégradé :
le systeme rule-based (moteur d'intentions + TF-IDF + graphe) reste
pleinement fonctionnel, 100 % offline et instantané.

Usage :
    from services.ia.llm_backend import LLMBackend
    llm = LLMBackend()
    if llm.disponible():
        texte = llm.refaire_naturel(rep_texte, question)
"""

import json
import threading
import time as _time
import urllib.request
import urllib.error

OLLAMA_URL = "http://127.0.0.1:11434/api/chat"
TAGS_URL = "http://127.0.0.1:11434/api/tags"
TIMEOUT = 60.0
# Cache de disponibilite : on re-teste ollama toutes les 30 s pour que
# l'app recupere le mode LLM si ollama demarre/se coupe en cours de route
# (audit : plus de cache illimite a vie).
CACHE_DISPONIBILITE = 30.0

# Durée maximum d'une génération. C'est la vraie garantie « fluide » :
# quel que soit le modèle ou la machine, Charo ne bloque JAMAIS plus de
# quelques secondes. Si ollama dépasse, la réponse est abandonnée et le
# moteur rule-based reprend la main (le modèle continue en arriere-plan).
TIMEOUT_GENERATION = 6.0

# Priorité des modèles rapides (petits, livrent une réponse en ~1-3 s
# sur un vieux PC sans carte graphique).
_PREFERRED_MODELS = [
    "qwen2.5:0.5b", "qwen2.5", "gemma:2b", "phi3",
    "qwen:0.5b", "llama3:8b", "tinyllama",
]

# Priorité des modèles « qualité » (plus gros, utilisés uniquement pour
# reformuler / raisonner, jamais pour le chemin rapide). phi3 (3,8B)
# est présent en standard et tourne sur 4 Go de RAM.
_QUALITY_MODELS = [
    "phi3", "qwen2.5", "llama3:8b", "gemma:2b",
    "qwen2.5:0.5b", "tinyllama",
]


class LLMBackend:
    """Client léger vers l'API ollama (HTTP natif, pas de dépendance)."""

    def __init__(self, modele=None):
        self.modele = modele
        self._ok = None
        self._teste_a = 0.0
        self._modele_detecte = None
        self._modele_qualite = None
        self._modele_charge = False

    def disponible(self) -> bool:
        """Vérifie si ollama tourne avec un modèle utilisable."""
        if self._ok is None or _time.monotonic() - self._teste_a > CACHE_DISPONIBILITE:
            self._ok = self._tester_connexion()
            self._teste_a = _time.monotonic()
        return self._ok

    def _tester_connexion(self) -> bool:
        """Vérifie qu'ollama est lancé et qu'au moins un modèle est disponible.
        Détecte automatiquement un modèle supporté si aucun n'est spécifié."""
        try:
            req = urllib.request.Request(
                TAGS_URL,
                headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=3.0) as r:
                data = json.loads(r.read().decode("utf-8"))
                modeles = {m["name"] for m in data.get("models", [])}
                if not modeles:
                    return False
                if self.modele and self.modele in modeles:
                    return True
                for m in _PREFERRED_MODELS:
                    if m in modeles:
                        self._modele_detecte = m
                        break
                else:
                    self._modele_detecte = sorted(modeles)[0]
                for m in _QUALITY_MODELS:
                    if m in modeles:
                        self._modele_qualite = m
                        break
                else:
                    self._modele_qualite = self._modele_detecte
                return True
        except Exception:
            return False

    @property
    def modele_effectif(self):
        """Le modèle réellement utilisé (détecté ou spécifié)."""
        if self.modele and self._ok:
            return self.modele
        return self._modele_detecte or "phi3"

    @property
    def modele_qualite(self):
        """Un modèle plus gros pour les tâches « soignées » (reformulation,
        raisonnement). Jamais pour le chemin rapide de réponse."""
        if self.modele and self._ok:
            return self.modele
        return self._modele_qualite or self.modele_effectif

    # ------------------------------------------------------------------
    # Génération de texte via ollama
    # ------------------------------------------------------------------

    def _generer(self, messages: list[dict], modele=None,
                 duree_max: float | None = None) -> str:
        """Appelle l'API chat d'ollama. Retourne le texte généré ou "".

        Le vrai garde-fou est *duree_max* (défaut TIMEOUT_GENERATION) :
        si ollama dépasse, on abandonne immédiatement et on renvoie "".
        L'appel HTTP continue en arrière-plan mais ne bloque plus l'app.
        """
        if not self.disponible():
            return ""
        if duree_max is None:
            duree_max = TIMEOUT_GENERATION
        payload = {
            "model": modele or self.modele_effectif,
            "messages": messages,
            "stream": False,
            "options": {"temperature": 0.3, "top_p": 0.9, "num_ctx": 2048},
        }
        resultat = {}
        abandonne = {"oui": False}

        def _appel():
            try:
                data = json.dumps(payload).encode("utf-8")
                req = urllib.request.Request(
                    OLLAMA_URL, data=data,
                    headers={"Content-Type": "application/json"},
                    method="POST")
                with urllib.request.urlopen(req,
                                            timeout=max(TIMEOUT,
                                                        duree_max + 10.0)) as r:
                    rep = json.loads(r.read().decode("utf-8"))
                if abandonne["oui"]:
                    return
                resultat["texte"] = rep.get("message", {}).get("content",
                                                               "").strip()
            except Exception:
                # Un appel abandonne ne doit pas marquer le backend KO :
                # ollama est juste lent, pas forcement en panne.
                if not abandonne["oui"]:
                    resultat["erreur"] = True

        fil = threading.Thread(target=_appel, daemon=True)
        fil.start()
        fil.join(duree_max)
        if fil.is_alive():
            abandonne["oui"] = True
            return ""                       # abandon : plus jamais de blocage
        if resultat.get("erreur"):
            self._ok = False
            self._modele_charge = False
            return ""
        texte = resultat.get("texte", "")
        if texte:
            self._modele_charge = True
        return texte

    # ------------------------------------------------------------------
    # Fonctions publiques
    # ------------------------------------------------------------------

    def reformuler_naturel(self, texte: str, question: str = "",
                           duree_max: float = 4.0) -> str:
        """Renvoie une version plus fluide et naturelle du texte,
        en conservant toutes les données factuelles."""
        if not texte.strip():
            return texte
        prompt = (
            "Tu es Charo, une assistante administrative scolaire "
            "très utile. Reformule la reponse suivante pour la rendre plus "
            "naturelle et conversationnelle, en conservant toutes les donnees "
            "numeriques et les faits. Ne dis pas 'je vais reformuler' ou "
            "de quoi tu as l'air.\n"
        )
        if question:
            prompt += f"Question de l'utilisateur : {question}\n"
        prompt += f"Reponse a reformuler : {texte}\n"
        resultat = self._generer([{"role": "user", "content": prompt}],
                                 modele=self.modele_qualite,
                                 duree_max=duree_max)
        return resultat if resultat else texte

    def ameliorer_suggestions(self, suggestions: list[str],
                              contexte: str = "",
                              duree_max: float = 3.0) -> list[str]:
        """Génère des suggestions de suivi plus pertinentes et naturelles."""
        if not suggestions:
            return suggestions
        prompt = (
            "Tu es Charo, une assistante administrative scolaire. "
            "Voici des suggestions de questions de suivi. Renumere-les "
            "sous forme de suggestions concises en français, 5 mots max, "
            "sans ponctuation superflue, sans numérotation.\n"
        )
        if contexte:
            prompt += f"Contexte récent : {contexte}\n"
        prompt += "Suggestions originales : " + ", ".join(suggestions) + "\n"
        resultat = self._generer([{"role": "user", "content": prompt}],
                                 duree_max=duree_max)
        if not resultat:
            return suggestions
        lignes = [l.strip().strip("-•. ") for l in resultat.split("\n") if l.strip()]
        if len(lignes) == len(suggestions):
            return lignes
        return suggestions

    def raisonner(self, question: str, faits: str,
                  duree_max: float = 8.0) -> str:
        """Fournit un raisonnement étape par étape pour une question."""
        prompt = (
            "Tu es Charo, assistante scolaire. Voici des faits et une "
            "question. Explique pas a pas comment tu arriverais a la reponse, "
            "en 2-3 phrases maximum.\n"
            f"Faits : {faits}\n"
            f"Question : {question}\n"
            "Explication :"
        )
        resultat = self._generer([{"role": "user", "content": prompt}],
                                 modele=self.modele_qualite,
                                 duree_max=duree_max)
        return resultat

    def detecter_intention(self, texte: str) -> str:
        """Classifie l'intention de la question en une catégorie."""
        prompt = (
            "Classifie la question suivante en une seule catégorie parmi : "
            "eleve, classe, note, moyenne, absence, caisse, paiement, "
            "personnel, planning, parametre, aide, conversation, creation, "
            "sync, calcul, inconnue.\n"
            f"Question : {texte}\n"
            "Categorie :"
        )
        resultat = self._generer([{"role": "user", "content": prompt}],
                                 duree_max=3.0)
        if resultat:
            for cat in ("eleve", "classe", "note", "moyenne", "absence",
                        "caisse", "paiement", "personnel", "planning",
                        "parametre", "aide", "conversation", "creation",
                        "sync", "calcul"):
                if cat in resultat.lower():
                    return cat
        return "inconnue"


# Instance singleton (lazy)
_backend = None


def get_backend():
    global _backend
    if _backend is None:
        _backend = LLMBackend()
    return _backend
