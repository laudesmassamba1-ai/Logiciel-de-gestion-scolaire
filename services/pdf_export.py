import base64
import datetime
import html
import os
from pathlib import Path

from core.config import DOCS_DIR, CRENEAUX, JOURS, VILLE_DEFAUT
from database import db
from repositories import repos


def echap(valeur):
    return html.escape(str(valeur if valeur is not None else ""))


def _generate_pdf(html_content: str, filename: str, dossier=None) -> str:
    try:
        from weasyprint import HTML
        # Path(...).name neutralise toute tentative de traversee (../)
        # fournie via un nom de classe / matricule : le PDF reste toujours
        # dans DOCS_DIR (audit injection fichiers).
        nom = Path(filename).name or "document.pdf"
        dest = Path(dossier) if dossier else DOCS_DIR
        dest.mkdir(parents=True, exist_ok=True)
        path = dest / nom
        HTML(string=html_content).write_pdf(str(path))
        return str(path)
    except ImportError:
        raise RuntimeError("weasyprint n'est pas installe. Installez-le avec : pip install weasyprint")
    except Exception as exc:
        # Toute erreur weasyprint (police, rendu, memoire...) doit arriver
        # a l'ecran : on la convertit en RuntimeError avec un message clair.
        raise RuntimeError(f"La generation du PDF a echoue : {exc}") from exc


def _ouvrir_pdf(path):
    """Ouvre le PDF genere dans le lecteur par defaut de la machine.

    Strategie multi-OS, robuste meme quand le gestionnaire de fichiers est
    lent ou absent :
    - Windows : os.startfile (fiable) ;
    - macOS : `open` en sous-processus detache ;
    - Linux : xdg-open puis `gio open` avec VERIFICATION qu'un processus
      lecteur nouveau est apparu ; en dernier recours on tente les lecteurs
      PDF connus en direct (evince, okular...), puis on montre le chemin et
      on ouvre le dossier Documents. On ne se fie jamais a la valeur de
      retour de QDesktopServices.openUrl (il peut repondre vrai sans rien
      ouvrir sur certains postes Wayland/X11).
    """
    import subprocess
    import sys
    import time as _time

    from PyQt5.QtCore import QUrl
    from PyQt5.QtGui import QDesktopServices
    from PyQt5.QtWidgets import QMessageBox

    p = Path(path)
    if not p.exists() or p.stat().st_size == 0:
        QMessageBox.warning(
            None, "Document",
            "Le document n'a pas pu etre cree (fichier introuvable ou "
            f"vide).\n{p}")
        return

    def _montrer_chemin():
        QMessageBox.information(
            None, "Document genere",
            "Aucun lecteur PDF n'a pu ouvrir le document sur ce poste.\n"
            f"Le fichier est disponible ici :\n{p}")

    if sys.platform == "win32":
        try:
            os.startfile(str(p))
            return
        except OSError:
            _montrer_chemin()
            return

    if sys.platform == "darwin":
        try:
            subprocess.Popen(["open", str(p)], stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL,
                             start_new_session=True)
            return
        except OSError:
            pass

    # ---- Linux : filet complet, sans compter sur QDesktopServices ----
    LECTEURS = ("evince", "okular", "qpdfview", "zathura", "mupdf",
                "atril", "epdfview", "xreader")

    def _pids_lecteurs():
        """PID des processus lecteurs PDF deja presents a l'instant T."""
        pids = set()
        for nom in LECTEURS:
            try:
                r = subprocess.run(["pgrep", "-f", nom],
                                   capture_output=True, text=True,
                                   timeout=5)
                if r.returncode == 0 and r.stdout.strip():
                    pids |= {int(x) for x in r.stdout.split()}
            except (OSError, ValueError, subprocess.TimeoutExpired):
                continue
        return pids

    def _lancer(cmd):
        try:
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL,
                             start_new_session=True)
            return True
        except OSError:
            return False

    avant = _pids_lecteurs()

    # 1) Outil generique du bureau : xdg-open, puis gio open.
    for essai in (["xdg-open", str(p)], ["gio", "open", str(p)]):
        if _lancer(essai):
            _time.sleep(2.5)
            if _pids_lecteurs() - avant:
                return  # un lecteur est bien en train d'ouvrir le fichier
            # certains environnements repondent "ok" sans rien lancer :
            # on poursuit vers le filet suivant

    # 2) Lecteurs PDF connus, en direct (ne depend d'aucun MIME/bureau).
    for nom in LECTEURS:
        if _lancer([nom, str(p)]):
            _time.sleep(1.2)
            if _pids_lecteurs() - avant:
                return

    # 3) Echec total : on montre ou trouver le fichier et on ouvre le dossier.
    _montrer_chemin()
    QDesktopServices.openUrl(QUrl.fromLocalFile(str(p.parent)))


def _img_data_uri(path_str):
    """Convertit un chemin d'image en data URI base64 pour embed HTML."""
    if not path_str:
        return ""
    p = Path(path_str)
    if not p.exists():
        return ""
    ext = p.suffix.lower()
    mime = {
        ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".gif": "image/gif", ".bmp": "image/bmp", ".svg": "image/svg+xml",
    }.get(ext, "image/png")
    data = p.read_bytes()
    b64 = base64.b64encode(data).decode("ascii")
    return f"data:{mime};base64,{b64}"


def _reglage_embleme(params, key, align_defaut, hauteur_defaut):
    """Alignement et hauteur maximale d'un embleme, reglables dans
    Parametres : cles doctypes `{key}_align` (gauche/centre/droite) et
    `{key}_hauteur` (pixels, borne 30..400)."""
    align = str(params.get(f"{key}_align", "") or "").strip().lower()
    if align not in ("gauche", "centre", "droite"):
        align = align_defaut
    try:
        hauteur = int(params.get(f"{key}_hauteur", "") or hauteur_defaut)
    except (TypeError, ValueError):
        hauteur = hauteur_defaut
    hauteur = max(30, min(hauteur, 400))
    return {"gauche": "left", "centre": "center", "droite": "right"}[align], hauteur


def _entete_doc():
    params = repos.parametres()
    nom_ecole = params.get("nom_ecole", "") or "Gestion Scolaire"
    pays = params.get("pays", "") or "Republique du Congo"
    ville = params.get("ville", "")
    now = datetime.datetime.now().strftime("%d/%m/%Y")
    localite = f" - {echap(ville)}" if ville else ""
    bandeau_haut = _img_data_uri(params.get("bandeau_haut", ""))
    bandeau_bas = _img_data_uri(params.get("bandeau_bas", ""))
    signature = _img_data_uri(params.get("signature", ""))
    align_haut, haut_h = _reglage_embleme(params, "bandeau_haut", "centre", 80)
    align_bas, haut_b = _reglage_embleme(params, "bandeau_bas", "centre", 80)
    align_sig, haut_s = _reglage_embleme(params, "signature", "droite", 50)
    entete = "<div style='border-bottom:2px solid #e2e8f0;padding-bottom:12px;margin-bottom:20px;'>"
    if bandeau_haut:
        entete += (f"<div style='text-align:{align_haut};margin-bottom:8px;'>"
                   f"<img src='{bandeau_haut}' style='max-width:100%;"
                   f"max-height:{haut_h}px;'/></div>")
    entete += (f"<div style='display:flex;justify-content:space-between;'>"
               f"<div><strong>{echap(nom_ecole)}</strong>"
               f"<div style='color:#64748b;font-size:12px;'>{echap(pays)}{localite}</div></div>"
               f"<div style='color:#64748b;font-size:12px;'>Edite le {now}</div></div>")
    if bandeau_bas:
        entete += (f"<div style='text-align:{align_bas};margin-top:8px;'>"
                   f"<img src='{bandeau_bas}' style='max-width:100%;"
                   f"max-height:{haut_b}px;'/></div>")
    if signature:
        entete += (f"<div style='text-align:{align_sig};margin-top:16px;'>"
                   f"<img src='{signature}' style='max-height:{haut_s}px;'/></div>")
    entete += "</div>"
    return entete


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
    from services.appreciations import appreciation
    return appreciation(moyenne)


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
    corps = [f"<h1>Bulletins - {echap(nom_classe)}</h1>", f"<p style='color:#64748b;font-size:12px;'>Periode : {echap(periode)} - Effectif : {len(eleves)}</p>"]
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
            f"<p style='color:#64748b;font-size:12px;'>Appreciation : <strong>{appreciation}</strong></p>")
    html = f"<html><head><meta charset='utf-8'><title>Bulletins {echap(nom_classe)}</title><style>{STYLE}</style></head><body>{_entete_doc()}{''.join(corps)}</body></html>"
    filename = f"bulletins_{nom_classe.replace(' ', '_')}_{periode.split()[0]}.pdf"
    path = _generate_pdf(html, filename)
    _ouvrir_pdf(path)
    return path


def recu_paiement_pdf(eleve, montant, mode, reference):
    from ui.widgets import fmt_money
    date = datetime.datetime.now().strftime("%d/%m/%Y")
    params = repos.parametres()
    ville = params.get("ville", "") or VILLE_DEFAUT
    corps = f"""
    <h2 style="text-align:center;">RECU DE PAIEMENT</h2>
    <p>Recu N <strong>{echap(reference)}</strong> en date du {date}</p>
    <table>
    <tr><th>Eleve</th><td>{echap(eleve['prenom'])} {echap(eleve['nom'])}</td></tr>
    <tr><th>Matricule</th><td>{echap(eleve['matricule'])}</td></tr>
    <tr><th>Montant</th><td><strong>{fmt_money(montant)}</strong></td></tr>
    <tr><th>Mode de reglement</th><td>{echap(mode)}</td></tr>
    </table>
    <p style="margin-top:60px;">Fait a {echap(ville)}, le {date}</p>
    """
    html = f"<html><head><meta charset='utf-8'><title>Recu de paiement</title><style>{STYLE}</style></head><body>{_entete_doc()}{corps}</body></html>"
    filename = f"recu_{eleve['matricule']}_{reference}.pdf"
    path = _generate_pdf(html, filename)
    _ouvrir_pdf(path)
    return path


def certificat_scolarite_pdf(eleve, params):
    date = datetime.datetime.now().strftime("%d/%m/%Y")
    ville = params.get("ville", "") or VILLE_DEFAUT
    signataire = params.get("signataire_nom", "")
    titre = params.get("signataire_titre", "")
    corps = f"""
    <h2 style="text-align:center;">CERTIFICAT DE SCOLARITE</h2>
    <p>Nous, soussignes, certifions que l'eleve <strong>{echap(eleve['prenom'])} {echap(eleve['nom'])}</strong>,
    matricule <strong>{echap(eleve['matricule'])}</strong>, ne le {echap(eleve.get('date_naissance') or '-')}
    a {echap(eleve.get('lieu_naissance') or '-')}, est regulierement inscrit(e) dans notre etablissement.</p>
    <table><tr><th>Classe</th><th>Statut</th><th>Date d'inscription</th></tr>
    <tr><td>{echap(eleve.get('classe_nom') or '-')}</td><td>{echap(eleve['statut'])}</td>
    <td>{echap(eleve.get('date_inscription', '-'))}</td></tr></table>
    <p style="margin-top:60px;">Fait a {echap(ville)}, le {date}<br>
    {echap(signataire)}<br><em>{echap(titre)}</em></p>
    """
    html = f"<html><head><meta charset='utf-8'><title>Certificat de scolarite</title><style>{STYLE}</style></head><body>{_entete_doc()}{corps}</body></html>"
    filename = f"certificat_{eleve['matricule']}.pdf"
    path = _generate_pdf(html, filename)
    _ouvrir_pdf(path)
    return path


def paie_pdf():
    from ui.widgets import fmt_money
    personnel = repos.personnel()
    masse = repos.masse_salariale()
    lignes = "".join(
        f"<tr><td>{echap(p['nom_complet'])}</td><td>{echap(p['fonction'])}</td><td>{echap(p['statut'])}</td>"
        f"<td>{fmt_money(p['salaire'])}</td></tr>" for p in personnel)
    corps = (
        f"<h1>Bulletins de paie - {datetime.date.today():%B %Y}</h1>"
        f"<table><tr><th>Nom</th><th>Fonction</th><th>Statut</th><th>Salaire</th></tr>{lignes}"
        f"<tr><td colspan='3'><strong>Masse salariale mensuelle</strong></td>"
        f"<td><strong>{fmt_money(masse)}</strong></td></tr></table>"
    )
    html = f"<html><head><meta charset='utf-8'><title>Paie</title><style>{STYLE}</style></head><body>{_entete_doc()}{corps}</body></html>"
    path = _generate_pdf(html, "paie.pdf")
    _ouvrir_pdf(path)
    return path


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
                salle = f" ({echap(entree['salle'])})" if entree['salle'] else ""
                cells += f"<td>{echap(entree['matiere'] or '')}{salle}</td>"
            else:
                cells += "<td></td>"
        lignes += f"<tr><td><strong>{creneau}</strong></td>{cells}</tr>"
    corps = f"<h1>Emploi du temps - {echap(classe['nom'])}</h1>" \
            f"<table><tr>{entetes}</tr>{lignes}</table>"
    html = f"<html><head><meta charset='utf-8'><title>Emploi du temps</title><style>{STYLE}</style></head><body>{_entete_doc()}{corps}</body></html>"
    filename = f"planning_{classe['nom'].replace(' ', '_')}.pdf"
    path = _generate_pdf(html, filename)
    _ouvrir_pdf(path)
    return path
