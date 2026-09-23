"""Espace Documents — tous les PDF generes (bulletins, recus, certificats,
plannings, paie) au meme endroit : classement, affectation a un eleve,
renommage, export et organisation en dossiers.

- Liste des documents de `DOCS_DIR` (data/documents), y compris dans les
  sous-dossiers apres une organisation.
- Classement virtuel par type (Bulletins, Recus, Certificats, Emplois du
  temps, Paie, Autres) et par eleve/classe (matricule lu dans le nom, ou
  affectation manuelle conservee dans un fichier de metadonnees local).
- Par document : ouvrir, renommer, affecter a un eleve, deplacer vers un
  dossier, exporter ailleurs, supprimer. Boutons globaux : nouveau dossier,
  organiser en sous-dossiers, exporter tout.
"""

import datetime
import json
import shutil
from pathlib import Path

from PyQt5.QtCore import QUrl
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout,
    QHBoxLayout, QInputDialog, QLabel, QLineEdit, QMessageBox,
    QStackedWidget, QVBoxLayout,
)

from core.config import (
    C_BG_SOFT, C_BORDER, C_PRIMARY, C_PRIMARY_LIGHT, C_RED, C_RED_BG,
    C_RED_BORDER, C_TEXT_SECONDARY, DOCS_DIR, C_AURORA,
    STYLE_BTN_PRIMARY, STYLE_BTN_SECONDARY,
)
from repositories import repos
from ui import toast
from ui.pages.helpers import (
    _btn, _actions_cell, _simple_btn_style, confirmer,
)
from ui.widgets import DataTable, EmptyState, PageHeader


META_FILE = DOCS_DIR / ".gestion_documents.json"
_ANNULE = object()
TYPES_PDF = (
    ("bulletins_", "Bulletins"),
    ("recu_", "Recus"),
    ("certificat_", "Certificats"),
    ("planning_", "Emplois du temps"),
    ("paie", "Paie"),
)


def _type_doc(nom):
    for prefixe, label in TYPES_PDF:
        if nom.lower().startswith(prefixe):
            return label
    return "Autres"


def _lire_meta():
    try:
        if META_FILE.exists():
            return json.loads(META_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        pass
    return {}


def _ecrire_meta(meta):
    try:
        DOCS_DIR.mkdir(parents=True, exist_ok=True)
        META_FILE.write_text(
            json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    except OSError:
        pass


def _lister_documents():
    docs = []
    if not DOCS_DIR.exists():
        return docs
    for p in sorted(DOCS_DIR.rglob("*.pdf")):
        try:
            st = p.stat()
        except OSError:
            continue
        docs.append({
            "path": str(p),
            "nom": p.name,
            "dossier": p.parent.name,
            "type": _type_doc(p.name),
            "taille": st.st_size,
            "date": datetime.datetime.fromtimestamp(st.st_mtime),
        })
    return docs


def _normaliser(texte):
    return "".join(c if c.isalnum() else "_" for c in (texte or "").lower())


def _taille_fr(n):
    if n < 1024:
        return f"{n} o"
    if n < 1024 * 1024:
        return f"{n / 1024:.1f} Ko"
    return f"{n / (1024 * 1024):.1f} Mo"


def _cibler(doc, eleves_par_matricule, classes_norm):
    """Retrouve l'eleve (recus/certificats) ou la classe (bulletins/
    plannings) d'un document a partir de son nom de fichier."""
    base = doc["nom"][:-4]
    bas = doc["nom"].lower()
    if bas.startswith("recu_") or bas.startswith("certificat_"):
        morceaux = base.split("_")
        if len(morceaux) >= 2:
            matricule = morceaux[1]
            label = eleves_par_matricule.get(matricule)
            if label:
                return label
            return matricule
    if bas.startswith("bulletins_") or bas.startswith("planning_"):
        partie = base.split("_", 1)[1] if "_" in base else ""
        meilleur = ""
        meilleure_longueur = 0
        for norm, affiche in classes_norm.items():
            if partie.startswith(norm) and len(norm) > meilleure_longueur:
                meilleur = affiche
                meilleure_longueur = len(norm)
        if meilleur:
            return meilleur
        return partie.replace("_", " ") or doc["type"]
    return ""


def _dialogue_eleve(parent, eleves, titre):
    """Dialogue de choix d'un eleve (avec filtre de recherche). Renvoie
    l'id de l'eleve, None si « Aucun eleve », ou `_ANNULE` si annule."""
    dlg = QDialog(parent)
    dlg.setWindowTitle(titre)
    dlg.setMinimumSize(460, 170)
    dlg.setStyleSheet(f"QDialog {{ {C_AURORA} }}")
    lay = QVBoxLayout(dlg)
    fon = QFormLayout()
    cherche = QLineEdit()
    cherche.setPlaceholderText("Filtrer par nom, prenom, matricule ou classe...")
    combo = QComboBox()

    def _remplir():
        mot = cherche.text().strip().lower()
        combo.blockSignals(True)
        combo.clear()
        combo.addItem("Aucun eleve (retirer l'affectation)", None)
        for e in eleves:
            ligne = (f"{e['prenom']} {e['nom']}"
                     f" - {e.get('classe_nom') or 'sans classe'}"
                     f" ({e['matricule']})")
            if mot and mot not in ligne.lower():
                continue
            combo.addItem(ligne, e["id"])
        combo.blockSignals(False)

    cherche.textEdited.connect(lambda _t: _remplir())
    _remplir()
    fon.addRow("Rechercher :", cherche)
    fon.addRow("Eleve :", combo)
    lay.addLayout(fon)
    boutons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
    boutons.rejected.connect(dlg.reject)
    lay.addWidget(boutons)
    boutons.button(QDialogButtonBox.Ok).setStyleSheet(STYLE_BTN_PRIMARY)
    boutons.button(QDialogButtonBox.Cancel).setStyleSheet(STYLE_BTN_SECONDARY)
    boutons.accepted.connect(dlg.accept)
    dlg.exec_()
    if dlg.result() == QDialog.Accepted:
        return combo.currentData()
    return _ANNULE


def _dialogue_dossier(parent, titre):
    """Choix d'un sous-dossier existant, ou de la racine des documents.
    Renvoie None pour la racine, le nom du sous-dossier, ou `_ANNULE`."""
    sous_dossiers = sorted(
        p.name for p in DOCS_DIR.iterdir() if p.is_dir()) if DOCS_DIR.exists() else []
    dlg = QDialog(parent)
    dlg.setWindowTitle(titre)
    dlg.setMinimumSize(380, 150)
    dlg.setStyleSheet(f"QDialog {{ {C_AURORA} }}")
    lay = QVBoxLayout(dlg)
    form = QFormLayout()
    combo = QComboBox()
    combo.addItem("Racine des documents", None)
    for nom in sous_dossiers:
        combo.addItem(nom, nom)
    form.addRow("Dossier :", combo)
    lay.addLayout(form)
    boutons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
    boutons.rejected.connect(dlg.reject)
    lay.addWidget(boutons)
    boutons.button(QDialogButtonBox.Ok).setStyleSheet(STYLE_BTN_PRIMARY)
    boutons.button(QDialogButtonBox.Cancel).setStyleSheet(STYLE_BTN_SECONDARY)
    boutons.accepted.connect(dlg.accept)
    dlg.exec_()
    if dlg.result() == QDialog.Accepted:
        return combo.currentData()
    return _ANNULE


def documents(page, ctx):
    if page.layout() is not None:
        return

    lay = QVBoxLayout(page)
    lay.setContentsMargins(20, 20, 20, 20)
    lay.setSpacing(14)

    titre = PageHeader(
        "Espace Documents",
        "Tous les PDF generes : bulletins, recus, certificats, plannings, paie.")
    lay.addWidget(titre)

    barre = QHBoxLayout()
    barre.setSpacing(10)
    combo_cat = QComboBox()
    combo_cat.addItem("Tous les types", None)
    for _p, label in TYPES_PDF:
        combo_cat.addItem(label, label)
    combo_cat.addItem("Autres", "Autres")
    combo_cat.setMinimumWidth(160)

    combo_tri = QComboBox()
    combo_tri.addItem("Plus recents", "date")
    combo_tri.addItem("Nom du document", "nom")
    combo_tri.addItem("Plus volumineux", "taille")
    combo_tri.setMinimumWidth(150)

    combo_eleve = QComboBox()
    combo_eleve.addItem("Tous les eleves / classes", None)
    combo_eleve.setMinimumWidth(190)

    rechercher = QLineEdit()
    rechercher.setPlaceholderText("Rechercher un document...")
    rechercher.setClearButtonEnabled(True)

    lbl_infos = QLabel()
    lbl_infos.setStyleSheet(f"color: {C_TEXT_SECONDARY}; font-size: 12px;")
    lbl_infos.setMinimumWidth(170)

    barre.addWidget(combo_cat)
    barre.addWidget(combo_tri)
    barre.addWidget(combo_eleve)
    barre.addWidget(rechercher, 1)
    barre.addWidget(lbl_infos)
    lay.addLayout(barre)

    table = DataTable()
    table.setColumnCount(6)
    table.setHorizontalHeaderLabels(
        ["Document", "Type", "Eleve / Classe", "Date", "Taille", "Actions"])
    vide = EmptyState("Aucun document",
                      "Les PDF generes (bulletins, recus, certificats...) "
                      "apparaitront ici.")
    pile = QStackedWidget()
    pile.addWidget(table)
    pile.addWidget(vide)
    lay.addWidget(pile, 1)

    def _document_selectionne(action):
        index = table.currentRow()
        current_rows = rows  # Copie locale pour eviter race condition
        if not (0 <= index < len(current_rows)):
            QMessageBox.warning(
                page, action,
                "Selectionnez d'abord un document dans la liste.")
            return None
        return current_rows[index]

    def _ouvrir_dossier():
        if not DOCS_DIR.exists():
            QMessageBox.warning(page, "Documents",
                                "Le dossier des documents n'existe pas encore.")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(DOCS_DIR)))

    def _dossier_destination():
        dossier = QFileDialog.getExistingDirectory(
            page, "Exporter vers un dossier",
            str(Path.home() / "Documents"))
        return dossier or None

    def _exporter():
        dossier = _dossier_destination()
        if not dossier:
            return
        exportes = 0
        for d in rows:
            try:
                shutil.copy2(d["path"], Path(dossier) / d["nom"])
                exportes += 1
            except OSError as exc:
                QMessageBox.warning(page, "Export", f"{d['nom']} : {exc}")
        toast.succes(
            page, f"{exportes} document(s) exporte(s) vers {dossier}.")

    def _exporter_selection():
        d = _document_selectionne("Exporter")
        if d is None:
            return
        dossier = _dossier_destination()
        if not dossier:
            return
        try:
            shutil.copy2(d["path"], Path(dossier) / d["nom"])
            toast.succes(page, f"Exporte vers {dossier}.")
        except OSError as exc:
            QMessageBox.warning(page, "Export", f"{d['nom']} : {exc}")

    def _supprimer():
        d = _document_selectionne("Supprimer")
        if d is None:
            return
        if not confirmer(page,
                         f"Supprimer definitivement « {d['nom']} » ?",
                         "Documents"):
            return
        try:
            Path(d["path"]).unlink()
        except OSError as exc:
            QMessageBox.warning(page, "Supprimer", str(exc))
            return
        meta = _lire_meta()
        if d["nom"] in meta.get("eleves", {}):
            del meta["eleves"][d["nom"]]
            _ecrire_meta(meta)
        toast.succes(page, "Document supprime.")
        rafraichir()

    def _ouvrir():
        d = _document_selectionne("Ouvrir")
        if d is None:
            return
        ok = QDesktopServices.openUrl(QUrl.fromLocalFile(d["path"]))
        if not ok:
            QMessageBox.warning(page, "Ouvrir",
                                f"Impossible d'ouvrir {d['nom']} (fichier introuvable ?)")

    def _renommer():
        d = _document_selectionne("Renommer")
        if d is None:
            return
        nom, ok = QInputDialog.getText(page, "Renommer",
                                       "Nouveau nom du document :",
                                       text=d["nom"])
        if not ok:
            return
        nom = nom.strip()
        if not nom or nom.lower() == d["nom"].lower():
            return
        if "/" in nom or "\\" in nom:
            QMessageBox.warning(page, "Renommer",
                                "Le nom ne peut pas contenir de separateur de dossier.")
            return
        if not nom.lower().endswith(".pdf"):
            nom += ".pdf"
        cible = Path(d["path"]).parent / nom
        if cible.exists():
            QMessageBox.warning(page, "Renommer",
                                "Un document porte deja ce nom.")
            return
        try:
            Path(d["path"]).rename(cible)
        except OSError as exc:
            QMessageBox.warning(page, "Renommer", str(exc))
            return
        meta = _lire_meta()
        if d["nom"] in meta.get("eleves", {}):
            meta["eleves"][nom] = meta["eleves"].pop(d["nom"])
            _ecrire_meta(meta)
        toast.succes(page, "Document renomme.")
        rafraichir()

    def _affecter():
        d = _document_selectionne("Affecter a un eleve")
        if d is None:
            return
        eleve_id = _dialogue_eleve(page, eleves, f"Affecter « {d['nom']} »")
        if eleve_id is _ANNULE:
            return
        meta = _lire_meta()
        affectations = meta.setdefault("eleves", {})
        if d["nom"] in affectations:
            del affectations[d["nom"]]
        if eleve_id:
            affectations[d["nom"]] = eleve_id
        _ecrire_meta(meta)
        toast.succes(page,
                     "Affectation mise a jour."
                     if eleve_id else "Affectation retiree.")
        rafraichir()

    def _nouveau_dossier():
        nom, ok = QInputDialog.getText(
            page, "Nouveau dossier", "Nom du dossier :")
        if not ok:
            return
        nom = nom.strip()
        if not nom:
            return
        cible = DOCS_DIR / nom
        try:
            cible.mkdir(parents=True, exist_ok=False)
            toast.succes(page, f"Dossier « {nom} » cree.")
        except FileExistsError:
            QMessageBox.warning(page, "Nouveau dossier",
                                "Ce dossier existe deja.")
        except OSError as exc:
            QMessageBox.warning(page, "Nouveau dossier", str(exc))

    def _deplacer():
        d = _document_selectionne("Deplacer")
        if d is None:
            return
        sous_dossier = _dialogue_dossier(page, f"Deplacer « {d['nom']} »")
        if sous_dossier is _ANNULE:
            return
        cible = DOCS_DIR if sous_dossier is None else DOCS_DIR / sous_dossier
        if Path(d["path"]).parent == cible:
            return
        try:
            cible.mkdir(parents=True, exist_ok=True)
            shutil.move(d["path"], cible / d["nom"])
            toast.succes(page, "Document deplace.")
        except OSError as exc:
            QMessageBox.warning(page, "Deplacer", str(exc))
        rafraichir()

    def _organiser():
        deplaces = 0
        for d in _lister_documents():
            dossier_type = DOCS_DIR / d["type"]
            if Path(d["path"]).parent == dossier_type:
                continue
            try:
                dossier_type.mkdir(parents=True, exist_ok=True)
                shutil.move(d["path"], dossier_type / d["nom"])
                deplaces += 1
            except OSError as exc:
                QMessageBox.warning(page, "Organiser",
                                    f"{d['nom']} : {exc} | {d['type']}")
        toast.succes(page,
                     f"{deplaces} document(s) ranges dans des sous-dossiers.")
        rafraichir()

    eleves = repos.eleves()
    eleves_par_matricule = {}
    eleves_par_id = {}
    for e in eleves:
        if e.get("matricule"):
            eleves_par_matricule[e["matricule"]] = (
                f"{e.get('prenom', '')} {e.get('nom', '')} ({e['matricule']})")
        eleves_par_id[e["id"]] = (
            f"{e.get('prenom', '')} {e.get('nom', '')} ({e.get('matricule', '')})")
    classes_norm = {}
    for c in repos.classes():
        classes_norm[_normaliser(c["nom"])] = c["nom"]

    rows = []

    def rafraichir():
        nonlocal rows
        meta = _lire_meta()
        affectations = meta.get("eleves", {})
        docs = _lister_documents()
        for d in docs:
            eleve_id = affectations.get(d["nom"])
            if eleve_id is not None:
                d["cible"] = (eleves_par_id.get(eleve_id)
                              or f"Eleve (sans dossier, id {eleve_id})")
            else:
                d["cible"] = _cibler(d, eleves_par_matricule, classes_norm)
        filtre_cat = combo_cat.currentData()
        filtre_eleve = combo_eleve.currentData()
        mot = rechercher.text().strip().lower()
        rows = []
        cibles_eleves = set()
        for d in docs:
            if filtre_cat and d["type"] != filtre_cat:
                continue
            if filtre_eleve and d["cible"] != filtre_eleve:
                continue
            if mot and mot not in (d["nom"] + " " + d["cible"]).lower():
                continue
            rows.append(d)
            if d["cible"]:
                cibles_eleves.add(d["cible"])
        tri = combo_tri.currentData()
        if tri == "nom":
            rows.sort(key=lambda d: d["nom"].lower())
        elif tri == "taille":
            rows.sort(key=lambda d: d["taille"], reverse=True)
        else:
            rows.sort(key=lambda d: d["date"], reverse=True)

        ancien_eleve = combo_eleve.currentData()
        combo_eleve.blockSignals(True)
        combo_eleve.clear()
        combo_eleve.addItem("Tous les eleves / classes", None)
        for cible in sorted(cibles_eleves):
            combo_eleve.addItem(cible, cible)
        if ancien_eleve in cibles_eleves:
            combo_eleve.setCurrentText(ancien_eleve)
        combo_eleve.blockSignals(False)

        valeurs = []
        for d in rows:
            valeurs.append([
                d["nom"], d["type"], d["cible"] or "-",
                d["date"].strftime("%d/%m/%Y %H:%M"),
                _taille_fr(d["taille"]), ""])
        table.remplir(valeurs)
        for i, d in enumerate(rows):
            table.setCellWidget(i, 5, _actions_cell(
                _btn("Ouvrir", _ouvrir,
                     _simple_btn_style(bg=C_BG_SOFT, fg=C_TEXT_SECONDARY,
                                       border=C_BORDER)),
                _btn("Renommer", _renommer,
                     _simple_btn_style(bg=C_BG_SOFT, fg=C_TEXT_SECONDARY,
                                       border=C_BORDER)),
                _btn("Affecter", _affecter,
                     _simple_btn_style(bg=C_BG_SOFT, fg=C_TEXT_SECONDARY,
                                       border=C_BORDER)),
                _btn("Supprimer", _supprimer,
                     _simple_btn_style(bg=C_RED_BG, fg=C_RED,
                                       border=C_RED_BORDER))))
        pile.setCurrentWidget(vide if not rows else table)
        total = sum(d["taille"] for d in rows)
        lbl_infos.setText(f"{len(rows)} document(s) - {_taille_fr(total)}")
        table.horizontalHeader().setStretchLastSection(True)

    actions = QHBoxLayout()
    actions.setSpacing(10)
    actions.addWidget(_btn("Ouvrir le dossier", _ouvrir_dossier,
                           _simple_btn_style(bg=C_BG_SOFT, fg=C_TEXT_SECONDARY,
                                             border=C_BORDER)))
    actions.addWidget(_btn("Nouveau dossier", _nouveau_dossier,
                           _simple_btn_style(bg=C_BG_SOFT, fg=C_TEXT_SECONDARY,
border=C_BORDER)))
    actions.addWidget(_btn("Deplacer vers...", _deplacer,
                           _simple_btn_style(bg=C_BG_SOFT, fg=C_TEXT_SECONDARY,
                                             border=C_BORDER)))
    actions.addWidget(_btn("Organiser en dossiers", _organiser,
                           _simple_btn_style(bg=C_PRIMARY_LIGHT, fg=C_PRIMARY,
                                             border=C_BORDER)))
    if ctx.role == "directeur":
        def _ouvrir_modeles():
            from ui.pages.modeles_documents import ouvrir_modeles
            ouvrir_modeles(page, ctx)
        actions.addWidget(_btn("Modeles de documents...", _ouvrir_modeles,
                               _simple_btn_style(bg=C_PRIMARY_LIGHT, fg=C_PRIMARY,
                                                 border=C_BORDER)))
    actions.addStretch(1)
    actions.addWidget(_btn("Actualiser", rafraichir, _simple_btn_style(
        bg=C_BG_SOFT, fg=C_TEXT_SECONDARY, border=C_BORDER)))
    lay.addLayout(actions)

    actions2 = QHBoxLayout()
    actions2.setSpacing(10)
    actions2.addWidget(_btn("Renommer la selection", _renommer,
                            _simple_btn_style(bg=C_PRIMARY_LIGHT, fg=C_PRIMARY,
                                              border=C_BORDER)))
    actions2.addWidget(_btn("Affecter a un eleve", _affecter,
                            _simple_btn_style(bg=C_PRIMARY_LIGHT, fg=C_PRIMARY,
                                              border=C_BORDER)))
    actions2.addWidget(_btn("Exporter la selection", _exporter_selection,
                            _simple_btn_style(bg=C_BG_SOFT, fg=C_TEXT_SECONDARY,
                                              border=C_BORDER)))
    actions2.addWidget(_btn("Exporter tout...", _exporter,
                            _simple_btn_style(bg=C_BG_SOFT, fg=C_TEXT_SECONDARY,
                                              border=C_BORDER)))
    lay.addLayout(actions2)

    table.doubleClicked.connect(lambda _i: _ouvrir())
    combo_cat.currentIndexChanged.connect(rafraichir)
    combo_tri.currentIndexChanged.connect(rafraichir)
    combo_eleve.currentIndexChanged.connect(rafraichir)
    rechercher.textChanged.connect(rafraichir)

    rafraichir()
    page.refresh = rafraichir