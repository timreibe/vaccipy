import os
import json

from PyQt5 import QtWidgets, uic
from PyQt5.QtCore import QTime
from PyQt5.QtGui import QIcon

from tools.gui import *

# Folgende Widgets stehen zur Verfügung:

### QLineEdit ####
# i_plz_impfzentren
# i_code_impfzentren
# i_vorname
# i_nachname
# i_strasse
# i_hausnummer
# i_wohnort
# i_plz_wohnort
# i_telefon
# i_mail

### QComboBox ###
# i_anrede_combo_box

### QDialogButtonBox ###
# buttonBox
# Apply
# Cancel
# Reset

### Layouts ###
# kontakdaten_layout

PATH = os.path.dirname(os.path.realpath(__file__))


class QtKontakt(QtWidgets.QDialog):
    def __init__(self, modus: Modus, standard_speicherpfad: str, ROOT_PATH: str, pfad_fenster_layout=os.path.join(PATH, "kontaktdaten.ui")):
        super().__init__()

        self.standard_speicherpfad = standard_speicherpfad

        # Laden der .ui Datei
        uic.loadUi(pfad_fenster_layout, self)
        self.setWindowIcon(QIcon(os.path.join(ROOT_PATH, "images/spritze.ico")))
        self.setup(modus)

        # Funktionen für Buttonbox zuweisen
        self.buttonBox.clicked.connect(self.__button_clicked)

    def setup(self, modus: Modus):
        if modus == Modus.TERMIN_SUCHEN:
            # Default - Alle Felder aktiv
            pass
        elif modus == Modus.CODE_GENERIEREN:
            # Benötig wird: PLZ's der Impfzentren, Telefonnummer, Mail
            # Alles andere wird daher deaktiviert
            self.readonly_alle_line_edits(("i_plz_impfzentren", "i_telefon", "i_mail"))
        else:
            raise RuntimeError("Modus ungueltig!")

    def bestaetigt(self):
        """
        Versucht die Daten zu speichern und schließt sich anschließend selbst
        """

        try:
            self.speicher_einstellungen()
            QtWidgets.QMessageBox.information(self, "Gepseichert", "Daten erfolgreich gespeichert")
            self.close()
        except (TypeError, IOError, FileNotFoundError) as error:
            QtWidgets.QMessageBox.critical(self, "Fehler beim Speichern!", "Bitte erneut versuchen!")

    def speicher_einstellungen(self):
        """
        Speichert alle Werte in der entsprechenden JSON-Formatierung
        Speicherpfad wird vom User abgefragt
        """

        speicherpfad = oeffne_file_dialog_save(self, "Kontaktdaten", self.standard_speicherpfad)
        data = self.__get_alle_werte()

        speichern(speicherpfad, data)

    def __button_clicked(self, button):
        """
        Zuweisung der einzelnen Funktionen der Buttons in der ButtonBox

        Args:
            button (PyQt5.QtWidgets.QPushButton): Button welcher gedrückt wurde
        """

        clicked_button = self.buttonBox.standardButton(button)
        if clicked_button == QtWidgets.QDialogButtonBox.Save:
            self.bestaetigt()
        if clicked_button == QtWidgets.QDialogButtonBox.Reset:
            self.__reset()
        elif clicked_button == QtWidgets.QDialogButtonBox.Cancel:
            self.close()

    def __get_alle_werte(self) -> dict:
        """
        Holt sich alle Werte aus der GUI und gibt diese fertig zum speichern zurück

        Returns:
            dict: User eingaben
        """

        plz_zentrum_raw = self.i_plz_impfzentren.text()
        code = self.i_code_impfzentren.text().strip()
        anrede = self.i_anrede_combo_box.currentText().strip()
        vorname = self.i_vorname.text().strip()
        nachname = self.i_nachname.text().strip()
        strasse = self.i_strasse.text().strip()
        hausnummer = self.i_hausnummer.text().strip()
        wohnort = self.i_wohnort.text().strip()
        plz_wohnort = self.i_plz_wohnort.text().strip()
        telefon = self.i_telefon.text().strip()
        mail = self.i_mail.text().strip()

        # PLZ der Zentren in liste und "strippen"
        plz_zentren = plz_zentrum_raw.split(",")
        plz_zentren = [plz.strip() for plz in plz_zentren]

        kontaktdaten = {
            "plz_impfzentren": plz_zentren,
            "code": code,
            "kontakt": {
                "anrede": anrede,
                "vorname": vorname,
                "nachname": nachname,
                "strasse": strasse,
                "hausnummer": hausnummer,
                "plz": plz_wohnort,
                "ort": wohnort,
                "phone": telefon,
                "notificationChannel": "email",
                "notificationReceiver": mail
            }
        }
        return kontaktdaten

    def readonly_alle_line_edits(self, ausgeschlossen: list):
        """
        Setzt alle QLineEdit auf "read only", ausgeschlossen der Widgets in ausgeschlossen.
        Setzt zudem den PlacholderText auf "Daten werden nicht benötigt"

        Args:
            ausgeschlossen (list): Liste mit den ObjectNamen der Widgets die ausgeschlossen werden sollen
        """

        line_edits = self.findChildren(QtWidgets.QLineEdit)

        for line_edit in line_edits:
            if line_edit.objectName() not in ausgeschlossen:
                line_edit.setReadOnly(True)
                line_edit.setPlaceholderText("Daten werden nicht benötigt")

    def __reset(self):
        """
        Setzt alle Werte in der GUI zurück
        """

        for widget in self.children():
            if isinstance(widget, QtWidgets.QLineEdit):
                widget.setText("")
            elif isinstance(widget, QtWidgets.QComboBox):
                widget.setCurrentText("Bitte Wählen")


# Zum schnellen einzeltesten
if __name__ == "__main__":
    app = QtWidgets.QApplication(list())
    window = QtKontakt("./kontaktdaten.json")
    window.show()
    app.exec_()
