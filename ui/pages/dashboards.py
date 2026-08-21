import datetime

from PyQt5.QtWidgets import (
    QHBoxLayout, QLabel, QTableWidgetItem, QVBoxLayout,
)

from api import client
from repositories import repos
from services import auth_service as auth, reports
from ui.loader import apply_ui
from ui.pages.helpers import (
    _btn, _simple_btn_style, _today_fr, _replace_layout, _classe_items,
)
from ui.widgets import SimpleBarChart, SimplePieChart, fmt_money
from ui.workers import run_async


def dashboard_directeur(page, ctx):
    if page.layout() is not None:
        return
    apply_ui("dashboards/dashboard_admin.ui", page)

    def refresh():
        comptes = repos.utilisateurs()
        actifs = [c for c in comptes if c["actif"]]
        inactifs = [c for c in comptes if not c["actif"]]
        directeurs = [c for c in actifs if c["role"] == "directeur"]
        gestionnaires = [c for c in actifs if c["role"] == "gestionnaire"]
        page.lbl_kpi1_valeur.setText(str(len(actifs)))
        page.lbl_kpi2_valeur.setText(str(len(directeurs)))
        page.lbl_kpi3_valeur.setText(str(len(gestionnaires)))
        page.lbl_kpi4_valeur.setText(str(len(inactifs)))
        logs = auth.derniere_connexions()
        page.list_dernieres_connexions.clear()
        for log in logs:
            page.list_dernieres_connexions.addItem(
                f"{log['date_connexion']}  -  {log['nom_complet']} ({log['role']})")
        page.lbl_activite_empty.setVisible(not logs)

    from ui.pages.comptes_page import open_compte_dialog, open_reset_password_dialog

    page.btn_quick_nouveau_compte.clicked.connect(
        lambda: open_compte_dialog(page, ctx))
    page.btn_goto_comptes.clicked.connect(lambda: ctx.navigate("comptes"))
    page.btn_reset_password.clicked.connect(
        lambda: open_reset_password_dialog(page, ctx))

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

    page.btn_quick_inscrire.clicked.connect(
        lambda: open_inscription_dialog(page, ctx))
    page.btn_quick_recette.clicked.connect(
        lambda: open_transaction_dialog(page, ctx, "entree"))
    page.btn_quick_depense.clicked.connect(
        lambda: open_transaction_dialog(page, ctx, "sortie"))
    page.btn_quick_certificat.clicked.connect(
        lambda: open_certificat_dialog(page))

    refresh()
    page.refresh = refresh
