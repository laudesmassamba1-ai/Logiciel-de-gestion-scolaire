"""Sous-modules de l'assistante Charo (100% stdlib, leger, offline-first).

- langue   : normalisation, distance Damerau-Levenshtein, correction
             orthographique contre un vocabulaire, similarite n-grammes.
- maths    : calculatrice sure basee sur ast + francais naturel.
- graphe   : graphe des relations de l'ecole, BFS, resolution floue.
- contexte : memoire conversationnelle (anaphores « et en cm2 ? »).
- webrecherche : recherche web optionnelle (DuckDuckGo HTML, repli
             Wikipedia) — sans cle API, bornee par timeouts et une sonde
             de disponibilite cachee. Hors ligne, Charo n'en depend pas.
- apprentissage : journal, feedback, renforcement et auto-amelioration
             (fusion des doublons, purge, auto-apprentissage des questions
             frequentes).
- llm_backend : backend LLM optionnel (ollama en local) — enhancement.
"""