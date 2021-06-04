import os
from PyQt5 import QtWidgets, uic, QtGui, QtCore
from tools.utils import get_grouped_impfzentren
from typing import Tuple, List


PATH = os.path.dirname(os.path.realpath(__file__))


class QtImpfzentren(QtWidgets.QDialog):
    # Folgende Widgets stehen zur Verfügung:

    ### Layout ###
    # impfzentren_grid_layout

    ### ButtonBox ###
    # buttonBox
    # Ok
    # Cancel

    ### QWidget ###
    # scrollAreaWidgetContents

    # Signal welches geworfen wird, wenn man auf Apply drückt
    # Gibt einen String mit allen aktiven PLZ zurück
    update_impfzentren_plz = QtCore.pyqtSignal(str)

    def __init__(self, parent: QtWidgets.QWidget, pfad_fenster_layout=os.path.join(PATH, "impfzentren.ui")):
        super().__init__(parent=parent)

        # Laden der .ui Datei und init config
        uic.loadUi(pfad_fenster_layout, self)

        # ButtonBox Event verknüpfen
        self.buttonBox.clicked.connect(self.__button_box_clicked)

        self.init_layout()

    def init_layout(self):
        """
        Erstellt dynamisch die Gruppen, CheckBoxes und Labels
        """

        impfzentren: dict = get_grouped_impfzentren()

        for gruppe, zentren in impfzentren.items():
            row = self.impfzentren_grid_layout.rowCount()
            gruppen_font = QtGui.QFont()
            gruppen_font.setPointSize(12)
            gruppen_font.setUnderline(True)

            horizontale_linie = self.get_horizontale_linie()
            gruppen_label = QtWidgets.QLabel(f"{gruppe} - {zentren[0]['Bundesland']}")
            gruppen_label.setFont(gruppen_font)

            self.impfzentren_grid_layout.addWidget(horizontale_linie, row, 0, 1, 1)
            self.impfzentren_grid_layout.addWidget(gruppen_label, row+1, 0, 1, 1)

            form_layout = QtWidgets.QFormLayout()
            form_layout.setVerticalSpacing(15)
            form_layout.setHorizontalSpacing(10)
            for zentrum in zentren:
                checkbox, info_grid = self.get_zentrum_widgets(gruppe, zentrum)

                # Skippen, wenn es keine PLZ gibt (bsp. Gruppe 10)
                if checkbox.property("PLZ"):
                    form_layout.addRow(checkbox, info_grid)

            self.impfzentren_grid_layout.addLayout(form_layout, row+2, 0, 1, 1)

    def get_horizontale_linie(self) -> QtWidgets.QFrame:
        """
        Erstellt eine Horizontal Linie

        Returns:
            QtWidgets.QFrame: [description]
        """

        linie = QtWidgets.QFrame()
        linie.setMinimumWidth(1)
        linie.setFixedHeight(20)
        linie.setFrameShape(QtWidgets.QFrame.HLine)
        linie.setFrameShadow(QtWidgets.QFrame.Sunken)
        linie.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Minimum)

        return linie

    def get_zentrum_widgets(self, gruppe: str, zentrum: dict) -> Tuple[QtWidgets.QCheckBox, QtWidgets.QGridLayout]:
        """
        Erstellt ein Widget Paket für die Checkbox mit entsprechendem Layout welches die Labels enhalten

        Args:
            gruppe (str): Gruppe welcher der Button zugeordnet werden soll
            zentrum (dict): Zentrum Daten

        Returns:
            tuple[QtWidgets.QCheckBox, QtWidgets.QGridLayout]: Checkbox mit den propertys PLZ und GRUPPE
                                                               Layout mit entsprechenden Labels und beschriftungen
        """

        # Form und Layout erstellen
        info_form_Layout = QtWidgets.QGridLayout()
        font_ort = QtGui.QFont()
        font_ort.setBold(True)

        # Checkbox erstellen und konfigurieren
        checkbox = QtWidgets.QCheckBox()
        checkbox.setText(zentrum["PLZ"])
        checkbox.setProperty("PLZ", zentrum["PLZ"])
        checkbox.setProperty("GRUPPE", gruppe)
        checkbox.stateChanged.connect(lambda: self.checkbox_clicked(checkbox))

        # Label beschriften
        ort_zentrum_label = QtWidgets.QLabel(zentrum["Ort"])
        name_zentrum_label = QtWidgets.QLabel(zentrum["Zentrumsname"])

        # Extra Font für den Ort Label
        ort_zentrum_label.setFont(font_ort)

        # Labels dem GridLayout hinzufügen
        info_form_Layout.addWidget(ort_zentrum_label)
        info_form_Layout.addWidget(name_zentrum_label)

        return checkbox, info_form_Layout

    def disable_plz_checkboxes(self, gruppe: str):
        """
        Deaktiviert alle Checkboxen außer der übergebenen Gruppe

        Args:
            gruppe (str): Gruppenname welcher nicht deaktiviert wird
        """

        all_checkboxes = self.scrollAreaWidgetContents.findChildren(QtWidgets.QCheckBox)

        for checkbox in all_checkboxes:
            if checkbox.property("GRUPPE") == gruppe:
                checkbox.setEnabled(True)
            else:
                checkbox.setDisabled(True)

    def enable_all_checkboxes(self):
        """
        Aktiviert alle Checkboxen
        """

        all_checkboxes = self.scrollAreaWidgetContents.findChildren(QtWidgets.QCheckBox)

        for checkbox in all_checkboxes:
            checkbox.setEnabled(True)

    def checkbox_clicked(self, checkbox: QtWidgets.QCheckBox):
        """
        Funktion welche nach dem Klicken auf eine Checkbox ausgeführt werden soll
        Aktiviert / Deaktiviert alle andern Checkboxen in einer anderen Gruppe

        Args:
            checkbox (QtWidgets.QCheckBox): chebox welche geklickt wurde
        """

        gruppe = checkbox.property("GRUPPE")

        if self.get_all_checked_boxes():
            self.disable_plz_checkboxes(gruppe)
        else:
            self.enable_all_checkboxes()

    def bestaetigt(self):
        """
        Die Aktiven PLZ werden in dem Hauptfenster eingetragen
        Emit von update_impfzentren_plz
        """

        plz_string = ",".join(self.get_all_plz_from_checked_boxes())
        self.update_impfzentren_plz.emit(plz_string)

    def get_all_plz_from_checked_boxes(self) -> List[str]:
        """
        Liste mit allen aktiven PLZ

        Returns:
            list[str]: Aktive PLZ
        """

        plzs = list()
        checked_boxes = self.get_all_checked_boxes()

        for checkbox in checked_boxes:
            plzs.append(checkbox.property("PLZ"))

        return plzs

    def __button_box_clicked(self, button: QtWidgets.QPushButton):
        """
        Zuweisung der einzelnen Funktionen der Buttons in der ButtonBox

        Args:
            button (PyQt5.QtWidgets.QPushButton): Button welcher gedrückt wurde
        """

        clicked_button = self.buttonBox.standardButton(button)
        if clicked_button == QtWidgets.QDialogButtonBox.Ok:
            self.bestaetigt()
        if clicked_button == QtWidgets.QDialogButtonBox.Reset:
            self.reset()
        elif clicked_button == QtWidgets.QDialogButtonBox.Cancel:
            self.close()

    def get_all_checked_boxes(self) -> List[QtWidgets.QCheckBox]:
        """
        Gibt alle checked checkboxes zurück

        Returns:
            list[QtWidgets.QCheckBox]: Liste mit Checkboxen
        """

        all_checkboxes = self.scrollAreaWidgetContents.findChildren(QtWidgets.QCheckBox)
        checked_boxes = list()

        for checkbox in all_checkboxes:
            if checkbox.isChecked():
                checked_boxes.append(checkbox)
        return checked_boxes

    def reset(self):
        """
        Alle Checkboxen "uncheck"
        Alle Checkboxen aktivieren
        """

        all_checkboxes = self.scrollAreaWidgetContents.findChildren(QtWidgets.QCheckBox)

        for checkbox in all_checkboxes:
            checkbox.setChecked(False)

        self.enable_all_checkboxes()
