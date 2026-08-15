from kivy.metrics import dp, sp


def format_montant(montant):
    try:
        val = round(float(montant or 0))
    except (TypeError, ValueError):
        val = 0
    return f"{val:,.0f} FCFA".replace(",", " ")


def format_int(n):
    try:
        return f"{int(n or 0):,}".replace(",", " ")
    except (TypeError, ValueError):
        return "0"


def page_cols(width):
    if width >= dp(900):
        return 3
    if width >= dp(560):
        return 2
    return 1


def page_cols_cards(width):
    if width >= dp(900):
        return 4
    if width >= dp(560):
        return 2
    return 1
