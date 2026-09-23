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
TOKEN_EXPIRATION_SECONDS = 8 * 3600
try:
    _raw = os.environ.get("GS_TOKEN_EXPIRATION_SECONDES", "").strip()
    if _raw:
        TOKEN_EXPIRATION_SECONDS = int(_raw)
except (ValueError, TypeError):
    pass


# ============================================================
# SECRET DE SYNDICATION (optionnel, protege les flux sensibles)
# ============================================================
# Quand GS_SYNC_SECRET est defini, les routes sensibles exigent
# l'en-tete X-Sync-Secret correspondante. A defaut (trusted LAN),
# les routes restent ouvertes pour la retrocompatibilite bureau.
SYNC_SECRET = os.environ.get("GS_SYNC_SECRET", "")


def sync_autorisee(secret_entete: str) -> bool:
    """True si pas de secret configure OU si le secret est valide."""
    if not SYNC_SECRET:
        return True
    import hmac as _hmac
    return _hmac.compare_digest(SYNC_SECRET, secret_entete or "")


# ============================================================
# CODE DE L'ECOLE (cloisonnement entre etablissements)
# ============================================================
# Meme logiciel installe dans plusieurs ecoles : chaque serveur porte le
# code de SON ecole (GS_ECOLE_CODE, injecte par le poste hote). Les postes
# clients l'envoient dans l'en-tete X-Ecole-Code. Defini -> tout acces avec
# un code different (ou absent) est refuse : une ecole ne peut jamais
# synchroniser ses donnees avec une autre. Vide -> retrocompatibilite.
ECOLE_CODE = os.environ.get("GS_ECOLE_CODE", "").strip()


def ecole_autorisee(code_entete: str) -> bool:
    """True si aucun code n'est configure OU si le code correspond."""
    if not ECOLE_CODE:
        return True
    import hmac as _hmac
    return _hmac.compare_digest(ECOLE_CODE, str(code_entete or "").strip())


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


# ============================================================
# JWT ACCESS + REFRESH TOKENS
# ============================================================
# Double-token pattern :
#   - access token : courte duree (configurable, defaut 8h), pour API calls
#   - refresh token : longue duree (30j), pour renouveler l'access sans
#     redemander les identifiants. Stocke hashé en base (revocable).
# Le client desktop gere le renouvellement automatique (refresh_token_auto).

REFRESH_TOKEN_EXPIRATION_DAYS = 30
REFRESH_TOKEN_EXPIRATION_SECONDS = REFRESH_TOKEN_EXPIRATION_DAYS * 86400


def creer_tokens(utilisateur_id: int, role: str, username: str) -> dict:
    """Genere un couple access_token / refresh_token pour un utilisateur."""
    import jwt as _jwt
    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)
    access_payload = {
        "sub": str(utilisateur_id),
        "username": username,
        "role": role,
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=TOKEN_EXPIRATION_SECONDS)).timestamp())
    }
    refresh_payload = {
        "sub": str(utilisateur_id),
        "username": username,
        "type": "refresh",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=REFRESH_TOKEN_EXPIRATION_SECONDS)).timestamp())
    }
    access_token = _jwt.encode(access_payload, SECRET_KEY, algorithm=ALGORITHM)
    refresh_token = _jwt.encode(refresh_payload, SECRET_KEY, algorithm=ALGORITHM)
    return {"access_token": access_token, "refresh_token": refresh_token,
            "token_type": "bearer", "expires_in": TOKEN_EXPIRATION_SECONDS}


def verifier_access_token(token: str) -> dict:
    """Verifie un access token et retourne le payload (leve HTTPException si invalide)."""
    import jwt as _jwt
    try:
        payload = _jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Type de token invalide")
        return payload
    except _jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expire")
    except _jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token invalide")


def verifier_refresh_token(token: str, conn) -> dict:
    """Verifie un refresh token (en base pour revocation)."""
    import jwt as _jwt
    import hashlib

    try:
        payload = _jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Type de token invalide")

        # Verifie en base que le refresh token n'a pas ete revoque
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT 1 FROM refresh_tokens WHERE token_hash = %s AND revoque = 0",
            (token_hash,))
        if not cursor.fetchone():
            raise HTTPException(status_code=401, detail="Refresh token revoque ou inconnu")
        cursor.close()

        return payload
    except _jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh token expire")
    except _jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Refresh token invalide")


def stocker_refresh_token(conn, utilisateur_id: int, refresh_token: str):
    """Stocke le hash du refresh token en base (pour revocation)."""
    import hashlib
    from datetime import datetime, timedelta, timezone

    token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
    expires_at = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRATION_DAYS)

    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO refresh_tokens (utilisateur_id, token_hash, expire_le)
           VALUES (%s, %s, %s)""",
        (utilisateur_id, token_hash, expires_at))
    conn.commit()
    cursor.close()


def revoquer_refresh_token(conn, refresh_token: str):
    """Revoque un refresh token (logout, changement mot de passe, etc.)."""
    import hashlib
    token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE refresh_tokens SET revoque = 1 WHERE token_hash = %s",
        (token_hash,))
    conn.commit()
    cursor.close()


def revoquer_tous_refresh_tokens(conn, utilisateur_id: int):
    """Revoque tous les refresh tokens d'un utilisateur."""
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE refresh_tokens SET revoque = 1 WHERE utilisateur_id = %s",
        (utilisateur_id,))
    conn.commit()
    cursor.close()
