from PyQt5.QtCore import Qt
from PyQt5.QtGui import QBrush, QColor, QFont
from PyQt5.QtWidgets import (
    QHBoxLayout, QLabel, QMessageBox, QComboBox, QPushButton, QTableWidgetItem,
    QVBoxLayout, QTableWidget, QTabWidget, QWidget, QFileDialog, QStackedWidget,
    QDialog, QFormLayout, QLineEdit, QDialogButtonBox,
)

from repositories import repos
from services import pdf_export
from services import rapports
from ui import toast
from ui.pages.helpers import (
    _btn, _classe_items, _reload_combo, _appreciation, _fill_combos,
)
from ui.widgets import DataTable, EmptyState, PageHeader
from core.config import (
    PERIODES, C_DANGER, C_SUCCESS_DARK,
    STYLE_BTN_PRIMARY, STYLE_BTN_SECONDARY, STYLE_BTN_SUCCESS, STYLE_BTN_ADD,
)


def _table(sans_edition=False):
    """Tableau centralise + reactivation de l'edition si besoin."""
    t = DataTable()
    t.setShowGrid(False)
    t.horizontalHeader().setMinimumSectionSize(80)
    if not sans_edition:
        t.setEditTriggers(QTableWidget.DoubleClicked | QTableWidget.EditKeyPressed)
    return t


def notes(page, ctx):
    if page.layout() is not None:
        return
    peut_editer = ctx.can_edit("notes")
    page_layout = QVBoxLayout(page)
    page_layout.setContentsMargins(20, 20, 20, 20)
    page_layout.setSpacing(16)

    tabs = QTabWidget()
    tabs.setDocumentMode(True)
    page_layout.addWidget(tabs)

    # ---------------- Onglet 1 : Saisie par Matiere ----------------
    tab_saisie = QWidget()
    lay1 = QVBoxLayout(tab_saisie)
    lay1.setContentsMargins(0, 8, 0, 0)
    lay1.setSpacing(12)
    tabs.addTab(tab_saisie, "Saisie par Matiere")
    h1 = PageHeader(
        "Saisie par Matiere",
        "Selectionnez une classe et une matiere pour saisir les notes "
        "de tous les eleves")
    lay1.addWidget(h1)

    filtre1 = QHBoxLayout()
    combo_classe = QComboBox()
    combo_matiere = QComboBox()
    combo_periode = QComboBox()
    for p in PERIODES:
        combo_periode.addItem(p)
    filtre1.addWidget(QLabel("Classe :"))
    filtre1.addWidget(combo_classe)
    filtre1.addWidget(QLabel("Matiere :"))
    filtre1.addWidget(combo_matiere)
    filtre1.addWidget(QLabel("Periode :"))
    filtre1.addWidget(combo_periode)
    filtre1.addStretch(1)
    btn_charger = QPushButton("Charger les Eleves")
    btn_charger.setCursor(Qt.PointingHandCursor)
    btn_charger.setStyleSheet(STYLE_BTN_SECONDARY)
    filtre1.addWidget(btn_charger)
    lay1.addLayout(filtre1)

    table_notes = _table(sans_edition=not peut_editer)
    table_notes.setColumnCount(7)
    table_notes.setHorizontalHeaderLabels([
        "Matricule", "Nom et Prenom", "Devoir 1 /20",
        "Devoir 2 /20", "Composition /20", "Moyenne", "Appreciation"])
    vide1 = EmptyState(
        "Choisissez une classe et une matiere",
        "Cliquez ensuite 'Charger les Eleves' pour voir la feuille de notes.")
    pile1 = QStackedWidget()
    pile1.addWidget(table_notes)
    pile1.addWidget(vide1)
    lay1.addWidget(pile1, 1)

    bottom1 = QHBoxLayout()
    lbl_status = QLabel("Aucune modification en attente")
    bottom1.addWidget(lbl_status)
    bottom1.addStretch(1)
    btn_save = QPushButton("Enregistrer les Notes")
    btn_save.setCursor(Qt.PointingHandCursor)
    btn_save.setStyleSheet(STYLE_BTN_SUCCESS)
    btn_save.setVisible(peut_editer)
    bottom1.addWidget(btn_save)
    lay1.addLayout(bottom1)

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

    def _add_matiere_dialog():
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
        btns.rejected.connect(dlg.reject)

        def valider():
            if not nom_input.text().strip():
                QMessageBox.warning(dlg, "Matiere", "Le nom est obligatoire.")
                return
            repos.add_matiere(nom_input.text().strip())
            dlg.accept()

        btns.accepted.connect(valider)
        if dlg.exec_() == QDialog.Accepted:
            return nom_input.text().strip()
        return None

    def add_matiere():
        added = _add_matiere_dialog()
        if added:
            _refresh_matieres()
            lbl_status.setText(f"Matiere '{added}' ajoutee")

    btn_add_matiere_h1 = _btn("+ Matiere", add_matiere, STYLE_BTN_ADD)
    h1.ajouter_action(btn_add_matiere_h1)
    btn_bulletins = QPushButton("Generer les Bulletins")
    btn_bulletins.setCursor(Qt.PointingHandCursor)
    btn_bulletins.setStyleSheet(STYLE_BTN_PRIMARY)
    h1.ajouter_action(btn_bulletins)

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
        _reload_combo(combo_matiere,
                      [(m["nom"], m["id"]) for m in repos.matieres()])
        classe_id = combo_classe.currentData()
        matiere_id = combo_matiere.currentData()
        periode = combo_periode.currentText()
        if not classe_id or not matiere_id:
            pile1.setCurrentWidget(vide1)
            return
        eleves_rows = repos.eleves(classe_id=classe_id)
        notes_rows = repos.notes_for(classe_id, matiere_id, periode)
        notes_map = {n["eleve_id"]: n for n in notes_rows}
        table_notes.blockSignals(True)
        table_notes.setRowCount(len(eleves_rows))
        for i, e in enumerate(eleves_rows):
            item_mat = QTableWidgetItem(e["matricule"])
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
        table_notes.refresh_height()
        pile1.setCurrentWidget(vide1 if not eleves_rows else table_notes)

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
        if saved:
            toast.succes(page, f"{saved} notes enregistrees.")

    def bulletins():
        classe_id = combo_classe.currentData()
        if not classe_id:
            QMessageBox.warning(page, "Bulletins", "Choisissez une classe.")
            return
        try:
            pdf_export.bulletins_pdf(classe_id, combo_periode.currentText())
        except RuntimeError as e:
            QMessageBox.warning(page, "Bulletins", str(e))

    btn_charger.clicked.connect(load_classe)
    btn_save.clicked.connect(save_notes)
    btn_bulletins.clicked.connect(bulletins)

    # ---------------- Onglet 2 : Saisie par Eleve ----------------
    tab_eleve = QWidget()
    lay2 = QVBoxLayout(tab_eleve)
    lay2.setContentsMargins(0, 8, 0, 0)
    lay2.setSpacing(12)
    tabs.addTab(tab_eleve, "Saisie par Eleve")
    lay2.addWidget(PageHeader(
        "Saisie par Eleve",
        "Selectionnez un eleve pour saisir ses notes dans toutes les matieres"))

    filtre2 = QHBoxLayout()
    combo_ev_classe = QComboBox()
    combo_ev_eleve = QComboBox()
    combo_ev_periode = QComboBox()
    for p in PERIODES:
        combo_ev_periode.addItem(p)
    filtre2.addWidget(QLabel("Classe :"))
    filtre2.addWidget(combo_ev_classe)
    filtre2.addWidget(QLabel("Eleve :"))
    filtre2.addWidget(combo_ev_eleve)
    filtre2.addWidget(QLabel("Periode :"))
    filtre2.addWidget(combo_ev_periode)
    filtre2.addStretch(1)
    btn_ev_charger = QPushButton("Charger les Notes")
    btn_ev_charger.setCursor(Qt.PointingHandCursor)
    btn_ev_charger.setStyleSheet(STYLE_BTN_SECONDARY)
    filtre2.addWidget(btn_ev_charger)
    lay2.addLayout(filtre2)

    for c in repos.classes():
        combo_ev_classe.addItem(c["nom"], c["id"])

    def _on_ev_classe_changed():
        combo_ev_eleve.clear()
        cid = combo_ev_classe.currentData()
        if not cid:
            return
        for e in repos.eleves(classe_id=cid):
            combo_ev_eleve.addItem(f"{e['prenom']} {e['nom']} ({e['matricule']})",
                                   e["id"])

    combo_ev_classe.currentIndexChanged.connect(_on_ev_classe_changed)
    if combo_ev_classe.count():
        _on_ev_classe_changed()

    table_ev = _table(sans_edition=not peut_editer)
    table_ev.setColumnCount(6)
    table_ev.setHorizontalHeaderLabels([
        "Matiere", "Coefficient", "Devoir 1 /20",
        "Devoir 2 /20", "Composition /20", "Moyenne /20"])
    vide2 = EmptyState(
        "Selectionnez un eleve et une periode",
        "Cliquez ensuite 'Charger les Notes' pour saisir ses notes.")
    pile2 = QStackedWidget()
    pile2.addWidget(table_ev)
    pile2.addWidget(vide2)
    lay2.addWidget(pile2, 1)

    bottom2 = QHBoxLayout()
    lbl_ev_status = QLabel("")
    bottom2.addWidget(lbl_ev_status)
    bottom2.addStretch(1)
    btn_ev_save = QPushButton("Enregistrer les Notes")
    btn_ev_save.setCursor(Qt.PointingHandCursor)
    btn_ev_save.setStyleSheet(STYLE_BTN_SUCCESS)
    btn_ev_save.setVisible(peut_editer)
    bottom2.addWidget(btn_ev_save)
    lay2.addLayout(bottom2)

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
        table_ev.refresh_height()
        pile2.setCurrentWidget(table_ev)
        nb_notes = sum(1 for n in notes_rows
                       if n.get("devoir1") is not None or n.get("devoir2") is not None
                       or n.get("composition") is not None)
        lbl_ev_status.setText(
            f"{len(all_matieres)} matieres | {nb_notes} notes existantes")

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
        if saved:
            toast.succes(page, f"{saved} notes enregistrees.")

    btn_ev_charger.clicked.connect(load_eleve_notes)
    btn_ev_save.clicked.connect(save_eleve_notes)

    # ---------------- Onglet 3 : Moyennes Generales ----------------
    tab_moyennes = QWidget()
    lay3 = QVBoxLayout(tab_moyennes)
    lay3.setContentsMargins(0, 8, 0, 0)
    lay3.setSpacing(12)
    tabs.addTab(tab_moyennes, "Moyennes Generales")
    lay3.addWidget(PageHeader(
        "Moyennes Generales de la Classe",
        "Classement des eleves par moyenne generale sur la periode choisie"))

    filtre3 = QHBoxLayout()
    combo_moy_classe = QComboBox()
    combo_moy_periode = QComboBox()
    for p in PERIODES:
        combo_moy_periode.addItem(p)
    filtre3.addWidget(QLabel("Classe :"))
    filtre3.addWidget(combo_moy_classe)
    filtre3.addWidget(QLabel("Periode :"))
    filtre3.addWidget(combo_moy_periode)
    filtre3.addStretch(1)
    btn_calculer = QPushButton("Calculer les Moyennes")
    btn_calculer.setCursor(Qt.PointingHandCursor)
    btn_calculer.setStyleSheet(STYLE_BTN_PRIMARY)
    btn_export_csv = QPushButton("Exporter CSV")
    btn_export_csv.setCursor(Qt.PointingHandCursor)
    btn_export_csv.setStyleSheet(STYLE_BTN_SECONDARY)
    btn_export_pdf = QPushButton("Exporter PDF")
    btn_export_pdf.setCursor(Qt.PointingHandCursor)
    btn_export_pdf.setStyleSheet(STYLE_BTN_SECONDARY)
    filtre3.addWidget(btn_calculer)
    filtre3.addWidget(btn_export_csv)
    filtre3.addWidget(btn_export_pdf)
    lay3.addLayout(filtre3)

    table_moy = DataTable()
    table_moy.setShowGrid(False)
    table_moy.horizontalHeader().setMinimumSectionSize(80)
    vide3 = EmptyState(
        "Aucune moyenne calculee",
        "Choisissez une classe et une periode, puis cliquez "
        "'Calculer les Moyennes'.")
    pile3 = QStackedWidget()
    pile3.addWidget(table_moy)
    pile3.addWidget(vide3)
    lay3.addWidget(pile3, 1)

    lbl_moy_status = QLabel("")
    lay3.addWidget(lbl_moy_status)

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
            if (n["devoir1"] is not None or n["devoir2"] is not None
                    or n["composition"] is not None):
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
                "appreciation": (_appreciation(generale)
                                 if generale is not None else "-"),
                "matieres_notes": mn,
            })

        resultats.sort(
            key=lambda r: r["generale"] if r["generale"] is not None else -1,
            reverse=True)

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

        table_moy.refresh_height()
        pile3.setCurrentWidget(vide3 if not resultats else table_moy)
        avec_notes = [r for r in resultats if r["generale"] is not None]
        sans_notes = len(resultats) - len(avec_notes)
        if avec_notes:
            moy_classe = round(sum(r["generale"] for r in avec_notes)
                               / len(avec_notes), 2)
            best = avec_notes[0]
            worst = avec_notes[-1]
            status = (f"{len(avec_notes)} eleves avec notes | "
                      f"Moyenne de classe : {moy_classe:.2f} | "
                      f"Meilleur : {best['eleve']['prenom']} {best['eleve']['nom']} "
                      f"({best['generale']:.2f}) | "
                      f"A ameliorer : {worst['eleve']['prenom']} {worst['eleve']['nom']} "
                      f"({worst['generale']:.2f})")
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
        toast.succes(page, f"Moyennes exportees vers {path}")

    def export_moyennes_pdf():
        if table_moy.rowCount() == 0:
            QMessageBox.warning(
                page, "Export",
                "Calculez d'abord les moyennes : il n'y a rien a exporter.")
            return
        entetes = [table_moy.horizontalHeaderItem(j).text()
                   for j in range(table_moy.columnCount())]
        lignes = []
        for i in range(table_moy.rowCount()):
            row_data = []
            for j in range(table_moy.columnCount()):
                item = table_moy.item(i, j)
                row_data.append(item.text() if item else "")
            lignes.append(row_data)
        nom_classe = combo_moy_classe.currentText()
        rapports.export_table_pdf(
            f"Moyennes - {nom_classe} ({combo_moy_periode.currentText()})",
            "Resultats calcules depuis les notes saisies",
            entetes, lignes, "rapport_moyennes_detail.pdf")

    btn_calculer.clicked.connect(calculer_moyennes)
    btn_export_csv.clicked.connect(export_moyennes_csv)
    btn_export_pdf.clicked.connect(export_moyennes_pdf)
    combo_classe.currentIndexChanged.connect(_sync_moy_classes)

    def _refresh_notes():
        _reload_combo(combo_classe, _classe_items(avec_toutes=False))
        _reload_combo(combo_matiere,
                      [(m["nom"], m["id"]) for m in repos.matieres()])
        _sync_moy_classes()
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


def _cell_float(item):
    if not item or not item.text().strip():
        return None
    try:
        return float(item.text().replace(",", "."))
    except ValueError:
        return None