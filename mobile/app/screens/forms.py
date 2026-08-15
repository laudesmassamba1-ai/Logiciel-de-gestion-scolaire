from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput

from app.utils import format_montant
from repositories import repos


class Field:
    def __init__(self, title):
        self.title = title


def _labeled(title):
    lbl = Label(text=title, size_hint_y=None, height=dp(22), halign="left",
                font_size="14sp", color=(0.09, 0.16, 0.24, 1))
    lbl.bind(size=lambda *a: setattr(lbl, "text_size", (lbl.width, None)))
    return lbl


def _spinner(values, default=None):
    sp = Spinner(text=default or (values[0] if values else ""),
                 values=tuple(values),
                 size_hint_y=None, height=dp(46))
    return sp


def eleve_form(on_saved):
    content = BoxLayout(orientation="vertical", spacing=dp(10), padding=dp(10))

    nom = TextInput(hint_text="Nom", multiline=False, size_hint_y=None, height=dp(46))
    prenom = TextInput(hint_text="Prenom", multiline=False, size_hint_y=None, height=dp(46))
    sexe = _spinner(["Masculin", "Feminin"])
    date_naissance = TextInput(hint_text="Date de naissance (AAAA-MM-JJ)",
                               multiline=False, size_hint_y=None, height=dp(46))
    lieux = TextInput(hint_text="Lieu de naissance", multiline=False,
                      size_hint_y=None, height=dp(46))
    adresse = TextInput(hint_text="Adresse", multiline=False,
                        size_hint_y=None, height=dp(46))

    classes = repos.classes()
    classe_items = {c["nom"]: c["id"] for c in classes}
    classe = _spinner(list(classe_items.keys()) or [""])

    scroll = ScrollView()
    box = BoxLayout(orientation="vertical", size_hint_y=None,
                    height=dp(340), spacing=dp(8))
    box.add_widget(nom)
    box.add_widget(prenom)
    box.add_widget(sexe)
    box.add_widget(date_naissance)
    box.add_widget(lieux)
    box.add_widget(adresse)
    box.add_widget(classe)
    scroll.add_widget(box)
    content.add_widget(scroll)

    lbl_err = Label(text="", color=(0.86, 0.15, 0.15, 1), size_hint_y=None,
                    height=dp(20), font_size="13sp")
    content.add_widget(lbl_err)

    popup = Popup(title="Nouvel eleve", content=content,
                  size_hint=(0.92, 0.82))

    def save(*_):
        if not nom.text.strip() or not prenom.text.strip():
            lbl_err.text = "Le nom et le prenom sont obligatoires."
            return
        data = {
            "nom": nom.text.strip(),
            "prenom": prenom.text.strip(),
            "sexe": sexe.text if sexe.text else None,
            "date_naissance": date_naissance.text.strip() or None,
            "lieu_naissance": lieux.text.strip() or None,
            "classe_id": classe_items.get(classe.text),
            "adresse": adresse.text.strip() or None,
            "statut": "Inscrit",
        }
        repos.eleve.add_eleve(data)
        popup.dismiss()
        on_saved()

    btn = Button(text="Enregistrer", size_hint_y=None, height=dp(50),
                 background_color=(0.02, 0.47, 0.35, 1), background_normal="")
    btn.bind(on_release=save)
    content.add_widget(btn)
    popup.open()


def transaction_form(on_saved, type_trans="entree"):
    content = BoxLayout(orientation="vertical", spacing=dp(10), padding=dp(10))

    type_sp = _spinner(["entree", "sortie"], default=type_trans)
    montant = TextInput(hint_text="Montant (FCFA)", multiline=False,
                        input_filter="int", size_hint_y=None, height=dp(46))
    motif = TextInput(hint_text="Motif", multiline=False, size_hint_y=None, height=dp(46))
    categorie = TextInput(hint_text="Categorie (ex: Scolarite, Fournitures...)",
                          multiline=False, size_hint_y=None, height=dp(46))
    beneficiaire = TextInput(hint_text="Beneficiaire / Payeur",
                             multiline=False, size_hint_y=None, height=dp(46))
    modes = _spinner(["Especes", "Mobile Money", "Virement", "Cheque"])

    scroll = ScrollView()
    box = BoxLayout(orientation="vertical", size_hint_y=None,
                    height=dp(300), spacing=dp(8))
    box.add_widget(type_sp)
    box.add_widget(montant)
    box.add_widget(motif)
    box.add_widget(categorie)
    box.add_widget(beneficiaire)
    box.add_widget(modes)
    scroll.add_widget(box)
    content.add_widget(scroll)

    lbl_err = Label(text="", color=(0.86, 0.15, 0.15, 1), size_hint_y=None,
                    height=dp(20), font_size="13sp")
    content.add_widget(lbl_err)

    popup = Popup(title="Nouvelle operation", content=content,
                  size_hint=(0.92, 0.75))

    def save(*_):
        try:
            valeur = int(montant.text)
        except (TypeError, ValueError):
            lbl_err.text = "Montant invalide."
            return
        if valeur <= 0:
            lbl_err.text = "Le montant doit etre superieur a 0."
            return
        if not motif.text.strip():
            lbl_err.text = "Le motif est obligatoire."
            return
        repos.finance.add_transaction(
            type_trans=type_sp.text,
            montant=valeur,
            motif=motif.text.strip(),
            categorie=categorie.text.strip() or "Divers",
            beneficiaire=beneficiaire.text.strip() or "Non renseigne",
            mode=modes.text or None,
        )
        popup.dismiss()
        on_saved()

    btn = Button(text="Enregistrer", size_hint_y=None, height=dp(50),
                 background_color=(0.02, 0.47, 0.35, 1), background_normal="")
    btn.bind(on_release=save)
    content.add_widget(btn)
    popup.open()
