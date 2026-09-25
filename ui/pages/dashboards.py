import datetime

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QGridLayout, QHBoxLayout, QLabel, QTableWidgetItem, QVBoxLayout,
    QSizePolicy,
)

from api import client
from core.config import (
    C_AURORA, C_BLUE, C_BLUE_HOVER, C_BLUE_PRESSED, C_RED, C_WARNING,
    C_ACCENT_VIOLET,
    C_CARD, ROLE_LABELS, STYLE_TABLE,
    STYLE_BTN_PRIMARY, STYLE_BTN_SECONDARY, STYLE_BTN_DANGER,
)
from repositories import repos
from services import auth_service as auth, reports
from ui import motion
from ui.loader import apply_ui
from ui.pages.helpers import (
    _btn, _simple_btn_style, _today_fr, _replace_layout,
    _styler_carte,
)
from ui.widgets import SimpleBarChart, SimplePieChart, fmt_money
from ui.workers import run_async


_STYLE_RECETTE = (
    f"QPushButton {{ background: {C_BLUE}; color: {C_CARD}; border: none;"
    f" border-radius: 12px; padding: 10px 18px; font-weight: 700; font-size: 13px; }}"
    f" QPushButton:hover {{ background: {C_BLUE_HOVER}; }}"
    f" QPushButton:pressed {{ background: {C_BLUE_PRESSED}; }}"
)


# Cartes KPI « chiffre + libelle » : hauteur bornee pour ne jamais
# s'etirer verticalement. (Les cartes de contenu - activite, graphiques,
# actions rapides - ne sont pas concernees.)
_CARTES_KPI = {
    "card_total_comptes", "card_directeurs", "card_gestionnaires",
    "card_comptes_inactifs", "card_effectifs", "card_inscriptions_jour",
    "card_caisse_jour", "card_taches",
}


def _styler_dashboard(page, cartes):
    """Style moderne des cartes (coeurs uniformes, hairline 1px, sans
    bande d'accent) puis apparitions echelonnees a l'ouverture du tableau
    de bord."""
    for nom, accent in cartes:
        w = getattr(page, nom, None)
        if w is None:
            continue
        _styler_carte(w, accent)
        if nom in _CARTES_KPI:
            w.setMaximumHeight(94)
            w.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
    page.setStyleSheet(C_AURORA)
    for nom, style in (
        ("btn_quick_nouveau_compte", STYLE_BTN_PRIMARY),
        ("btn_goto_comptes", STYLE_BTN_SECONDARY),
        ("btn_reset_password", STYLE_BTN_DANGER),
        ("btn_goto_personnel", STYLE_BTN_SECONDARY),
        ("btn_quick_inscrire", STYLE_BTN_PRIMARY),
        ("btn_quick_recette", _STYLE_RECETTE),
        ("btn_quick_depense", STYLE_BTN_DANGER),
        ("btn_quick_certificat", STYLE_BTN_SECONDARY),
    ):
        btn = getattr(page, nom, None)
        if btn is not None:
            btn.setStyleSheet(style)
    motion.stagger([getattr(page, nom, None) for nom, _accent in cartes],
                   au_total=440, duree=320)


KRPI_ADMIN = [
    ("card_total_comptes", C_ACCENT_VIOLET),
    ("card_directeurs", C_BLUE),
    ("card_gestionnaires", C_RED),
    ("card_comptes_inactifs", C_WARNING),
    ("card_activite", C_BLUE),
]

KRPI_GESTIONNAIRE = [
    ("card_effectifs", C_BLUE),
    ("card_inscriptions_jour", C_BLUE),
    ("card_caisse_jour", C_RED),
    ("card_taches", C_WARNING),
    ("container_chart_statuts", C_BLUE),
    ("card_actions_rapides", C_ACCENT_VIOLET),
    ("card_activite", C_BLUE),
    ("card_dossiers_incomplets", C_RED),
]


def dashboard_directeur(page, ctx):
    """Tableau de bord directeur — gabarit DashboardPageTemplate.

    POINT DE CONTROLE de la refonte : construit ENTIEREMENT depuis les
    composants reutilisables (KPICard, DataTable, EmptyState, PageHeader),
    aucun .ui, aucun stylesheet eparpille.
    """
    if page.layout() is not None:
        return

    from qfluentwidgets import CardWidget
    from resources.design_tokens import Colors, Spacing
    from ui.widgets import (
        DataTable, EmptyState, KPICard, fmt_money,
    )
    from ui.widgets.page_templates import DashboardPageTemplate

    tpl = DashboardPageTemplate(
        page, "Tableau de bord")

    kpi = [
        tpl.ajouter_kpi(KPICard("Comptes actifs", "0", Colors.PRIMARY), 0),
        tpl.ajouter_kpi(KPICard("Directeurs", "0", Colors.INFO), 1),
        tpl.ajouter_kpi(KPICard("Gestionnaires", "0", Colors.DANGER), 2),
        tpl.ajouter_kpi(KPICard("Comptes inactifs", "0", Colors.WARNING), 3),
    ]

    def _carte(titre):
        carte = CardWidget()
        carte.setBorderRadius(16)
        carte.setContentsMargins(12, 8, 12, 8)
        lbl = QLabel(titre)
        lbl.setStyleSheet(
            f"color: {Colors.TEXT_PRIMARY}; font-size: 14px; font-weight: 700;"
            " border: none; background: transparent;")
        v = QVBoxLayout(carte)
        v.setContentsMargins(16, 10, 16, 12)
        v.setSpacing(8)
        v.addWidget(lbl)
        return carte, v

    # --- Actions rapides + dernieres connexions (rangee haute) ------
    rang1 = QHBoxLayout()
    rang1.setSpacing(Spacing.MD)

    carte_actions, v_actions = _carte("Actions rapides")
    btns = [
        _btn("+ Nouveau Compte", lambda: _ouvrir_compte(), STYLE_BTN_PRIMARY),
        _btn("Gerer les Comptes", lambda: ctx.navigate("comptes"), STYLE_BTN_SECONDARY),
        _btn("Reinitialiser Mot de Passe", lambda: _ouvrir_reset(), STYLE_BTN_DANGER),
    ]
    grille_actions = QGridLayout()
    grille_actions.setSpacing(Spacing.SM)
    for i, b in enumerate(btns):
        grille_actions.addWidget(b, i // 2, i % 2)
    v_actions.addLayout(grille_actions)
    v_actions.addStretch(1)
    rang1.addWidget(carte_actions, 1)

    carte_connex, v_connex = _carte("Dernieres connexions")
    table = DataTable()
    table.setColumnCount(3)
    table.setHorizontalHeaderLabels(["Nom", "Role", "Date de connexion"])
    vide = EmptyState("Aucune connexion enregistree",
                      icone="fa5s.history", hauteur=140)
    v_connex.addWidget(table)
    v_connex.addWidget(vide)
    rang1.addWidget(carte_connex, 2)
    tpl.contenu.addLayout(rang1, 1)

    # --- Graphiques (rangee basse) ---------------------------------
    rang2 = QHBoxLayout()
    rang2.setSpacing(Spacing.MD)
    charts = []
    for titre_chart, cle in (
        ("Flux financier par mois", "fin"),
        ("Effectifs par classe", "scol"),
        ("Personnel par statut", "pers"),
    ):
        carte_chart, v_chart = _carte(titre_chart)
        c = SimpleBarChart()
        c.set_data([], [])
        v_chart.addWidget(c)
        charts.append((cle, c))
        rang2.addWidget(carte_chart, 1)
    tpl.contenu.addLayout(rang2, 1)

    def _charters():
        data = _directeur_charts()
        charts[0][1].set_data(data["fin_labels"], data["fin_values"])
        charts[1][1].set_data(data["scol_labels"], data["scol_values"])
        statuts = {}
        for p in repos.personnel():
            s = p["statut"] or "Autre"
            statuts[s] = statuts.get(s, 0) + 1
        charts[2][1].set_data(list(statuts.keys()), list(statuts.values()))

    def refresh():
        comptes = repos.utilisateurs()
        actifs = [c for c in comptes if c["actif"]]
        inactifs = [c for c in comptes if not c["actif"]]
        directeurs = [c for c in actifs if c["role"] == "directeur"]
        gestionnaires = [c for c in actifs if c["role"] == "gestionnaire"]
        kpi[0].set_value(len(actifs))
        kpi[1].set_value(len(directeurs))
        kpi[2].set_value(len(gestionnaires))
        kpi[3].set_value(len(inactifs))

        logs = auth.derniere_connexions()
        if logs:
            table.remplir([
                [l["nom_complet"], ROLE_LABELS.get(l["role"], l["role"]),
                 l["date_connexion"]]
                for l in logs[:12]
            ], largeurs=[220, 150, 180])
            table.setVisible(True)
            vide.setVisible(False)
        else:
            table.setVisible(False)
            vide.setVisible(True)
        _charters()

    from ui.pages.comptes_page import open_compte_dialog, open_reset_password_dialog

    def _ouvrir_compte():
        open_compte_dialog(page, ctx)
        refresh()

    def _ouvrir_reset():
        open_reset_password_dialog(page, ctx)
        refresh()

    refresh()
    page.refresh = refresh


def _directeur_charts():
    rows = repos.transactions()
    active_year = repos.annee_scolaire_active()
    months = {}
    for r in rows:
        key = r["date"][:7]
        months.setdefault(key, 0)
        months[key] += r["montant"] if r["type"] == "entree" else -r["montant"]
    if active_year and active_year.get("date_debut"):
        start = datetime.date.fromisoformat(active_year["date_debut"])
        end = datetime.date.fromisoformat(active_year["date_fin"]) if active_year.get("date_fin") else datetime.date.today()
        month_count = min(12, max(1, (end.year - start.year) * 12 + end.month - start.month + 1))
        labels, values = [], []
        for i in range(month_count):
            d = datetime.date(start.year + (start.month + i - 1) // 12, (start.month + i - 1) % 12 + 1, 1)
            key = d.strftime("%Y-%m")
            labels.append(d.strftime("%b"))
            values.append(int(months.get(key, 0)))
    else:
        today = datetime.date.today()
        labels, values = [], []
        for i in range(5, -1, -1):
            d = today - datetime.timedelta(days=30 * i)
            key = d.strftime("%Y-%m")
            labels.append(d.strftime("%b"))
            values.append(int(months.get(key, 0)))
    classes = repos.classes()
    scol_labels = [c["nom"][:10] for c in classes[:6]]
    scol_values = [c["effectif"] for c in classes[:6]]
    return {"fin_labels": labels, "fin_values": values,
            "scol_labels": scol_labels, "scol_values": scol_values}


def dashboard_gestionnaire(page, ctx):
    if page.layout() is not None:
        return
    apply_ui("dashboards/dashboard_gestionnaire.ui", page)

    _styler_dashboard(page, KRPI_GESTIONNAIRE)

    lay_bas = getattr(page, "bottomLayout", None)
    if lay_bas is not None:
        from PyQt5.QtWidgets import QSplitter
        split = QSplitter(Qt.Horizontal)
        split.setObjectName("gestionnaireSplit")
        split.setHandleWidth(6)
        split.setChildrenCollapsible(False)
        split.addWidget(page.card_activite)
        split.addWidget(page.card_dossiers_incomplets)
        split.setStretchFactor(0, 1)
        split.setStretchFactor(1, 0)
        split.setSizes([620, 320])
        lay_bas.addWidget(split, 1)

    tokens = {"n": 0}

    def refresh():
        tokens["n"] += 1
        token = tokens["n"]
        page.lbl_date.setText(_today_fr())
        stats = repos.stats_dashboard()
        page.lbl_kpi1_valeur.setText(str(stats["total_eleves"]))
        page.lbl_kpi2_valeur.setText(str(stats["inscriptions_jour"]))
        page.lbl_kpi3_valeur.setText(fmt_money(stats["encaissements_jour"]))
        page.lbl_kpi4_valeur.setText(str(stats["dossiers_incomplets"]))

        def _on_eleves(result):
            if isinstance(result, Exception) or token != tokens["n"]:
                return
            total_api, _ = result if isinstance(result, tuple) else (None, None)
            if total_api is not None:
                page.lbl_kpi1_valeur.setText(str(total_api))

        run_async(client.total_eleves, _on_eleves)

        def _on_encaisse(result):
            if isinstance(result, Exception) or token != tokens["n"]:
                return
            enc_api, _ = result if isinstance(result, tuple) else (None, None)
            if enc_api is not None:
                page.lbl_kpi3_valeur.setText(fmt_money(float(enc_api)))

        run_async(client.total_montant_paiement, _on_encaisse)

        actifs = repos.transactions(recherche="")[:8]
        page.list_activite_recente.clear()
        for t in actifs:
            sens = "+" if t["type"] == "entree" else "-"
            page.list_activite_recente.addItem(
                f"{t['date']}  {t['motif']}  {sens}{fmt_money(t['montant'])}")
        page.lbl_activite_empty.setVisible(not actifs)

        # Une seule requete pour les dossiers incomplets et la repartition.
        tous_les_eleves = repos.eleves()
        incomplets = [e for e in tous_les_eleves
                      if not (e["check_acte"] and e["check_photos"] and e["check_bulletin"])]
        page.list_dossiers_incomplets.clear()
        for e in incomplets[:8]:
            manque = []
            if not e["check_acte"]:
                manque.append("acte")
            if not e["check_photos"]:
                manque.append("photos")
            if not e["check_bulletin"]:
                manque.append("bulletin")
            page.list_dossiers_incomplets.addItem(
                f"{e['prenom']} {e['nom']}  - manque: {', '.join(manque)}")

        def _render_statuts(source):
            if not hasattr(page, "layout_chart_statuts"):
                return
            statuts = {}
            for e in source:
                s = e.get("statut") or "inconnu"
                statuts[s] = statuts.get(s, 0) + 1
            chart = SimplePieChart(titre="Repartition des eleves par statut")
            chart.set_data(list(statuts.keys()), list(statuts.values()))
            _replace_layout(page.layout_chart_statuts, chart)

        _render_statuts(tous_les_eleves)

    from ui.pages.eleves import open_inscription_dialog
    from ui.pages.caisse_page import open_transaction_dialog
    from ui.pages.certificat_dialog import open_certificat_dialog

    def _ouvrir_inscrire():
        open_inscription_dialog(page, ctx)
        refresh()

    def _transaction(sens):
        open_transaction_dialog(page, ctx, sens)
        refresh()

    page.btn_quick_inscrire.clicked.connect(_ouvrir_inscrire)
    page.btn_quick_recette.clicked.connect(lambda: _transaction("entree"))
    page.btn_quick_depense.clicked.connect(lambda: _transaction("sortie"))
    page.btn_quick_certificat.clicked.connect(
        lambda: open_certificat_dialog(page))

    refresh()
    page.refresh = refresh
