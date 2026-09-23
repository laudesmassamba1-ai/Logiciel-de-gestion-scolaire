import datetime
import html
from pathlib import Path

from core.config import CRENEAUX, DOCS_DIR, JOURS, VILLE_DEFAUT
from database import db
from repositories import repos
from ui.widgets import fmt_money


def echap(valeur):
    """Echappe une donnee utilisateur avant insertion dans le HTML :
    un nom contenant '<' ou un script ne doit jamais casser le rapport."""
    return html.escape(str(valeur if valeur is not None else ""))

STYLE = """
body { font-family: 'Inter', 'Segoe UI', sans-serif; margin: 40px; color: #1e293b; }
h1 { color: #047857; font-size: 22px; }
h2 { color: #1e293b; font-size: 18px; }
h3 { color: #334155; font-size: 15px; }
table { border-collapse: collapse; width: 100%; margin-top: 16px; }
th, td { border: 1px solid #e2e8f0; padding: 10px 14px; text-align: left; font-size: 13px; }
th { background-color: #f8fafc; color: #475569; font-weight: 700; }
.header { display: flex; justify-content: space-between; border-bottom: 2px solid #e2e8f0; padding-bottom: 12px; margin-bottom: 20px; }
.meta { color: #64748b; font-size: 12px; }
p { color: #334155; }
strong { color: #1e293b; }
"""

def _open_in_browser(path: Path):

    from PyQt5.QtCore import QUrl
    from PyQt5.QtGui import QDesktopServices
    ouvert = QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
    if not ouvert:
        # Feedback explicite : l'utilisateur sait ou trouver son fichier
        # meme si le navigateur ne s'ouvre pas.
        from PyQt5.QtWidgets import QMessageBox
        QMessageBox.information(
            None, "Rapport genere",
            f"Le fichier a ete cree ici :\n{path}\n\n"
            "Ouvrez-le manuellement avec votre navigateur.")

def _write(title, body_html, filename):

    # Path(...).name neutralise toute tentative de traversee (../) via un
    # nom de classe / matricule : le rapport reste toujours dans DOCS_DIR.
    nom = Path(filename).name or "rapport.html"
    path = DOCS_DIR / nom
    html = (f"<html><head><meta charset='utf-8'><title>{echap(title)}</title>"
            f"<style>{STYLE}</style></head><body>{body_html}</body></html>")
    path.write_text(html, encoding="utf-8")
    _open_in_browser(path)
    return path

def _entete_doc():

    params = repos.parametres()
    pays = params.get("pays", "") or "Republique du Congo"
    ville = params.get("ville", "")
    now = datetime.datetime.now().strftime("%d/%m/%Y")
    localite = f" - {echap(ville)}" if ville else ""
    return (f"<div class='header'><div><strong>Gestion Scolaire</strong>"
            f"<div class='meta'>{echap(pays)}{localite}</div></div>"
            f"<div class='meta'>Edite le {now}</div></div>")

def export_eleves_csv(eleves):

    import csv
    path = DOCS_DIR / f"eleves_{datetime.date.today():%Y%m%d}.csv"
    with open(path, "w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.writer(fh, delimiter=";")
        writer.writerow(["Matricule", "Nom", "Prenom", "Sexe", "Date Naissance",
                         "Classe", "Contact Tuteur", "Statut"])
        for e in eleves:
            writer.writerow([e["matricule"], e["nom"], e["prenom"], e["sexe"],
                             e["date_naissance"], e["classe_nom"] or "-",
                             e["tuteur_tel"] or "-", e["statut"]])
    _open_in_browser(path)

def bulletins(classe_id, periode):
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
    corps = [f"<h1>Bulletins - {echap(nom_classe)}</h1>",
             f"<p class='meta'>Periode : {echap(periode)} - Effectif : {len(eleves)}</p>"]
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
                lignes += (f"<tr><td>{echap(m['nom'])}</td><td>{d1}</td><td>{d2}</td>"
                           f"<td>{comp}</td><td>{moy}</td></tr>")
            else:
                lignes += (f"<tr><td>{echap(m['nom'])}</td><td>-</td><td>-</td>"
                           f"<td>-</td><td>-</td></tr>")

        generale = round(total / coefs, 2) if coefs else 0
        appreciation = _appreciation(generale)
        corps.append(
            f"<h3>{echap(eleve['prenom'])} {echap(eleve['nom'])} ({echap(eleve['matricule'])})</h3>"
            f"<table><tr><th>Matiere</th><th>Devoir 1</th><th>Devoir 2</th>"
            f"<th>Composition</th><th>Moyenne</th></tr>{lignes}"
            f"<tr><td><strong>Moyenne generale</strong></td><td colspan='3'></td>"
            f"<td><strong>{generale} /20</strong></td></tr></table>"
            f"<p class='meta'>Appreciation : <strong>{appreciation}</strong></p>")
    return _write(f"Bulletins {nom_classe}", _entete_doc() + "".join(corps), f"bulletins_{nom_classe.replace(' ', '_')}_{periode.split()[0]}.html")

def recu_paiement(eleve, montant, mode, reference):

    date = datetime.datetime.now().strftime("%d/%m/%Y")
    params = repos.parametres()
    ville = params.get("ville", "") or VILLE_DEFAUT
    corps = f"""
    {_entete_doc()}
    <h2 style="text-align:center;">RECU DE PAIEMENT</h2>
    <p>Reçu N° <strong>{echap(reference)}</strong> en date du {date}</p>
    <table>
    <tr><th>Eleve</th><td>{echap(eleve['prenom'])} {echap(eleve['nom'])}</td></tr>
    <tr><th>Matricule</th><td>{echap(eleve['matricule'])}</td></tr>
    <tr><th>Montant</th><td><strong>{fmt_money(montant)}</strong></td></tr>
    <tr><th>Mode de reglement</th><td>{echap(mode)}</td></tr>
    </table>
    <p style="margin-top:60px;">Fait a {echap(ville)}, le {date}</p>
    """
    return _write("Recu de paiement", corps, f"recu_{eleve['matricule']}_{reference}.html")

def certificat_scolarite(eleve, params):

    date = datetime.datetime.now().strftime("%d/%m/%Y")
    ville = params.get("ville", "") or VILLE_DEFAUT
    signataire = params.get("signataire_nom", "")
    titre = params.get("signataire_titre", "")
    corps = f"""
    {_entete_doc()}
    <h2 style="text-align:center;">CERTIFICAT DE SCOLARITE</h2>
    <p>Nous, soussignes, certifions que l'eleve <strong>{echap(eleve['prenom'])} {echap(eleve['nom'])}</strong>,
    matricule <strong>{echap(eleve['matricule'])}</strong>, ne le {echap(eleve['date_naissance'] or '-')}
    a {echap(eleve['lieu_naissance'] or '-')}, est regulierement inscrit(e) dans notre etablissement.</p>
    <table><tr><th>Classe</th><th>Statut</th><th>Date d'inscription</th></tr>
    <tr><td>{echap(eleve['classe_nom'] or '-')}</td><td>{echap(eleve['statut'])}</td>
    <td>{echap(eleve['date_inscription'])}</td></tr></table>
    <p style="margin-top:60px;">Fait a {echap(ville)}, le {date}<br>
    {echap(signataire)}<br><em>{echap(titre)}</em></p>
    """
    return _write("Certificat de scolarite", corps, f"certificat_{eleve['matricule']}.html")

def paie():

    personnel = repos.personnel()
    masse = repos.masse_salariale()
    lignes = "".join(
        f"<tr><td>{echap(p['nom_complet'])}</td><td>{echap(p['fonction'])}</td><td>{echap(p['statut'])}</td>"
        f"<td>{fmt_money(p['salaire'])}</td></tr>" for p in personnel)
    corps = (
        f"{_entete_doc()}<h1>Bulletins de paie - {datetime.date.today():%B %Y}</h1>"
        f"<table><tr><th>Nom</th><th>Fonction</th><th>Statut</th><th>Salaire</th></tr>{lignes}"
        f"<tr><td colspan='3'><strong>Masse salariale mensuelle</strong></td>"
        f"<td><strong>{fmt_money(masse)}</strong></td></tr></table>"
    )
    return _write("Paie", corps, "paie.html")

def rapport_rh():
    personnel = repos.personnel()
    enseignants = repos.enseignants()
    lignes = "".join(
        f"<tr><td>{echap(p['nom_complet'])}</td><td>{echap(p['fonction'])}</td><td>{echap(p['telephone'])}</td>"
        f"<td>{echap(p['statut'])}</td></tr>" for p in personnel)
    corps = (
        f"{_entete_doc()}<h1>Rapport RH Mensuel</h1>"
        f"<p class='meta'>Effectif total : {len(personnel)} - Enseignants : {len(enseignants)}</p>"
        f"<table><tr><th>Nom</th><th>Fonction</th><th>Telephone</th><th>Statut</th></tr>{lignes}</table>"
    )
    return _write("Rapport RH", corps, "rapport_rh.html")

def planning(classe):

    entetes = "".join(f"<th>{j}</th>" for j in ["Creneau"] + list(JOURS))
    grid = {row["jour"]: {row["creneau"]: row} for row in
            db.query("SELECT * FROM planning WHERE classe_id = ?", (classe["id"],))}
    lignes = ""
    for creneau in CRENEAUX:
        cells = ""
        for jour in JOURS:
            entree = grid.get(jour, {}).get(creneau)
            if entree:
                salle = f" ({echap(entree['salle'])})" if entree["salle"] else ""
                cells += f"<td>{echap(entree['matiere'] or '')}{salle}</td>"
            else:
                cells += "<td></td>"
        lignes += f"<tr><td><strong>{creneau}</strong></td>{cells}</tr>"
    corps = f"{_entete_doc()}<h1>Emploi du temps - {echap(classe['nom'])}</h1>" \
            f"<table><tr>{entetes}</tr>{lignes}</table>"
    return _write("Emploi du temps", corps, f"planning_{classe['nom'].replace(' ', '_')}.html")

def _appreciation(moyenne):
    from services.appreciations import appreciation
    return appreciation(moyenne)
