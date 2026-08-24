"""
Securite du serveur : configuration chargee depuis un fichier .env,
secret JWT persistant et limiteur de tentatives de connexion.

Le fichier .env (a cote de ce module) est charge automatiquement au
demarrage. Voir .env.example pour la liste des variables supportees.
"""

import os
import secrets as _secrets
import threading
import time

from fastapi import HTTPException

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None

DOSSIER_SERVEUR = os.path.dirname(os.path.abspath(__file__))

if load_dotenv is not None:
    load_dotenv(os.path.join(DOSSIER_SERVEUR, ".env"))


# ============================================================
# SECRET JWT
# ============================================================

TAILLE_MINIMALE_SECRET = 32


def charger_secret_jwt(dossier=None):
    """Retourne le secret de signature des tokens JWT.

    Ordre de priorite :
      1. variable d'environnement GS_JWT_SECRET (32 caracteres minimum) ;
      2. fichier .jwt_secret persistant dans le dossier du serveur ;
      3. generation d'un secret aleatoire enregistre dans .jwt_secret.

    Un secret genere puis conserve, les tokens restent valides apres un
    redemarrage du service sans jamais figer une valeur faible dans le code.
    """
    dossier = dossier or DOSSIER_SERVEUR
    secret_env = os.environ.get("GS_JWT_SECRET", "").strip()
    if secret_env:
        if len(secret_env) < TAILLE_MINIMALE_SECRET:
            raise ValueError(
                "GS_JWT_SECRET est trop court : 32 caracteres minimum "
                "(par exemple : python -c \"import secrets; print(secrets.token_urlsafe(48))\")"
            )
        return secret_env

    chemin_fichier = os.path.join(dossier, ".jwt_secret")
    try:
        with open(chemin_fichier, "r", encoding="utf-8") as fichier:
            secret_fichier = fichier.read().strip()
        if len(secret_fichier) >= TAILLE_MINIMALE_SECRET:
            return secret_fichier
    except OSError:
        pass

    nouveau_secret = _secrets.token_urlsafe(48)
    with open(chemin_fichier, "w", encoding="utf-8") as fichier:
        fichier.write(nouveau_secret)
    try:
        os.chmod(chemin_fichier, 0o600)
    except OSError:
        pass  # Windows ne supporte pas les permissions POSIX
    return nouveau_secret


SECRET_KEY = charger_secret_jwt()
ALGORITHM = "HS256"
TOKEN_EXPIRATION_SECONDS = int(os.environ.get("GS_TOKEN_EXPIRATION_SECONDES", 8 * 3600))


# ============================================================
# LIMITEUR DE TENTATIVES DE CONNEXION
# ============================================================

class LimiteurConnexion:
    """Limiteur en memoire : N echecs par (IP, identifiant) sur une fenetre
    glissante entrainent un blocage temporaire. Sans dependance externe,
    suffisant pour un reseau local mono-serveur."""

    def __init__(self, max_echecs=5, fenetre_secondes=300):
        self.max_echecs = max_echecs
        self.fenetre = fenetre_secondes
        self._echecs = {}
        self._verrou = threading.Lock()

    @staticmethod
    def _cle(adresse_ip, identifiant):
        return ((adresse_ip or "?"), str(identifiant or "").strip().lower())

    def _purger(self, maintenant):
        for cle in [c for c, t in self._echecs.items()
                    if not t or maintenant - t[-1] >= self.fenetre]:
            del self._echecs[cle]

    def verifier(self, adresse_ip, identifiant):
        """Leve HTTPException 429 si le couple (IP, identifiant) est bloque."""
        cle = self._cle(adresse_ip, identifiant)
        maintenant = time.time()
        with self._verrou:
            essais = [t for t in self._echecs.get(cle, [])
                      if maintenant - t < self.fenetre]
            self._echecs[cle] = essais
            if len(essais) >= self.max_echecs:
                attente = int(self.fenetre - (maintenant - essais[0])) + 1
                raise HTTPException(
                    status_code=429,
                    detail=(
                        "Trop de tentatives de connexion echouees. "
                        f"Reessayez dans {attente // 60 + 1} minute(s)."
                    ),
                )

    def enregistrer_echec(self, adresse_ip, identifiant):
        cle = self._cle(adresse_ip, identifiant)
        maintenant = time.time()
        with self._verrou:
            essais = self._echecs.setdefault(cle, [])
            essais.append(maintenant)
            if len(self._echecs) > 10000:
                self._purger(maintenant)

    def reinitialiser(self, adresse_ip=None, identifiant=None):
        """Efface tout l'historique (ou une seule cle). Utilise par les tests."""
        with self._verrou:
            if adresse_ip is None and identifiant is None:
                self._echecs.clear()
            else:
                self._echecs.pop(self._cle(adresse_ip, identifiant), None)


limiteur_connexion = LimiteurConnexion()
