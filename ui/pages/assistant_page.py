"""Fenetre de chat de l'assistante locale Charo — interface moderne.

Experience proche des grands assistants de chat, en restant 100% local,
sans thread lourd ni carte graphique :
- bulles asymetriques avec avatars et horodatage ;
- indicateur « Charo écrit » anime pendant un delai court avant chaque
  reponse ;
- effet machine a ecrire (reponse revelee progressivement) ;
- champ de saisie auto-extensible (Entree = envoyer, Maj+Entree = saut de
  ligne) avec bouton d'envoi circulaire ;
- suggestions cliquables mises a jour apres chaque reponse.

Le moteur services/assistant_ia.py renvoie {"texte","action","choix"} :
les actions (navigation, dialogs, reseau) sont executees ici, le reseau
toujours en tache de fond via run_async pour ne jamais bloquer l'UI.
"""

from PyQt5.QtCore import Qt, QDateTime, QPropertyAnimation, QTimer
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QDialog, QFrame, QGraphicsOpacityEffect, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QTextEdit, QVBoxLayout, QWidget,
    QSizePolicy,
)

from core.config import (
    C_BG, C_BORDER, C_CARD, C_GOLD, C_GOLD_LIGHT,
    C_TEXT, C_TEXT_MUTED, C_GOLD_PRESSED,
)
from services.assistant_ia import NOM_ASSISTANT, AssistantIA, formater_fcfa
from ui import math_design as md
from ui.workers import run_async


# --------------------------------------------------------------------------
# Style : tout decoule du nombre d'or PHI et de la suite de Fibonacci
# (ui/math_design.py). Les bulles prennent leur largeur par coupe d'or :
# l'assistante occupe la partie majeure, l'utilisateur la partie mineure.
# --------------------------------------------------------------------------

_RAYON_BULLE = md.PILULE                       # 13  (F7)
_RAYON_COIN = md.fib(5)                        # 8   (F5) - coin accentue
_PAD_BULLE = md.PAD_BULLE                      # (13, 8, 13, 8)
_RAYON_AVATAR = md.AVATAR // 2                 # 17  (cercle parfait)

_BULLE_ASSISTANT = (
    f"QFrame {{ background-color: {C_CARD}; border: 1px solid {C_BORDER};"
    f" border-radius: {_RAYON_BULLE}px;"
    f" border-top-left-radius: {_RAYON_COIN}px; }}")
_BULLE_UTILISATEUR = (
    f"QFrame {{ background-color: {C_GOLD_LIGHT}; border: 1px solid {C_GOLD};"
    f" border-radius: {_RAYON_BULLE}px;"
    f" border-top-right-radius: {_RAYON_COIN}px; }}")
_STYLE_CHIP = (
    f"QPushButton {{ background-color: transparent; color: {C_GOLD_PRESSED};"
    f" border: 1px solid {C_GOLD}; border-radius: {_RAYON_BULLE}px;"
    f" padding: {md.fib(5)}px {md.MARGE}px;"
    f" font-size: {md.POLICE_TEXTE}px; font-weight: 600; }}"
    f"QPushButton:hover {{ background-color: {C_GOLD}; color: white; }}")
_STYLE_ENVOI = (
    f"QPushButton {{ background-color: {C_GOLD}; color: white; border: none;"
    f" border-radius: {md.AVATAR // 2}px; font-size: {md.MOYEN}px;"
    f" font-weight: 700; }}"
    f"QPushButton:hover {{ background-color: {C_GOLD_PRESSED}; }}"
    "QPushButton:disabled { background-color: #D8D3C8; color: #F5F3EF; }")
_STYLE_ENTETE_BTN = (
    "QPushButton { background: transparent; border: none; font-size: 13px;"
    " color: #8A6D1F; padding: 4px 7px; border-radius: 8px; }"
    "QPushButton:hover { background-color: rgba(0,0,0,0.07); }")

_AVATAR_ASSISTANT = (
    f"QLabel {{ background-color: {C_GOLD}; color: white;"
    f" border-radius: {_RAYON_AVATAR}px;"
    f" font-weight: 800; font-size: {md.MOYEN}px; }}")


def _horodatage():
    return QDateTime.currentDateTime().toString("HH:mm")


def _avatar_assistant(taille=md.AVATAR):
    """Avatar rond de l'assistante (diametre fib -> cercle parfait)."""
    avatar = QLabel(NOM_ASSISTANT[:1].upper())
    avatar.setFixedSize(taille, taille)
    avatar.setAlignment(Qt.AlignCenter)
    avatar.setStyleSheet(
        _AVATAR_ASSISTANT.replace(
            str(_RAYON_AVATAR) + "px",
            str(taille // 2) + "px").replace(
            str(md.MOYEN) + "px",
            str(section_fonte(taille)) + "px"))
    return avatar


def section_fonte(taille):
    """Taille de police proportionnelle a l'avatar (coupe d'or)."""
    return md.section(taille, md.GOLDEN)


class _BulleChat(QFrame):
    """Bulle + animation d'apparition en fondu (legere, 144 ms = F12)."""

    def __init__(self, style, texte, parent=None):
        super().__init__(parent)
        self.setStyleSheet(style)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(*_PAD_BULLE)
        lay.setSpacing(md.fib(3))
        self.label = QLabel(texte)
        self.label.setWordWrap(True)
        self.label.setTextFormat(Qt.PlainText)
        self.label.setTextInteractionFlags(
            Qt.TextSelectableByMouse | Qt.LinksAccessibleByMouse)
        self.label.setStyleSheet(
            f"color: {C_TEXT}; font-size: {md.POLICE_TEXTE}px;"
            " background: transparent;")
        lay.addWidget(self.label)

        self._effet = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._effet)
        self._anim = QPropertyAnimation(self._effet, b"opacity", self)
        self._anim.setDuration(md.DUREE_FONDU)          # 144 ms (F12)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)

    def apparaitre(self):
        self._anim.start()

    def setText(self, texte):
        self.label.setText(texte)


class AssistantChatDialog(QDialog):

    def __init__(self, parent, ctx):
        super().__init__(parent)
        self.ctx = ctx
        self.moteur = AssistantIA(ctx.user)
        self.setWindowTitle(f"{NOM_ASSISTANT} — Assistante locale")
        self.resize(md.DIALOGUE_LARGEUR, md.DIALOGUE_HAUTEUR)   # 377 x 610
        self.setMinimumSize(md.MINI_LARGEUR, md.MINI_HAUTEUR)   # 233 x 377
        self.setModal(False)
        self.setAttribute(Qt.WA_DeleteOnClose, False)
        self.setStyleSheet(f"QDialog {{ background-color: {C_BG}; }}")

        racine = QVBoxLayout(self)
        racine.setContentsMargins(0, 0, 0, 0)
        racine.setSpacing(0)

        racine.addWidget(self._construire_entete())
        racine.addWidget(self._construire_zone_chat(), 1)
        racine.addWidget(self._construire_zone_saisie())

        self._accueil_affiche = False
        self._minuteur_ecriture = None
        self._minuteur_revelation = None
        self._derniere_question = None
        self._boutons_feedback = []
        self._tous_feedback = []

    # ------------------------------------------------------------------
    # Construction de l'interface
    # ------------------------------------------------------------------

    def _construire_entete(self):
        entete = QFrame()
        entete.setObjectName("charoHeader")
        entete.setStyleSheet(
            "#charoHeader { background-color: #FFF7E0;"
            " border-bottom: 2px solid #111111; }")
        lay = QHBoxLayout(entete)
        lay.setContentsMargins(md.MARGE, md.fib(5), md.fib(5), md.fib(5))
        lay.setSpacing(md.fib(5))

        avatar = _avatar_assistant(md.AVATAR)
        lay.addWidget(avatar)

        col = QVBoxLayout()
        col.setSpacing(0)
        titre = QLabel(NOM_ASSISTANT)
        police = QFont()
        police.setBold(True)
        police.setPointSize(md.POLICE_TITRE - 8)   # 13 pt majestueux
        titre.setFont(police)
        titre.setStyleSheet("color: #111111; background: transparent;")
        sous_ligne = QHBoxLayout()
        sous_ligne.setSpacing(md.fib(3))
        point = QLabel()
        point.setFixedSize(md.fib(5), md.fib(5))   # 8 x 8
        point.setStyleSheet("background-color:#34A853; border-radius:4px;")
        statut = QLabel("En ligne · sur ce PC")
        statut.setStyleSheet(
            f"color: {C_TEXT_MUTED}; font-size: {md.POLICE_DETAIL}px;"
            "background: transparent;")
        sous_ligne.addWidget(point)
        sous_ligne.addWidget(statut)
        sous_ligne.addStretch(1)
        col.addWidget(titre)
        col.addLayout(sous_ligne)
        lay.addLayout(col)
        lay.addStretch(1)

        btn_nouveau = QPushButton("\u21bb")   # fleche circulaire
        btn_nouveau.setToolTip("Nouvelle discussion")
        btn_fermer = QPushButton("\u2715")
        btn_fermer.setToolTip("Fermer")
        for b in (btn_nouveau, btn_fermer):
            b.setCursor(Qt.PointingHandCursor)
            b.setStyleSheet(_STYLE_ENTETE_BTN)
            lay.addWidget(b)
        btn_nouveau.clicked.connect(self._nouvelle_discussion)
        btn_fermer.clicked.connect(self.close)
        return entete

    def _construire_zone_chat(self):
        self.zone_chat = QScrollArea()
        self.zone_chat.setWidgetResizable(True)
        self.zone_chat.setFrameShape(QFrame.NoFrame)
        self.zone_chat.setStyleSheet(
            f"QScrollArea {{ background: {C_BG}; border: none; }}")
        self.conteneur = QWidget()
        self.conteneur.setStyleSheet(f"background: {C_BG};")
        self.flux = QVBoxLayout(self.conteneur)
        self.flux.setContentsMargins(md.MARGE, md.MARGE,
                                     md.MARGE, md.fib(5))
        self.flux.setSpacing(md.MARGE)
        self.flux.addStretch(1)
        self.zone_chat.setWidget(self.conteneur)
        return self.zone_chat

    def _construire_zone_saisie(self):
        panneau = QFrame()
        panneau.setStyleSheet(
            f"QFrame {{ background-color: {C_CARD};"
            f" border-top: 1px solid {C_BORDER}; }}")
        vertical = QVBoxLayout(panneau)
        vertical.setContentsMargins(md.MARGE, md.fib(5),
                                    md.MARGE, md.fib(5))
        vertical.setSpacing(md.fib(5))

        self.rangee_chips = QHBoxLayout()
        self.rangee_chips.setSpacing(md.fib(5))
        self.rangee_chips.addStretch(1)
        vertical.addLayout(self.rangee_chips)

        rangee = QHBoxLayout()
        rangee.setSpacing(md.fib(5))
        self.champ = _ChampMultiligne(self._envoyer)
        self.champ.setPlaceholderText(f"Ecrivez a {NOM_ASSISTANT}...")
        rangee.addWidget(self.champ, 1)

        self.btn_envoi = QPushButton("\u27a4")
        self.btn_envoi.setCursor(Qt.PointingHandCursor)
        self.btn_envoi.setFixedSize(md.AVATAR, md.AVATAR)
        self.btn_envoi.setStyleSheet(_STYLE_ENVOI)
        self.btn_envoi.setEnabled(False)
        self.btn_envoi.clicked.connect(self._envoyer)
        rangee.addWidget(self.btn_envoi, 0, Qt.AlignBottom)
        vertical.addLayout(rangee)

        self.champ.textChanged.connect(self._maj_etat_envoi)
        return panneau

    # ------------------------------------------------------------------
    # Affichage des messages
    # ------------------------------------------------------------------

    def showEvent(self, event):
        super().showEvent(event)
        self._afficher_accueil()

    def _defiler_bas(self):
        barre = self.zone_chat.verticalScrollBar()
        QTimer.singleShot(md.fib(8), lambda: barre.setValue(barre.maximum()))

    def _retirer_rangee_chips(self):
        while self.rangee_chips.count():
            item = self.rangee_chips.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()

    def _maj_chips(self, choix):
        self._retirer_rangee_chips()
        for texte in (choix or [])[:4]:
            chip = QPushButton(texte)
            chip.setCursor(Qt.PointingHandCursor)
            chip.setStyleSheet(_STYLE_CHIP)
            chip.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
            chip.clicked.connect(lambda _=False, v=texte:
                                 self._traiter_message(v))
            self.rangee_chips.addWidget(chip)
        self.rangee_chips.addStretch(1)

    def _largeur_chat(self):
        """Largeur utile du flux, calculee sur le flux reel (sinon defaut)."""
        larg = self.conteneur.width() or md.DIALOGUE_LARGEUR
        return larg - md.MARGE * 2

    def _bulle_utilisateur(self, texte):
        rangee = QHBoxLayout()
        rangee.setContentsMargins(md.MARGE, 0, 0, 0)
        bulle = _BulleChat(_BULLE_UTILISATEUR, texte)
        bulle.layout().addWidget(self._petite_heure())
        bulle.setMaximumWidth(                       # partie mineure : 0.382
            max(md.fib(4), md.section(self._largeur_chat(), md.GOLDEN_MINO)))
        rangee.addStretch(1)
        rangee.addWidget(bulle)
        self.flux.insertLayout(self.flux.count() - 1, rangee)
        bulle.apparaitre()
        self._defiler_bas()

    def _bulle_assistante(self, texte, avec_feedback=True):
        """Bulle de l'assistante, largeur selon la partie majeure d'or."""
        rangee = QHBoxLayout()
        rangee.setContentsMargins(0, 0, md.MARGE, 0)
        rangee.setSpacing(md.fib(3))
        avatar = _avatar_assistant()
        rangee.addWidget(avatar, 0, Qt.AlignTop)
        colonne = QVBoxLayout()
        colonne.setContentsMargins(0, 0, 0, 0)
        colonne.setSpacing(md.fib(3))
        bulle = _BulleChat(_BULLE_ASSISTANT, texte)
        bulle.setMaximumWidth(                       # partie majeure : 0.618
            max(md.fib(4), md.section(self._largeur_chat(), md.GOLDEN)))
        colonne.addWidget(bulle)
        if avec_feedback:
            colonne.addLayout(self._rangee_feedback())
        rangee.addLayout(colonne, 1)
        self.flux.insertLayout(self.flux.count() - 1, rangee)
        bulle.apparaitre()
        self._defiler_bas()
        return bulle

    def _rangee_feedback(self):
        """Boutons discrets 👍 / 👎 pour noter la reponse de l'assistante."""
        rangee = QHBoxLayout()
        rangee.setContentsMargins(md.fib(3), 0, 0, 0)
        rangee.setSpacing(md.fib(3))
        for note, symbole, astuce in ((1, "\U0001F44D", "Cette reponse est utile"),
                                      (-1, "\U0001F44E",
                                       "Cette reponse n'est pas bonne")):
            bouton = QPushButton(symbole)
            bouton.setFixedSize(md.MOYEN, md.MOYEN)   # 21 x 21 (F8)
            bouton.setCursor(Qt.PointingHandCursor)
            bouton.setToolTip(astuce)
            bouton.setStyleSheet(
                f"{_STYLE_CHIP} padding: 0px; margin: 0px;"
                " border-radius: 10px;")
            bouton.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            bouton.setCheckable(True)
            bouton.clicked.connect(self._fabriquer_noter(note, bouton))
            rangee.addWidget(bouton)
        rangee.addStretch(1)
        return rangee

    def _fabriquer_noter(self, note, bouton):
        def _noter(_=False):
            # Un seul avis par conversation : desactive TOUS les boutons de
            # feedback (meme sur les anciennes bulles) pour que le vote
            # reste attribue a la derniere reponse du moteur.
            for precedent in getattr(self, "_tous_feedback", []):
                if precedent is not bouton:
                    precedent.setEnabled(False)
                    precedent.setChecked(False)
            self._boutons_feedback = [bouton]
            bouton.setEnabled(False)
            self._feedback(note)
        self._tous_feedback.append(bouton)
        return _noter

    @staticmethod
    def _petite_heure():
        heure = QLabel(_horodatage())
        heure.setAlignment(Qt.AlignRight)
        heure.setStyleSheet(
            f"color: {C_TEXT_MUTED}; font-size: {md.POLICE_DETAIL}px;"
            "background: transparent;")
        return heure

    def _indicateur_ecriture(self, visible=True):
        """Bulle « ... » animee pendant le delai de reflexion."""
        if visible:
            if getattr(self, "_bulle_typing", None) is not None:
                return
            self._bulle_typing = _BulleChat(_BULLE_ASSISTANT, "\u25cf")
            self._bulle_typing.label.setStyleSheet(
                f"color: {C_GOLD_PRESSED}; font-size: {md.POLICE_TEXTE}px;"
                f" letter-spacing: {md.fib(5)}px; background: transparent;")
            rangee = QHBoxLayout()
            rangee.setContentsMargins(0, 0, md.MARGE, 0)
            rangee.setSpacing(md.fib(3))
            avatar = _avatar_assistant()
            rangee.addWidget(avatar, 0, Qt.AlignTop)
            rangee.addWidget(self._bulle_typing, 1)
            self._typing_rangee = rangee
            self.flux.insertLayout(self.flux.count() - 1, rangee)
            self._bulle_typing.apparaitre()
            self._points = 1
            self._minuteur_points = QTimer(self)
            self._minuteur_points.timeout.connect(self._animer_points)
            self._minuteur_points.start(md.POINTS_PAS)   # 233 ms (F13)
            self._defiler_bas()
        else:
            minuteur = getattr(self, "_minuteur_points", None)
            if minuteur is not None:
                minuteur.stop()
                self._minuteur_points = None
            rangee = getattr(self, "_typing_rangee", None)
            if rangee is not None:
                idx = self.flux.indexOf(rangee)
                if idx >= 0:
                    self.flux.takeAt(idx)
                while rangee.count():
                    sous = rangee.takeAt(0)
                    w = sous.widget()
                    if w is not None:
                        w.setParent(None)
                        w.deleteLater()
                rangee.deleteLater()
                self._bulle_typing = None
                self._typing_rangee = None

    def _animer_points(self):
        bulle = getattr(self, "_bulle_typing", None)
        if bulle is None:
            return
        self._points = (self._points % 3) + 1
        bulle.setText("\u25cf" * self._points)

    # ------------------------------------------------------------------
    # Traitement d'un message : delai -> indicateur -> machine a ecrire
    # ------------------------------------------------------------------

    def _envoyer(self):
        texte = self.champ.toPlainText().strip()
        if not texte:
            return
        self.champ.clear()
        self._traiter_message(texte)

    def _maj_etat_envoi(self):
        self.btn_envoi.setEnabled(bool(self.champ.toPlainText().strip()))

    def _traiter_message(self, texte):
        self._derniere_question = texte
        self._boutons_feedback = []
        self._bulle_utilisateur(texte)
        try:
            reponse = self.moteur.traiter(texte)
        except Exception as exc:
            reponse = {"texte": f"Erreur interne de l'assistant : {exc}\n"
                                "La demande n'a pas abouti.",
                       "action": None, "choix": None}
        self._maj_chips(None)

        # Delai naturel proportionnel a la longueur de la reponse
        # (bornes et pas de la suite de Fibonacci).
        contenu = reponse.get("texte") or ""
        delai = max(md.fib(13), min(md.fib(16),
                                    md.fib(13) + md.section(len(contenu) * 2)))
        self._indicateur_ecriture(True)

        def _reveler():
            self._indicateur_ecriture(False)
            action = reponse.get("action")
            if action:
                QTimer.singleShot(md.fib(8), lambda: self._executer_action(action))
            bulle = self._bulle_assistante("")
            self._ecrire_progressivement(bulle, contenu, reponse)

        self._minuteur_revelation = QTimer.singleShot(delai, _reveler)

    def _ecrire_progressivement(self, bulle, contenu, reponse):
        """Revele la reponse par petits paquets (effet ChatGPT)."""
        total = len(contenu)
        if not total:
            self._fin_revelation(bulle, contenu, reponse)
            return
        position = [0]
        pas = max(2, total // 90)

        def _tick():
            position[0] = min(total, position[0] + pas)
            bulle.setText(contenu[:position[0]])
            self._defiler_bas()
            if position[0] >= total:
                minuteur.disconnect()
                self._minuteur_ecriture = None
                self._fin_revelation(bulle, contenu, reponse)

        self._minuteur_ecriture = QTimer(self)
        minuteur = self._minuteur_ecriture
        minuteur.timeout.connect(_tick)
        minuteur.start(md.ECRITURE_PAS)   # 13 ms (F7)

    def _fin_revelation(self, bulle, contenu, reponse):
        bulle.setText(contenu)
        self._maj_chips(reponse.get("choix"))
        self._defiler_bas()

    def _feedback(self, note):
        """Traite un retour 👍/👎 et affiche la reaction de l'assistante."""
        try:
            reponse = self.moteur.noter_reponse(note)
        except Exception as exc:
            reponse = {"texte": f"Impossible de noter la reponse : {exc}",
                       "action": None, "choix": None}
        texte = reponse.get("texte") or ""
        self._maj_chips(reponse.get("choix"))
        self._bulle_assistante(texte, avec_feedback=False)
        self._defiler_bas()

    def _nouvelle_discussion(self):
        if self._minuteur_ecriture is not None:
            self._minuteur_ecriture.stop()
            self._minuteur_ecriture = None
        self.moteur.reinitialiser()
        self._indicateur_ecriture(False)
        while self.flux.count() > 1:
            item = self.flux.takeAt(0)
            self._supprimer_item(item)
        self._accueil_affiche = False
        self._afficher_accueil()

    @staticmethod
    def _supprimer_item(item):
        w = item.widget()
        if w is not None:
            w.setParent(None)
            w.deleteLater()
            return
        lay = item.layout()
        if lay is None:
            return
        while lay.count():
            sous = lay.takeAt(0)
            AssistantChatDialog._supprimer_item(sous)
        lay.deleteLater()

    def _afficher_accueil(self):
        if not self._accueil_affiche:
            self._accueil_affiche = True
            bienvenue = (
                f"Bonjour ! Je suis {NOM_ASSISTANT}.\nTapez « aide » "
                "pour la liste complete.")
            self._bulle_assistante(bienvenue)
            self._maj_chips(["Combien d'eleves ?", "Solde de la caisse",
                             "Aide"])

    # ------------------------------------------------------------------
    # Execution des actions retournees par le moteur
    # ------------------------------------------------------------------

    def _executer_action(self, action):
        type_act = action.get("type")
        if type_act == "navigate":
            page = action.get("page")
            if page:
                try:
                    self.ctx.navigate(page)
                except Exception as exc:
                    self._bulle_assistante(
                        f"Impossible d'ouvrir la section : {exc}")
        elif type_act == "dialog":
            self._ouvrir_dialog(action.get("dialog"))
        elif type_act == "ping_serveur":
            self._ping_serveur()
        elif type_act == "sync_now":
            self._sync_maintenant()
        elif type_act == "requete_distant":
            self._requete_distance(action.get("quoi"))

    def _ouvrir_dialog(self, nom_dialog):
        from ui import pages
        try:
            if nom_dialog == "inscription":
                pages.open_inscription_dialog(self, self.ctx)
            elif nom_dialog == "paiement":
                pages.open_paiement_dialog(self, self.ctx,
                                           on_created=lambda: None)
            else:
                self._bulle_assistante(
                    "Ce formulaire n'est pas disponible.")
        except Exception as exc:
            self._bulle_assistante(
                f"Ouverture impossible : {exc}")

    def _ping_serveur(self):
        from api import api_disponible
        from core import network

        def _verifier():
            return api_disponible(force=True)

        def _resultat(en_ligne):
            if not isinstance(en_ligne, bool):
                en_ligne = bool(en_ligne)
            if not network.sync_active():
                message = ("Mode Autonome confirme : la synchronisation est "
                           "desactivee sur ce poste. Ouvrez l'assistant "
                           "multi-postes via le badge en bas de la colonne "
                           "de gauche pour connecter vos PC.")
            elif en_ligne:
                message = ("Serveur joignable : les donnees circulent bien "
                           "entre vos postes.")
            else:
                message = ("Serveur INJOIGNABLE : verifiez que le PC serveur "
                           "est allume et que le logiciel serveur y est demarre "
                           "(une connexion Internet normale ne suffit pas).")
            self._bulle_assistante(message)

        run_async(_verifier, _resultat)

    def _sync_maintenant(self):
        from services.sync_service import pull_structure

        def _tirer():
            return pull_structure()

        def _resultat(res):
            if isinstance(res, Exception):
                self._bulle_assistante(
                    f"Synchronisation impossible : {res}")
                return
            parties = ["Synchronisation terminee — lignes recuperees :",
                       f"- Cycles : {res.get('cycles', 0)}",
                       f"- Classes : {res.get('classes', 0)}",
                       f"- Matieres : {res.get('matieres', 0)}",
                       f"- Annees : {res.get('annees', 0)}",
                       f"- Tarifs : {res.get('tarifs', 0)}"]
            erreurs = res.get("erreurs") or []
            if erreurs:
                parties.append("Erreurs partielles : " + "; ".join(erreurs[:3]))
            self._bulle_assistante("\n".join(parties))

        run_async(_tirer, _resultat)

    def _requete_distance(self, quoi):
        from api import client as api_client

        def _interroger():
            cli = api_client.client
            if quoi == "total_paiements":
                data, err = cli.total_montant_paiement()
                if err:
                    return err
                montant = data.get("total_montant") if isinstance(data, dict) \
                    else data
                return formater_fcfa(montant or 0) + " de paiements enregistres"
            if quoi == "classes":
                data, err = cli.classes()
                if err:
                    return err
                noms = [c.get("nom") or c.get("classe") or "?" for c in
                        (data or [])]
                return f"{len(noms)} classe(s) sur le serveur : " + \
                    ", ".join(noms[:15])
            data, err = cli.total_eleves()
            if err:
                return err
            total = data.get("total_eleves") if isinstance(data, dict) else data
            return f"{total} eleve(s) enregistre(s) sur le serveur central."

        def _resultat(res):
            if isinstance(res, Exception):
                self._bulle_assistante(
                    f"Echec de la requete distante : {res}")
            elif isinstance(res, str) and res:
                self._bulle_assistante("(Donnees des autres PC)\n" + res)
            else:
                self._bulle_assistante(
                    "Le serveur n'a pas repondu. Lancez-le sur le PC central "
                    "puis reessayez « synchronise maintenant ».")

        run_async(_interroger, _resultat)


class _ChampMultiligne(QTextEdit):
    """Champ auto-extensible (1 a 4 lignes). Entree = envoyer,
    Maj+Entree = saut de ligne."""

    MAX_HAUTEUR = 96

    def __init__(self, on_envoyer):
        super().__init__()
        self._on_envoyer = on_envoyer
        self.setFixedHeight(md.CHAMP)
        self.setTabChangesFocus(True)
        self.setStyleSheet(
            "QTextEdit { border: 1px solid #C9BFA8; border-radius: 17px;"
            f" padding: {md.fib(3)}px {md.MARGE}px; background: white;"
            f" font-size: {md.POLICE_TEXTE}px; }}"
            "QTextEdit:focus { border: 2px solid #E0A800; }")

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter) and \
                not event.modifiers() & Qt.ShiftModifier:
            self._on_envoyer()
            return
        super().keyPressEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._ajuster_hauteur()

    def _ajuster_hauteur(self):
        hauteur_doc = int(self.document().size().height()) + 18
        hauteur = max(md.CHAMP, min(self.MAX_HAUTEUR, hauteur_doc))
        self.setFixedHeight(hauteur)


_instance = {}


def ouvrir_assistant_ia(parent, ctx):
    """Ouvre (ou ramene au premier plan) la fenetre de chat.

    NB : show() seul suffit rarement sous GNOME/XWayland (prevention du vol
    de focus) : sans raise_() + activateWindow() la fenetre s'ouvrait
    DERRIERE la fenetre principale et le clic semblait ne rien faire."""
    cle = id(parent)
    fenetre = _instance.get(cle)
    if fenetre is not None:
        try:
            fenetre.setWindowState(
                (fenetre.windowState() & ~Qt.WindowMinimized) | Qt.WindowActive)
            fenetre.show()
            fenetre.raise_()
            fenetre.activateWindow()
            return fenetre
        except RuntimeError:
            _instance.pop(cle, None)
    fenetre = AssistantChatDialog(parent, ctx)
    _instance[cle] = fenetre
    fenetre.show()
    fenetre.raise_()
    fenetre.activateWindow()
    return fenetre
