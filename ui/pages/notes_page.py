from PyQt5.QtCore import Qt
from PyQt5.QtGui import QBrush, QColor, QFont
from PyQt5.QtWidgets import (
    QHBoxLayout, QLabel, QMessageBox, QComboBox, QPushButton, QTableWidgetItem,
    QVBoxLayout, QTableWidget, QTabWidget, QFrame, QWidget, QFileDialog,
)

from repositories import repos
from services import reports
from ui.pages.helpers import (
    _btn, _simple_btn_style, _classe_items, _reload_combo, _fill_combos,
    _fit_rows, _appreciation,
)
from core.config import (
    PERIODES, C_DANGER, C_SUCCESS_DARK,
    STYLE_BTN_PRIMARY, STYLE_BTN_SECONDARY, STYLE_BTN_SUCCESS, STYLE_BTN_ADD,
    STYLE_SELECTOR, STYLE_HEADER_TITLE, STYLE_HEADER_SUBTITLE,
    STYLE_EMPTY_STATE, STYLE_STATUS, STYLE_TABLE,
)


def notes(page, ctx):
    if page.layout() is not None:
        return
    page_layout = QVBoxLayout(page)
    page_layout.setContentsMargins(20, 20, 20, 20)
    page_layout.setSpacing(16)

    tabs = QTabWidget()
    tabs.setDocumentMode(True)
    page_layout.addWidget(tabs)

    tab_saisie = QWidget()
    tab_saisie_layout = QVBoxLayout(tab_saisie)
    tab_saisie_layout.setContentsMargins(0, 8, 0, 0)
    tab_saisie_layout.setSpacing(12)
    tabs.addTab(tab_saisie, "Saisie par Matiere")

    tab_eleve = QWidget()
    tab_eleve_layout = QVBoxLayout(tab_eleve)
    tab_eleve_layout.setContentsMargins(0, 8, 0, 0)
    tab_eleve_layout.setSpacing(12)
    tabs.addTab(tab_eleve, "Saisie par Eleve")

    tab_moyennes = QWidget()
    tab_moyennes_layout = QVBoxLayout(tab_moyennes)
    tab_moyennes_layout.setContentsMargins(0, 8, 0, 0)
    tab_moyennes_layout.setSpacing(12)
    tabs.addTab(tab_moyennes, "Moyennes Generales")

    def _cell_float(item):
        if not item or not item.text().strip():
            return None
        try:
            return float(item.text().replace(",", "."))
        except ValueError:
            return None

    def _add_matiere_dialog():
        from PyQt5.QtWidgets import QDialog, QFormLayout, QLineEdit, QDialogButtonBox
        dlg = QDialog(page)
        dlg.setWindowTitle("Nouvelle matiere")
        dlg.resize(360, 130)
        dlg.setMinimumSize(320, 110)
        lay = QVBoxLayout(dlg)
        form = QFormLayout()
        nom_input = QLineEdit()
        form.addRow("Nom de la matiere :", nom_input)
        lay.addLayout(form)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        lay.addWidget(btns)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        if dlg.exec_() == QDialog.Accepted and nom_input.text().strip():
            repos.add_matiere(nom_input.text().strip())
            return nom_input.text().strip()
        return None

    header1 = QHBoxLayout()
    header1.setSpacing(12)
    title1 = QVBoxLayout()
    title1.setSpacing(2)
    lbl_t1 = QLabel("Saisie par Matiere")
    lbl_t1.setStyleSheet(STYLE_HEADER_TITLE)
    title1.addWidget(lbl_t1)
    lbl_s1 = QLabel("Selectionnez une classe et une matiere pour saisir les notes de tous les eleves")
    lbl_s1.setStyleSheet(STYLE_HEADER_SUBTITLE)
    title1.addWidget(lbl_s1)
    header1.addLayout(title1)
    header1.addStretch(1)
    btn_add_matiere_h1 = QPushButton("+ Matiere")
    btn_add_matiere_h1.setCursor(Qt.PointingHandCursor)
    btn_add_matiere_h1.setStyleSheet(STYLE_BTN_ADD)
    header1.addWidget(btn_add_matiere_h1)
    btn_bulletins = QPushButton("Generer les Bulletins")
    btn_bulletins.setCursor(Qt.PointingHandCursor)
    btn_bulletins.setStyleSheet(STYLE_BTN_PRIMARY)
    header1.addWidget(btn_bulletins)
    tab_saisie_layout.addLayout(header1)

    sel1 = QFrame()
    sel1.setStyleSheet(STYLE_SELECTOR)
    sel1_lay = QHBoxLayout(sel1)
    sel1_lay.setContentsMargins(12, 8, 12, 8)
    sel1_lay.setSpacing(10)
    sel1_lay.addWidget(QLabel("Classe :"))
    combo_classe = QComboBox()
    combo_classe.setMinimumWidth(160)
    sel1_lay.addWidget(combo_classe)
    sel1_lay.addWidget(QLabel("Matiere :"))
    combo_matiere = QComboBox()
    combo_matiere.setMinimumWidth(160)
    sel1_lay.addWidget(combo_matiere)
    sel1_lay.addWidget(QLabel("Periode :"))
    combo_periode = QComboBox()
    for p in PERIODES:
        combo_periode.addItem(p)
    sel1_lay.addWidget(combo_periode)
    sel1_lay.addStretch(1)
    btn_charger = QPushButton("Charger les Eleves")
    btn_charger.setCursor(Qt.PointingHandCursor)
    btn_charger.setStyleSheet(STYLE_BTN_SECONDARY)
    sel1_lay.addWidget(btn_charger)
    tab_saisie_layout.addWidget(sel1)

    table_notes = QTableWidget(0, 7)
    table_notes.setHorizontalHeaderLabels([
        "Matricule", "Nom et Prenom", "Devoir 1 /20",
        "Devoir 2 /20", "Composition /20", "Moyenne", "Appreciation"])
    if ctx.can_edit("notes"):
        table_notes.setEditTriggers(QTableWidget.DoubleClicked | QTableWidget.EditKeyPressed)
    else:
        table_notes.setEditTriggers(QTableWidget.NoEditTriggers)
    table_notes.setSelectionBehavior(QTableWidget.SelectRows)
    table_notes.setAlternatingRowColors(True)
    table_notes.setShowGrid(False)
    table_notes.verticalHeader().setVisible(False)
    table_notes.verticalHeader().setDefaultSectionSize(42)
    table_notes.horizontalHeader().setStretchLastSection(True)
    table_notes.horizontalHeader().setMinimumSectionSize(80)
    table_notes.setStyleSheet(STYLE_TABLE)
    tab_saisie_layout.addWidget(table_notes, 1)
    _fit_rows(table_notes)

    lbl_empty = QLabel("Choisissez une classe et une matiere, puis cliquez 'Charger les Eleves'")
    lbl_empty.setStyleSheet(STYLE_EMPTY_STATE)
    lbl_empty.setAlignment(Qt.AlignCenter)
    tab_saisie_layout.addWidget(lbl_empty)
    lbl_empty.setVisible(False)

    bottom1 = QHBoxLayout()
    lbl_status = QLabel("Aucune modification en attente")
    lbl_status.setStyleSheet(STYLE_STATUS)
    bottom1.addWidget(lbl_status)
    bottom1.addStretch(1)
    btn_save = QPushButton("Enregistrer les Notes")
    btn_save.setCursor(Qt.PointingHandCursor)
    btn_save.setStyleSheet(STYLE_BTN_SUCCESS)
    bottom1.addWidget(btn_save)
    tab_saisie_layout.addLayout(bottom1)

    _fill_combos(combo_classe, [])
    for c in repos.classes():
        combo_classe.addItem(c["nom"], c["id"])
    _fill_combos(combo_matiere, [])
    for m in repos.matieres():
        combo_matiere.addItem(m["nom"], m["id"])

    def _refresh_matieres(select_id=None):
        combo_matiere.blockSignals(True)
        combo_matiere.clear()
        for m in repos.matieres():
            combo_matiere.addItem(m["nom"], m["id"])
        if select_id is not None:
            idx = combo_matiere.findData(select_id)
            if idx >= 0:
                combo_matiere.setCurrentIndex(idx)
        combo_matiere.blockSignals(False)

    def add_matiere():
        added = _add_matiere_dialog()
        if added:
            _refresh_matieres()
            lbl_status.setText(f"Matiere '{added}' ajoutee")

    btn_add_matiere_h1.clicked.connect(add_matiere)

    if not ctx.can_edit("notes"):
        btn_save.setVisible(False)

    # Selection reellement chargee dans la table (peut différer des combos
    # si l'utilisateur les change sans recharger). On enregistre TOUJOURS
    # par rapport a cette selection chargee, jamais par rapport aux combos.
    etat1 = {"charge": None}
    etat2 = {"charge": None}

    def recompute_row(row):
        d1 = _cell_float(table_notes.item(row, 2))
        d2 = _cell_float(table_notes.item(row, 3))
        comp = _cell_float(table_notes.item(row, 4))
        if d1 is None and d2 is None and comp is None:
            table_notes.setItem(row, 5, QTableWidgetItem(""))
            table_notes.setItem(row, 6, QTableWidgetItem(""))
            return
        moyenne = round(((d1 or 0) + (d2 or 0) + 2 * (comp or 0)) / 4, 2)
        table_notes.setItem(row, 5, QTableWidgetItem(f"{moyenne:.2f}"))
        table_notes.setItem(row, 6, QTableWidgetItem(_appreciation(moyenne)))

    def on_item_changed(item):
        if item.column() in (2, 3, 4):
            texte = item.text().replace(",", ".")
            if texte.strip():
                try:
                    val = float(texte)
                    if val < 0 or val > 20:
                        table_notes.blockSignals(True)
                        item.setText(f"{max(0.0, min(20.0, val)):.1f}")
                        table_notes.blockSignals(False)
                except ValueError:
                    table_notes.blockSignals(True)
                    item.setText("")
                    table_notes.blockSignals(False)
            recompute_row(item.row())
            lbl_status.setText("Modifications en attente")

    table_notes.itemChanged.connect(on_item_changed)

    def load_classe():
        _reload_combo(combo_classe, _classe_items(avec_toutes=False))
        _reload_combo(combo_matiere, [(m["nom"], m["id"]) for m in repos.matieres()])
        classe_id = combo_classe.currentData()
        matiere_id = combo_matiere.currentData()
        periode = combo_periode.currentText()
        if not classe_id or not matiere_id:
            return
        eleves_rows = repos.eleves(classe_id=classe_id)
        notes_rows = repos.notes_for(classe_id, matiere_id, periode)
        notes_map = {n["eleve_id"]: n for n in notes_rows}
        table_notes.blockSignals(True)
        table_notes.setRowCount(len(eleves_rows))
        for i, e in enumerate(eleves_rows):
            item_mat = QTableWidgetItem(e["matricule"])
            # L'eleve est attache a sa ligne : la sauvegarde ne peut plus
            # associer les notes au mauvais eleve via un simple index.
            item_mat.setData(Qt.UserRole, e["id"])
            table_notes.setItem(i, 0, item_mat)
            table_notes.setItem(i, 1, QTableWidgetItem(f"{e['prenom']} {e['nom']}"))
            note = notes_map.get(e["id"])
            for j, key in ((2, "devoir1"), (3, "devoir2"), (4, "composition")):
                val = note[key] if note and note[key] is not None else ""
                table_notes.setItem(i, j, QTableWidgetItem("" if val == "" else str(val)))
            recompute_row(i)
        table_notes.blockSignals(False)
        etat1["charge"] = {"classe_id": classe_id, "matiere_id": matiere_id,
                           "periode": periode}
        lbl_status.setText(f"{len(eleves_rows)} eleves charges")
        table_notes.resizeColumnsToContents()
        lbl_empty.setVisible(len(eleves_rows) == 0)

    def save_notes():
        if etat1["charge"] is None:
            QMessageBox.warning(page, "Notes",
                                "Chargez d'abord les eleves avant d'enregistrer.")
            return
        sel = {"classe_id": combo_classe.currentData(),
               "matiere_id": combo_matiere.currentData(),
               "periode": combo_periode.currentText()}
        if sel != etat1["charge"]:
            QMessageBox.warning(
                page, "Selection modifiee",
                "La selection (classe/matiere/periode) a change depuis le "
                "chargement. Cliquez 'Charger les Eleves' pour recharger, "
                "puis enregistrez : evite d'ecrire les notes affichees sur "
                "une autre selection.")
            return
        saved = 0
        for i in range(table_notes.rowCount()):
            item_mat = table_notes.item(i, 0)
            eleve_id = item_mat.data(Qt.UserRole) if item_mat else None
            if eleve_id is None:
                continue
            d1 = _cell_float(table_notes.item(i, 2))
            d2 = _cell_float(table_notes.item(i, 3))
            comp = _cell_float(table_notes.item(i, 4))
            if d1 is None and d2 is None and comp is None:
                continue
            repos.save_note(eleve_id, sel["matiere_id"], sel["periode"],
                            d1, d2, comp)
            saved += 1
        lbl_status.setText(f"{saved} notes enregistrees")
        QMessageBox.information(page, "Notes", f"{saved} notes enregistrees.")

    btn_charger.clicked.connect(load_classe)
    btn_save.clicked.connect(save_notes)

    def bulletins():
        classe_id = combo_classe.currentData()
        if not classe_id:
            QMessageBox.warning(page, "Bulletins", "Choisissez une classe.")
            return
        reports.bulletins(classe_id, combo_periode.currentText())

    btn_bulletins.clicked.connect(bulletins)

    header2 = QHBoxLayout()
    header2.setSpacing(12)
    title2 = QVBoxLayout()
    title2.setSpacing(2)
    lbl_t2 = QLabel("Saisie par Eleve")
    lbl_t2.setStyleSheet(STYLE_HEADER_TITLE)
    title2.addWidget(lbl_t2)
    lbl_s2 = QLabel("Selectionnez un eleve pour saisir ses notes dans toutes les matieres")
    lbl_s2.setStyleSheet(STYLE_HEADER_SUBTITLE)
    title2.addWidget(lbl_s2)
    header2.addLayout(title2)
    header2.addStretch(1)
    tab_eleve_layout.addLayout(header2)

    sel2 = QFrame()
    sel2.setStyleSheet(STYLE_SELECTOR)
    sel2_lay = QHBoxLayout(sel2)
    sel2_lay.setContentsMargins(12, 8, 12, 8)
    sel2_lay.setSpacing(10)
    sel2_lay.addWidget(QLabel("Classe :"))
    combo_ev_classe = QComboBox()
    combo_ev_classe.setMinimumWidth(160)
    sel2_lay.addWidget(combo_ev_classe)
    sel2_lay.addWidget(QLabel("Eleve :"))
    combo_ev_eleve = QComboBox()
    combo_ev_eleve.setMinimumWidth(200)
    sel2_lay.addWidget(combo_ev_eleve)
    sel2_lay.addWidget(QLabel("Periode :"))
    combo_ev_periode = QComboBox()
    for p in PERIODES:
        combo_ev_periode.addItem(p)
    sel2_lay.addWidget(combo_ev_periode)
    sel2_lay.addStretch(1)
    btn_ev_charger = QPushButton("Charger les Notes")
    btn_ev_charger.setCursor(Qt.PointingHandCursor)
    btn_ev_charger.setStyleSheet(STYLE_BTN_SECONDARY)
    sel2_lay.addWidget(btn_ev_charger)
    tab_eleve_layout.addWidget(sel2)

    for c in repos.classes():
        combo_ev_classe.addItem(c["nom"], c["id"])

    def _on_ev_classe_changed():
        combo_ev_eleve.clear()
        cid = combo_ev_classe.currentData()
        if not cid:
            return
        for e in repos.eleves(classe_id=cid):
            combo_ev_eleve.addItem(f"{e['prenom']} {e['nom']} ({e['matricule']})", e["id"])

    combo_ev_classe.currentIndexChanged.connect(_on_ev_classe_changed)
    if combo_ev_classe.count():
        _on_ev_classe_changed()

    table_ev = QTableWidget(0, 6)
    table_ev.setHorizontalHeaderLabels([
        "Matiere", "Coefficient", "Devoir 1 /20",
        "Devoir 2 /20", "Composition /20", "Moyenne /20"])
    table_ev.setEditTriggers(QTableWidget.DoubleClicked | QTableWidget.EditKeyPressed)
    table_ev.setSelectionBehavior(QTableWidget.SelectRows)
    table_ev.setAlternatingRowColors(True)
    table_ev.setShowGrid(False)
    table_ev.verticalHeader().setVisible(False)
    table_ev.verticalHeader().setDefaultSectionSize(44)
    table_ev.horizontalHeader().setStretchLastSection(True)
    table_ev.horizontalHeader().setMinimumSectionSize(80)
    table_ev.setStyleSheet(STYLE_TABLE)
    tab_eleve_layout.addWidget(table_ev, 1)

    lbl_ev_empty = QLabel("Selectionnez un eleve, puis cliquez 'Charger les Notes'")
    lbl_ev_empty.setStyleSheet(STYLE_EMPTY_STATE)
    lbl_ev_empty.setAlignment(Qt.AlignCenter)
    tab_eleve_layout.addWidget(lbl_ev_empty)
    lbl_ev_empty.setVisible(True)
    table_ev.setVisible(False)

    bottom2 = QHBoxLayout()
    lbl_ev_status = QLabel("")
    lbl_ev_status.setStyleSheet(STYLE_STATUS)
    bottom2.addWidget(lbl_ev_status)
    bottom2.addStretch(1)
    btn_ev_save = QPushButton("Enregistrer les Notes")
    btn_ev_save.setCursor(Qt.PointingHandCursor)
    btn_ev_save.setStyleSheet(STYLE_BTN_SUCCESS)
    bottom2.addWidget(btn_ev_save)
    tab_eleve_layout.addLayout(bottom2)
    btn_ev_save.setVisible(ctx.can_edit("notes"))
    if not ctx.can_edit("notes"):
        # Lecture seule effective des deux tables de saisie
        table_notes.setEditTriggers(QTableWidget.NoEditTriggers)
        table_ev.setEditTriggers(QTableWidget.NoEditTriggers)

    def _ev_recompute_row(row):
        d1 = _cell_float(table_ev.item(row, 2))
        d2 = _cell_float(table_ev.item(row, 3))
        comp = _cell_float(table_ev.item(row, 4))
        if d1 is None and d2 is None and comp is None:
            table_ev.setItem(row, 5, QTableWidgetItem(""))
            return
        moyenne = round(((d1 or 0) + (d2 or 0) + 2 * (comp or 0)) / 4, 2)
        cell = QTableWidgetItem(f"{moyenne:.2f}")
        if moyenne < 10:
            cell.setForeground(QBrush(QColor(C_DANGER)))
        elif moyenne >= 14:
            cell.setForeground(QBrush(QColor(C_SUCCESS_DARK)))
        table_ev.setItem(row, 5, cell)

    def _ev_on_item_changed(item):
        if item.column() in (2, 3, 4):
            texte = item.text().replace(",", ".")
            if texte.strip():
                try:
                    val = float(texte)
                    if val < 0 or val > 20:
                        table_ev.blockSignals(True)
                        item.setText(f"{max(0.0, min(20.0, val)):.1f}")
                        table_ev.blockSignals(False)
                except ValueError:
                    table_ev.blockSignals(True)
                    item.setText("")
                    table_ev.blockSignals(False)
            _ev_recompute_row(item.row())
            lbl_ev_status.setText("Modifications en attente")

    table_ev.itemChanged.connect(_ev_on_item_changed)

    def load_eleve_notes():
        eleve_id = combo_ev_eleve.currentData()
        periode = combo_ev_periode.currentText()
        if not eleve_id:
            return
        all_matieres = repos.matieres()
        notes_rows = repos.notes_eleve(eleve_id, periode)
        notes_map = {n["matiere_id"]: n for n in notes_rows}
        table_ev.blockSignals(True)
        table_ev.setRowCount(len(all_matieres))
        for i, m in enumerate(all_matieres):
            item_mat = QTableWidgetItem(m["nom"])
            # La matiere est attachee a sa ligne par id : plus de recherche
            # par nom (doublons/renommages ne corrompent plus la sauvegarde).
            item_mat.setData(Qt.UserRole, m["id"])
            table_ev.setItem(i, 0, item_mat)
            coeff_item = QTableWidgetItem(f"{m['coefficient']:.1f}")
            coeff_item.setFlags(coeff_item.flags() & ~Qt.ItemIsEditable)
            table_ev.setItem(i, 1, coeff_item)
            note = notes_map.get(m["id"])
            for j, key in ((2, "devoir1"), (3, "devoir2"), (4, "composition")):
                val = note[key] if note and note[key] is not None else ""
                table_ev.setItem(i, j, QTableWidgetItem("" if val == "" else str(val)))
            _ev_recompute_row(i)
        table_ev.blockSignals(False)
        etat2["charge"] = {"eleve_id": eleve_id, "periode": periode}
        table_ev.resizeColumnsToContents()
        table_ev.setVisible(True)
        lbl_ev_empty.setVisible(False)
        nb_notes = sum(1 for n in notes_rows
                       if n.get("devoir1") is not None or n.get("devoir2") is not None
                       or n.get("composition") is not None)
        lbl_ev_status.setText(f"{len(all_matieres)} matieres | {nb_notes} notes existantes")

    def save_eleve_notes():
        if etat2["charge"] is None:
            QMessageBox.warning(page, "Notes",
                                "Chargez d'abord les notes avant d'enregistrer.")
            return
        sel = {"eleve_id": combo_ev_eleve.currentData(),
               "periode": combo_ev_periode.currentText()}
        if sel != etat2["charge"]:
            QMessageBox.warning(
                page, "Selection modifiee",
                "L'eleve ou la periode a change depuis le chargement. "
                "Cliquez 'Charger les Notes' pour recharger, puis enregistrez.")
            return
        eleve_id = sel["eleve_id"]
        saved = 0
        for i in range(table_ev.rowCount()):
            matiere_item = table_ev.item(i, 0)
            if not matiere_item:
                continue
            matiere_id = matiere_item.data(Qt.UserRole)
            if not matiere_id:
                continue
            d1 = _cell_float(table_ev.item(i, 2))
            d2 = _cell_float(table_ev.item(i, 3))
            comp = _cell_float(table_ev.item(i, 4))
            if d1 is None and d2 is None and comp is None:
                continue
            repos.save_note(eleve_id, matiere_id, periode=sel["periode"],
                            devoir1=d1, devoir2=d2, composition=comp)
            saved += 1
        lbl_ev_status.setText(f"{saved} notes enregistrees")
        QMessageBox.information(page, "Notes", f"{saved} notes enregistrees.")

    btn_ev_charger.clicked.connect(load_eleve_notes)
    btn_ev_save.clicked.connect(save_eleve_notes)

    lbl_moy_title = QLabel("Moyennes Generales de la Classe")
    lbl_moy_title.setStyleSheet(STYLE_HEADER_TITLE)
    tab_moyennes_layout.addWidget(lbl_moy_title)

    moy_selector = QFrame()
    moy_selector.setStyleSheet(STYLE_SELECTOR)
    moy_sel_layout = QHBoxLayout(moy_selector)
    moy_sel_layout.setContentsMargins(12, 8, 12, 8)
    moy_sel_layout.setSpacing(10)
    lbl_moy_cls = QLabel("Classe :")
    moy_sel_layout.addWidget(lbl_moy_cls)
    combo_moy_classe = QComboBox()
    combo_moy_classe.setMinimumWidth(160)
    moy_sel_layout.addWidget(combo_moy_classe)
    moy_sel_layout.addWidget(QLabel("Periode :"))
    combo_moy_periode = QComboBox()
    for p in PERIODES:
        combo_moy_periode.addItem(p)
    moy_sel_layout.addWidget(combo_moy_periode)
    moy_sel_layout.addStretch(1)
    btn_calculer = QPushButton("Calculer les Moyennes")
    btn_calculer.setCursor(Qt.PointingHandCursor)
    btn_calculer.setStyleSheet(STYLE_BTN_PRIMARY)
    btn_export_csv = QPushButton("Exporter CSV")
    btn_export_csv.setCursor(Qt.PointingHandCursor)
    btn_export_csv.setStyleSheet(STYLE_BTN_SECONDARY)
    moy_sel_layout.addWidget(btn_calculer)
    moy_sel_layout.addWidget(btn_export_csv)
    tab_moyennes_layout.addWidget(moy_selector)

    table_moy = QTableWidget(0, 5)
    table_moy.setHorizontalHeaderLabels(
        ["Rang", "Matricule", "Eleve", "Moyenne Generale", "Appreciation"])
    table_moy.setEditTriggers(QTableWidget.NoEditTriggers)
    table_moy.setSelectionBehavior(QTableWidget.SelectRows)
    table_moy.setAlternatingRowColors(True)
    table_moy.setShowGrid(False)
    table_moy.verticalHeader().setVisible(False)
    table_moy.verticalHeader().setDefaultSectionSize(44)
    table_moy.horizontalHeader().setStretchLastSection(True)
    table_moy.horizontalHeader().setMinimumSectionSize(80)
    table_moy.setStyleSheet(STYLE_TABLE)
    table_moy.setVisible(False)
    tab_moyennes_layout.addWidget(table_moy, 1)

    lbl_moy_empty = QLabel("Choisissez une classe et une periode, puis cliquez 'Calculer les Moyennes'")
    lbl_moy_empty.setStyleSheet(STYLE_EMPTY_STATE)
    lbl_moy_empty.setAlignment(Qt.AlignCenter)
    tab_moyennes_layout.addWidget(lbl_moy_empty)

    lbl_moy_status = QLabel("")
    lbl_moy_status.setStyleSheet(STYLE_STATUS)
    tab_moyennes_layout.addWidget(lbl_moy_status)

    def _sync_moy_classes():
        combo_moy_classe.blockSignals(True)
        combo_moy_classe.clear()
        for c in repos.classes():
            combo_moy_classe.addItem(c["nom"], c["id"])
        idx = combo_moy_classe.findData(combo_classe.currentData())
        if idx >= 0:
            combo_moy_classe.setCurrentIndex(idx)
        combo_moy_classe.blockSignals(False)

    def calculer_moyennes():
        classe_id = combo_moy_classe.currentData()
        if not classe_id:
            QMessageBox.warning(page, "Moyennes", "Choisissez une classe.")
            return
        periode = combo_moy_periode.currentText()
        matieres = repos.matieres()
        if not matieres:
            QMessageBox.warning(page, "Moyennes", "Aucune matiere enregistree.")
            return
        eleves_rows = repos.eleves(classe_id=classe_id)
        notes_data = repos.notes_classe(classe_id, periode)

        eleve_notes = {}
        for n in notes_data:
            eid = n["eleve_id"]
            if eid not in eleve_notes:
                eleve_notes[eid] = {}
            if n["devoir1"] is not None or n["devoir2"] is not None or n["composition"] is not None:
                d1 = n["devoir1"] or 0
                d2 = n["devoir2"] or 0
                comp = n["composition"] or 0
                moy = round((d1 + d2 + 2 * comp) / 4, 2)
                eleve_notes[eid][n["matiere_id"]] = {
                    "moyenne": moy,
                    "coeff": n["matiere_coeff"] or 1,
                    "nom": n["matiere_nom"]
                }

        resultats = []
        for e in eleves_rows:
            eid = e["id"]
            mn = eleve_notes.get(eid, {})
            total_pondere = 0.0
            total_coefs = 0.0
            for mt in matieres:
                if mt["id"] in mn:
                    total_pondere += mn[mt["id"]]["moyenne"] * mn[mt["id"]]["coeff"]
                    total_coefs += mn[mt["id"]]["coeff"]
            generale = round(total_pondere / total_coefs, 2) if total_coefs > 0 else None
            resultats.append({
                "eleve": e, "generale": generale,
                "appreciation": _appreciation(generale) if generale is not None else "-",
                "matieres_notes": mn,
            })

        resultats.sort(key=lambda r: r["generale"] if r["generale"] is not None else -1, reverse=True)

        col_count = 5 + len(matieres)
        table_moy.setColumnCount(col_count)
        headers = ["Rang", "Matricule", "Eleve"]
        for mt in matieres:
            headers.append(f"{mt['nom'][:12]} /20")
        headers.extend(["Generale /20", "Appreciation"])
        table_moy.setHorizontalHeaderLabels(headers)
        table_moy.setRowCount(len(resultats))

        for rank, r in enumerate(resultats, 1):
            e = r["eleve"]
            ri = rank - 1
            table_moy.setItem(ri, 0, QTableWidgetItem(str(rank)))
            table_moy.setItem(ri, 1, QTableWidgetItem(e["matricule"]))
            table_moy.setItem(ri, 2, QTableWidgetItem(f"{e['prenom']} {e['nom']}"))
            col = 3
            for mt in matieres:
                note = r["matieres_notes"].get(mt["id"])
                if note:
                    item = QTableWidgetItem(f"{note['moyenne']:.2f}")
                    if note["moyenne"] < 10:
                        item.setForeground(QBrush(QColor(C_DANGER)))
                    elif note["moyenne"] >= 14:
                        item.setForeground(QBrush(QColor(C_SUCCESS_DARK)))
                    table_moy.setItem(ri, col, item)
                else:
                    table_moy.setItem(ri, col, QTableWidgetItem("-"))
                col += 1
            gen = r["generale"]
            if gen is not None:
                gen_item = QTableWidgetItem(f"{gen:.2f}")
                if gen < 10:
                    gen_item.setForeground(QBrush(QColor(C_DANGER)))
                elif gen >= 14:
                    gen_item.setForeground(QBrush(QColor(C_SUCCESS_DARK)))
                gen_item.setFont(QFont("", -1, QFont.Bold))
                table_moy.setItem(ri, col, gen_item)
            else:
                table_moy.setItem(ri, col, QTableWidgetItem("-"))
            table_moy.setItem(ri, col + 1, QTableWidgetItem(r["appreciation"]))

        table_moy.resizeColumnsToContents()
        table_moy.setVisible(bool(resultats))
        lbl_moy_empty.setVisible(not resultats)
        avec_notes = [r for r in resultats if r["generale"] is not None]
        sans_notes = len(resultats) - len(avec_notes)
        if avec_notes:
            moy_classe = round(sum(r["generale"] for r in avec_notes) / len(avec_notes), 2)
            best = avec_notes[0]
            worst = avec_notes[-1]
            status = (f"{len(avec_notes)} eleves avec notes | "
                      f"Moyenne de classe : {moy_classe:.2f} | "
                      f"Meilleur : {best['eleve']['prenom']} {best['eleve']['nom']} ({best['generale']:.2f}) | "
                      f"A ameliorer : {worst['eleve']['prenom']} {worst['eleve']['nom']} ({worst['generale']:.2f})")
            if sans_notes:
                status += f" | {sans_notes} sans notes"
        else:
            status = "Aucune note saisie pour cette classe et cette periode"
        lbl_moy_status.setText(status)

    def export_moyennes_csv():
        if table_moy.rowCount() == 0:
            QMessageBox.warning(
                page, "Export",
                "Calculez d'abord les moyennes : il n'y a rien a exporter.")
            return
        from PyQt5.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(
            page, "Exporter les Moyennes", "moyennes_generales.csv", "CSV (*.csv)")
        if not path:
            return
        with open(path, "w", encoding="utf-8-sig") as f:
            headers = [table_moy.horizontalHeaderItem(j).text()
                       for j in range(table_moy.columnCount())]
            f.write(";".join(headers) + "\n")
            for i in range(table_moy.rowCount()):
                row_data = []
                for j in range(table_moy.columnCount()):
                    item = table_moy.item(i, j)
                    row_data.append(item.text() if item else "")
                f.write(";".join(row_data) + "\n")
        QMessageBox.information(page, "Export", f"Moyennes exportees vers {path}")

    btn_calculer.clicked.connect(calculer_moyennes)
    btn_export_csv.clicked.connect(export_moyennes_csv)

    # Le combo des moyennes suit la classe choisie dans le 1er onglet :
    # sinon le calcul pouvait porter sur l'ancienne classe.
    combo_classe.currentIndexChanged.connect(_sync_moy_classes)

    def _refresh_notes():
        _reload_combo(combo_classe, _classe_items(avec_toutes=False))
        _reload_combo(combo_matiere, [(m["nom"], m["id"]) for m in repos.matieres()])
        _sync_moy_classes()
        # Onglet 2 : les combos classe/eleve doivent suivre les creations
        # faites dans d'autres sections (eleves, classes).
        courant = combo_ev_classe.currentData()
        combo_ev_classe.blockSignals(True)
        combo_ev_classe.clear()
        for c in repos.classes():
            combo_ev_classe.addItem(c["nom"], c["id"])
        if courant is not None:
            idx = combo_ev_classe.findData(courant)
            if idx >= 0:
                combo_ev_classe.setCurrentIndex(idx)
        combo_ev_classe.blockSignals(False)
        _on_ev_classe_changed()

    page.refresh = _refresh_notes
