from kivy.lang import Builder
from kivy.metrics import dp
from kivy.uix.screenmanager import Screen

from app.utils import format_montant
from app.widgets import ListItem, StatCard
from repositories import repos

Builder.load_string("""
<CaisseScreen>:
    canvas.before:
        Color:
            rgba: 0.945, 0.961, 0.973, 1
        Rectangle:
            pos: self.pos
            size: self.size
    BoxLayout:
        orientation: 'vertical'
        padding: 16, 12
        spacing: 12
        GridLayout:
            id: cards_grid
            cols: 3
            size_hint_y: None
            height: dp(100)
            spacing: 8
        ScrollView:
            do_scroll_x: False
            BoxLayout:
                id: trans_list
                orientation: 'vertical'
                size_hint_y: None
                height: max(self.parent.height, self.minimum_height)
                spacing: 10
        BoxLayout:
            size_hint_y: None
            height: dp(52)
            Button:
                text: '+ Nouvelle operation'
                font_size: '15sp'
                bold: True
                color: 1, 1, 1, 1
                background_normal: ''
                background_color: 0.02, 0.47, 0.35, 1
                on_release: root.add_transaction()
""")


class CaisseScreen(Screen):
    def __init__(self, home=None, **kwargs):
        self.home = home
        super().__init__(**kwargs)

    def on_enter(self):
        self.refresh()

    def refresh(self):
        entree, sortie, solde = repos.caisse_totals()
        grid = self.ids.cards_grid
        grid.clear_widgets()
        grid.add_widget(StatCard(title="Entrees", value=format_montant(entree),
                                 bg=(1, 1, 1, 1), value_color=(0.02, 0.47, 0.35, 1)))
        grid.add_widget(StatCard(title="Sorties", value=format_montant(sortie),
                                 bg=(1, 1, 1, 1), value_color=(0.85, 0.2, 0.2, 1)))
        grid.add_widget(StatCard(title="Solde", value=format_montant(solde),
                                 bg=(1, 1, 1, 1), value_color=(0.02, 0.47, 0.35, 1)))

        box = self.ids.trans_list
        box.clear_widgets()
        rows = repos.transactions()[:30]
        for t in rows:
            sens = "+" if t["type"] == "entree" else "-"
            color = (0.02, 0.47, 0.35, 1) if t["type"] == "entree" else (0.85, 0.2, 0.2, 1)
            item = ListItem(
                title=t["motif"],
                subtitle=f"{t['date']} - {t.get('mode_reglement') or t['categorie']} - {t['reference']}",
                trailing=f"{sens} {format_montant(t['montant'])}",
                trailing_color=color,
            )
            box.add_widget(item)
        if not rows:
            from kivy.uix.label import Label
            box.add_widget(Label(text="Aucune operation", font_size="15sp",
                                 color=(0.39, 0.46, 0.54, 1)))

    def add_transaction(self):
        from app.screens.forms import transaction_form
        transaction_form(on_saved=self.refresh, type_trans="entree")
