"""Rapports PDF generiques.

Un concentrateur de rapports : les pages du logiciel peuvent exporter un
« etat » (tableau affiche) en PDF via `export_table_pdf`, et le centre de
rapports (`ui/pages/rapports_page.py`) propose des syntheses structurees
de toute la base (effectifs, eleves, finance, presences, moyennes,
personnel). Tous ces PDF gardent le meme habillage que les documents
officiels (bandeaux, entete, signature de l'ecole) et atterrissent dans
l'Espace Documents.
"""

import datetime
import re

from core.config import DOCS_DIR
from repositories import repos
from services.pdf_export import STYLE, _entete_doc, _generate_pdf, _ouvrir_pdf, echap


def _date_pdf():
    return datetime.date.today().strftime("%d/%m/%Y")


def _annee_active():
    try:
        active = repos.annee_scolaire_active()
        if active and active.get("libelle"):
            return active["libelle"]
    except Exception:
        pass
    return "-"


def export_table_pdf(titre, sous_titre, entetes, lignes,
                     nom_fichier=None, ouvrir=True):
    """Exporte un tableau (donnees affichees) en PDF, uniforme pour toutes
    les pages. Refuse un tableau vide : retourne False sans generer."""
    if not lignes:
        return False
    nb = len(entetes) or 1
    lignes_html = "".join(
        "<tr>" + "".join(f"<td>{echap(c)}</td>" for c in ligne[:nb]) + "</tr>"
        for ligne in lignes)
    entete_html = "".join(f"<th>{echap(t)}</th>" for t in entetes)
    corps = f"<h1>{echap(titre)}</h1>"
    if sous_titre:
        corps += (f"<p style='color:#64748b;font-size:12px;'>"
                  f"{echap(sous_titre)}</p>")
    corps += f"<table><tr>{entete_html}</tr>{lignes_html}</table>"
    html = (f"<html><head><meta charset='utf-8'><title>{echap(titre)}</title>"
            f"<style>{STYLE}</style></head><body>{_entete_doc()}{corps}"
            f"</body></html>")
    if not nom_fichier:
        slug = re.sub(r"[^A-Za-z0-9_]+", "_", titre).strip("_").lower()
        nom_fichier = f"rapport_{slug}.pdf"
    path = _generate_pdf(html, nom_fichier)
    if ouvrir:
        _ouvrir_pdf(path)
    return path


def _section(entetes, lignes):
    """Petit tableau de synthese (2 colonnes type « cle / valeur »)."""
    return ("<table>" + "".join(
        f"<tr><td><strong>{echap(l[0])}</strong></td><td>{echap(l[1])}</td></tr>"
        for l in lignes) + "</table>")


def _contextuel(sous_titre):
    return f"{sous_titre} - le {_date_pdf()} (annee {_annee_active()})"


# --------------------------------------------------------------------------
# Rapports du centre de rapports
# --------------------------------------------------------------------------
def rapport_synthese(ouvrir=True):
    """Vue d'ensemble chiffree de l'etablissement."""
    classes = repos.classes()
    eleves = repos.eleves()
    from ui.widgets import fmt_money
    rec, dep, solde = repos.caisse_totals()
    paiements = repos.paiements()
    personnel = repos.personnel()
    statuts = {r["statut"]: r["total"] for r in repos.presences_statuts()}
    total_pres = sum(statuts.values()) or 1
    dossiers = sum(1 for e in eleves
                   if e.get("check_acte") and e.get("check_photos")
                   and e.get("check_bulletin"))

    cadre = _section("", [
        ("Classes", len(classes)),
        ("Eleves inscrits", len(eleves)),
        ("Enseignants et personnel", len(personnel)),
        ("Masse salariale mensuelle", fmt_money(repos.masse_salariale())),
    ])
    effectifs = _section("", [
        ("Effectif total", sum(c["effectif"] for c in classes)),
        ("Capacite d'accueil", sum(c["capacite"] for c in classes)),
        ("Dossiers eleves complets", f"{dossiers} / {len(eleves)}"),
    ])
    finances = _section("", [
        ("Total encaisse (paiements)", fmt_money(repos.bilan_total())),
        ("Nombre de paiements", len(paiements)),
        ("Recettes de caisse", fmt_money(rec)),
        ("Depenses de caisse", fmt_money(dep)),
        ("Solde de caisse", fmt_money(solde)),
    ])
    presences = _section("", [
        ("Presents", f"{statuts.get('Present', 0)}"
                     f" ({round(100 * statuts.get('Present', 0) / total_pres)}%)"),
        ("Absents", f"{statuts.get('Absent', 0)}"
                    f" ({round(100 * statuts.get('Absent', 0) / total_pres)}%)"),
        ("Retards", statuts.get("Retard", 0)),
    ])

    corps = (f"<h1>Synthese de l'etablissement</h1>"
             f"<p style='color:#64748b;font-size:12px;'>"
             f"{_contextuel('Etat global au')}</p>"
             f"<h3>Cadre general</h3>{cadre}"
             f"<h3>Effectifs</h3>{effectifs}"
             f"<h3>Finances</h3>{finances}"
             f"<h3>Presences</h3>{presences}")
    html = (f"<html><head><meta charset='utf-8'><title>Synthese</title>"
            f"<style>{STYLE}</style></head><body>{_entete_doc()}{corps}"
            f"</body></html>")
    path = _generate_pdf(html, "rapport_synthese.pdf")
    if ouvrir:
        _ouvrir_pdf(path)
    return path


def rapport_effectifs(classe_id=None, ouvrir=True):
    rows = repos.classes()
    if classe_id:
        rows = [c for c in rows if c["id"] == classe_id]
    lignes = []
    for c in rows:
        eff = c["effectif"] or 0
        cap = c["capacite"] or 0
        taux = round(100 * eff / cap) if cap else 0
        lignes.append([c["nom"], c["cycle_nom"] or "-", eff, cap,
                       f"{taux} %"])
    total_eff = sum(c["effectif"] for c in rows)
    total_cap = sum(c["capacite"] for c in rows)
    lignes.append(["TOTAL", "-", total_eff, total_cap,
                   f"{round(100 * total_eff / total_cap)} %" if total_cap else "-"])
    return export_table_pdf(
        "Effectifs par classe",
        _contextuel("Filtre : toutes les classes"
                    if not classe_id else "Filtre : classe selectionnee"),
        ["Classe", "Cycle", "Effectif", "Capacite", "Taux de remplissage"],
        lignes, "rapport_effectifs.pdf", ouvrir=ouvrir)


def rapport_eleves(classe_id=None, ouvrir=True):
    rows = repos.eleves(classe_id=classe_id)
    lignes = [[e["matricule"], f"{e['prenom']} {e['nom']}",
               e["sexe"] or "-", e["date_naissance"] or "-",
               e["classe_nom"] or "-", e["statut"] or "-",
               e["tuteur_tel"] or "-"] for e in rows]
    return export_table_pdf(
        "Etat des eleves",
        _contextuel("Filtre : toutes les classes"
                    if not classe_id else "Filtre : classe selectionnee"),
        ["Matricule", "Nom complet", "Sexe", "Naissance", "Classe",
         "Statut", "Tel tuteur"],
        lignes, "rapport_etat_eleves.pdf", ouvrir=ouvrir)


def rapport_finance(classe_id=None, ouvrir=True):
    from ui.widgets import fmt_money
    paiements = repos.paiements(classe_id=classe_id)
    lignes = [[p["date_paiement"], p["matricule"],
               f"{p['prenom']} {p['nom']}", p["classe_nom"] or "-",
               p["type_frais"] or "-", p["mode_reglement"] or "-",
               fmt_money(p["montant"])] for p in paiements]
    rec, dep, _solde = repos.caisse_totals()
    total = sum(float(p["montant"]) for p in paiements)
    corps = (f"<h1>Bilan financier</h1>"
             f"<p style='color:#64748b;font-size:12px;'>"
             f"{_contextuel('Periode : toutes les operations')}</p>"
             + _section("", [
                 ("Paiements enregistres", len(paiements)),
                 ("Montant vers etant", fmt_money(total)),
                 ("Recettes de caisse", fmt_money(rec)),
                 ("Depenses de caisse", fmt_money(dep)),
                 ("Solde de caisse", fmt_money(rec - dep)),
             ])
             + "<h3>Detail des paiements</h3>"
             + "<table><tr>" + "".join(
                 f"<th>{echap(t)}</th>" for t in
                 ["Date", "Matricule", "Eleve", "Classe", "Type frais",
                  "Mode", "Montant"]) + "</tr>"
             + "".join("<tr>" + "".join(f"<td>{echap(c)}</td>"
                                       for c in ligne) + "</tr>"
                      for ligne in lignes) + "</table>")
    html = (f"<html><head><meta charset='utf-8'><title>Bilan financier</title>"
            f"<style>{STYLE}</style></head><body>{_entete_doc()}{corps}"
            f"</body></html>")
    path = _generate_pdf(html, "rapport_bilan_financier.pdf")
    if ouvrir:
        _ouvrir_pdf(path)
    return path


def rapport_presences(classe_id=None, date=None, ouvrir=True):
    """Sans classe : repartition globale. Avec classe + date : feuille de
    presence des eleves (statut effectif enregistre, defaut Present)."""
    if classe_id is None:
        statuts = {r["statut"]: r["total"]
                   for r in repos.presences_statuts()}
        lignes = [[st, statuts.get(st, 0)] for st in
                  ("Present", "Absent", "Retard")]
        return export_table_pdf(
            "Repartition des presences",
            _contextuel("Sur toutes les classes et dates"),
            ["Statut", "Nombre"], lignes,
            "rapport_presences.pdf", ouvrir=ouvrir)
    date = date or datetime.date.today().strftime("%Y-%m-%d")
    eleves_rows = repos.eleves(classe_id=classe_id)
    pres_rows = {p["eleve_id"]: p for p in repos.presences(classe_id, date)}
    lignes = []
    for e in eleves_rows:
        pres = pres_rows.get(e["id"])
        statut = pres["statut"] if pres else "-"
        motif = (pres.get("motif") or "") if pres else ""
        lignes.append([e["matricule"], f"{e['prenom']} {e['nom']}",
                       statut, motif])
    classe_nom = "-"
    for c in repos.classes():
        if c["id"] == classe_id:
            classe_nom = c["nom"]
    return export_table_pdf(
        f"Presences - {classe_nom}",
        f"Feuille de presence du {date}",
        ["Matricule", "Eleve", "Statut", "Motif"], lignes,
        f"rapport_presences_{classe_nom}_{date}.pdf", ouvrir=ouvrir)


def _moyenne_eleve(row):
    d1 = row["devoir1"] or 0
    d2 = row["devoir2"] or 0
    comp = row["composition"] or 0
    return round((d1 + d2 + 2 * comp) / 4, 2)


def rapport_moyennes(classe_id=None, periode=None, ouvrir=True):
    periode = periode or "T1"
    classes = repos.classes()
    if classe_id:
        classes = [c for c in classes if c["id"] == classe_id]
    lignes = []
    for c in classes:
        prog = repos.programmes(classe_id=c["id"])
        matieres = [repos.matiere_by_id(p["matiere_id"])
                    for p in prog if p.get("matiere_id")]
        total_gen = 0.0
        nb_matieres = 0
        for m in matieres:
            notes = repos.notes_classe(c["id"], periode)
            moyennes = [_moyenne_eleve(n) for n in notes
                        if n["matiere_id"] == m["id"]]
            if moyennes:
                moy_matiere = round(sum(moyennes) / len(moyennes), 2)
                total_gen += moy_matiere * (m["coefficient"] or 1)
                nb_matieres += m["coefficient"] or 1
                lignes.append([c["nom"], m["nom"], moy_matiere])
        if nb_matieres and matieres:
            lignes.append([c["nom"], "MOYENNE GENERALE",
                           round(total_gen / nb_matieres, 2)])
    return export_table_pdf(
        f"Moyennes par classe ({periode})",
        _contextuel("Periode selectionnee"),
        ["Classe", "Matiere", "Moyenne / 20"], lignes,
        f"rapport_moyennes_{periode.lower()}.pdf", ouvrir=ouvrir)


def rapport_personnel(ouvrir=True):
    from ui.widgets import fmt_money
    personnel = repos.personnel()
    lignes = [[p["nom_complet"], p["fonction"] or "-",
               p["telephone"] or "-", p["email"] or "-",
               fmt_money(p["salaire"])] for p in personnel]
    corps = (f"<h1>Personnel et salaires</h1>"
             f"<p style='color:#64748b;font-size:12px;'>"
             f"{_contextuel('Etat du personnel au')}</p>"
             + _section("", [
                 ("Nombre de personnes", len(personnel)),
                 ("Masse salariale mensuelle",
                  fmt_money(repos.masse_salariale())),
             ])
             + "<h3>Detail du personnel</h3>"
             + "<table><tr>" + "".join(
                 f"<th>{echap(t)}</th>" for t in
                 ["Nom", "Fonction", "Telephone", "Email", "Salaire"]
                 ) + "</tr>"
             + "".join("<tr>" + "".join(f"<td>{echap(c)}</td>"
                                       for c in ligne) + "</tr>"
                      for ligne in lignes) + "</table>")
    html = (f"<html><head><meta charset='utf-8'><title>Personnel</title>"
            f"<style>{STYLE}</style></head><body>{_entete_doc()}{corps}"
            f"</body></html>")
    path = _generate_pdf(html, "rapport_personnel_salaires.pdf")
    if ouvrir:
        _ouvrir_pdf(path)
    return path


def rapport_statistiques(ouvrir=True):
    """Chiffres + graphiques de la page Statistiques dans un PDF : courbes de
    tresorerie (12 mois), barems (effectifs, cycles, solde, encaissements),
    camemberts (sexe, statut, frais, mode, presences, dossiers). Les graphes
    sont rendus par les widgets Qt de la page (memes couleurs) en PNG, puis
    integres au PDF via WeasyPrint."""
    from ui.widgets import fmt_money
    from ui.widgets import SimpleBarChart, SimpleLineChart, SimplePieChart
    today = datetime.date.today()
    classes = repos.classes()
    eleves = repos.eleves()
    transactions = repos.transactions()
    paiements = repos.paiements()

    def _png(composant, largeur=700, hauteur=380):
        composant.resize(largeur, hauteur)
        pix = composant.grab()
        pix = pix.scaled(largeur, hauteur, _Qt().KeepAspectRatio,
                         _Qt().SmoothTransformation)
        import base64
        from PyQt5.QtCore import QBuffer, QIODevice
        tampon = QBuffer()
        tampon.open(QIODevice.WriteOnly)
        pix.save(tampon, "PNG")
        return ("data:image/png;base64,"
                + base64.b64encode(bytes(tampon.data())).decode())

    def _img(composant, titre=None):
        intro = f"<h3>{echap(titre)}</h3>" if titre else ""
        return (intro + "<div class='graphe'><img src='%s' "
                "style='width:100%%;max-width:100%%;'></div>" % _png(composant))

    def _flux():
        rec_mois, dep_mois = {}, {}
        for t in transactions:
            cle = t["date"][:7]
            if t["type"] == "entree":
                rec_mois[cle] = rec_mois.get(cle, 0) + float(t["montant"] or 0)
            else:
                dep_mois[cle] = dep_mois.get(cle, 0) + float(t["montant"] or 0)
        lbls, recs, deps = [], [], []
        annee, mois_num = today.year, today.month
        for _ in range(12):
            d = datetime.date(annee, mois_num, 1)
            cle = d.strftime("%Y-%m")
            lbls.insert(0, d.strftime("%b"))
            recs.insert(0, int(rec_mois.get(cle, 0)))
            deps.insert(0, int(dep_mois.get(cle, 0)))
            mois_num -= 1
            if mois_num == 0:
                mois_num, annee = 12, annee - 1
        chart = SimpleLineChart()
        chart.set_series([("Recettes", recs), ("Depenses", deps)], lbls)
        return _img(chart, "Flux de tresorerie : recettes / depenses (12 mois)")

    def _effectifs():
        chart = SimpleBarChart()
        labels = [c["nom"][:12] for c in classes]
        values = [c["effectif"] for c in classes]
        chart.set_data(*_avec_autre(labels, values))
        return _img(chart, "Effectifs par classe")

    def _cycles():
        par_cycle = {}
        for c in classes:
            cle = c.get("cycle_nom") or "Sans cycle"
            par_cycle[cle] = par_cycle.get(cle, 0) + c["effectif"]
        chart = SimpleBarChart()
        chart.set_data(list(par_cycle.keys()), list(par_cycle.values()))
        return _img(chart, "Effectifs par cycle")

    def _sexe():
        sexes = {}
        for e in eleves:
            s = (e.get("sexe") or "Non precise").strip().capitalize()
            sexes[s] = sexes.get(s, 0) + 1
        chart = SimplePieChart()
        chart.set_data(list(sexes.keys()), list(sexes.values()))
        return _img(chart, "Repartition par sexe")

    def _statut():
        statuts = {}
        for e in eleves:
            s = (e.get("statut") or "Inconnu").capitalize()
            statuts[s] = statuts.get(s, 0) + 1
        chart = SimplePieChart()
        chart.set_data(list(statuts.keys()), list(statuts.values()))
        return _img(chart, "Repartition par statut")

    def _solde():
        mois = {}
        for t in transactions:
            cle = t["date"][:7]
            mois[cle] = mois.get(cle, 0) + (float(t["montant"] or 0)
                                            if t["type"] == "entree"
                                            else -float(t["montant"] or 0))
        lbls, vals = [], []
        annee, mois_num = today.year, today.month
        for _ in range(12):
            d = datetime.date(annee, mois_num, 1)
            cle = d.strftime("%Y-%m")
            lbls.insert(0, d.strftime("%b"))
            vals.insert(0, int(mois.get(cle, 0)))
            mois_num -= 1
            if mois_num == 0:
                mois_num, annee = 12, annee - 1
        chart = SimpleBarChart()
        chart.set_data(lbls, vals)
        return _img(chart, "Solde de tresorerie (12 mois)")

    def _groupe(rows, cle, somme):
        d = {}
        for r in rows:
            k = r.get(cle) or "Autre"
            d[k] = d.get(k, 0) + float(r.get(somme) or 0)
        return d

    def _frais():
        chart = SimplePieChart()
        frais = _groupe(paiements, "type_frais", "montant")
        chart.set_data(list(frais.keys()), list(frais.values()))
        return _img(chart, "Encaissements par type de frais")

    def _mode():
        chart = SimplePieChart()
        modes = _groupe(paiements, "mode_reglement", "montant")
        chart.set_data(list(modes.keys()), list(modes.values()))
        return _img(chart, "Encaissements par mode de reglement")

    def _classe():
        chart = SimpleBarChart()
        par_classe = {}
        for p in paiements:
            cle = p.get("classe_nom") or "Sans classe"
            par_classe[cle] = par_classe.get(cle, 0) + float(p["montant"] or 0)
        tries = sorted(par_classe.items(), key=lambda kv: kv[1], reverse=True)
        chart.set_data(*_avec_autre([k for k, _ in tries],
                                    [v for _, v in tries]))
        return _img(chart, "Encaissements par classe")

    def _presences():
        comptes = {r["statut"]: r["total"]
                   for r in repos.presences_statuts()}
        chart = SimplePieChart()
        chart.set_data(list(comptes.keys()), list(comptes.values()))
        return _img(chart, "Presences (toutes dates)")

    def _dossiers():
        complets = sum(1 for e in eleves
                       if e.get("check_acte") and e.get("check_photos")
                       and e.get("check_bulletin"))
        chart = SimplePieChart()
        chart.set_data(["Complets", "Incomplets"],
                       [complets, len(eleves) - complets])
        return _img(chart, "Dossiers des eleves")

    corps = (f"<h1>Statistiques de l'ecole</h1>"
             f"<p style='color:#64748b;font-size:12px;'>"
             f"{_contextuel('Chiffres et graphiques au')}</p>"
             + _section("", [
                 ("Eleves inscrits", len(eleves)),
                 ("Classes", len(classes)),
                 ("Paiements enregistres", len(paiements)),
             ])
             + _flux()
             + _effectifs() + _cycles()
             + _sexe() + _statut()
             + _solde()
             + _frais() + _mode()
             + _classe()
             + _presences() + _dossiers())
    html = (f"<html><head><meta charset='utf-8'><title>Statistiques</title>"
            f"<style>{STYLE}</style></head><body>{_entete_doc()}{corps}"
            f"</body></html>")
    path = _generate_pdf(html, "rapport_statistiques.pdf")
    if ouvrir:
        _ouvrir_pdf(path)
    return path


def _Qt():
    from PyQt5.QtCore import Qt
    return Qt


def _avec_autre(labels, values, limite=8):
    labels, values = list(labels), list(values)
    if len(labels) <= limite:
        return labels, values
    reste = sum(values[limite:])
    labels, values = labels[:limite], values[:limite]
    if reste:
        labels.append("Autre")
        values.append(reste)
    return labels, values