from kivy.lang import Builder
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen

from app.utils import format_montant
from repositories import repos

Builder.load_string("""
<EleveDetailScreen>:
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
            Button:
                text: 'Retour'
                font_size: '14sp'
                size_hint_x: None
                width: dp(90)
                color: 1, 1, 1, 1
                background_normal: ''
                background_color: 0.02, 0.47, 0.35, 1
                on_release: root.go_back()
            Button:
                text: 'Supprimer'
                font_size: '14sp'
                size_hint_x: None
                width: dp(110)
                color: 1, 1, 1, 1
                background_normal: ''
                background_color: 0.8, 0.2, 0.2, 1
                on_release: root.delete_eleve()
        ScrollView:
            do_scroll_x: False
            BoxLayout:
                id: content
                orientation: 'vertical'
                size_hint_y: None
                height: max(self.parent.height, self.minimum_height)
                spacing: 10
""")


class EleveDetailScreen(Screen):
    def __init__(self, home=None, **kwargs):
        self.home = home
        self.eleve = None
        super().__init__(**kwargs)

    def show_eleve(self, eleve_id):
        self.eleve_id = eleve_id
        self.eleve = repos.eleve.eleve_by_id(eleve_id)
        self._render()

    def _render(self):
        box = self.ids.content
        box.clear_widgets()
        e = self.eleve
        if not e:
            box.add_widget(Label(text="Eleve introuvable",
                                 color=(0.39, 0.46, 0.54, 1)))
            return

        header = Label(text=f"{e['prenom']} {e['nom']}", font_size="22sp",
                       bold=True, halign="left", size_hint_y=None,
                       height=dp(32), color=(0.03, 0.09, 0.16, 1))
        header.bind(size=lambda *a: setattr(header, "text_size", (header.width, None)))
        box.add_widget(header)

        self._add(box, "Matricule", e["matricule"])
        self._add(box, "Sexe", e.get("sexe") or "-")
        self._add(box, "Date de naissance", e.get("date_naissance") or "-")
        self._add(box, "Lieu de naissance", e.get("lieu_naissance") or "-")
        self._add(box, "Adresse", e.get("adresse") or "-")
        self._add(box, "Statut", e.get("statut") or "-")
        self._add(box, "Date d'inscription", e.get("date_inscription") or "-")
        self._add(box, "Ecole de provenance", e.get("ecole_provenance") or "-")
        self._add(box, "Pere", f"{e.get('pere_nom') or '-'} ({e.get('pere_tel') or '-'})")
        self._add(box, "Mere", f"{e.get('mere_nom') or '-'} ({e.get('mere_tel') or '-'})")
        self._add(box, "Tuteur", f"{e.get('tuteur_nom') or '-'} ({e.get('tuteur_tel') or '-'})")

        solde = repos.finance.solde_eleve(e["id"])
        self._add(box, "Frais attendus", format_montant(solde["attendu"]))
        self._add(box, "Paye", format_montant(solde["paye"]))
        self._add(box, "Solde restant", format_montant(solde["solde"]))

    def _add(self, box, title, value):
        row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(46))
        lbl_t = Label(text=title, halign="left", font_size="14sp",
                      size_hint_x=0.4, color=(0.39, 0.46, 0.54, 1))
        lbl_t.bind(size=lambda *a: setattr(lbl_t, "text_size", (lbl_t.width, None)))
        lbl_v = Label(text=str(value), halign="left", font_size="14sp",
                      size_hint_x=0.6, color=(0.03, 0.09, 0.16, 1))
        lbl_v.bind(size=lambda *a: setattr(lbl_v, "text_size", (lbl_v.width, None)))
        row.add_widget(lbl_t)
        row.add_widget(lbl_v)
        box.add_widget(row)

    def go_back(self):
        self.home.navigate("eleves")

    def delete_eleve(self):
        if not self.eleve:
            return
        repos.eleve.delete_eleve(self.eleve_id)
        self.go_back()
