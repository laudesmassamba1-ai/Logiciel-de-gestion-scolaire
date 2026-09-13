"""Gabrits de page — 3 seulement, reutilises par toutes les pages.

- ListPageTemplate       : PageHeader + barre de filtres + DataTable
                          (etat vide gere par le gabarit, pas la page)
- DashboardPageTemplate  : PageHeader + rangee de KPICard (QGridLayout)
                          + zone de contenu libre en dessous
- FormPageTemplate       : titre + champs groupes + boutons bas alignes droite

Les pages concretes heritent/remplissent un de ces gabarits et ne
fournissent que leur contenu specifique.
"""

from PyQt5.QtWidgets import (
    QGridLayout, QHBoxLayout, QLabel, QPushButton, QStackedWidget, QVBoxLayout,
    QWidget,
)

from resources.design_tokens import Colors, FontSize, Radius, Spacing


class _BaseTemplate:
    def __init__(self, widget, titre, sous_titre=""):
        self.page = widget
        lay = QVBoxLayout(widget)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(Spacing.MD)
        self._monter_entete(lay, titre, sous_titre)
        self._monter_contenu(lay)

    def _monter_entete(self, lay, titre, sous_titre):
        from .page_header import PageHeader
        self.header = PageHeader(titre, sous_titre)
        lay.addWidget(self.header)
        self.entete = lay

    def _monter_contenu(self, lay):
        raise NotImplementedError


class ListPageTemplate(_BaseTemplate):
    """Page liste : en-tete + filtres + tableau a hauteur-calculee.

    L'etat vide est gere par le gabarit (pile tableau/etat vide) : aucun
    controller ne doit penser a masquer/afficher un message a la main.
    """

    def _monter_contenu(self, lay):
        self._page_lay = lay
        self.kpi_grid = None
        self.filtre = QHBoxLayout()
        self.filtre.setSpacing(Spacing.SM)
        lay.addLayout(self.filtre)

        from .data_table import DataTable
        from .empty_state import EmptyState

        self.table = DataTable()
        self.vide = EmptyState("Aucune donnee", icone="fa5s.inbox")
        self.pile = QStackedWidget()
        self.pile.addWidget(self.table)
        self.pile.addWidget(self.vide)
        lay.addWidget(self.pile, 1)

    def ajouter_kpi(self, carte, colonne):
        """Rangee de KPICard optionnelle entre l'en-tete et les filtres."""
        if self.kpi_grid is None:
            self.kpi_grid = QGridLayout()
            self.kpi_grid.setSpacing(Spacing.MD)
            for _i in range(4):
                self.kpi_grid.setColumnStretch(_i, 1)
            self._page_lay.insertLayout(1, self.kpi_grid)
        self.kpi_grid.addWidget(carte, 0, colonne)
        return carte

    def ajouter_filtre(self, widget):
        self.filtre.addWidget(widget)

    def ajouter_space_filtre(self):
        self.filtre.addStretch(1)

    def remplir(self, valeurs, largeurs=None, stretch_index=None,
                message_vide="Aucune donnee a afficher",
                sous_titre_vide=""):
        self.table.remplir(valeurs, largeurs, stretch_index)
        vide = not valeurs
        self.pile.setCurrentWidget(self.vide if vide else self.table)
        if vide:
            self.vide.set_message(message_vide, sous_titre_vide)
        return self


class DashboardPageTemplate(_BaseTemplate):
    """Page tableau de bord : en-tete + grille de KPICard + contenu libre.

    Les cartes sont posees dans un QGridLayout (jamais un QHBoxLayout a
    la main) pour garder un alignement propre quel que soit leur nombre.
    """

    def _monter_contenu(self, lay):
        self.kpi_grid = QGridLayout()
        self.kpi_grid.setSpacing(Spacing.MD)
        for _i in range(4):
            self.kpi_grid.setColumnStretch(_i, 1)
        lay.addLayout(self.kpi_grid)

        self.contenu = QVBoxLayout()
        self.contenu.setSpacing(Spacing.MD)
        lay.addLayout(self.contenu, 1)

    def ajouter_kpi(self, carte, colonne):
        self.kpi_grid.addWidget(carte, 0, colonne)
        return carte

    def ajouter_contenu(self, widget, stretch=0):
        self.contenu.addWidget(widget, stretch)
        return widget


class FormPageTemplate(_BaseTemplate):
    """Page/dialogue formulaire : titre + sections de champs + boutons
    Annuler/Enregistrer alignes en bas a droite."""

    def _monter_contenu(self, lay):
        self.champs = QVBoxLayout()
        self.champs.setSpacing(Spacing.MD)
        lay.addLayout(self.champs)

        self._boutons = QHBoxLayout()
        self._boutons.addStretch(1)
        lay.addLayout(self._boutons)

        self.btn_annuler = QPushButton("Annuler")
        self.btn_enregistrer = QPushButton("Enregistrer")
        self.btn_annuler.setStyleSheet(
            f"QPushButton {{ background-color: {Colors.BG_SOFT};"
            f" color: {Colors.TEXT_SECONDARY}; border: 1px solid {Colors.BORDER};"
            f" border-radius: {Radius.MD}px; padding: 8px 18px; font-weight: 600; }}")
        self.btn_enregistrer.setStyleSheet(
            f"QPushButton {{ background-color: {Colors.PRIMARY}; color: #FFFFFF;"
            " border: none; border-radius: " + str(Radius.MD) + "px; padding: 8px 18px;"
            " font-weight: 700; }"
            f" QPushButton:hover {{ background-color: {Colors.PRIMARY_HOVER}; }}"
            f" QPushButton:pressed {{ background-color: {Colors.PRIMARY_PRESSED}; }}")
        self._boutons.addWidget(self.btn_annuler)
        self._boutons.addWidget(self.btn_enregistrer)

    def ajouter_section(self, titre):
        section = QVBoxLayout()
        section.setSpacing(Spacing.SM)
        lbl = QLabel(titre)
        lbl.setStyleSheet(
            f"font-size: {FontSize.SUBTITLE}px; font-weight: 700;"
            f" color: {Colors.PRIMARY}; border: none; background: transparent;")
        section.addWidget(lbl)
        self.champs.addLayout(section)
        return section