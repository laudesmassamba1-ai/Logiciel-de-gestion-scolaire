"""Modeles de documents personnalises.

L'ecole peut ecrire un modele (HTML) depuis zero dans une fenetre dediee,
y inserer des variables `{{cle}}` (eleve, classe, ecole...), l'enregistrer
comme modele reutilisable, l'editer / le renommer / le dupliquer / le
supprimer, puis generer un vrai PDF (WeasyPrint) pour un eleve, une classe,
ou « echo ecole » (sans cible). Les PDF generes atterrissent dans l'Espace
Documents (DOCS_DIR) comme les autres documents.

Les modeles sont stockes dans `data/modeles/*.html`.
"""

import datetime
import re
from pathlib import Path

from core.config import DOCS_DIR, data_dir
from repositories import repos
from services.pdf_export import (STYLE, _entete_doc, _generate_pdf,
                                 _ouvrir_pdf, echap)

MODELE_DIR = data_dir() / "modeles"

_VARIABLES = (
    ("nom_ecole", "Nom de l'ecole"),
    ("pays", "Pays"),
    ("ville", "Ville"),
    ("date_courte", "Date du jour (jj/mm/aaaa)"),
    ("date_longue", "Date du jour en toutes lettres"),
    ("annee_scolaire", "Annee scolaire active"),
    ("signataire_nom", "Nom du signataire"),
    ("signataire_titre", "Titre du signataire"),
    ("prenom", "Prenom de l'eleve"),
    ("nom", "Nom de famille de l'eleve"),
    ("nom_complet", "Prenom + nom de l'eleve"),
    ("matricule", "Matricule de l'eleve"),
    ("sexe", "Sexe de l'eleve"),
    ("date_naissance", "Date de naissance de l'eleve"),
    ("lieu_naissance", "Lieu de naissance de l'eleve"),
    ("classe", "Classe de l'eleve"),
    ("statut", "Statut de l'eleve"),
    ("date_inscription", "Date d'inscription de l'eleve"),
    ("classe_nom", "Nom de la classe ciblee"),
    ("effectif", "Effectif de la classe ciblee"),
    ("cycle", "Cycle de la classe ciblee"),
)

MODELE_DEFAUT = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body { font-family: 'Inter', 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #1D1D1F; }
        h1 { color: #C8960C; border-bottom: 2px solid #C8960C; padding-bottom: 8px; }
        h2 { color: #42424A; margin-top: 24px; }
        h3 { color: #6E6E73; }
        .variables { background: #F6EED7; border: 1px solid #E9DFC4; border-radius: 8px; padding: 12px; margin: 16px 0; font-family: monospace; font-size: 12px; }
        .var { color: #7A5A08; }
        table { border-collapse: collapse; width: 100%; margin: 16px 0; }
        th, td { border: 1px solid #E7E7EC; padding: 8px 12px; text-align: left; }
        th { background: #F2F2F5; font-weight: 600; }
        tr:nth-child(even) td { background: #FAFAFA; }
        blockquote { border-left: 4px solid #C8960C; padding-left: 16px; margin: 16px 0; color: #6E6E73; font-style: italic; }
        .signature { margin-top: 48px; }
        .page-break { page-break-after: always; }
    </style>
</head>
<body>
    <h1>TITRE DU DOCUMENT</h1>
    <p>Redigez ici le contenu de votre modele, en utilisant le menu <strong>Insérer variable</strong> pour les donnees dynamiques.</p>
    
    <div class="variables">
        <strong>Variables disponibles :</strong><br>
        <span class="var">{{nom_complet}}</span> - Nom complet de l'eleve<br>
        <span class="var">{{matricule}}</span> - Matricule<br>
        <span class="var">{{classe}}</span> - Classe<br>
        <span class="var">{{nom_ecole}}</span> - Nom de l'ecole<br>
        <span class="var">{{date_courte}}</span> - Date du jour<br>
        <span class="var">{{signataire_nom}}</span> - Nom du signataire
    </div>
    
    <h2>Informations de l'eleve</h2>
    <table>
        <tr><th>Champ</th><th>Valeur</th></tr>
        <tr><td>Nom complet</td><td>{{nom_complet}}</td></tr>
        <tr><td>Matricule</td><td>{{matricule}}</td></tr>
        <tr><td>Classe</td><td>{{classe}}</td></tr>
        <tr><td>Date de naissance</td><td>{{date_naissance}}</td></tr>
        <tr><td>Lieu de naissance</td><td>{{lieu_naissance}}</td></tr>
    </table>
    
    <h2>Contenu du document</h2>
    <p>Ecrivez votre texte ici. Vous pouvez utiliser :</p>
    <ul>
        <li><strong>Gras</strong> (Ctrl+B), <em>Italique</em> (Ctrl+I), <u>Souligne</u> (Ctrl+U)</li>
        <li>Listes a puces ou numerotees</li>
        <li>Tableaux (Insertion > Tableau)</li>
        <li>Images (Insertion > Image)</li>
        <li>Separateurs horizontaux</li>
        <li>Sauts de page pour l'impression</li>
    </ul>
    
    <blockquote>
        Astuce : Utilisez les styles rapides (Titre 1, Titre 2, Citation, Code...) pour une mise en forme coherente.
    </blockquote>
    
    <div class="signature">
        <p>Fait a {{ville}}, le {{date_courte}}<br>
        {{signataire_nom}}<br>
        <em>{{signataire_titre}}</em></p>
    </div>
</body>
</html>
"""


def lister_modeles():
    """Liste les modeles enregistres, tries par nom."""
    if not MODELE_DIR.exists():
        return []
    modeles = []
    for p in sorted(MODELE_DIR.glob("*.html")):
        st = p.stat()
        modeles.append({
            "nom": p.stem,
            "chemin": str(p),
            "date": datetime.datetime.fromtimestamp(st.st_mtime),
            "taille": st.st_size,
        })
    return modeles


def _chemin_modele(nom):
    """Chemin securise : le nom ne peut pas evader le dossier des modeles."""
    propre = re.sub(r"[^A-Za-z0-9_\- ]+", "", str(nom)).strip()
    if not propre:
        raise ValueError("Nom de modele invalide")
    MODELE_DIR.mkdir(parents=True, exist_ok=True)
    return MODELE_DIR / f"{propre}.html"


def lire_modele(nom):
    p = _chemin_modele(nom)
    return p.read_text(encoding="utf-8") if p.exists() else None


def ecrire_modele(nom, texte):
    p = _chemin_modele(nom)
    p.write_text(texte, encoding="utf-8")
    return p.stem


def supprimer_modele(nom):
    p = _chemin_modele(nom)
    if p.exists():
        p.unlink()
        return True
    return False


def renommer_modele(ancien, nouveau):
    if nouveau != ancien and lire_modele(nouveau) is not None:
        raise FileExistsError(f"Le modele « {nouveau} » existe deja")
    p = _chemin_modele(ancien)
    if not p.exists():
        raise FileNotFoundError("Modele introuvable")
    p.rename(_chemin_modele(nouveau))
    return nouveau


def variables():
    """Variables insertibles dans un modele, sous forme (cle, libelle)."""
    return list(_VARIABLES)


def _sexe_label(valeur):
    s = str(valeur or "").lower()
    if s in ("m", "masculin", "garcon"):
        return "Masculin"
    if s in ("f", "feminin", "fille"):
        return "Feminin"
    return str(valeur or "-")


def _contexte_ecole():
    params = repos.parametres()
    jour = datetime.date.today()
    mois = ["janvier", "fevrier", "mars", "avril", "mai", "juin",
            "juillet", "aout", "septembre", "octobre", "novembre",
            "decembre"]
    annee = "-"
    try:
        active = repos.annee_scolaire_active()
        if active and active.get("libelle"):
            annee = active["libelle"]
    except Exception:
        pass
    return {
        "nom_ecole": params.get("nom_ecole") or "-",
        "pays": params.get("pays") or "-",
        "ville": params.get("ville") or "-",
        "date_courte": jour.strftime("%d/%m/%Y"),
        "date_longue": f"{jour.day} {mois[jour.month - 1]} {jour.year}",
        "annee_scolaire": annee,
        "signataire_nom": params.get("signataire_nom") or "-",
        "signataire_titre": params.get("signataire_titre") or "-",
    }


def _contexte_classe(classe_id):
    ctx = {}
    try:
        classe = repos.classe_by_id(classe_id)
        if classe:
            ctx["classe_nom"] = classe.get("nom") or "-"
            ctx["cycle"] = classe.get("cycle_nom") or "-"
            ctx["effectif"] = str(len(repos.eleves(classe_id=classe_id)))
    except Exception:
        ctx.update({"classe_nom": "-", "cycle": "-", "effectif": "-"})
    return ctx


def _contexte_eleve(eleve_id):
    ctx = {}
    try:
        eleve = repos.eleve_by_id(eleve_id)
        if not eleve:
            return ctx
        ctx.update({
            "prenom": eleve.get("prenom") or "-",
            "nom": eleve.get("nom") or "-",
            "nom_complet": f"{eleve.get('prenom') or ''} {eleve.get('nom') or ''}".strip() or "-",
            "matricule": eleve.get("matricule") or "-",
            "sexe": _sexe_label(eleve.get("sexe")),
            "date_naissance": eleve.get("date_naissance") or "-",
            "lieu_naissance": eleve.get("lieu_naissance") or "-",
            "classe": eleve.get("classe_nom") or "-",
            "statut": eleve.get("statut") or "-",
            "date_inscription": eleve.get("date_inscription") or "-",
        })
    except Exception:
        pass
    return ctx


def _remplacer_variables(texte, valeurs):
    for cle, valeur in valeurs.items():
        texte = texte.replace("{{" + cle + "}}", echap(valeur))
    return texte


def _extraire_corps(texte):
    """Repere le contenu du <body> quand le modele est un document HTML
    complet (sortie `QTextEdit.toHtml()`), sinon garde le fragment tel quel."""
    m = re.search(r"<body[^>]*>(.*)</body>", texte, re.S | re.I)
    return m.group(1) if m else texte


def _modele_valide(texte):
    if not texte or not texte.strip():
        raise ValueError("Le modele est vide : ecrivez du contenu avant d'enregistrer.")
    connues = {cle for cle, _ in _VARIABLES}
    restantes = re.findall(r"\{\{(\w+)\}\}", texte)
    inconnues = sorted({cle for cle in restantes if cle not in connues})
    if inconnues:
        raise ValueError("Variables inconnues (non remplacees) : "
                         + ", ".join(f"{{{{{cle}}}}}" for cle in inconnues))
    return True


def generer_pdf(nom, eleve_id=None, classe_id=None, cible=False, ouvrir=True):
    """Cree le PDF a partir d'un modele enregistre.

    `cible` : si eleve et classe absents, generateur « ecole » quand True,
    sinon erreur (il faut choisir une cible).
    """
    texte = lire_modele(nom)
    if texte is None:
        raise FileNotFoundError(f"Modele « {nom} » introuvable")
    _modele_valide(texte)
    if not eleve_id and not classe_id and not cible:
        raise ValueError("Choisissez un eleve ou une classe (ou le mode ecole).")
    valeurs = _contexte_ecole()
    if classe_id:
        valeurs.update(_contexte_classe(classe_id))
    suffixe = "ecole"
    if eleve_id:
        valeurs.update(_contexte_eleve(eleve_id))
        e = repos.eleve_by_id(eleve_id)
        suffixe = (e.get("matricule") if e else "") or str(eleve_id)
    elif classe_id:
        c = repos.classe_by_id(classe_id)
        suffixe = (c.get("nom") if c else "") or str(classe_id)
    corps = _remplacer_variables(_extraire_corps(texte), valeurs)
    html = (f"<html><head><meta charset='utf-8'><title>{echap(nom)}</title>"
            f"<style>{STYLE}</style></head><body>{_entete_doc()}{corps}</body></html>")
    suffixe_propre = re.sub(r"[^A-Za-z0-9_\- ]+", "", suffixe).strip()
    filename = f"modele_{nom.replace(' ', '_')}_{suffixe_propre}.pdf"
    path = _generate_pdf(html, filename)
    if ouvrir:
        _ouvrir_pdf(path)
    return path


def apercu_modele(nom):
    """Apercu sur donnees de demonstration (hors Espace Documents)."""
    import tempfile
    texte = lire_modele(nom)
    if texte is None:
        raise FileNotFoundError(f"Modele « {nom} » introuvable")
    _modele_valide(texte)
    valeurs = _contexte_ecole()
    valeurs.update({
        "prenom": "Keisha", "nom": "Kouakou", "nom_complet": "Keisha Kouakou",
        "matricule": "EX-2026-0001", "sexe": "Feminin",
        "date_naissance": "12/03/2012", "lieu_naissance": "Brazzaville",
        "classe": "CM1", "statut": "Inscrit(e)",
        "date_inscription": "01/09/2026",
    })
    corps = _remplacer_variables(_extraire_corps(texte), valeurs)
    html = (f"<html><head><meta charset='utf-8'><title>Apercu</title>"
            f"<style>{STYLE}</style></head><body>{_entete_doc()}{corps}</body></html>")
    return _generate_pdf(html, f"apercu_{nom.replace(' ', '_')}.pdf",
                         dossier=Path(tempfile.gettempdir()))


# ----------------------------------------------------------------------
# Favoris (modeles)
# ----------------------------------------------------------------------
_FAVORIS_FILE = MODELE_DIR.parent / "modeles_favoris.json"

def get_favoris():
    """Retourne la liste des noms de modeles favoris."""
    import json
    if _FAVORIS_FILE.exists():
        try:
            return json.loads(_FAVORIS_FILE.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def set_favoris(liste):
    """Enregistre la liste des favoris."""
    import json
    MODELE_DIR.mkdir(parents=True, exist_ok=True)
    _FAVORIS_FILE.write_text(json.dumps(liste, ensure_ascii=False, indent=2), encoding="utf-8")