import datetime
from pathlib import Path

from core.config import DOCS_DIR, CRENEAUX, JOURS, VILLE_DEFAUT
from database import db
from repositories import repos


def _generate_pdf(html_content: str, filename: str) -> str:
    try:
        from weasyprint import HTML
        path = DOCS_DIR / filename
        HTML(string=html_content).write_pdf(str(path))
        return str(path)
    except ImportError:
        raise RuntimeError("weasyprint n'est pas installe. Installez-le avec : pip install weasyprint")


def _entete_doc():
    params = repos.parametres()
    pays = params.get("pays", "") or "Republique du Congo"
    ville = params.get("ville", "")
    now = datetime.datetime.now().strftime("%d/%m/%Y")
    localite = f" - {ville}" if ville else ""
    return (f"<div style='display:flex;justify-content:space-between;border-bottom:2px solid #e2e8f0;padding-bottom:12px;margin-bottom:20px;'>"
            f"<div><strong>Gestion Scolaire</strong>"
            f"<div style='color:#64748b;font-size:12px;'>{pays}{localite}</div></div>"
            f"<div style='color:#64748b;font-size:12px;'>Edite le {now}</div></div>")


STYLE = """
body { font-family: 'Inter', 'Segoe UI', sans-serif; margin: 40px; color: #1e293b; }
h1 { color: #047857; font-size: 22px; }
h2 { color: #1e293b; font-size: 18px; }
h3 { color: #334155; font-size: 15px; }
table { border-collapse: collapse; width: 100%; margin-top: 16px; }
th, td { border: 1px solid #e2e8f0; padding: 10px 14px; text-align: left; font-size: 13px; }
th { background-color: #f8fafc; color: #475569; font-weight: 700; }
p { color: #334155; }
strong { color: #1e293b; }
"""


def _appreciation(moyenne):
    if moyenne >= 16:
        return "Excellent"
    if moyenne >= 14:
        return "Tres bien"
    if moyenne >= 12:
        return "Bien"
    if moyenne >= 10:
        return "Assez bien"
    if moyenne >= 8:
        return "Passable"
    return "Insuffisant"


def bulletins_pdf(classe_id, periode):
    classe = repos.classe_by_id(classe_id)
    nom_classe = classe["nom"] if classe else "?"
    eleves = repos.eleves(classe_id=classe_id)
    progs = repos.programmes(classe_id=classe_id)
    matieres = [repos.matiere_by_id(p["matiere_id"]) for p in progs if p.get("matiere_id")]
    all_notes = repos.notes_classe(classe_id, periode)
    notes_index = {}
    for n in all_notes:
        key = (n["eleve_id"], n["matiere_id"])
        notes_index[key] = n
    corps = [f"<h1>Bulletins - {nom_classe}</h1>", f"<p style='color:#64748b;font-size:12px;'>Periode : {periode} - Effectif : {len(eleves)}</p>"]
    for eleve in eleves:
        lignes = ""
        total = 0.0
        coefs = 0.0
        for m in matieres:
            row = notes_index.get((eleve["id"], m["id"]))
            if row and (row["devoir1"] is not None or row["devoir2"] is not None or row["composition"] is not None):
                d1 = row["devoir1"] or 0
                d2 = row["devoir2"] or 0
                comp = row["composition"] or 0
                moy = round((d1 + d2 + 2 * comp) / 4, 2)
                coef = m["coefficient"] or 1
                total += moy * coef
                coefs += coef
                lignes += (f"<tr><td>{m['nom']}</td><td>{d1}</td><td>{d2}</td>"
                           f"<td>{comp}</td><td>{moy}</td></tr>")
            else:
                lignes += (f"<tr><td>{m['nom']}</td><td>-</td><td>-</td>"
                           f"<td>-</td><td>-</td></tr>")
        generale = round(total / coefs, 2) if coefs else 0
        appreciation = _appreciation(generale)
        corps.append(
            f"<h3>{eleve['prenom']} {eleve['nom']} ({eleve['matricule']})</h3>"
            f"<table><tr><th>Matiere</th><th>Devoir 1</th><th>Devoir 2</th>"
            f"<th>Composition</th><th>Moyenne</th></tr>{lignes}"
            f"<tr><td><strong>Moyenne generale</strong></td><td colspan='3'></td>"
            f"<td><strong>{generale} /20</strong></td></tr></table>"
            f"<p style='color:#64748b;font-size:12px;'>Appreciation : <strong>{appreciation}</strong></p>")
    html = f"<html><head><meta charset='utf-8'><title>Bulletins {nom_classe}</title><style>{STYLE}</style></head><body>{_entete_doc()}{''.join(corps)}</body></html>"
    filename = f"bulletins_{nom_classe.replace(' ', '_')}_{periode.split()[0]}.pdf"
    return _generate_pdf(html, filename)


def recu_paiement_pdf(eleve, montant, mode, reference):
    from ui.widgets import fmt_money
    date = datetime.datetime.now().strftime("%d/%m/%Y")
    params = repos.parametres()
    ville = params.get("ville", "") or VILLE_DEFAUT
    corps = f"""
    <h2 style="text-align:center;">RECU DE PAIEMENT</h2>
    <p>Recu N <strong>{reference}</strong> en date du {date}</p>
    <table>
    <tr><th>Eleve</th><td>{eleve['prenom']} {eleve['nom']}</td></tr>
    <tr><th>Matricule</th><td>{eleve['matricule']}</td></tr>
    <tr><th>Montant</th><td><strong>{fmt_money(montant)}</strong></td></tr>
    <tr><th>Mode de reglement</th><td>{mode}</td></tr>
    </table>
    <p style="margin-top:60px;">Fait a {ville}, le {date}</p>
    """
    html = f"<html><head><meta charset='utf-8'><title>Recu de paiement</title><style>{STYLE}</style></head><body>{_entete_doc()}{corps}</body></html>"
    filename = f"recu_{eleve['matricule']}_{reference}.pdf"
    return _generate_pdf(html, filename)


def certificat_scolarite_pdf(eleve, params):
    date = datetime.datetime.now().strftime("%d/%m/%Y")
    ville = params.get("ville", "") or VILLE_DEFAUT
    signataire = params.get("signataire_nom", "")
    titre = params.get("signataire_titre", "")
    corps = f"""
    <h2 style="text-align:center;">CERTIFICAT DE SCOLARITE</h2>
    <p>Nous, soussignes, certifions que l'eleve <strong>{eleve['prenom']} {eleve['nom']}</strong>,
    matricule <strong>{eleve['matricule']}</strong>, ne le {eleve.get('date_naissance') or '-'}
    a {eleve.get('lieu_naissance') or '-'}, est regulierement inscrit(e) dans notre etablissement.</p>
    <table><tr><th>Classe</th><th>Statut</th><th>Date d'inscription</th></tr>
    <tr><td>{eleve.get('classe_nom') or '-'}</td><td>{eleve['statut']}</td>
    <td>{eleve.get('date_inscription', '-')}</td></tr></table>
    <p style="margin-top:60px;">Fait a {ville}, le {date}<br>
    {signataire}<br><em>{titre}</em></p>
    """
    html = f"<html><head><meta charset='utf-8'><title>Certificat de scolarite</title><style>{STYLE}</style></head><body>{_entete_doc()}{corps}</body></html>"
    filename = f"certificat_{eleve['matricule']}.pdf"
    return _generate_pdf(html, filename)


def paie_pdf():
    from ui.widgets import fmt_money
    personnel = repos.personnel()
    masse = repos.masse_salariale()
    lignes = "".join(
        f"<tr><td>{p['nom_complet']}</td><td>{p['fonction']}</td><td>{p['statut']}</td>"
        f"<td>{fmt_money(p['salaire'])}</td></tr>" for p in personnel)
    corps = (
        f"<h1>Bulletins de paie - {datetime.date.today():%B %Y}</h1>"
        f"<table><tr><th>Nom</th><th>Fonction</th><th>Statut</th><th>Salaire</th></tr>{lignes}"
        f"<tr><td colspan='3'><strong>Masse salariale mensuelle</strong></td>"
        f"<td><strong>{fmt_money(masse)}</strong></td></tr></table>"
    )
    html = f"<html><head><meta charset='utf-8'><title>Paie</title><style>{STYLE}</style></head><body>{_entete_doc()}{corps}</body></html>"
    return _generate_pdf(html, "paie.pdf")


def planning_pdf(classe):
    entetes = "".join(f"<th>{j}</th>" for j in ["Creneau"] + list(JOURS))
    grid = {row["jour"]: {row["creneau"]: row} for row in
            db.query("SELECT * FROM planning WHERE classe_id = ?", (classe["id"],))}
    lignes = ""
    for creneau in CRENEAUX:
        cells = ""
        for jour in JOURS:
            entree = grid.get(jour, {}).get(creneau)
            if entree:
                cells += f"<td>{entree['matiere'] or ''}{' (' + entree['salle'] + ')' if entree['salle'] else ''}</td>"
            else:
                cells += "<td></td>"
        lignes += f"<tr><td><strong>{creneau}</strong></td>{cells}</tr>"
    corps = f"<h1>Emploi du temps - {classe['nom']}</h1>" \
            f"<table><tr>{entetes}</tr>{lignes}</table>"
    html = f"<html><head><meta charset='utf-8'><title>Emploi du temps</title><style>{STYLE}</style></head><body>{_entete_doc()}{corps}</body></html>"
    filename = f"planning_{classe['nom'].replace(' ', '_')}.pdf"
    return _generate_pdf(html, filename)
