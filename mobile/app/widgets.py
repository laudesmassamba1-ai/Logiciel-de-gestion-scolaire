from kivy.animation import Animation
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.properties import ColorProperty, ListProperty, StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.clock import Clock

from app.theme import EMERALD

Builder.load_string("""
<StatCard>:
    size_hint_y: None
    height: dp(110)
    canvas.before:
        Color:
            rgba: root.bg
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(14), dp(14), dp(14), dp(14)]
    BoxLayout:
        orientation: 'vertical'
        padding: dp(14), dp(12)
        spacing: dp(6)
        Label:
            text: root.title
            font_size: sp(13)
            color: root.muted
            halign: 'left'
            size_hint_y: None
            height: self.texture_size[1]
            text_size: self.width, None
        Label:
            text: root.value
            font_size: sp(22)
            bold: True
            color: root.value_color
            halign: 'left'
            size_hint_y: None
            height: self.texture_size[1]
            text_size: self.width, None

<SectionTitle>:
    size_hint_y: None
    height: dp(28)
    Label:
        text: root.text
        font_size: sp(16)
        bold: True
        color: 0.03, 0.09, 0.16, 1
        halign: 'left'
        size_hint_x: 1
        text_size: self.width, None

<ListItem>:
    size_hint_y: None
    height: dp(64)
    canvas.before:
        Color:
            rgba: 1, 1, 1, 1
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(12), dp(12), dp(12), dp(12)]
    BoxLayout:
        padding: dp(14), dp(8)
        spacing: dp(10)
        BoxLayout:
            orientation: 'vertical'
            spacing: dp(2)
            Label:
                text: root.title
                font_size: sp(15)
                bold: True
                color: 0.03, 0.09, 0.16, 1
                halign: 'left'
                size_hint_y: None
                height: self.texture_size[1]
                text_size: self.width, None
            Label:
                text: root.subtitle
                font_size: sp(12)
                color: root.muted
                halign: 'left'
                size_hint_y: None
                height: self.texture_size[1]
                text_size: self.width, None
        Label:
            text: root.trailing
            font_size: sp(15)
            bold: True
            color: root.trailing_color
            halign: 'right'
            size_hint_x: 0.35
            text_size: self.width, None
""")

_THEME = {
    "primary": EMERALD,
}


class StatCard(BoxLayout):
    title = StringProperty("")
    value = StringProperty("")
    bg = ColorProperty((1, 1, 1, 1))
    value_color = ColorProperty((0.02, 0.47, 0.35, 1))
    muted = ColorProperty((0.39, 0.46, 0.54, 1))


class SectionTitle(BoxLayout):
    text = StringProperty("")


class ListItem(BoxLayout):
    title = StringProperty("")
    subtitle = StringProperty("")
    trailing = StringProperty("")
    trailing_color = ColorProperty((0.02, 0.47, 0.35, 1))
    muted = ColorProperty((0.39, 0.46, 0.54, 1))

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            return super().on_touch_down(touch)
        return super().on_touch_down(touch)


class Snackbar(FloatLayout):
    def __init__(self, message, color=EMERALD, **kwargs):
        super().__init__(**kwargs)
        label = Label(
            text=message,
            color=(1, 1, 1, 1),
            size_hint=(None, None),
            padding=(dp(18), dp(12)),
        )
        label.background_color = color
        self._label = label
        self.add_widget(label)
        self.bind(pos=self._layout, size=self._layout)

    def _layout(self, *args):
        self._label.pos = (self.width / 2 - self._label.width / 2, dp(40))

    def _size(self, *args):
        pass

    def show(self):
        self._label.size = self._label.texture_size
        self._label.pos = (self.width / 2 - self._label.width / 2, dp(40))
        anim = Animation(opacity=1, duration=0.2)
        self.opacity = 0
        anim.start(self)
        Clock.schedule_once(self._dismiss, 2.2)

    def _dismiss(self, *args):
        Animation(opacity=0, duration=0.3).start(self)
        Clock.schedule_once(lambda *a: self.parent and self.parent.remove_widget(self), 0.35)
