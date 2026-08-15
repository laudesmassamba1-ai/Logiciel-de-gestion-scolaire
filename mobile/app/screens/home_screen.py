from kivy.animation import Animation
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.properties import ColorProperty, StringProperty
from kivy.uix.button import Button
from kivy.uix.screenmanager import Screen
from kivy.uix.widget import Widget

from app.screens.placeholder_screen import PlaceholderScreen
from core.config import ROLE_LABELS
from services.auth import RoleAuthorizer

from app.screens.caisse_screen import CaisseScreen
from app.screens.classes_screen import ClassesScreen
from app.screens.dashboard_screen import DashboardScreen
from app.screens.eleve_detail_screen import EleveDetailScreen
from app.screens.eleves_screen import ElevesScreen

Builder.load_string("""
#:import dp kivy.metrics.dp
#:import sp kivy.metrics.sp

<DrawerOverlay>:
    canvas.before:
        Color:
            rgba: self.rgba
        Rectangle:
            pos: self.pos
            size: self.size

<DrawerNavButton>:
    text_size: self.size
    halign: 'left'
    valign: 'middle'
    font_size: sp(15)
    size_hint_y: None
    height: dp(50)
    color: 0.82, 0.96, 0.90, 1
    background_normal: ''
    background_color: 0, 0, 0, 0

<HomeScreen>:
    FloatLayout:
        BoxLayout:
            orientation: 'vertical'
            BoxLayout:
                id: topbar
                size_hint_y: None
                height: dp(56)
                canvas.before:
                    Color:
                        rgba: 0.02, 0.35, 0.28, 1
                    Rectangle:
                        pos: self.pos
                        size: self.size
                padding: dp(6), 0
                spacing: dp(4)
                Button:
                    id: btn_menu
                    text: '\\u2630'
                    font_size: sp(22)
                    size_hint_x: None
                    width: dp(52)
                    color: 1, 1, 1, 1
                    background_normal: ''
                    background_color: 0, 0, 0, 0
                    on_release: root.toggle_drawer()
                Label:
                    id: lbl_title
                    text: root.page_title
                    font_size: sp(17)
                    bold: True
                    color: 1, 1, 1, 1
                    halign: 'left'
                    text_size: self.width, None
                Button:
                    id: btn_logout
                    text: 'Quitter'
                    font_size: sp(14)
                    size_hint_x: None
                    width: dp(64)
                    color: 1, 0.85, 0.85, 1
                    background_normal: ''
                    background_color: 0, 0, 0, 0
                    on_release: root.confirm_logout()

            ScreenManager:
                id: pages

        DrawerOverlay:
            id: overlay
            on_touch_down:
                if self.collide_point(*args[1].pos) and root.drawer_open: root.close_drawer()

        BoxLayout:
            id: drawer
            size_hint_x: None
            width: min(dp(300), root.width * 0.82)
            x: -min(dp(300), root.width * 0.82)
            orientation: 'vertical'
            canvas.before:
                Color:
                    rgba: 0.02, 0.35, 0.28, 1
                Rectangle:
                    pos: self.pos
                    size: self.size
            padding: 0, dp(20), 0, dp(16)
            spacing: 0

            Label:
                id: drawer_user
                text: root.user_text
                font_size: sp(16)
                bold: True
                color: 1, 1, 1, 1
                halign: 'center'
                size_hint_y: None
                height: dp(28)
            Label:
                id: drawer_role
                text: root.role_text
                font_size: sp(12)
                color: 0.78, 0.95, 0.88, 1
                halign: 'center'
                size_hint_y: None
                height: dp(22)
                padding: 0, 0, 0, dp(14)

            ScrollView:
                do_scroll_x: False
                BoxLayout:
                    id: drawer_list
                    orientation: 'vertical'
                    size_hint_y: None
                    height: max(self.parent.height, self.minimum_height)
                    spacing: dp(4)
""")


class DrawerNavButton(Button):
    pass


class DrawerOverlay(Widget):
    rgba = ColorProperty((0, 0, 0, 0))


PAGE_LABELS = {
    "dashboard": "Tableau de bord",
    "stats": "Statistiques",
    "eleves": "Eleves",
    "classes": "Classes",
    "caisse": "Caisse",
    "tarifs": "Tarifs",
    "paiements": "Paiements",
    "notes": "Notes",
    "presences": "Presences",
    "planning": "Planning",
    "personnel": "Personnel",
    "programmes": "Programmes",
    "parametres": "Parametres",
    "comptes": "Comptes",
}

IMPLEMENTED = {"dashboard", "eleves", "classes", "caisse"}


class HomeScreen(Screen):
    page_title = StringProperty("Gestion Scolaire")
    user_text = StringProperty("")
    role_text = StringProperty("")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.drawer_open = False
        self.user = None
        self._built = False
        self._page_widgets = {}

    def set_user(self, user):
        self.user = user
        self.role = user["role"]
        self.role_label = ROLE_LABELS.get(self.role, self.role)
        self.user_text = user["nom_complet"]
        self.role_text = self.role_label
        from kivy.app import App
        App.get_running_app().title = f"Gestion Scolaire - {user['nom_complet']}"
        if not self._built:
            self._build_pages()
        self.navigate("dashboard")

    def _build_pages(self):
        self._built = True
        authorizer = RoleAuthorizer(self.role)
        for page_name in authorizer.NAV.get(self.role, ["dashboard"]):
            self._add_page_button(page_name, authorizer)
        self._add_page_button("logout", authorizer, special="logout")

        allowed = authorizer.NAV.get(self.role, ["dashboard"])
        for page_name in allowed:
            widget = self._make_page(page_name)
            if widget is not None:
                self.ids.pages.add_widget(widget)
                self._page_widgets[page_name] = widget

    def _add_page_button(self, page_name, authorizer, special=None):
        label = PAGE_LABELS.get(page_name, page_name)
        btn = DrawerNavButton(text=label)
        if special == "logout":
            btn.color = (1, 0.75, 0.75, 1)
            btn.bind(on_release=lambda *a: self.confirm_logout())
        else:
            btn.bind(on_release=lambda *a, p=page_name: self.navigate(p))
        self.ids.drawer_list.add_widget(btn)

    def _make_page(self, page_name):
        page = self._page_widgets.get(page_name)
        if page is not None:
            return page
        if page_name == "dashboard":
            return DashboardScreen(name=page_name, home=self)
        if page_name == "eleves":
            return ElevesScreen(name=page_name, home=self)
        if page_name == "classes":
            return ClassesScreen(name=page_name, home=self)
        if page_name == "caisse":
            return CaisseScreen(name=page_name, home=self)
        if page_name == "eleve_detail":
            return EleveDetailScreen(name="eleve_detail", home=self)
        return PlaceholderScreen(name=page_name, home=self)

    def navigate(self, page_name):
        if page_name == "eleve_detail":
            return
        widget = self._page_widgets.get(page_name)
        if widget is None:
            widget = self._make_page(page_name)
            if widget is None:
                return
            self.ids.pages.add_widget(widget)
            self._page_widgets[page_name] = widget
        self.ids.pages.current = widget.name
        self.page_title = PAGE_LABELS.get(page_name, page_name)
        refresh = getattr(widget, "refresh", None)
        if refresh:
            refresh()
        self.close_drawer()

    def open_eleve_detail(self, eleve_id):
        widget = self._make_page("eleve_detail")
        if widget is None:
            return
        if widget.parent is None:
            self.ids.pages.add_widget(widget)
        widget.show_eleve(eleve_id)
        self.ids.pages.current = widget.name
        self.page_title = "Fiche eleve"

    def open_eleves_for_class(self, classe_id):
        eleves_page = self._page_widgets.get("eleves")
        if eleves_page is not None:
            eleves_page.set_class_filter(classe_id)
            self.navigate("eleves")

    def toggle_drawer(self):
        if self.drawer_open:
            self.close_drawer()
        else:
            self.open_drawer()

    def open_drawer(self):
        self.drawer_open = True
        target = min(dp(300), self.width * 0.82)
        Animation(x=0, d=0.22, t="out_quad").start(self.ids.drawer)
        Animation(rgba=(0, 0, 0, 0.45), d=0.22).start(self.ids.overlay)

    def close_drawer(self):
        self.drawer_open = False
        target = min(dp(300), self.width * 0.82)
        Animation(x=-target, d=0.2, t="out_quad").start(self.ids.drawer)
        Animation(rgba=(0, 0, 0, 0), d=0.2).start(self.ids.overlay)

    def confirm_logout(self):
        from kivy.app import App
        App.get_running_app().go_login()
