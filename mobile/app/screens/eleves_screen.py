from kivy.lang import Builder
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput

from app.utils import format_int
from app.widgets import ListItem
from repositories import repos

Builder.load_string("""
<ElevesScreen>:
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
        BoxLayout:
            size_hint_y: None
            height: dp(48)
            spacing: 10
            TextInput:
                id: in_search
                hint_text: 'Rechercher un eleve...'
                font_size: '15sp'
                multiline: False
                write_tab: False
                on_text: root.on_search(self.text)
            Button:
                id: btn_class_filter
                text: 'Toutes classes'
                font_size: '13sp'
                size_hint_x: None
                width: dp(120)
                color: 0.02, 0.35, 0.28, 1
                background_normal: ''
                background_color: 1, 1, 1, 1
                on_release: root.show_class_selector()
            Button:
                text: '+ Nouveau'
                font_size: '13sp'
                bold: True
                size_hint_x: None
                width: dp(100)
                color: 1, 1, 1, 1
                background_normal: ''
                background_color: 0.02, 0.47, 0.35, 1
                on_release: root.add_button()
        ScrollView:
            do_scroll_x: False
            BoxLayout:
                id: eleves_list
                orientation: 'vertical'
                size_hint_y: None
                height: max(self.parent.height, self.minimum_height)
                spacing: 10
        Label:
            id: lbl_nb
            text: ''
            font_size: '13sp'
            color: 0.39, 0.46, 0.54, 1
            size_hint_y: None
            height: dp(22)
""")


class ElevesScreen(Screen):
    def __init__(self, home=None, **kwargs):
        self.home = home
        self._classe_id = None
        self._classes = {}
        super().__init__(**kwargs)

    def on_enter(self):
        self.refresh()

    def set_class_filter(self, classe_id):
        self._classe_id = classe_id
        self._refresh_filter_label()

    def _refresh_filter_label(self):
        if self._classe_id:
            nom = self._classes.get(self._classe_id)
            if nom is None:
                row = repos.classe_by_id(self._classe_id)
                nom = row["nom"] if row else "Classe"
            self.ids.btn_class_filter.text = nom
        else:
            self.ids.btn_class_filter.text = "Toutes classes"

    def on_search(self, text):
        self.refresh()

    def show_class_selector(self):
        self._classes = {c["id"]: c["nom"] for c in repos.classes()}
        content = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(8))
        scroll = ScrollView()
        box = BoxLayout(orientation="vertical", size_hint_y=None,
                        height=max(len(self._classes) * dp(46), dp(46)))
        box.spacing = dp(4)

        def choose(classe_id):
            self._classe_id = classe_id
            self._refresh_filter_label()
            popup.dismiss()
            self.refresh()

        all_btn = Button(text="Toutes classes", size_hint_y=None, height=dp(44))
        all_btn.bind(on_release=lambda *a: choose(None))
        box.add_widget(all_btn)
        for cid in self._classes:
            b = Button(text=self._classes[cid], size_hint_y=None, height=dp(44))
            b.bind(on_release=lambda *a, c=cid: choose(c))
            box.add_widget(b)
        scroll.add_widget(box)
        content.add_widget(scroll)
        popup = Popup(title="Choisir une classe", content=content,
                      size_hint=(0.9, 0.7))
        popup.open()

    def refresh(self):
        recherche = self.ids.in_search.text.strip()
        rows = repos.eleves(classe_id=self._classe_id, recherche=recherche)
        box = self.ids.eleves_list
        box.clear_widgets()
        self.ids.lbl_nb.text = f"{len(rows)} eleves"
        for e in rows:
            item = ListItem(
                title=f"{e['prenom']} {e['nom']}",
                subtitle=f"{e.get('classe_nom') or 'Sans classe'} - {e['matricule']}",
                trailing=e["statut"],
                trailing_color=(0.02, 0.47, 0.35, 1),
            )
            item.bind(on_touch_down=lambda w, t, e=e: self._open(w, t, e))
            box.add_widget(item)
        if not rows:
            lbl = Label(text="Aucun eleve trouve", font_size="15sp",
                        color=(0.39, 0.46, 0.54, 1))
            box.add_widget(lbl)

    def _open(self, widget, touch, e):
        if widget.collide_point(*touch.pos):
            self.home.open_eleve_detail(e["id"])

    def add_button(self):
        from app.screens.forms import eleve_form
        eleve_form(on_saved=self.refresh)
