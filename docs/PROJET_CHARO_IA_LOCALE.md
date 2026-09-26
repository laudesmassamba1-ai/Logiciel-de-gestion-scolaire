# Charo — Projet d'architecture « IA locale v2 » (sans modèle téléchargé)

> **Contrainte structurante** : Charo v2 ne télécharge **aucun modèle**. Ni Ollama/Qwen, ni llama-cpp, ni sentence-transformers, ni chromadb, ni aucun poids neuronal. Tout repose sur le moteur local existant (règles, index TF-IDF, graphe, mémoire SQLite) et sur la bibliothèque standard Python. L'IA reste 100 % hors-ligne, sans dépendance, sans clé API, sans_gpu, sans Installation.

- **Branche de travail** : `fix/updater-timeout` (1.6.4)
- **Fichiers moteur** : `services/assistant_ia.py` (3058 l.), `services/ia/` (14 modules, 1570 l.)
- **Version cible** : 1.6.5 (v2 progressive, activable par paliers, jamais de big-bang)

---

## 1. Ce que « ton propre modèle local » signifie concrètement

Le « modèle » de Charo v2 = **l'ensemble des couches symboliques déjà présentes**, renforcées :

| Couche actuelle | Rôle | Force en v2 |
|---|---|---|
| Règles métier (`_q_*`, `MANUEL`, `_PAGES_NAV`) | réponses déterministes | + intends déclaratives, seuils, priorités |
| `IndexSemantique` (TF-IDF + cosinus maison) | lecture floue du corpus local | BM25 + synonymie + pondération de fraîcheur |
| `MoteurApprentissage` (mémoire SQLite) | mémorisation, feedback, oubli | renforcement simplifié + décroissance dans le temps |
| `GrapheEcole` (BFS) | relations, chemins | déduction transitive, contradictions |
| `PersonaliteCharo` | rendu, empathie | gabarits par intention + cohérence de ton |
| `RechercheWeb` (optionnel) | dernier recours réseau | inchangé (déjà hors-ligne-first) |

Aucune couche ne nécessite de réseau. `LLMBackend` reste **optionnel et non requis** : s'il est présent (Ollama déjà installé par l'utilisateur), Charo l'ignore par défaut (garde existante) ; sinon, rien ne casse.

---

## 2. Diagnostic de l'existant (ce qui manque pour une v2 crédible)

Cartographie issue de l'audit du moteur (HEAD 1c7cb9a) :

1. **Règles peu priorisées** : 12 handlers `_q_*` testés dans un tuple fixe (`:1084-1089`) ; pas de score de confiance, pas de mécanisme « je ne sais pas » structuré.
2. **Corpus indexé étroit** : `_construire_corps_donnees()` (`:2931`) n'indexe que classes/élèves/transactions[:60]/tarifs/personnel — pas de documents, pas d'historique pédagogique.
3. **Pas de mémoire « faits »** : `ia_memoire` sait le type `fait` (`type ∈ {qa, fait}`) mais rien ne l'alimente automatiquement.
4. **Explications superficielles** : `_rep(explication=...)` existe et alimente « explique » (`:1328`) mais les raisonnements pas-à-pas (moyenne, solde, classement) ne sont pas instrumentés.
5. **Graphe sous-exploité** : `chemin_plus_court` existe (BFS) mais n'est utilisé que par `_q_graphe` (`:1428`).
6. **Vocabulaire limité** : ~180 mots (`:396-418`), seuil de correction distance 2 exigeant préfixe commun + len ≥ 6 (`langue.py:87`).
7. **Oubli non temporel** : `_supprimer_faibles` (`:311`) supprime par usage/score, sans décroissance dans le temps.
8. **Zéro quantification** de la qualité : les tests vérifient des sous-chaînes, pas un taux de réussite global.

---

## 3. Architecture cible v2 (5 piliers, toujours stdlib)

### Pilier 1 — Moteur d'intentions déclaratif (« routeur » unifié) — **livré (P1)**

Un **registre déclaratif** remplace la cascade implicite, sans réécrire `traiter()`.

- Module livré : `services/ia/intentions.py` (~330 l., stdlib + `ia/langue.py`)
- Chaque intention : `Intention(nom, cles, mots, synonymes, expressions, poids, handler, exige_donnees, exemple)`
- API : `RouteurIntentions.resoudre(question, seuil=0.45) -> (intention|None, score, classement)` et `.expliquer(question)` (trace lisible, réutilisée par les tests et le journal)
- **Barème de scoring** (explicite, dans le module) : 1 clé → 0.60 · 2 clés ou plus → 0.80 · 2 mots d'appoint → 0.50 · 3 mots → 0.60 · 1 seul mot → 0.30 (sous le seuil, donc repli) · expression régulière → +0.25 ; le tout est multiplié par le poids puis borné à 1.0.
- **Insensibilité** : la question est normalisée (minuscules, sans accents, espaces compactes) via `ia/langue.normaliser`, et les mots sont recherchés en mot entier (`\b`) — « moyenneponderee » ne déclenche pas « moyenne ».
- **Seuil de confiance** (0.80) : au-dessus seulement, le routeur court-circuite l'ordre fixe ; en dessous, il ne tranche pas et l'ordre historique reste décisionnaire.
- **Repli systématique** : si le handler choisi renvoie `None` (ou lève une exception), `traiter()` poursuit sur l'ordre historique `HANDLERS_METIER` — le comportement v1 est intégralement conservé, d'où le critère « 0 régression » tenu.
- **Feature flag** : `CHARO_V2["ROUTEUR"]` (`core/config.py`, surchargeable par `GS_CHARO_ROUTEUR=false`), plus `SEUIL_INTENTION` / `SEUIL_CONFIANT` (idem `GS_CHARO_SEUIL_INTENTION`, `GS_CHARO_SEUIL_CONFIANT`).
- Les 12 handlers métier existants sont **ré-enregistrés** (intention → méthode existante), aucun n'est réécrit : `tests/test_intentions.py` vérifie que le registre couvre exactement `HANDLERS_METIER`.
- Tests : 39 tests unitaires (`tests/test_intentions.py`) + 16 tests d'intégration dans `tests/test_assistant_ia.py` (non-régression v1/v2 réponse par réponse, court-circuit vérifié sur l'ordre d'appel, repli, désactivation du flag, hors-périmètre).

### Pilier 2 — Index de connaissance local enrichi (BM25 maison)

- Étendre `IndexSemantique` (`assistant_ia.py:513-574`) vers BM25 (k1=1.5, b=0.75) **en conservant** la cosine comme repli (comparaison A/B sur les tests existants).
- Nouvelles sources indexées (toutes locales, TTL 60 s) :
  - **Historique pédagogique** : `notes` agrégées par élève/matière/période, moyennes calculées, evolution.
  - **Frais & tarifs** : tous types, pas seulement les 3 synchronisables.
  - **Annuaire** : personnel (fonctions), parents (contacts), classes (effectifs, capacité).
  - **Journal IA** : les questions sans réponse (`ia_journal` sans correspondance mémoire) deviennent des lacunes, listables.
- **Synonymie sans modèle** : table `SYNONYMES` à la main (école/établissement, élève/élève/étudiant, scolarité/scolarité/inscription, prof/enseignant, etc.) appliquée au tokenisation.
- **Fraîcheur** : champ `poids` decay (ex. 1.0 récent, 0.7 ancient) pour que les données de l'année active remontent.

### Pilier 3 — Raisonnement traçable (« explique » de qualité)

- Nouveau module : `services/ia/raisonnement.py` (~200 l.) : petits calculateurs purs, retour `(valeur, etapes: list[str])`.
  - `moyenne_eleve(notes)` : moyenne pondérée par coefficients, arrondi, exclusions, étapes (« 3 notes retenues sur 5 : (12+14+16)/3 = 14,00 »).
  - `solde_eleve(paiements, tarifs, annee)` : détail ligne à ligne (facturé / réglé / reste).
  - `classement(classe, periode)` : tri, ex æquo, rangs.
  - `ecart_type / dispersion`, `taux presence`, `effectifs`.
- Ces fonctions alimentent `_rep(explication=...)` : « Charo, explique » répond alors avec les étapes réelles, pas une phrase générique.
- Aucun `eval()` : même discipline que `ia/maths.py` (liste blanche, limites).

### Pilier 4 — Mémoire et apprentissage (renforcés, sans réseau)

- **Decay temporel** : `MoteurApprentissage.ameliorer()` ajoute `score = score * facteur_decay(âge)` (demi-vie 90 j, plancher 0.05) avant les seuils existants (`_SEUIL_SUPPRESSION=0.25`).
- **Faits automatiques** : quand un handler métier répond avec succès (`_rep(source="moteur", contexte_type=...)`), un fait abstrait (« X est en classe Y », « Z a réglé N F CFA en T2 ») est dérivé et stocké en `type='fait'`, avec utilité mesurée par le nombre de réutilisations. Seuil : 3 réutilisations avant promotion en fait (évite la pollution mémoire).
- **Feedback renforcé** : `noter()` (`:167`) déjà branché sur l'UI ; ajouter l'effet sur les hits mémoire voisins (voisins TF-IDF 0.75+, pas seulement SequenceMatcher 0.6).
- **Garde-fous** : plafond mémoire (ex. 2000 entrées), purge des entrées jamais relues après 180 j, export/import CSV déjà en place.

### Pilier 5 — Graphe : déduction et contradictions

- Étendre `GrapheEcole` (`ia/graphe.py`) :
  - arêtes `classe → annee`, `paiement → eleve` (montant/date), `tarif → classe`.
  - `chemin_contradictoire(eleve)` :.detecte un élève inscrit sans classe active, un paiement sans inscription, un tarif orphelin, une classe sans enseignant.
  - `voisins_avec_poids` pour classer les réponses par graphe (hub de centralité déjà calculé par `stats()`).
- Cas d'usage : « Qui n'a pas encore payé ? » = parcours graphe paiement↔inscription, pas SQL ad hoc.

---

## 4. Plan de livraison (phases, chacune testable et réversible)

| Phase | Contenu | Fichiers | Critère de sortie | Version |
|---|---|---|---|---|
| **P0 — Socle** (fait) | web sans clé + auto-apprentissage | `ia/webrecherche.py`, `apprentissage.py` | 146 tests IA verts | 1.6.4 ✔ |
| **P1 — Routeur** (fait) | `ia/intentions.py`, ré-enregistrement des `_q_*` | nouveau + `assistant_ia.py` | 0 régression sur `test_assistant_ia.py`; chaque intention a ≥ 1 test via `traiter()` | 1.6.5 ✔ |
| **P2 — Index BM25 + synonymes** | `IndexSemantique` étendu, sources enrichies | `assistant_ia.py`, `ia/langue.py` | recall ≥ actuel sur la base de tests; seuil paramétrable | 1.6.5 |
| **P3 — Raisonnement** | `ia/raisonnement.py` + explication | nouveau | « explique » fournit ≥ 3 étapes vérifiables sur moyennes et soldes | 1.6.5 |
| **P4 — Mémoire renforcée** | decay, faits, feedback élargi | `apprentissage.py` | stats mémoire stables; purge testée; export CSV intact | 1.6.6 |
| **P5 — Graphe déductif** | arêtes, contradictions, « qui n'a pas payé » | `ia/graphe.py` | 3 nouveaux tests de contradiction | 1.6.6 |
| **P6 — Qualité** | batterie de 100 questions-types, rapport de taux de réussite | `tests/test_ia_qualite.py` | rapport versionné dans `docs/` | 1.6.6 |

Chaque phase : feature flag dans `core/config.py` (dict `CHARO_V2`, clés `ROUTEUR`, `SEUIL_INTENTION`, `SEUIL_CONFIANT`, etc.) pour revenir à la v1 en un paramètre, surchargeable aussi par variable d'environnement (`GS_CHARO_ROUTEUR`, `GS_CHARO_SEUIL_INTENTION`, `GS_CHARO_SEUIL_CONFIANT`) sans toucher au code.

---

## 5. Non-régression et conventions

- **Réseau** : aucun accès dans les tests ; `conftest.py` neutralise déjà LLM/web (option `--llm` pour les tests live).
- **Contrat moteur** : toute réponse passe par `_rep()` (`assistant_ia.py:1477`) → journalisation et mémoire automatiques conservées.
- **Ordre local-first** : les données locales restent la source de vérité ; web = 21ᵉ position, jamais avant.
- **Tests** : chaque.handler/intention testé via l'API publique `traiter()` sur la fixture `base_vierge` (dicts utilisateurs en dur), assertions sur substrings + sur l'état SQLite.
- **Migration** : toute nouvelle colonne de `ia_memoire` passe par `ensure_tables()` (ALTER idempotent) + test de migration (ALTER DROP COLUMN puis re-ensure), comme le fait déjà `apprentissage.py:104`.
- **Zéro dépendance** : `requirements.txt` inchangé ; pas de torch/numpy/onnx.

---

## 6. Idées écartées (et pourquoi)

| Idée | Raison de l'écarter |
|---|---|
| llama-cpp + Qwen 2.5 (3 Go) | contradictoire avec « sans téléchargement de modèle » ; poids, mémoire RAM, CPU |
| sentence-transformers / embeddings | dépendances lourdes ; un BM25 maison + synonymie couvre nos questions métier (mot-clé, pas paraphrase) |
| chromadb / base vectorielle | redondant : index TF-IDF local en RAM, corpus de l'école = quelques milliers de lignes |
| Ollama comme « modèle local » | optionnel déjà ; ne peut pas être la base de v2 (indisponible hors ligne, non installé) |
| fine-tuning | impossible sans modèle de départ ; l'apprentissage se fait par la mémoire, pas par les poids |

---

## 7. Perspective « modèle local » à moyen terme (optionnelle, non requise)

Si un jour l'utilisateur **installe** lui-même un LLM local (Ollama déjà supporté par `ia/llm_backend.py`, non requis), la v2 est conçue pour en profiter **en enrichissement** (réécriture de formulations, jamais de calcul métier) : les réponses de vérité restent produites par les piliers 1-5, donc le comportement est identique avec ou sans LLM. Le point d'injection est unique : `get_backend()` (`assistant_ia.py:897`).

---

*Document de projet — à implémenter par phases (P1 → P6). Chaque phase est un commit, avec tests et version.*
