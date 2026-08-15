import os

from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager

from app.screens.home_screen import HomeScreen
from app.screens.login_screen import LoginScreen


class GestionScolaireApp(App):
    title = "Gestion Scolaire"

    def build(self):
        sm = ScreenManager()
        sm.add_widget(LoginScreen(name="login"))
        sm.add_widget(HomeScreen(name="home"))
        return sm

    def go_login(self):
        self.root.current = "login"

    def go_home(self, user):
        self.root.get_screen("home").set_user(user)
        self.root.current = "home"
