from functools import partial

from PyQt5.QtCore import QDate, QTime, Qt, pyqtSlot, QTimer, QUrl
from PyQt5.QtGui import QColor, QTextCharFormat, QIcon
from PyQt5.QtWidgets import (
    QCalendarWidget, QCheckBox, QDateEdit, QDialog, QDialogButtonBox,
    QFormLayout, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QStackedWidget, QTimeEdit, QVBoxLayout, QPushButton, QGroupBox,
)
from PyQt5.QtMultimedia import QSoundEffect

from repositories import repos
from ui import toast
from ui.pages.helpers import (
    _btn, _simple_btn_style, _add_btn, _actions_cell, confirmer,
)
from ui.widgets import DataTable, EmptyState, PageHeader
from core.config import (
    C_BLUE, C_BLUE_LIGHT, C_BLUE_BORDER, C_PRIMARY,
    C_PRIMARY_LIGHT, C_RED, C_RED_BG, C_RED_BORDER, C_GREEN, C_GREEN_BG,
    C_TEXT_SECONDARY, C_BORDER, C_BG_SOFT, data_dir,
)


def _utilisateur_id(ctx):
    return ctx.user.get("id", 0)


def _jour_iso(date):
    return date.toString("yyyy-MM-dd")


def calendrier(page, ctx):
    if page.layout() is not None:
        return
    uid = _utilisateur_id(ctx)
    lay = QVBoxLayout(page)
    lay.setContentsMargins(20, 20, 20, 20)
    lay.setSpacing(16)
    lay.addWidget(PageHeader(
        "Calendrier",
        "Evenements, marquage des dates et alarmes (ce poste)"))

    corps = QHBoxLayout()
    corps.setSpacing(16)
    lay.addLayout(corps, 1)

    cal = QCalendarWidget()
    cal.setGridVisible(True)
    corps.addWidget(cal, 3)

    panneau_droite = QVBoxLayout()
    panneau_droite.setSpacing(10)
    corps.addLayout(panneau_droite, 2)

    titre_jour = QLabel()
    titre_jour.setStyleSheet(
        f"color: {C_PRIMARY}; font-size: 14px; font-weight: 700;")
    panneau_droite.addWidget(titre_jour)

    table = DataTable()
    table.setColumnCount(4)
    table.setHorizontalHeaderLabels(["Heure", "Titre", "Alarme", "Actions"])
    vide = EmptyState("Aucun evenement",
                      "Ajoutez un evenement a cette date (bouton ci-dessous).")
    pile = QStackedWidget()
    pile.addWidget(table)
    pile.addWidget(vide)
    panneau_droite.addWidget(pile, 1)

    btn_add = _add_btn("+ Ajouter un Evenement", lambda: open_evenement_dialog(
        page, ctx, None, cal.selectedDate(), fill_jour))
    panneau_droite.addWidget(btn_add, 0, Qt.AlignRight)

    # --- Panneau: Alarmes a venir + Test ---
    grp_alarmes = QGroupBox("Alarmes a venir")
    grp_alarmes.setStyleSheet(f"""
        QGroupBox {{
            font-weight: 700; color: {C_TEXT_SECONDARY};
            border: 1px solid {C_BORDER}; border-radius: 10px;
            padding: 4px 10px; margin-top: 6px;
        }}
        QGroupBox::title {{
            subcontrol-origin: margin; subcontrol-position: top left;
            left: 14px; top: 2px; padding: 0 8px;
            background: {C_BG_SOFT}; color: {C_TEXT_SECONDARY};
        }}
    """)
    ga_lay = QVBoxLayout(grp_alarmes)
    ga_lay.setSpacing(6)
    
    # Liste des alarmes a venir
    table_alarmes = DataTable()
    table_alarmes.setColumnCount(4)
    table_alarmes.setHorizontalHeaderLabels(["Date", "Heure", "Titre", "Action"])
    table_alarmes.setMaximumHeight(160)
    ga_lay.addWidget(table_alarmes)
    
    def _refresh_alarmes_a_venir():
        """Affiche les evenements avec alarme non encore signalees, futures."""
        from datetime import datetime
        now_iso = datetime.now().strftime("%Y-%m-%d %H:%M")
        rows = repos.agenda.evenements(uid)
        a_venir = []
        for ev in rows:
            if not ev["alarme"] or ev["alarme_signalee"]:
                continue
            dt_str = f"{ev['jour']} {ev['heure'] or '00:00'}"
            if dt_str <= now_iso:
                continue  # Deja passee, sera prise en charge par le systeme d'alarme
            a_venir.append(ev)
        # On boucle sur les memes entrees que celles affichees, sinon les
        # boutons "Test" tombent sur de mauvaises lignes des qu'une alarme
        # est filtree (mots melanges / defilement decale).
        valeurs = [[ev["jour"], ev["heure"] or "-", ev["titre"], ""]
                   for ev in a_venir]
        table_alarmes.remplir(valeurs)
        for i, ev in enumerate(a_venir):
            table_alarmes.setCellWidget(i, 3, _actions_cell(
                _btn("Test", lambda e=ev: _tester_alarme(e),
                     _simple_btn_style(bg=C_GREEN_BG, fg=C_GREEN, border=C_BORDER)),
            ))
    
    def _tester_alarme(ev):
        """Declenche l'alarme complete avec dialogue pour test."""
        main_win = page.window()
        if main_win and hasattr(main_win, "_afficher_dialogue_alarme"):
            # Creer un evenement de test base sur l'evenement selectionne
            test_ev = {
                "id": ev["id"],
                "titre": ev["titre"] + " (TEST)",
                "jour": ev["jour"],
                "heure": ev["heure"] or "",
                "note": ev.get("note", "")
            }
            main_win._afficher_dialogue_alarme(test_ev)
        else:
            toast.info(page, "Test d'alarme non disponible")
    
    # Bouton test global
    btn_test = _btn("Tester l'alarme complète", lambda: _tester_alarme_global(),
                    _simple_btn_style(bg=C_PRIMARY_LIGHT, fg=C_PRIMARY, border=C_BLUE_BORDER))
    ga_lay.addWidget(btn_test, 0, Qt.AlignRight)
    
    def _tester_alarme_global():
        main_win = page.window()
        if main_win and hasattr(main_win, "_afficher_dialogue_alarme"):
            test_ev = {
                "id": 0,
                "titre": "Test Alarme Globale",
                "jour": "Aujourd'hui",
                "heure": "Maintenant",
                "note": "Ceci est un test de l'alarme"
            }
            main_win._afficher_dialogue_alarme(test_ev)
            toast.succes(page, "Dialogue d'alarme ouvert (son en boucle jusqu'a action)")
        else:
            toast.info(page, "Test d'alarme non disponible")
    
    panneau_droite.addWidget(grp_alarmes)
    
    # Rafraichir les alarmes a venir periodiquement
    page._timer_alarmes_avenir = QTimer(page)
    page._timer_alarmes_avenir.setInterval(30000)  # 30 secondes
    page._timer_alarmes_avenir.timeout.connect(_refresh_alarmes_a_venir)
    page._timer_alarmes_avenir.start()
    _refresh_alarmes_a_venir()

    # Nettoyer le timer a la fermeture
    def _cleanup():
        if hasattr(page, '_timer_alarmes_avenir'):
            page._timer_alarmes_avenir.stop()
        if hasattr(page, '_connect_timer'):
            page._connect_timer.stop()
    page.destroyed.connect(_cleanup)

    def _marquer_dates():
        cal.setDateTextFormat(QDate(), QTextCharFormat())
        fmt_semaine = cal.weekdayTextFormat(Qt.Monday)
        fmt_weekend = cal.weekdayTextFormat(Qt.Saturday)
        for ev in repos.agenda.evenements(uid):
            d = QDate.fromString(ev["jour"], "yyyy-MM-dd")
            if not d.isValid():
                continue
            fmt = (fmt_weekend
                   if d.dayOfWeek() in (Qt.Saturday, Qt.Sunday)
                   else fmt_semaine)
            fmt = QTextCharFormat(fmt)
            fmt.setBackground(QColor(C_BLUE_LIGHT))
            cal.setDateTextFormat(d, fmt)

    def fill_jour():
        jour = _jour_iso(cal.selectedDate())
        titre_jour.setText(cal.selectedDate().toString("dddd dd MMMM yyyy"))
        rows = repos.agenda.evenements_du_jour(uid, jour)
        valeurs = []
        for ev in rows:
            alarme = "\U0001F514 (sonnera)" if ev["alarme"] else "-"
            if ev["alarme"] and ev["alarme_signalee"]:
                alarme = "\U0001F514 (deja signalee)"
            valeurs.append([ev["heure"] or "-", ev["titre"], alarme, ""])
        table.remplir(valeurs)
        for i, ev in enumerate(rows):
            table.setCellWidget(i, 3, _actions_cell(
                _btn("Modifier",
                     partial(open_evenement_dialog, page, ctx, ev,
                             cal.selectedDate(), fill_jour),
                     _simple_btn_style(bg=C_BLUE_LIGHT, fg=C_BLUE, border=C_BLUE_BORDER)),
                _btn("Supprimer", partial(_delete_evenement, page, ev, fill_jour),
                     _simple_btn_style(bg=C_RED_BG, fg=C_RED, border=C_RED_BORDER))))
        pile.setCurrentWidget(vide if not rows else table)
        table.horizontalHeader().setStretchLastSection(True)

    def _delete_evenement(parent, ev, on_done):
        if confirmer(parent,
                     f"Supprimer l'evenement « {ev['titre']} » du {ev['jour']} ?",
                     "Calendrier"):
            repos.agenda.supprimer(ev["id"])
            toast.succes(parent, "Evenement supprime.")
            _marquer_dates()
            on_done()

    cal.selectionChanged.connect(fill_jour)

    cal.setSelectedDate(QDate.currentDate())
    fill_jour()
    _marquer_dates()
    page.refresh = lambda: (_marquer_dates(), fill_jour())

    # Connexion au signal d'alarme de la fenetre principale pour rafraichir en temps reel
    def _connect_alarme_signal():
        try:
            main_win = page.window()
            if main_win and hasattr(main_win, "alarme_declenchee"):
                main_win.alarme_declenchee.connect(lambda *args: (_marquer_dates(), fill_jour()))
        except RuntimeError:
            pass
    
    # Connecter maintenant et aussi quand la fenetre est realisee
    _connect_alarme_signal()
    page._connect_timer = QTimer(page)
    page._connect_timer.setSingleShot(True)
    page._connect_timer.timeout.connect(_connect_alarme_signal)
    page._connect_timer.start(100)


def open_evenement_dialog(parent, ctx, evenement=None, date_defaut=None,
                          on_saved=None):
    dlg = QDialog(parent)
    dlg.setWindowTitle("Nouvel Evenement" if not evenement
                       else "Modifier l'Evenement")
    dlg.setMinimumSize(440, 280)
    lay = QVBoxLayout(dlg)

    form = QFormLayout()
    titre = QLineEdit()
    date_e = QDateEdit()
    date_e.setCalendarPopup(True)
    heure_e = QTimeEdit()
    heure_e.setDisplayFormat("HH:mm")
    note = QLineEdit()
    alarme = QCheckBox("Activer une alarme (notification sur ce PC)")

    if evenement:
        titre.setText(evenement["titre"])
        d = QDate.fromString(evenement["jour"], "yyyy-MM-dd")
        if d.isValid():
            date_e.setDate(d)
        heures = QTime.fromString(evenement["heure"] or "08:00", "HH:mm")
        if heures.isValid():
            heure_e.setTime(heures)
        note.setText(evenement["note"] or "")
        alarme.setChecked(bool(evenement["alarme"]))
    else:
        date_e.setDate(date_defaut or QDate.currentDate())

    form.addRow("Titre :", titre)
    form.addRow("Date :", date_e)
    form.addRow("Heure :", heure_e)
    form.addRow("Note :", note)
    lay.addLayout(form)
    lay.addWidget(alarme)

    buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
    buttons.rejected.connect(dlg.reject)
    lay.addWidget(buttons)

    def _enregistrer():
        nom = titre.text().strip()
        if not nom:
            QMessageBox.warning(dlg, "Titre manquant",
                                "Donnez un titre a l'evenement.")
            return
        jour = _jour_iso(date_e.date())
        heure = heure_e.time().toString("HH:mm")
        activer_alarme = alarme.isChecked()
        if evenement is None:
            repos.agenda.ajouter(_utilisateur_id(ctx), nom, jour, heure,
                                 note.text().strip(), activer_alarme)
            toast.succes(dlg, "Evenement ajoute.")
        else:
            repos.agenda.modifier(evenement["id"], nom, jour, heure,
                                  note.text().strip(), activer_alarme)
            toast.succes(dlg, "Evenement modifie.")
        dlg.accept()
        if on_saved:
            on_saved()

    buttons.accepted.connect(_enregistrer)
    dlg.exec_()