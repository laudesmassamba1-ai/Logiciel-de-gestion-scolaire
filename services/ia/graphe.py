"""Graphe des relations de l'ecole — theorie des graphes appliquee.

Construit un graphe NON ORIENTE etiquette depuis la base locale :
  annee --(contient)--> cycle --(regroupe)--> classe --(scolarise)--> eleve
  classe --(programme)--> matiere, eleve --(note)--> matiere,
  eleve --(paiement)--> paiement, personnel --(titulaire de)--> classe

Usages :
- chemin_plus_court : BFS (plus court chemin en nombre d'aretes) pour
  « quel est le lien entre X et Y ? » ;
- trouver : resolution floue d'entite (Damerau + Dice n-grammes) ;
- hubs : centralite de degre (les classes/personnels les plus connectes).

Reconstruit avec un cache TTL court : cout negligeable sur une base
scolaire (quelques milliers de noeuds), aucune dependance externe.
"""

import time
from collections import deque

from database import db
from services.ia.langue import damerau, normaliser, similarite


class GrapheEcole:

    TTL = 30.0
    _instance = None

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self._construit_a = 0.0
        self._noeuds = {}   # id -> {"type": str, "label": str}
        self._adj = {}      # id -> [(id_voisin, relation), ...]

    # -- construction --------------------------------------------------

    def _fraiche(self):
        return (time.monotonic() - self._construit_a) < self.TTL

    def _ajouter(self, nid, type_noeud, label):
        self._noeuds[nid] = {"type": type_noeud,
                             "label": normaliser(label or str(nid))}
        self._adj.setdefault(nid, [])

    def _lier(self, a, b, relation):
        if a in self._adj and b in self._adj:
            self._adj[a].append((b, relation))
            self._adj[b].append((a, relation))

    def construire(self, force=False):
        if not force and self._fraiche():
            return
        self._noeuds.clear()
        for liste in self._adj.values():
            liste.clear()
        conn = None
        try:
            conn = db.connect()
            self._charger(conn)
        except Exception:
            pass  # base absente/en cours d'init : graphe vide, sans crash
        finally:
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass
        self._construit_a = time.monotonic()

    def _charger(self, conn):

        for aid, libelle in conn.execute(
                "SELECT id, libelle FROM annees_scolaires"):
            self._ajouter(f"annee:{aid}", "annee", libelle)
        for cid, nom in conn.execute("SELECT id, nom FROM cycles"):
            self._ajouter(f"cycle:{cid}", "cycle", nom)
        for mid, nom in conn.execute("SELECT id, nom FROM matieres"):
            self._ajouter(f"matiere:{mid}", "matiere", nom)
        for pid, nom_complet in conn.execute(
                "SELECT id, nom_complet FROM personnel"):
            self._ajouter(f"personnel:{pid}", "personnel", nom_complet)
        for cid, nom, cycle_id, titulaire in conn.execute(
                "SELECT id, nom, cycle_id, titulaire FROM classes"):
            self._ajouter(f"classe:{cid}", "classe", nom)
            if cycle_id:
                self._lier(f"classe:{cid}", f"cycle:{cycle_id}",
                           "cycle")
            if titulaire:
                self.trouver_ou_creer_personnel(titulaire, cid)
        for eid, prenom, nom, classe_id, statut in conn.execute(
                "SELECT id, prenom, nom, classe_id, statut FROM eleves"):
            label = f"{prenom} {nom}".strip()
            suffixe = "" if statut == "Inscrit" else f" ({statut})"
            self._ajouter(f"eleve:{eid}", "eleve", label + suffixe)
            if classe_id:
                self._lier(f"eleve:{eid}", f"classe:{classe_id}",
                           "scolarise")
        for eleve_id, matiere_id in conn.execute(
                "SELECT DISTINCT eleve_id, matiere_id FROM notes"):
            self._lier(f"eleve:{eleve_id}", f"matiere:{matiere_id}", "note")
        for eleve_id, montant in conn.execute(
                "SELECT eleve_id, montant FROM paiements "
                "WHERE eleve_id IS NOT NULL LIMIT 2000"):
            self._ajouter(f"paie:{eleve_id}:{int(montant)}", "paiement",
                          f"paiement {int(montant)} fcfa")
            self._lier(f"eleve:{eleve_id}", f"paie:{eleve_id}:{int(montant)}",
                       "paiement")
        self._construit_a = time.monotonic()

    def trouver_ou_creer_personnel(self, nom_complet, classe_id):
        nid = f"personnel:t:{normaliser(nom_complet)}"
        if nid not in self._noeuds:
            self._ajouter(nid, "personnel", nom_complet)
        self._lier(nid, f"classe:{classe_id}", "titulaire")

    # -- consultation ----------------------------------------------------

    def stats(self):
        """Comptages par type + hubs (centralite de degre)."""
        self.construire()
        comptes = {}
        for info in self._noeuds.values():
            comptes[info["type"]] = comptes.get(info["type"], 0) + 1
        hubs = sorted(
            ((len(self._adj[n]), n) for n in self._noeuds),
            reverse=True)[:3]
        return {
            "comptages": comptes,
            "total_noeuds": len(self._noeuds),
            "total_relations": sum(len(v) for v in self._adj.values()) // 2,
            "hubs": [(self._noeuds[n]["label"], deg)
                     for deg, n in hubs if deg > 1],
        }

    def trouver(self, nom, types=None):
        """Resolution floue d'un libelle vers un noeud.

        Score combine : egalite exacte > prefixe > Damerau borne >
        Dice n-grammes. Renvoie (id, noeud) ou None."""
        self.construire()
        cible = normaliser(nom)
        if len(cible) < 2:
            return None
        meilleur, meilleur_score = None, 0.0
        for nid, info in self._noeuds.items():
            if types and info["type"] not in types:
                continue
            label = info["label"]
            if label == cible:
                score = 3.0
            elif cible in label or label in cible:
                score = 2.5 - 0.1 * abs(len(label) - len(cible))
            else:
                dist_plafond = 2 if len(cible) >= 6 else 1
                dist = min(
                    (damerau(cible, mot, plafond=dist_plafond + 1)
                     for mot in label.replace("(", " ").split()),
                    default=99)
                score = max(0.0, (dist_plafond + 1 - dist)) \
                    if dist <= dist_plafond else similarite(label, cible) * 2
            if score > meilleur_score:
                meilleur, meilleur_score = (nid, info), score
        return meilleur if meilleur_score >= 1.0 else None

    def chemin_plus_court(self, id_a, id_b):
        """BFS classique : file d'attente + carte des parents.
        Renvoie la liste d'ids du chemin, ou None si pas de lien."""
        self.construire()
        if id_a not in self._noeuds or id_b not in self._noeuds:
            return None
        parents = {id_a: None}
        file = deque([id_a])
        while file:
            courant = file.popleft()
            if courant == id_b:
                chemin = []
                while courant is not None:
                    chemin.append(courant)
                    courant = parents[courant]
                return list(reversed(chemin))
            for voisin, _relation in self._adj.get(courant, ()):
                if voisin not in parents:
                    parents[voisin] = courant
                    file.append(voisin)
        return None

    def relations_du_chemin(self, ids):
        """Etiquettes lisibles du chemin : labels + relations traversees."""
        morceaux = [self._noeuds[i]["label"] for i in ids]
        relations = []
        for a, b in zip(ids, ids[1:]):
            rel = next((r for v, r in self._adj[a] if v == b), "?")
            relations.append(rel)
        return morceaux, relations

    def label_de(self, nid):
        """Libelle d'un noeud (ou None). Force la construction si besoin."""
        self.construire()
        info = self._noeuds.get(nid)
        return info["label"] if info else None

    def voisins(self, nid, type_souhaite=None):
        self.construire()
        resultat = []
        for voisin, relation in self._adj.get(nid, ()):
            info = self._noeuds.get(voisin)
            if info and (type_souhaite is None
                         or info["type"] == type_souhaite):
                resultat.append((voisin, info, relation))
        return resultat
