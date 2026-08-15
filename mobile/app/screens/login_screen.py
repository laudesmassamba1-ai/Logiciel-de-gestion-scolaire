from kivy.lang import Builder
from kivy.properties import StringProperty
from kivy.uix.screenmanager import Screen

from app.theme import EMERALD, EMERALD_DARK, TEXT_MUTED

Builder.load_string("""
#:import dp kivy.metrics.dp
#:import sp kivy.metrics.sp

<LoginScreen>:
    canvas.before:
        Color:
            rgba: 0.02, 0.47, 0.35, 1
        Rectangle:
            pos: self.pos
            size: self.size
    ScrollView:
        do_scroll_x: False
        BoxLayout:
            orientation: 'vertical'
            size_hint_y: None
            height: max(self.parent.height, self.minimum_height)
            padding: dp(28), dp(48)
            spacing: dp(18)

            Label:
                text: 'Gestion Scolaire'
                font_size: sp(30)
                bold: True
                color: 1, 1, 1, 1
                size_hint_y: None
                height: self.texture_size[1]
            Label:
                text: 'Ecole Primaire & Secondaire'
                font_size: sp(15)
                color: 0.78, 0.95, 0.88, 1
                size_hint_y: None
                height: self.texture_size[1]
                padding: 0, 0, 0, dp(10)

            BoxLayout:
                orientation: 'vertical'
                size_hint_y: None
                height: self.minimum_height
                canvas.before:
                    Color:
                        rgba: 1, 1, 1, 1
                    RoundedRectangle:
                        pos: self.pos
                        size: self.size
                        radius: [dp(18), dp(18), dp(18), dp(18)]
                padding: dp(22), dp(26)
                spacing: dp(14)

                Label:
                    text: 'Connexion'
                    font_size: sp(20)
                    bold: True
                    color: 0.03, 0.09, 0.16, 1
                    size_hint_y: None
                    height: self.texture_size[1]

                TextInput:
                    id: in_username
                    hint_text: "Nom d'utilisateur ou email"
                    font_size: sp(15)
                    size_hint_y: None
                    height: dp(52)
                    background_color: 0.96, 0.98, 1, 1
                    foreground_color: 0.03, 0.09, 0.16, 1
                    cursor_color: 0.02, 0.47, 0.35, 1
                    write_tab: False
                    input_type: 'text'

                TextInput:
                    id: in_password
                    hint_text: 'Mot de passe'
                    password: True
                    font_size: sp(15)
                    size_hint_y: None
                    height: dp(52)
                    background_color: 0.96, 0.98, 1, 1
                    foreground_color: 0.03, 0.09, 0.16, 1
                    cursor_color: 0.02, 0.47, 0.35, 1
                    write_tab: False

                Label:
                    id: lbl_error
                    text: root.error
                    color: 0.86, 0.15, 0.15, 1
                    font_size: sp(13)
                    size_hint_y: None
                    height: self.texture_size[1] if root.error else 0
                    opacity: 1 if root.error else 0

                Button:
                    text: 'Se connecter'
                    font_size: sp(16)
                    bold: True
                    size_hint_y: None
                    height: dp(52)
                    background_normal: ''
                    background_color: 0.02, 0.47, 0.35, 1
                    on_release: root.do_login()

                Label:
                    text: 'Comptes de demonstration : admin / directeur / gestionnaire'
                    font_size: sp(11)
                    color: 0.39, 0.46, 0.54, 1
                    halign: 'center'
                    size_hint_y: None
                    height: self.texture_size[1]
                    text_size: self.width, None
""")


class LoginScreen(Screen):
    error = StringProperty("")

    def on_start(self):
        self.error = ""

    def do_login(self):
        from services.auth import AuthService

        username = self.ids.in_username.text.strip()
        password = self.ids.in_password.text
        if not username or not password:
            self.error = "Veuillez saisir votre identifiant et votre mot de passe."
            return

        user, err = AuthService().login(username, password)
        if err:
            self.error = err
            return
        self.error = ""
        self.ids.in_password.text = ""
        from kivy.app import App
        App.get_running_app().go_home(user)
