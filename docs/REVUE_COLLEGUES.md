# Revue du travail des collegues — Backend et synchro multi-postes

> Audit factuel des livrables des deux branches collèges :
> - **`gestion_scolaire_api`** — backend FastAPI + MySQL (college Sterling, auteur
>   `sterlingnkenzo3-cell`, ~24 commits) : `main.py` (2409 lignes, 87 routes),
>   `schema.sql`, `requirements.txt`, `setup_service.bat`.
> - **`fresnel`** — synchro offline-first (college Fresnel, auteur
>   `sterlingnkenzo3-cell` également) : `sync_engine.py`, `sync_pull.py`,
>   `sync_queue.py`, `database.py`, `config.json`, `installer_synchro.bat`.
>
> Chaque item indique le numero de ligne du code d'origine.

---

## A. Ce qui devait etre code/ajoute/creer mais ne l'a pas ete

### Backend (gestion_scolaire_api / `api_main.py`)

1. **Aucun test livre** : aucune suite de tests backend ni synchro dans les deux
   branches (`git ls-tree` vide de tests).
2. **Authentification inachevee** : le token JWT est emis au login
   (`creer_token_acces` api_main.py:2276) mais **jamais verifie** — aucun
   `jwt.decode`, aucun `Depends`, aucune lecture d'en-tete `Authorization`.
   Toutes les 87 routes CRUD sont publiques.
3. **`GET /utilisateurs` (api_main.py:2390) expose publiquement** noms, emails,
   telephones de tous les comptes, sans aucun controle d'acces.
4. **Pas de route profil `/me`, pas de deconnexion, pas de changement de mot de
   passe**, pas de rate-limiting ni de verrouillage de compte.
5. **Colonne `identifiant` jamais ecrite** : l'INSERT utilisateur (L.2306-2318)
   l'omet alors que le modele la propose ; la condition de login
   `WHERE telephone = %s OR email = %s OR identifiant = %s` (L.2336) ne peut
   donc jamais matcher par identifiant.
6. **Route `GET /eleve/{id}` inexistante** : seuls `PUT /eleve/{eleve_id}`
   (L.412) et `DELETE /eleve/{id}` (L.481) existent — impossible de consulter
   un eleve par son id.
7. **ENUM jamais calibres** : commentaires `a verifier/ajuster` dans
   `schema.sql` (L.95 et L.111) ; les valeurs metier du code (« Scolarité »,
   « Espèces », « Mobile Money », « 1er Trimestre », « En retard ») sont
   incompatibles avec les ENUM MySQL -> `Error 1265 Data truncated`.
8. **Bareme du bulletin non valide** : `# ⚠️ à confirmer avec le vrai barème`
   (L.1445) : la moyenne du bulletin n'est pas conforme au reglement de l'ecole.

### Synchro (fresnel)

9. **`remplacer_temp_par_serveur()` (database.py:292-305) ecrit mais joue
   nulle part** : le remappage des id locaux vers les id serveur au push est
   inoperant -> doublons garantis.
10. **`charger_donnees_par_defaut()` promis (database.py:200-203) mais jamais
    appele** au premier boot : les tables de reference (cycles, classes) sont
    vides hors-ligne alors que le commentaire promettait des donnees de test.
11. **Fichier de config mal nomme** : le moteur lit `"config.json"` (engine:10)
    mais le fichier livre s'appelle autrement -> bascule silencieuse sur
    `http://127.0.0.1:8000` sans erreur visible.
12. **IP en dur `172.20.10.3`** (sous-reseau de partage de connexion
    telephone/hotspot) -> serveur injoignable hors du labo ; lue une seule fois
    a l'import (engine:26), toute modification exige un redemarrage.
13. **`installer_synchro.bat` fragile** : aucun controle `errorlevel` apres
    `nssm install`/`set` (si le service existe deja ou pas admin, tout echoue
    en silence) ; logs nssm sans rotation (grossissent indefiniment).
14. **`fresnel_api_client.py:28` = `pass  # Bascule silencieuse sur la base
    SQLite...`** : implementation differee (absent de l'arbre final).
15. **`synchroniser_toutes_les_donnees` (pull:287) jamais utilise**.

### Code mort / duplication (commun)

16. Helpers d'authentification **dupliques 2 fois** (L.67-77 puis L.2263-2272,
    la 2e ecrase la 1re) ; **`get_presence_par_classe` defini 2 fois**
    (L.1485-1486 et L.1530-1531).
17. Imports morts : `passlib`, double `from typing import Optional` ;
    CORS invalide `["*"]` + `allow_credentials=True` (L.16-22).

---

## B. Tout ce qui ne marche pas dans le backend

### B1. Routes 500 systématiques (SQL vers colonnes inexistantes)

1. `/eleve_recherche` sans parametre -> **500** : requete
   `eleve.classe_id=classe.id` (L.212) alors que la classe est portee par la
   table `inscription` (schema L.36-50) ; `eleve.classe_id` n'existe pas.
2. `/bulletin/...` -> **500 a 100 %** : `note.programme_id` (L.1428, L.1437)
   et `note.eleve_id` (L.1420, L.1429-1430, L.1438-1439) n'existent pas dans
   le schema (L.96-108, qui n'a que `matiere_id`).
3. `/paiement/bilan/classe/{classe}` -> **500** sous MySQL `ONLY_FULL_GROUP_BY`
   (L.1051) : `SELECT type_frais, SUM(...), classe.classe ... GROUP BY
   type_frais` selectionne une colonne non groupee.
4. `delete_un_enseignant` -> **500** si enseignant absent : `fetchone()[0]`
   sur `None` avant le test (L.932-936) ; le DELETE est execute avant le
   controle d'existence, dans le mauvais ordre.
5. `creer_tarif_scolarite` sans annee active -> **500** : `fetchone()[0]`
   (L.1987) avant le test `if not annee_scolaire` (L.1989) ; le `400` prevu
   (L.1990-1993) est du code mort.
6. `put_une_classe` (L.606-647) : le `HTTPException(404)` (L.623) est leve
   DANS le `try`, puis `except Exception` (L.640) le capte et le re-emet en
   **500** (L.642). `modifier_eleve` faisait pourtant le bon pattern
   (`except HTTPException: raise`).
7. **`None[0]` -> TypeError 500** : idem pour toute route qui indexe
   `fetchone()[0]` sans controle (`delete_un_enseignant`, `creer_tarif`).

### B2. Reponses 200 mensongères / 404 absents

8. `supprimer_eleve` (L.481-493) marque `est_supprime=TRUE` meme si l'id
   n'existe pas -> 200 « supprime » sans effet.
9. `restaurer_eleve` (L.505-517) restaure par `nom`+`prenom` sans controle
   d'existence -> restaure potentiellement plusieurs homonymes ; 200 meme si
   0 ligne touchee.
10. `modifier_note` (L.1339-1342) -> 404 a tort si les valeurs envoyees sont
    identiques a l'existant (`rowcount == 0`).
11. `supprimer_programme` (L.1905-1912) et `modifier_tarif_scolarite`
    (L.2031-2068) : 200 « reussi » sans effet sur id inexistant.
12. Recherches inexactes : `LIKE %s` sans wildcard (L.1001, L.526-527) equivaut
    a un `=` ; prenom `LIKE '%None%'` (L.208) quand seul `recherche` est fourni
    -> resultat vide.

### B3. Doublons et pertes de donnees (cœur de l'architecture offline-first)

13. **`/ajout_eleve` non-idempotent sur le paiement** (L.279-288) : en cas de
    timeout apres commit serveur, la ligne de file reste ; au re-push le
    garde-fou renvoie 200 « deja enregistre » AVANT l'insertion du paiement
    -> **le paiement est perdu definitivement** et la ligne de file est
    supprimee sur ce 200 (engine:73-76).
14. **`/ajout_paiement`, `/ajout_note`, `/ajout_presence` sans aucun garde
    anti-doublon** (L.1118, L.1264, L.1560) ni contrainte UNIQUE sur
    `uuid_client` en MySQL -> re-push apres timeout = doublons.
15. **`uuid_client` jamais stoke cote serveur** : inscription (INSERT
    L.326-332 l'omet), presence (L.1571-1573), note (ecrit L.1271 mais jamais
    relu) -> le pull lit `uuid_client = NULL` et fabrique un uuid technique
    (`SERVEUR-...`) qui ne matche jamais la ligne locale -> **2e inscription**,
    doublons de presences (pull:251, database:323-324).
16. **Ids locaux envoyes tels quels** : pour un enregistrement cree hors-ligne,
    `id_serveur` est NULL -> URL `/eleve/None` -> **422** FastAPI
    (engine:59) ; engine:78-81 fait `continue` sans retirer l'operation ->
    re-tente indefiniment. Paiement/note/presence avec `inscription_id` ou
    `eleve_id` local inconnu de MySQL -> **500/404** -> file bloquee a vie.
17. **Suppression jamais propagee** : `/eleve` filtre `est_supprime = false`
    (L.195) -> le pull ne voit jamais les tombes -> l'eleve archive reste
    vivant localement indefiniment.

### B4. Pull impossible / champs NULLes

18. `pull_programme` (pull:129-139) : le serveur `/tous_les_programme`
    (L.1821-1828) renvoie les NOMS (`classe`, `matiere`, `enseignant_nom`),
    pas les id -> le cache local ecrit `classe_id=NULL, matiere_id=NULL,
    enseignant_id=NULL` -> toutes les jointures locales programmees cassent.
19. `pull_tarifs` (pull:112) : le serveur renvoie `annee_scolaire` (le
    libelle, L.2081), pas l'id -> `annee_scolaire_id = NULL` dans
    `tarif_scolarite` local.
20. **`INSERT OR REPLACE` + `PRAGMA foreign_keys=ON`** (database.py:10,
    283-285) : REPLACE = DELETE+INSERT du parent alors qu'une ligne enfant
    existe localement -> `sqlite3.IntegrityError` des le `pull_cycle`
    (pull:267) -> tout le rafraichissement meurt, epidemiquement attrape en
    silence (engine:100-101).
21. `redoublant` **NOT NULL** cote SQLite local (database:105) vs **nullable**
    cote serveur (`Optional`, L.244) : une ligne serveur avec NULL ->
    `IntegrityError` dans `upsert_action_row` (database:350) -> pull casse.
22. **`INNER JOIN enseignant`** dans `/tous_les_programme` (L.1821-1828) et
    `/programme/{classe}` (L.1845-1852) : `enseignant_id` est nullable
    (schema L.87) -> les programmes sans professeur disparaissent
    silencieusement (il faut des LEFT JOIN).
23. Moyennes du bulletin appliquent les coefficients de **toutes** les classes
    (jamais `programme.classe_id = inscription.classe_id`, L.1383-1421) ->
    resultats faux meme sans crash.

### B5. Securite et hygiene

24. **Identifiants MySQL et `SECRET_KEY` en dur** dans le code (L.28, L.37,
    L.2257).
25. Boot lit `"schema.sql"` (L.44) alors que le fichier a un autre nom ->
    `FileNotFoundError` au demarrage selon le CWD.
26. **Dizaines de connexions/curseurs jamais fermes** (et non fermes en cas
    d'exception) : liste non exhaustive — L.80, L.182, L.191, L.496, L.520,
    L.532, L.677, L.686, L.791, L.800, L.957, L.966, L.997, L.1224, L.1233,
    L.1242 (rien ferme) ; ~45 autres ne ferment que `conn` sans `cursor`.
27. Pas de `try/rollback` sur presque toutes les ecritures (seules 6 routes
    rollbackent) ; ex. `ajouter_annee_scolaire` (L.1921) fait UPDATE
    `est_active=FALSE` (L.1928) puis INSERT sans protection.
28. **Pas de gestion du doublon `telephone`** (UNIQUE, schema L.154) :
    un 2e compte avec le meme telephone -> `IntegrityError` non catchée -> 500.
29. `suivi_mensuel` impose `type_frais` en query-param REQUIS (L.2229) ->
    422 si le client ne l'envoie pas.
30. `ajouter_paiement` exige `uuid_client: str` obligatoire (L.1115) alors
    qu'il est Optional partout ailleurs.
31. Fonctions a nom trompeur : `get_classe_par_id` (L.556) cherche par NOM ;
    `get_enseignant_par_id` (L.810) par nom+prenom.
32. Echec du doublon gestion de la synchro locale : la colonne `matricule` et
    les clefs `uuid_client` prevues pour dedupliquer ont ete SUPPRIMEES de la
    table eleve (commit `fresnel` 4619635 « suppression de la colonne
    matricule ») — sans cela, plus aucune cle unique pour eviter les doublons.