import datetime

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QFrame, QGridLayout, QLabel, QScrollArea, QSizePolicy,
    QVBoxLayout, QWidget,
)

from repositories import repos
from core.config import STYLE_SCROLL, STYLE_CHART_CARD
from ui.pages.helpers import _page_header
from ui.widgets import SimpleBarChart, SimpleLineChart, SimplePieChart


def statistiques(page, ctx):
    if page.layout() is not None:
        return
    page.setStyleSheet("")
    lay = QVBoxLayout(page)
    lay.setContentsMargins(20, 20, 20, 20)
    lay.setSpacing(16)
    _page_header(lay, "Statistiques de l'ecole",
                 "Scolarite, finances et presences en un coup d'oeil")

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setStyleSheet(STYLE_SCROLL)
    conteneur = QWidget()
    grille = QGridLayout(conteneur)
    grille.setSpacing(16)
    grille.setColumnStretch(0, 1)
    grille.setColumnStretch(1, 1)
    scroll.setWidget(conteneur)
    lay.addWidget(scroll)

    def _ajouter(chart, ligne, colonne):
        cadre = QFrame()
        cadre.setStyleSheet(STYLE_CHART_CARD)
        cadre.setMinimumHeight(250)
        cl = QVBoxLayout(cadre)
        cl.setContentsMargins(15, 15, 15, 15)
        cl.setSpacing(10)
        chart.setMinimumHeight(230)
        chart.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        cl.addWidget(chart)
        grille.addWidget(cadre, ligne, colonne)
        grille.setRowStretch(ligne, 1)

    def _ajouter_pleine_largeur(chart, ligne):
        """Carte pleine largeur (2 colonnes) pour les graphes a lire de loin."""
        cadre = QFrame()
        cadre.setStyleSheet(STYLE_CHART_CARD)
        cadre.setMinimumHeight(260)
        cl = QVBoxLayout(cadre)
        cl.setContentsMargins(15, 15, 15, 15)
        cl.setSpacing(10)
        chart.setMinimumHeight(220)
        chart.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        cl.addWidget(chart)
        grille.addWidget(cadre, ligne, 0, 1, 2)
        grille.setRowStretch(ligne, 1)

    def _avec_autre(labels, values, limite=8):
        """Tronque a `limite` categories en regroupant le reste dans 'Autre'."""
        labels = list(labels)
        values = list(values)
        if len(labels) <= limite:
            return labels, values
        reste = sum(values[limite:])
        labels = labels[:limite]
        values = values[:limite]
        if reste:
            labels.append("Autre")
            values.append(reste)
        return labels, values

    def _group_rows(rows, cle, somme):
        d = {}
        for r in rows:
            k = r.get(cle) or "Autre"
            d[k] = d.get(k, 0) + float(r.get(somme) or 0)
        return d

    def refresh():
        while grille.count():
            item = grille.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        classes = repos.classes()
        eleves = repos.eleves()
        today = datetime.date.today()

        # Courbes colorees : une ligne Recettes, une ligne Depenses.
        rec_mois, dep_mois = {}, {}
        for t in repos.transactions():
            cle = t["date"][:7]
            rec_mois.setdefault(cle, 0.0)
            dep_mois.setdefault(cle, 0.0)
            if t["type"] == "entree":
                rec_mois[cle] += float(t["montant"] or 0)
            else:
                dep_mois[cle] += float(t["montant"] or 0)
        lbls_flux, recs, deps = [], [], []
        annee, mois_num = today.year, today.month
        for _ in range(12):
            d = datetime.date(annee, mois_num, 1)
            cle = d.strftime("%Y-%m")
            lbls_flux.insert(0, d.strftime("%b"))
            recs.insert(0, int(rec_mois.get(cle, 0)))
            deps.insert(0, int(dep_mois.get(cle, 0)))
            mois_num -= 1
            if mois_num == 0:
                mois_num = 12
                annee -= 1
        ch_flux = SimpleLineChart(
            titre="Flux de tresorerie : recettes / depenses sur 12 mois")
        ch_flux.set_series([("Recettes", recs), ("Depenses", deps)], lbls_flux)
        _ajouter_pleine_largeur(ch_flux, 0)

        eff = SimpleBarChart(titre="Effectifs par classe")
        eff_labels = [c["nom"][:12] for c in classes]
        eff_values = [c["effectif"] for c in classes]
        eff.set_data(*_avec_autre(eff_labels, eff_values))
        _ajouter(eff, 1, 0)

        par_cycle = {}
        for c in classes:
            cle = c.get("cycle_nom") or "Sans cycle"
            par_cycle[cle] = par_cycle.get(cle, 0) + c["effectif"]
        ch_cycle = SimpleBarChart(titre="Effectifs par cycle")
        ch_cycle.set_data(list(par_cycle.keys()), list(par_cycle.values()))
        _ajouter(ch_cycle, 1, 1)

        sexes = {}
        for e in eleves:
            s = (e.get("sexe") or "Non precise").strip().capitalize()
            sexes[s] = sexes.get(s, 0) + 1
        ch_sexe = SimplePieChart(titre="Repartition par sexe")
        ch_sexe.set_data(list(sexes.keys()), list(sexes.values()))
        _ajouter(ch_sexe, 2, 0)

        statuts = {}
        for e in eleves:
            s = (e.get("statut") or "Inconnu").capitalize()
            statuts[s] = statuts.get(s, 0) + 1
        ch_statut = SimplePieChart(titre="Repartition par statut")
        ch_statut.set_data(list(statuts.keys()), list(statuts.values()))
        _ajouter(ch_statut, 2, 1)

        mois = {}
        for t in repos.transactions():
            cle = t["date"][:7]
            mois.setdefault(cle, 0)
            mois[cle] += t["montant"] if t["type"] == "entree" else -t["montant"]
        lbls, vals = [], []
        # 12 vrais mois calendaires (evite les doublons/trous du pas de 30 jours).
        annee, mois_num = today.year, today.month
        for _ in range(12):
            d = datetime.date(annee, mois_num, 1)
            cle = d.strftime("%Y-%m")
            lbls.insert(0, d.strftime("%b"))
            vals.insert(0, int(mois.get(cle, 0)))
            mois_num -= 1
            if mois_num == 0:
                mois_num = 12
                annee -= 1
        ch_mois = SimpleBarChart(titre="Solde de tresorerie sur 12 mois")
        ch_mois.set_data(lbls, vals)
        _ajouter(ch_mois, 3, 0)

        paiements = repos.paiements()
        ch_frais = SimplePieChart(titre="Encaissements par type de frais")
        frais = _group_rows(paiements, "type_frais", "montant")
        ch_frais.set_data(list(frais.keys()), list(frais.values()))
        _ajouter(ch_frais, 3, 1)

        ch_mode = SimplePieChart(titre="Encaissements par mode de reglement")
        modes = _group_rows(paiements, "mode_reglement", "montant")
        ch_mode.set_data(list(modes.keys()), list(modes.values()))
        _ajouter(ch_mode, 4, 0)

        par_classe = {}
        for p in paiements:
            cle = p.get("classe_nom") or "Sans classe"
            par_classe[cle] = par_classe.get(cle, 0) + float(p["montant"] or 0)
        # Top classes par montant, le reste regroupe dans 'Autre'.
        tries = sorted(par_classe.items(), key=lambda kv: kv[1], reverse=True)
        ch_classe = SimpleBarChart(titre="Encaissements par classe")
        ch_classe.set_data(*_avec_autre([k for k, _ in tries],
                                        [v for _, v in tries]))
        _ajouter(ch_classe, 4, 1)

        comptes = {}
        for r in repos.presences_statuts():
            comptes[r["statut"]] = r["total"]
        ch_pres = SimplePieChart(titre="Presences (toutes dates)")
        ch_pres.set_data(list(comptes.keys()), list(comptes.values()))
        _ajouter(ch_pres, 5, 0)

        complets = sum(1 for e in eleves
                       if e.get("check_acte") and e.get("check_photos")
                       and e.get("check_bulletin"))
        ch_doss = SimplePieChart(titre="Dossiers des eleves")
        ch_doss.set_data(["Complets", "Incomplets"],
                         [complets, len(eleves) - complets])
        _ajouter(ch_doss, 5, 1)

    refresh()
    page.refresh = refresh
