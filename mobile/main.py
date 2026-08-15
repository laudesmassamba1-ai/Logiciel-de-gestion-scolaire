import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from kivy.utils import platform  # noqa: E402

if platform == "android":
    private = os.environ.get("ANDROID_PRIVATE") or str(Path.home())
    os.environ.setdefault("GS_DATA_DIR", private)

if platform != "android":
    from kivy.core.window import Window
    Window.size = (430, 900)

from app.main import GestionScolaireApp  # noqa: E402


def main():
    GestionScolaireApp().run()


if __name__ == "__main__":
    main()
