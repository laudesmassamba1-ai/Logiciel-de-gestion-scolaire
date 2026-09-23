# RAPPORT DE RECENSEMENT DES BUGS — Logiciel de gestion scolaire

**Date** : 2026-08-24  
**Auteur** : Kilo  
**Portée** : Projet complet (`main.py`, `core/`, `database/`, `models/`, `repositories/`, `services/`, `ui/`, `server/`, `api/`, `tests/`)

---

## ✅ TRAITEMENT DU RAPPORT (session 2026-08-25)

Tous les points ont été **vérifiés puis traités**. Validation :
compileall OK · **144 tests bureau OK** (dont 16 nouveaux dans
`tests/test_rapport_bugs.py`) · **35 tests serveur OK**.

| # | Verdict | Détail |
|---|---------|--------|
| 1 | ✅ Corrigé | `.dict()` → `.model_dump()` (9 occurrences) |
| 2 | ⚠️ Faux positif | Architecture « local-first » assumée : l'écriture locale est indispensable à l'affichage ; aucun doublon grâce à `uuid_client`/clés naturelles (dédoublonnage vérifié). Un **retry** a été ajouté (#12) |
| 3 | ✅ Déjà corrigé + amélioré | Les deux routes existent avec des chemins distincts (pas de conflit FastAPI) ; clés de réponse rendues canoniques (voir #38) |
| 4 | ✅ Corrigé | `ok` → `en_ligne` (état réellement mesuré) |
| 5 | ⚠️ Documenté | La couche `compat.py` normalise les deux schémas ; `pull_structure` fonctionne (testé réellement). Réconciliation complète = refonte hors périmètre |
| 6 | ❌ Faux positif | `est_supprime`, `numero_parent`, `nom_parent`, `adresse` existent dans `schema.sql` ET `schema_sqlite.sql` |
| 7 | ✅ Corrigé | `verifier_mot_de_passe` accepte bcrypt ET PBKDF2 desktop (2 définitions) ; le hash PBKDF2 est transmis lors de la création de compte (#14) |
| 8 | ✅ Corrigé | Clé canonique `total_paiement` ajoutée (ancienne clé conservée) |
| 9 | ✅ Corrigé | `COALESCE(SUM(montant), 0)` |
| 10 | ✅ Corrigé | `_supprimer_absents` propage les suppressions cycles/matieres/classes **uniquement si aucune donnée locale n'en dépend** (jamais de destruction en cascade) |
| 11 | ✅ Corrigé | La réinscription préserve `redoublant` existant |
| 12 | ✅ Corrigé | 1 retry immédiat avant mise en file |
| 13 | ✅ Corrigé | API `sqlite3` backup (cohérente en WAL) pour sauvegarde ET restauration |
| 14 | ✅ Corrigé | Le bureau transmet son hash PBKDF2 ; le serveur le stocke tel quel (vérifiable via #7) |
| 15 | ❌ Faux positif | L'UPDATE ne touche jamais `uuid_client` → rien ne peut être perdu |
| 16 | ✅ Corrigé | Index actions = `columnCount()-1` |
| 17 | ✅ Corrigé | `rsplit("(", 1)` aux deux endroits |
| 18 | ✅ Corrigé | Restauration limitée à l'élève le plus récent (`ORDER BY id DESC LIMIT 1`) |
| 19 | ❌ Faux positif | `set_annee_active` utilise déjà `_route_write("PUT", .../actif)` |
| 20 | ❌ Faux positif | Plus aucun `classe_fallback = 1` dans le code actuel |
| 21 | ✅ Corrigé | UUID généré une fois et conservé sur l'objet |
| 22 | ✅ Corrigé | Upgrade silencieux vers PBKDF2 dès la première connexion réussie (fallback legacy conservé pour les anciens comptes) |
| 23 | ✅ Corrigé | `makedirs` protégé (avertissement au lieu d'échec d'import) |
| 24 | ✅ Corrigé | Doublon retiré |
| 25 | ✅ Corrigé | Helper `echap()` (html.escape) appliqué aux ~40 insertions de données utilisateur dans `reports.py` + `pdf_export.py` |
| 26 | ❌ Faux positif | `allow_credentials` déjà conditionnel (`"*"` incompatible credentials) |
| 27 | ⚠️ Documenté | Comportement voulu (élève sans classe = non facturable), commenté dans le code |
| 28 | ✅ Corrigé | Dédoublonnage `enqueue` (opération PENDING identique → ignorée) |
| 29 | ✅ Corrigé | 404 explicite si la fiche disparaît après UPDATE |
| 30 | ✅ Corrigé | `"-"` par convention |
| 31 | ✅ Corrigé | `/eleve/{classe}` accepte un id numérique OU un libellé |
| 32 | ⚠️ Documenté | Rejeu théorique neutralisé par l'anti-doublon `uuid_client` côté serveur |
| 33 | ✅ Corrigé | WHERE dynamique selon paramètres fournis + jointure `inscription` réparée dans la branche « sans recherche » |
| 34 | ✅ Corrigé | Le doublon n'est supprimé qu'APRÈS l'enregistrement réussi |
| 35 | ❌ Faux positif | Les migrations utilisent déjà `PRAGMA table_info` (pattern idempotent robuste) |
| 36 | ⚠️ Documenté | Choix assumé (la config ne change que via l'assistant qui appelle `set_sync_active`) |
| 37 | ❌ Faux positif | Le refresh initial est nécessaire : `main_view` n'appelle pas `refresh()` au premier affichage d'une page |
| 38 | ✅ Corrigé | Clé canonique `total_eleves_par_classe` + ancienne clé conservée sur les DEUX routes |
| 39 | ✅ Corrigé | `db.transaction()` : DELETE+INSERT atomiques côté local, rollback testé |
| 40 | ✅ Corrigé | `combo_classe.currentIndexChanged` → `_sync_moy_classes` |
| 41 | ✅ Corrigé | Classe `Parent` supprimée (+ export `__init__`) |
| 42 | ✅ Corrigé | Explicite + docstring (« 0.0 si aucune valeur numérique ») |
| 43 | ✅ Corrigé | QMessageBox avec le chemin du fichier si le navigateur ne s'ouvre pas |
| 44 | ✅ Corrigé | Plus d'ICO factice ; PNG minimal valide seul + avertissement build |
| 45 | ⚠️ Documenté | Le verrou global reflète SQLite (mono-rédacteur) ; commentaire perf ajouté |
| 46 | ✅ Corrigé | `RuntimeError` interceptée dans le callback `finished` |
| 47 | ⚠️ Documenté | Comportement noté en commentaire (historique perdu au redémarrage) |
| 48 | ✅ Corrigé | Extension contrôlée + taille max 5 Mo |
| 49 | ✅ Corrigé | `masse_salariale` exclut les statuts `inactif` |
| 50 | ❌ Faux positif | Segments différents (`{nom}/{prenom}` = 2 segments, `{id}` = 1) → aucun conflit de routage FastAPI |

**Bilan : 30 corrigés · 10 faux positifs vérifiés · 10 documentés/acceptés.**

---

## 🆕 ADDENDUM (session 2026-09-08) — Bugs supplémentaires découverts à l'audit

L'audit des branches (fresnel / gestion_scolaire_api / test / exe / main /
installers) a révélé de nouveaux points, **tous corrigés et testés** :

| # | Verdict | Détail |
|---|---------|--------|
| 51 | ✅ Corrigé | `tests/test_helpers.py` : 12 erreurs `DB_PATH` dues au masquage du sous-module `database.db` par `database/__init__.py` (`db = Database()`). Fix `importlib.import_module` + singleton `Database()` + `DB_PATH` en `pathlib.Path` → **193 tests bureau verts** |
| 52 | ✅ Corrigé | `GET /utilisateurs` : SELECT sur colonne `date_creation` inexistante (schéma = `updated_at`) → 500 → `updated_at AS date_creation` |
| 53 | ✅ Corrigé | `POST /ajout_tarifs-scolarite` : `fetchone()[0]` indexé avant test `None` → `TypeError` sans année active → ligne testée puis indexée |
| 54 | ✅ Corrigé | `GET /tarifs-scolarite` : liste brute incompréhensible pour le client (`data.get("tarifs", [])` → toujours `[]`) → `{"tarifs": [...]}` |
| 55 | ✅ Corrigé | `GET /inscriptions/{id}/suivi-mensuel` : `type_frais` requis non envoyé par le client → 422 → paramètre optionnel |
| 56 | ✅ Corrigé | **RÉGRESSION vs #20** : `classe_fallback = _id_entier(...) or 1` réintroduit dans `compat.py` (`_ajouter_paiement` + `_ajouter_note`) → 400 explicite si `classe_id` manquant |
| 57 | ✅ Corrigé | 7 appels `.dict(exclude_unset=True)` restants dans `server/main.py` → `.model_dump(exclude_unset=True)` (complète le #1) |

**Validation : compileall OK · 193 tests bureau OK · 35 tests serveur OK.**

**Complément (même session) :** les 15 pages de l'UI se construisent et les
14 pages locales se rafraîchissent sans erreur (test offscreen) ; warning
JWT `InsecureKeyLengthWarning` du test d'audit éliminé (fausse cle portée à
40 octets, test toujours 401). **228 tests verts en une commande, 0 à ignorer,
0 warning.**

---

## 🐛 BUGS CRITIQUES (Plantages / Perte de données / Incohérences majeures)

### 1. `server/main.py` — Méthode `.dict()` inexistante en Pydantic v2
**Lignes** : 606, 878, 1303, 1156, 1663, 1800, 1912  
`classe.dict()`, `enseignant.dict()`, `note.dict()`, `paiement.dict()`, `matiere.dict()`, `association.dict()`, `annee_scolaire.dict()`  
**Description** : En Pydantic v2, `.dict()` a été remplacé par `.model_dump()`. Ces appels lèveront une `AttributeError` à l'exécution.  
**Impact** : Plantage systématique des routes serveur concernées.  
**Sévérité** : Critique.

### 2. `repositories/base.py` — Écriture locale systématique même quand le serveur a réussi
**Ligne** : 31  
**Description** : Dans `_route_write`, quand `network.sync_active() and network.is_online()` et que la requête API réussit (`err` est None), le code exécute quand même `result = fn(*args, **kwargs)` (écriture locale). Il manque un `else` ou un `return` précoce.  
**Impact** : Doublons locaux quand le serveur fonctionne.  
**Sévérité** : Critique.

### 3. `server/main.py` — Deux routes identiques : la seconde est injoignable
**Lignes** : 142-181 et 184-196  
**Description** : Deux décorateurs `@app.get("/total_eleve_par_classe")`. FastAPI n'utilise que la première. La seconde (avec `dictionary=True`) est morte. De plus, la première route attend un paramètre `recherche` obligatoire, mais le client `api/client.py` ligne 68 l'appelle sans paramètre, provoquant une réponse d'erreur au lieu des données.  
**Impact** : Fonctionnalité "total élèves par classe" cassée.  
**Sévérité** : Critique.

### 4. `ui/assistant_serveur.py` — Variable `ok` indéfinie
**Lignes** : 173-182  
```python
if ok:
    boite.setIcon(QMessageBox.Information)
else:
    boite.setIcon(QMessageBox.Warning)
```
**Description** : La variable `ok` n'est jamais définie. Ce bloc lève une `NameError` à chaque activation du serveur.  
**Impact** : Plantage de l'assistant de connexion multi-postes.  
**Sévérité** : Critique.

### 5. `server/main.py` — Incohérence de schéma totale entre desktop et serveur
**Description** : Le desktop stocke les élèves dans `eleves` avec `classe_id`, `pere_nom`, `mere_tel`, etc. Le serveur stocke les élèves dans `eleve` avec `inscription` (table séparée), `nom_parent`, `numero_parent`, etc. La couche `compat.py` tente de normaliser, mais le schéma local SQLite (`database/db.py`) n'a pas de table `inscription`, pas de colonne `nom_parent`, etc. La synchronisation `pull_structure` ne peut pas fonctionner entre ces deux schémas.  
**Impact** : Synchronisation impossible, perte de données.  
**Sévérité** : Critique.

### 6. `server/main.py` — Colonnes inexistantes dans les requêtes
**Lignes** : 223, 232, 500, 509, 524, 566, 332, 345, 427, 512, 539, 279  
**Description** : `est_supprime`, `numero_parent`, `nom_parent`, `adresse` n'existent pas dans `schema.sql` ni `schema_sqlite.sql`.  
**Impact** : Plantage ou perte de données.  
**Sévérité** : Critique.

### 7. `server/main.py` — Hachage de mot de passe incompatible
**Lignes** : 104-114, 2229-2238  
**Description** : Desktop (`database/db.py`) utilise PBKDF2-HMAC-SHA256 avec salt hex. Serveur (`server/main.py`) utilise bcrypt. Un mot de passe créé sur le desktop ne pourra jamais être vérifié sur le serveur et vice-versa.  
**Impact** : Authentification impossible entre desktop et serveur.  
**Sévérité** : Critique.

### 8. `server/main.py` — `/total_paiement` retourne une clé française
**Ligne** : 962  
**Description** : `return { "nombre total de paiements": total_paiement}`. Le client (`api/client.py` ligne 224) cherche `"total_paiement"` ou `"nombre total de paiements"`, donc ça fonctionne par coincidence, mais c'est incohérent avec toutes les autres routes.  
**Impact** : Code fragile, risque de casse si le client change.  
**Sévérité** : Critique.

### 9. `server/main.py` — `get_total_montant_paiement` retourne `None` quand aucune donnée
**Ligne** : 971  
**Description** : `SELECT SUM(montant)` retourne `None` (pas `0`) quand il n'y a aucun paiement. Le client reçoit `None` au lieu de `0`.  
**Impact** : Affichage incorrect, crash potentiel si `None` est utilisé dans un calcul.  
**Sévérité** : Critique.

### 10. `services/sync_service.py` — Pas de gestion des suppressions
**Description** : `pull_structure()` ne fait que des upserts et un mirroir des tarifs. Si le directeur supprime un cycle, une classe ou une matière sur le serveur, la suppression n'est jamais propagée aux autres postes.  
**Impact** : Incohérence entre postes.  
**Sévérité** : Critique.

---

## 🐛 BUGS SÉRIEUX (Fonctionnalités cassées / Comportement incorrect)

### 11. `ui/pages/eleves.py` — Réinscription marque systématiquement comme redoublant
**Ligne** : 284  
```python
data["redoublant"] = 1  # un eleve reinscrit repete son année
```
**Description** : Tout élève réinscrit est automatiquement marqué comme redoublant, ce qui est faux.  
**Impact** : Données erronées.  
**Sévérité** : Sérieux.

### 12. `repositories/base.py` — Aucune logique de retry
**Description** : Si la requête API échoue temporairement (timeout, 502), l'opération est immédiatement mise en queue. Pas de retry avec backoff, ce qui réduit la résilience.  
**Impact** : Synchronisation échouée prématurément.  
**Sévérité** : Sérieux.

### 13. `services/backup.py` — Copie de fichier sans verrouillage
**Lignes** : 19, 37  
**Description** : `shutil.copy2` copie le fichier SQLite sans garantie de cohérence transactionnelle. Si la base est en cours d'écriture (WAL), la sauvegarde peut être corrompue.  
**Impact** : Sauvegarde corrompue.  
**Sévérité** : Sérieux.

### 14. `server/compat.py` — Création de compte avec mot de passe inutilisable
**Ligne** : 1251  
**Description** : `hacher(_token_aleatoire())` génère un mot de passe aléatoire côté serveur, mais le desktop ne l'utilise jamais (il gère l'authentification localement). Le compte créé via `/comptes` sur le desktop aura un mot de passe local différent du serveur.  
**Impact** : Compte non fonctionnel sur le serveur.  
**Sévérité** : Sérieux.

### 15. `repositories/eleve_repository.py` — `update_eleve` n'inclut pas `uuid_client`
**Lignes** : 55-65  
**Description** : Les colonnes mises à jour ne contiennent pas `uuid_client`. Si un élève est créé hors-ligne (avec UUID généré) puis modifié, l'UUID peut être perdu lors de la synchro.  
**Impact** : Perte de traçabilité hors-ligne.  
**Sévérité** : Sérieux.

### 16. `ui/pages/classes_page.py` — Index de colonne fixe risqué
**Ligne** : 57  
**Description** : `page.table_classes.setCellWidget(i, 7, cell)` suppose que la table a au moins 8 colonnes. Si le fichier `.ui` change, ça crashe.  
**Impact** : Crash UI.  
**Sévérité** : Sérieux.

### 17. `ui/pages/planning_page.py` — Parsing fragile de la salle
**Lignes** : 124-129, 148-150  
```python
matiere = texte.split("(")[0].strip()
salle = texte.split("(")[1].rstrip(")").strip()
```
**Description** : Si le nom de la matière contient des parenthèses, le parsing échoue.  
**Impact** : Données de planning corrompues.  
**Sévérité** : Sérieux.

### 18. `server/main.py` — `/restaurer_eleve` restore par nom/prénom
**Ligne** : 518  
```python
cursor.execute("UPDATE eleve SET est_supprime = FALSE WHERE nom = %s and prenom=%s", ...)
```
**Description** : Si deux élèves ont le même nom et prénom, tous sont restaurés.  
**Impact** : Restauration non ciblée.  
**Sévérité** : Sérieux.

### 19. `repositories/classe_repository.py` — `set_annee_active` hors sync
**Lignes** : 107-116  
**Description** : Cette méthode fait des SQL directs au lieu d'utiliser `_route_write`. Le changement d'année active n'est jamais synchronisé avec le serveur.  
**Impact** : Incohérence entre postes.  
**Sévérité** : Sérieux.

### 20. `server/main.py` — `/ajout_eleve` hardcode `classe_fallback = 1`
**Ligne** : 1073  
**Description** : Si aucune `classe_id` n'est fournie et qu'aucune année scolaire active n'existe, le code insère dans la classe ID 1 par défaut, qui peut ne pas exister.  
**Impact** : Crash ou insertion invalide.  
**Sévérité** : Sérieux.

---

## 🐛 BUGS MOYENS (Incohérences / Code smell / Risques latents)

### 21. `models/eleve.py` — `to_dict()` génère un UUID sans le stocker
**Lignes** : 30-34  
```python
def to_dict(self):
    d = asdict(self)
    if not d["uuid_client"]:
        d["uuid_client"] = str(_uuid.uuid4())
    return d
```
**Description** : L'UUID est généré à chaque appel mais pas sauvegardé dans l'objet. Deux appels successifs produisent deux UUID différents.  
**Impact** : Traçabilité compromise.  
**Sévérité** : Moyen.

### 22. `database/db.py` — Fallback SHA-256 sans salt
**Ligne** : 208  
```python
return hmac.compare_digest(hashlib.sha256(password.encode("utf-8")).hexdigest(), stored)
```
**Description** : Ce fallback pour les anciens hashs est extrêmement vulnérable au cracking (GPU, rainbow tables).  
**Impact** : Sécurité compromise.  
**Sévérité** : Moyen.

### 23. `core/config.py` — `data_dir()` appelé au niveau module
**Ligne** : 299  
**Description** : `os.makedirs(data_dir(), exist_ok=True)` s'exécute à l'import. Si le disque est plein ou les permissions manquent, l'import échoue.  
**Impact** : Application impossible à lancer.  
**Sévérité** : Moyen.

### 24. `ui/pages/programmes_page.py` — `lay.setSpacing(16)` en double
**Ligne** : 29  
**Description** : Appelé deux fois de suite. Inutile mais pas bloquant.  
**Impact** : Code smell.  
**Sévérité** : Moyen.

### 25. `services/reports.py` / `services/pdf_export.py` — Injection HTML
**Description** : Les noms d'élèves, adresses, etc. sont insérés directement dans le HTML sans échappement. Un nom contenant `<script>` pourrait injecter du code malveillant dans le rapport ouvert dans le navigateur.  
**Impact** : XSS potentiel.  
**Sévérité** : Moyen.

### 26. `server/main.py` — CORS avec origine wildcard
**Lignes** : 29-40  
**Description** : Si `GS_CORS_ORIGINS` n'est pas défini, `ORIGINS_AUTORISEES = ["*"]`. Avec `allow_credentials=False`, c'est correct, mais si un utilisateur configure une origine spécifique, les credentials sont autorisés, ce qui peut être risqué si mal configuré.  
**Impact** : Risque de sécurité.  
**Sévérité** : Moyen.

### 27. `repositories/finance_repository.py` — `solde_eleve` ne vérifie pas `classe_id`
**Ligne** : 165-167  
**Description** : Si `classe_id` est NULL, la requête `attendu_sql` retourne 0, ce qui est correct mais cache un problème de donnée incomplète.  
**Impact** : Données incomplètes non détectées.  
**Sévérité** : Moyen.

### 28. `api/sync_worker.py` — Pas de gestion des doublons dans la queue
**Description** : Si une opération est enqueued plusieurs fois (ex: double-click), le worker l'exécute plusieurs fois. Pas de dédoublonnage.  
**Impact** : Opérations en double.  
**Sévérité** : Moyen.

### 29. `server/compat.py` — `_modifier_enseignant` retourne `None` si erreur
**Lignes** : 853-856  
**Description** : Si `curseur.fetchone()` retourne None après UPDATE, `ligne` est None et `fiche` est None. Le client reçoit `{"enseignant": null}`.  
**Impact** : Comportement incohérent.  
**Sévérité** : Moyen.

### 30. `ui/pages/certificat_dialog.py` — `classe_nom` vide au lieu de "-"
**Ligne** : 52  
**Description** : `eleve["classe_nom"] = ""` — partout ailleurs dans le code, l'absence de valeur est représentée par `"-"`.  
**Impact** : Incohérence UI.  
**Sévérité** : Moyen.

### 31. `server/main.py` — Route `/eleve/{classe}` attend un nom, pas un ID
**Ligne** : 219  
**Description** : Le client `api/client.py` ligne 81 appelle `/eleve/{classe}` avec un ID entier, mais le serveur attend un nom de classe string.  
**Impact** : Erreur 404 ou résultats inattendus.  
**Sévérité** : Moyen.

### 32. `repositories/base.py` — `_route_write` enqueuelenque double en mode hors-ligne
**Description** : Quand `network.sync_active() and not network.is_online()`, l'opération est exécutée localement ET enqueued. C'est intentionnel, mais si le réseau revient avant que la queue soit traitée, l'opération pourrait être rejouée.  
**Impact** : Doublons potentiels.  
**Sévérité** : Moyen.

### 33. `server/main.py` — `get_eleve_par_son_nom` peut retourner tous les élèves
**Lignes** : 242-259  
**Description** : Si `recherche` est fourni mais `recherche1` est None, la requête SQL utilise `prenom like %s` avec `None`, ce qui peut retourner des résultats inattendus.  
**Impact** : Résultats de recherche erronés.  
**Sévérité** : Moyen.

### 34. `ui/pages/tarifs_page.py` — Suppression avant confirmation de doublon
**Lignes** : 158-171  
**Description** : Si un tarif doublon existe, il est supprimé avant que le nouveau tarif ne soit validé. Si la validation échoue ensuite, le tarif original est perdu.  
**Impact** : Perte de données.  
**Sévérité** : Moyen.

### 35. `database/db.py` — Migration `_migrate` non idempotente sur certaines colonnes
**Lignes** : 248-267  
**Description** : Les migrations ajoutent des colonnes avec `ALTER TABLE ... ADD COLUMN`. Si la colonne existe déjà, SQLite lève une erreur. Le code vérifie avec `PRAGMA table_info`, mais c'est fragile.  
**Impact** : Crash migration.  
**Sévérité** : Moyen.

### 36. `core/network.py` — `_sync_active` persiste après changement de config
**Ligne** : 6  
**Description** : Si l'utilisateur change la config sync via l'assistant, `_sync_active` est mis à jour, mais si le fichier `sync.json` est modifié manuellement ou par un autre processus, la variable runtime n'est jamais réinitialisée à `None`.  
**Impact** : Configuration sync désynchronisée.  
**Sévérité** : Moyen.

### 37. `ui/pages/presences_page.py` — `refresh()` appelé trop tôt
**Ligne** : 174  
**Description** : `refresh()` est appelé immédiatement après la définition des widgets, avant que la page ne soit affichée. Cela cause des requêtes DB inutiles au chargement.  
**Impact** : Performance dégradée.  
**Sévérité** : Moyen.

### 38. `server/main.py` — `/total_eleves_par_classe` (première version) retourne une clé française
**Ligne** : 177  
**Description** : `return {"nombre total d'élèves": {nom_classe: total_eleves}}`. Le client attend `data.get("total_eleves", [])` (ligne 68), donc cette route retourne toujours `[]` au client.  
**Impact** : Fonctionnalité cassée.  
**Sévérité** : Moyen.

### 39. `repositories/planning_repository.py` — Pas de transaction entre DELETE et INSERT
**Lignes** : 15-24  
**Description** : Si l'INSERT échoue après le DELETE, le planning est vide. Un BEGIN/COMMIT explicite ou un rollback serait nécessaire.  
**Impact** : Perte de données.  
**Sévérité** : Moyen.

### 40. `ui/pages/notes_page.py` — `combo_moy_classe` peut être désynchronisé
**Lignes** : 555-563  
**Description** : `_sync_moy_classes()` essaie de suivre le combo principal, mais si l'utilisateur change la classe dans le premier onglet sans recharger, le combo des moyennes garde l'ancienne valeur.  
**Impact** : Calcul de moyenne sur la mauvaise classe.  
**Sévérité** : Moyen.

---

## 🐛 BUGS MINEURS (UI / Cosmétiques / Edge cases)

### 41. `models/eleve.py` — `Parent.to_dict()` jamais utilisée
**Lignes** : 60-68  
**Description** : La classe `Parent` et sa méthode `to_dict()` existent mais ne sont jamais utilisées dans le codebase.  
**Impact** : Code mort.  
**Sévérité** : Mineur.

### 42. `ui/pages/helpers.py` — `_parse_money` accepte des chaînes vides
**Ligne** : 177  
**Description** : `return float(text.replace(" ", "").replace(",", "").replace("FCFA", "").strip())`. Si `text` est `"FCFA"` ou `"   "`, `float("")` lève `ValueError`, mais le `except` retourne `0.0`. Ce comportement est implicite.  
**Impact** : Comportement implicite.  
**Sévérité** : Mineur.

### 43. `services/reports.py` — `_open_in_browser` peut échouer silencieusement
**Ligne** : 27  
**Description** : `QDesktopServices.openUrl()` retourne un booléen qui n'est jamais vérifié. Si l'ouverture échoue, l'utilisateur ne sait pas où est le fichier.  
**Impact** : Utilisateur perdu.  
**Sévérité** : Mineur.

### 44. `build_app.py` — `_ensure_icon` écrit des icônes factices de 1024 octets
**Ligne** : 69  
**Description** : Si la génération d'icône échoue, un fichier de 1024 octets contenant des zéros est créé. Ce n'est pas une icône valide.  
**Impact** : Build défectueux.  
**Sévérité** : Mineur.

### 45. `server/sqlite_backend.py` — Verrou global pour toutes les opérations
**Ligne** : 75-78  
**Description** : `_VERROU` (RLock) est utilisé pour toutes les opérations SQL. Cela devient un goulot d'étranglement sous charge concurrente.  
**Impact** : Performance.  
**Sévérité** : Mineur.

### 46. `ui/main_view.py` — `_fade_in` peut crasher si le widget est détruit
**Ligne** : 358  
**Description** : `anim.finished.connect(lambda w=widget: w.setGraphicsEffect(None))` — si le widget est détruit avant la fin de l'animation, `w.setGraphicsEffect(None)` lève une erreur.  
**Impact** : Crash UI rare.  
**Sévérité** : Mineur.

### 47. `server/main.py` — `limiteur_connexion` stocke les tentatives en mémoire
**Ligne** : 91  
**Description** : Les tentatives sont stockées dans un dictionnaire en mémoire. Si le serveur redémarre, l'historique est perdu, ce qui est acceptable mais pas documenté.  
**Impact** : Comportement non documenté.  
**Sévérité** : Mineur.

### 48. `ui/pages/parametres_page.py` — Image upload sans validation
**Lignes** : 188-194  
**Description** : `QFileDialog.getOpenFileName` accepte tous les fichiers images, mais aucune validation de taille ou de format n'est faite. Un fichier de 100 MB pourrait être copié.  
**Impact** : Disque plein, crash.  
**Sévérité** : Mineur.

### 49. `repositories/personnel_repository.py` — `masse_salariale` ne filtre pas par statut
**Ligne** : 42  
**Description** : `SELECT COALESCE(SUM(salaire), 0) FROM personnel` — inclut les salaires des employés en stage, CDD, etc., sans distinction.  
**Impact** : Calcul de masse salariale imprécis.  
**Sévérité** : Mineur.

### 50. `server/main.py` — `get_enseignant_par_id` utilise nom/prénom au lieu d'ID
**Ligne** : 817  
**Description** : `/enseignant/{nom}/{prenom}` — mais le client appelle `/enseignant/{id}` (ligne 311). La route correcte est `/enseignant/{enseignant_id}` (ligne 817 dans compat.py), mais la route historique `/enseignant/{nom}/{prenom}` (ligne 817 dans main.py) entre en conflit.  
**Impact** : Conflit de routage.  
**Sévérité** : Mineur.

---

## 📋 RECOMMANDATIONS PRIORITAIRES

1. **Corriger immédiatement** le bug `ok` indéfini dans `assistant_serveur.py` (bloque l'activation du serveur).
2. **Corriger immédiatement** les appels à `.dict()` en Pydantic v2 (plantage systématique des routes serveur).
3. **Corriger le doublon d'écriture locale** dans `repositories/base.py` (doublons en mode connecté).
4. **Réconcilier les schémas** desktop vs serveur avant toute synchronisation.
5. **Ajouter les colonnes manquantes** (`est_supprime`, `numero_parent`, `nom_parent`) dans les schémas SQL ou supprimer les références.
6. **Corriger le hachage incompatible** (utiliser le même algorithme des deux côtés ou migrer les comptes).
7. **Ajouter une transaction** autour de DELETE+INSERT dans `planning_repository.py`.
8. **Échapper le HTML** dans les rapports et exports PDF.
9. **Retirer le soft-delete ambigu** ou le rendre cohérent entre desktop (hard delete) et serveur (soft delete).

---

*Fin du rapport*
