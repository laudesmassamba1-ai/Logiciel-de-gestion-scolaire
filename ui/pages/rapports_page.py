"""Page « Rapports PDF » : centre de rapports.

Des syntheses structurees de toute la base (effectifs, etat des eleves,
bilan financier, presences, moyennes, personnel, chiffres des
statistiques) exportees en PDF avec l'habillage officiel de l'ecole.
Chaque PDF atterrit dans l'Espace Documents et s'ouvre automatiquement.
"""

from PyQt5.QtCore import QDate, Qt
from PyQt5.QtWidgets import (
    QComboBox, QDateEdit, QFrame, QHBoxLayout, QLabel, QMessageBox,
    QScrollArea, QVBoxLayout, QWidget,
)

from core.config import (
    C_BG, C_BORDER, C_PRIMARY, C_PRIMARY_LIGHT, C_TEXT_SECONDARY,
    STYLE_CHART_CARD, STYLE_SCROLL,
)
from repositories import repos
from services import rapports
from ui import toast
from ui.pages.helpers import _btn, _page_header, _simple_btn_style


RAPPORTS = [
    ("rapport_synthese", "Synthese generale de l'etablissement"),
    ("rapport_effectifs", "Effectifs par classe"),
    ("rapport_eleves", "Etat des eleves"),
    ("rapport_finance", "Bilan financier"),
    ("rapport_presences", "Feuille de presence"),
    ("rapport_moyennes", "Moyennes par classe"),
    ("rapport_personnel", "Personnel et salaires"),
    ("rapport_statistiques", "Chiffres des statistiques"),
]


def rapports_page(page, ctx):
    if page.layout() is not None:
        return
    page.setStyleSheet(f"background-color: {C_BG};")
    lay = QVBoxLayout(page)
    lay.setContentsMargins(20, 20, 20, 20)
    lay.setSpacing(16)
    _page_header(lay, "Rapports PDF")

    # ---------- Filtres communs ----------
    cadre_filtres = QFrame()
    cadre_filtres.setStyleSheet(STYLE_CHART_CARD)
    fl = QHBoxLayout(cadre_filtres)
    fl.setContentsMargins(15, 12, 15, 12)
    fl.setSpacing(8)

    combo_classe = QComboBox()
    combo_classe.addItem("Toutes les classes", None)
    for c in repos.classes():
        combo_classe.addItem(c["nom"], c["id"])
    combo_periode = QComboBox()
    combo_periode.addItems(["T1", "T2", "T3", "Annuel"])
    date_pres = QDateEdit()
    date_pres.setDisplayFormat("dd/MM/yyyy")
    date_pres.setCalendarPopup(True)
    date_pres.setDate(QDate.currentDate())

    for lbl, w in (("Classe :", combo_classe), ("Periode :", combo_periode),
                   ("Presences le :", date_pres)):
        et = QLabel(lbl)
        et.setStyleSheet(f"color:{C_TEXT_SECONDARY};font-size:13px;")
        fl.addWidget(et)
        fl.addWidget(w)
    fl.addStretch(1)
    lay.addWidget(cadre_filtres)

    # ---------- Liste des rapports ----------
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setStyleSheet(STYLE_SCROLL)
    conteneur = QWidget()
    cont = QVBoxLayout(conteneur)
    cont.setSpacing(12)

    def _generer(nom_rapport):
        fn = getattr(rapports, nom_rapport, None)
        if fn is None:
            return
        classe_id = combo_classe.currentData()
        periode = combo_periode.currentText()
        date = date_pres.date().toString("yyyy-MM-dd")
        try:
            if nom_rapport == "rapport_presences":
                if classe_id is None:
                    chemin = fn(ouvrir=False)
                else:
                    chemin = fn(classe_id=classe_id, date=date, ouvrir=False)
            elif nom_rapport in ("rapport_effectifs", "rapport_eleves",
                                 "rapport_finance"):
                chemin = fn(classe_id=classe_id, ouvrir=False)
            elif nom_rapport == "rapport_moyennes":
                chemin = fn(classe_id=classe_id, periode=periode, ouvrir=False)
            else:
                chemin = fn(ouvrir=False)
            if not chemin:
                QMessageBox.information(page, "Rapport",
                                        "Rien a exporter : le jeu de donnees "
                                        "est vide pour ces filtres.")
                return
            toast.succes(page, "Rapport genere dans l'Espace Documents.")
            rapports._ouvrir_pdf(chemin)
        except Exception as exc:
            QMessageBox.warning(page, "Rapport",
                                f"Erreur pendant la generation : {exc}")

    for nom, titre in RAPPORTS:
        cadre = QFrame()
        cadre.setStyleSheet(STYLE_CHART_CARD)
        cl = QHBoxLayout(cadre)
        cl.setContentsMargins(15, 12, 15, 12)
        cl.setSpacing(12)
        texte = QVBoxLayout()
        texte.setSpacing(2)
        t = QLabel(titre)
        t.setStyleSheet("font-size:14px;font-weight:600;")
        texte.addWidget(t)
        cl.addLayout(texte, 1)
        cl.addWidget(_btn("Generer PDF", lambda *_, n=nom: _generer(n),
                          _simple_btn_style(bg=C_PRIMARY_LIGHT, fg=C_PRIMARY,
                                            border=C_BORDER)))
        cont.addWidget(cadre)

    cont.addStretch(1)
    scroll.setWidget(conteneur)
    lay.addWidget(scroll, 1)

    page.refresh = lambda: None