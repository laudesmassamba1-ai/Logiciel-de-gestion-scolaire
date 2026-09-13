"""ui/widgets — composants reutilisables de l'application.

Chaque composant vit dans un seul fichier et est reutilise par tous les
gabarits de page. Ne JAMAIS dupliquer ces composants dans une page.

Le module historique `ui/widgets.py` (graphiques, fmt_money) a ete
renomme `ui/widgets_core.py` : ses noms restent accessibles ici pour ne
rien casser chez les importeurs existants.
"""

from ..widgets_core import (  # noqa: F401
    SimpleBarChart,
    SimpleLineChart,
    SimplePieChart,
    fmt_money,
    fmt_money_short,
    CHART_COLORS,
)

from .data_table import DataTable
from .empty_state import EmptyState
from .kpi_card import KPICard
from .page_header import PageHeader

__all__ = [
    "SimpleBarChart",
    "SimpleLineChart",
    "SimplePieChart",
    "fmt_money",
    "fmt_money_short",
    "CHART_COLORS",
    "DataTable",
    "EmptyState",
    "KPICard",
    "PageHeader",
]