"""Systeme de design mathematique : nombre d'or PHI + suite de Fibonacci.

Toutes les mesures de l'interface d'assistante decoulent de la suite de
Fibonacci et des ratios du nombre d'or. Aucun nombre magique :

    PHI          = (1 + sqrt(5)) / 2  ≈ 1.6180
    GOLDEN       = 1 / PHI            ≈ 0.6180  (partie majeure d'une coupe)
    GOLDEN_MINO  = 1 - GOLDEN         ≈ 0.3820  (partie mineure)

Suite de Fibonacci (indices) :
    F0=1  F1=1  F2=2  F3=3  F4=5  F5=8   F6=13  F7=21
    F8=34 F9=55 F10=89 F11=144 F12=233 F13=377 F14=610 F15=987

Loi des proportions :
    - chaque dimension = fib(n) de la suite ;
    - rectangle d'or : grand cote = petit cote * PHI ;
    - bulles : l'assistante occupe la partie majeure (GOLDEN) de la largeur
      de chat, l'utilisateur la partie mineure (GOLDEN_MINO) ;
    - cercles (avatars, boutons) : diametre fib, rayon = diametre / 2 ;
    - durees : 144 ms (F11), pas de machine a ecrire 13 ms (F6) ;
    - police : texte 13 (F6), titres 21 (F7), horodatage < 13.

Fonctions :
    rectangle_dore(mineur)  -> cote majeur
    section(taille, ratio)  -> decoupe de `taille` selon un ratio d'or
    section_or(taille)      -> (majeure, mineure) d'une coupe d'or
    fib(n)                  -> n-ieme nombre de Fibonacci (F0 = 1)
"""

import math

PHI = (1.0 + math.sqrt(5.0)) / 2.0
GOLDEN = 1.0 / PHI
GOLDEN_MINO = 1.0 - GOLDEN

_FIBO = (1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377, 610, 987,
         1597, 2584, 4181, 6765)


def fib(n):
    """n-ieme nombre de Fibonacci (F0 = 1, F1 = 1, F2 = 2 ...)."""
    if 0 <= n < len(_FIBO):
        return _FIBO[n]
    return int(round((PHI ** n) / math.sqrt(5.0)))


# Echelle officielle utilisee par l'interface (index dans FIBO).
F3 = fib(3)       # 3    : micro-espacements
F5 = fib(5)       # 8    : espacements serres
F7 = fib(7)       # 21   : moyennes mesures / titres
F8 = fib(8)       # 34   : avatars, boutons d'envoi, champ de saisie
F13 = fib(13)     # 377  : largeur du dialogue
F14 = fib(14)     # 610  : hauteur du dialogue (377 * PHI)
F12 = fib(12)     # 233  : minimum du dialogue

MARGE_COURTE = F5  # 8    : espacements serres
MARGE = fib(6)     # 13   : marges standard
MOYEN = F7         # 21   : moyennes mesures
AVATAR = F8        # 34   : avatars, boutons d'envoi
CHAMP = F8         # 34   : hauteur du champ de saisie
PILULE = fib(6)    # 13   : rayon des bulles / chips
DIALOGUE_LARGEUR = F13       # 377
DIALOGUE_HAUTEUR = F14       # 610  (377 * PHI : rectangle d'or)
MINI_LARGEUR = F12           # 233
MINI_HAUTEUR = F13           # 377

# Police : suite de Fibonacci.
POLICE_TEXTE = fib(6)     # 13
POLICE_TITRE = F7         # 21
POLICE_DETAIL = 10        # sous-suite pratique (horodatage) < 13

# Durees d'animation (Fibonacci) et pas de machine a ecrire.
DUREE_FONDU = fib(11)     # 144 ms (fondu des bulles)
ECRITURE_PAS = fib(6)     # 13 ms  (paquets de texte du streaming)
POINTS_PAS = F12          # 233 ms (clignotement de l'indicateur)

PAD_BULLE = (MARGE, MARGE_COURTE, MARGE, MARGE_COURTE)


def rectangle_dore(mineur):
    """Grand cote d'un rectangle d'or : mineur * PHI."""
    return int(round(mineur * PHI))


def section(taille, ratio=GOLDEN):
    """Decoupe `taille` selon un ratio d'or (0 < ratio < 1)."""
    return int(round(taille * ratio))


def section_or(taille):
    """Coupe d'or : (partie majeure, partie mineure)."""
    return section(taille, GOLDEN), section(taille, GOLDEN_MINO)