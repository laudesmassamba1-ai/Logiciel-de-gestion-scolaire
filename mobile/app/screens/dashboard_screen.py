from kivy.lang import Builder
from kivy.metrics import dp
from kivy.uix.gridlayout import GridLayout
from kivy.uix.screenmanager import Screen

from app.utils import format_int, format_montant, page_cols, page_cols_cards
from app.widgets import ListItem, SectionTitle, StatCard
from repositories import repos

Builder.load_string("""
<DashboardScreen>:
    canvas.before:
        Color:
            rgba: 0.945, 0.961, 0.973, 1
        Rectangle:
            pos: self.pos
            size: self.size
    BoxLayout:
        orientation: 'vertical'
        ScrollView:
            do_scroll_x: False
            BoxLayout:
                id: content
                orientation: 'vertical'
                size_hint_y: None
                height: max(self.parent.height, self.minimum_height)
                padding: 16, 16
                spacing: 14
                GridLayout:
                    id: cards_grid
                    cols: 2
                    size_hint_y: None
                    height: self.minimum_height
                    spacing: 12
                Label:
                    id: lbl_empty
                    text: 'Aucune donnee'
                    opacity: 0
                    size_hint_y: None
                    height: 0
""")


class DashboardScreen(Screen):
    def __init__(self, home=None, **kwargs):
        self.home = home
        super().__init__(**kwargs)

    def on_enter(self):
        self.refresh()

    def on_size(self, *args):
        self._apply_cols()

    def _apply_cols(self):
        if not hasattr(self, "ids"):
            return
        self.ids.cards_grid.cols = page_cols_cards(self.width)
        self.ids.cards_grid.size_hint_x = 1 if self.ids.cards_grid.cols > 1 else None
        self.ids.cards_grid.width = self.width - dp(32)

    def refresh(self):
        self._apply_cols()
        grid = self.ids.cards_grid
        grid.clear_widgets()

        stats = repos.stats_dashboard()
        entree, sortie, solde = repos.caisse_totals()
        enseignants = len(repos.enseignants())

        self._add_card(grid, "Eleves inscrits", format_int(stats["total_eleves"]),
                       (1, 1, 1, 1), (0.02, 0.47, 0.35, 1))
        self._add_card(grid, "Enseignants", format_int(enseignants),
                       (1, 1, 1, 1), (0.02, 0.47, 0.35, 1))
        self._add_card(grid, "Solde caisse", format_montant(solde),
                       (1, 1, 1, 1), (0.02, 0.47, 0.35, 1))
        self._add_card(grid, "Entrees du jour", format_montant(stats["encaissements_jour"]),
                       (1, 1, 1, 1), (0.02, 0.47, 0.35, 1))

        self._add_section("Effectif par classe")
        classes = repos.classes()
        if classes:
            classes_grid = GridLayout(cols=page_cols(self.width), spacing=dp(10),
                                      size_hint_y=None, height=len(classes) * dp(64))
            self.ids.content.add_widget(classes_grid)
            for c in classes:
                item = ListItem(
                    title=c["nom"],
                    subtitle=f"{c.get('cycle_nom') or 'Sans cycle'} - Capacite {format_int(c['capacite'])}",
                    trailing=f"{format_int(c['effectif'])} eleves",
                    trailing_color=(0.02, 0.47, 0.35, 1),
                )
                item.bind(on_touch_down=lambda w, t, c=c: self._class_tap(w, t, c))
                classes_grid.add_widget(item)
        else:
            self._add_section("Aucune classe enregistree")

        self._add_section("Derniers paiements")
        paiements = repos.paiements()[:6]
        if paiements:
            paiements_grid = GridLayout(cols=1, spacing=dp(10),
                                        size_hint_y=None,
                                        height=len(paiements) * dp(64))
            self.ids.content.add_widget(paiements_grid)
            for p in paiements:
                paiements_grid.add_widget(ListItem(
                    title=f"{p['prenom']} {p['nom']}",
                    subtitle=f"{p.get('classe_nom') or ''} - {p['type_frais']} - {p['date_paiement']}",
                    trailing=format_montant(p["montant"]),
                    trailing_color=(0.02, 0.47, 0.35, 1),
                ))
        else:
            self._add_section("Aucun paiement enregistre")

    def _class_tap(self, widget, touch, c):
        if widget.collide_point(*touch.pos):
            self.home.open_eleves_for_class(c["id"])

    def _add_card(self, grid, title, value, bg, color):
        grid.add_widget(StatCard(title=title, value=value, bg=bg, value_color=color))

    def _add_section(self, text):
        self.ids.content.add_widget(SectionTitle(text=text))
