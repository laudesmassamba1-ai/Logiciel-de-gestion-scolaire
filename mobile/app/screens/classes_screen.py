from kivy.lang import Builder
from kivy.metrics import dp
from kivy.uix.screenmanager import Screen

from app.utils import format_int
from app.widgets import ListItem
from repositories import repos

Builder.load_string("""
<ClassesScreen>:
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
        ScrollView:
            do_scroll_x: False
            BoxLayout:
                id: classes_list
                orientation: 'vertical'
                size_hint_y: None
                height: max(self.parent.height, self.minimum_height)
                spacing: 10
""")


class ClassesScreen(Screen):
    def __init__(self, home=None, **kwargs):
        self.home = home
        super().__init__(**kwargs)

    def on_enter(self):
        self.refresh()

    def refresh(self):
        box = self.ids.classes_list
        box.clear_widgets()
        rows = repos.classes()
        for c in rows:
            item = ListItem(
                title=c["nom"],
                subtitle=f"{c.get('cycle_nom') or 'Sans cycle'} - Salle {c.get('salle') or '-'} - {c.get('titulaire') or 'Sans titulaire'}",
                trailing=f"{format_int(c['effectif'])}/{format_int(c['capacite'])}",
                trailing_color=(0.02, 0.47, 0.35, 1),
            )
            item.bind(on_touch_down=lambda w, t, c=c: self._open(w, t, c))
            box.add_widget(item)
        if not rows:
            box.add_widget(_EmptyLabel())

    def _open(self, widget, touch, c):
        if widget.collide_point(*touch.pos):
            self.home.open_eleves_for_class(c["id"])


def _EmptyLabel():
    from kivy.uix.label import Label
    return Label(text="Aucune classe enregistree", font_size="15sp",
                 color=(0.39, 0.46, 0.54, 1))
