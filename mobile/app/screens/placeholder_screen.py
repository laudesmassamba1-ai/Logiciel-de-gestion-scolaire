from kivy.lang import Builder
from kivy.properties import StringProperty
from kivy.uix.screenmanager import Screen

Builder.load_string("""
<PlaceholderScreen>:
    canvas.before:
        Color:
            rgba: 0.945, 0.961, 0.973, 1
        Rectangle:
            pos: self.pos
            size: self.size
    BoxLayout:
        orientation: 'vertical'
        padding: 30, 40
        spacing: 12
        Label:
            text: root.page_title
            font_size: '22sp'
            bold: True
            color: 0.03, 0.09, 0.16, 1
            halign: 'center'
            size_hint_y: None
            height: self.texture_size[1]
            text_size: self.width, None
        Label:
            text: 'Cette page arrive bientot sur la version mobile.'
            font_size: '14sp'
            color: 0.39, 0.46, 0.54, 1
            halign: 'center'
            size_hint_y: None
            height: self.texture_size[1]
            text_size: self.width, None
""")


class PlaceholderScreen(Screen):
    page_title = StringProperty("")

    def __init__(self, home=None, **kwargs):
        self.home = home
        super().__init__(**kwargs)
        self.page_title = self.name or ""
