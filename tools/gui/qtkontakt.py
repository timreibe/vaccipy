import os

from PyQt5 import QtWidgets, uic
from PyQt5.QtCore import QTime
from PyQt5.QtGui import QIcon

from tools.gui import *
from tools.gui.qtimpfzentren import QtImpfzentren
from tools import kontaktdaten as kontakt_tools
from tools import Modus
from tools.exceptions import ValidationError, MissingValuesError

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

### Buttons ###
# b_impfzentren_waehlen

PATH = os.path.dirname(os.path.realpath(__file__))


class QtKontakt(QtWidgets.QDialog):
    def __init__(self, parent: QtWidgets.QWidget, modus: Modus, standard_speicherpfad: str, ROOT_PATH: str, pfad_fenster_layout=os.path.join(PATH, "kontaktdaten.ui")):
        super().__init__(parent=parent)

        # Setze Attribute
        self.standard_speicherpfad = standard_speicherpfad
        self.modus = modus

        # Laden der .ui Datei und init config
        uic.loadUi(pfad_fenster_layout, self)
        self.setWindowIcon(QIcon(os.path.join(ROOT_PATH, "images/spritze.ico")))
        self.setup()

        # Funktionen der ButtonBox zuordnen
        self.buttonBox.clicked.connect(self.__button_clicked)

        # Funktion vom Button zuordnen
        self.b_impfzentren_waehlen.clicked.connect(self.__open_impfzentren)

    def setup(self):
        """
        Aktiviert abhänfig vom Modus die Eingabefelder

        Raises:
            RuntimeError: Modus ungültig
        """

        if self.modus == Modus.TERMIN_SUCHEN:
            # Default - Alle Felder aktiv
            pass
        elif self.modus == Modus.CODE_GENERIEREN:
            # Benötig wird: PLZ's der Impfzentren, Telefonnummer, Mail
            # Alles andere wird daher deaktiviert
            self.readonly_alle_line_edits(("i_plz_impfzentren", "i_telefon", "i_mail"))
            self.i_code_impfzentren.setInputMask("")
        else:
            raise RuntimeError("Modus ungueltig!")

    def bestaetigt(self):
        """
        Versucht die Daten zu speichern und schließt sich anschließend selbst
        Ändert zusätzlich den Text in self.parent().i_kontaktdaten_pfad zum Pfad, falls möglich
        """

        try:
            data = self.__get_alle_werte()

            self.__check_werte(data)

            # Daten speichern
            speicherpfad = self.speicher_einstellungen(data)
            QtWidgets.QMessageBox.information(self, "Gepseichert", "Daten erfolgreich gespeichert")
            self.parent().i_kontaktdaten_pfad.setText(speicherpfad)
            self.close()
        except (TypeError, IOError, FileNotFoundError) as error:
            QtWidgets.QMessageBox.critical(self, "Fehler beim Speichern!", "Bitte erneut versuchen!")
        except ValidationError as error:
            QtWidgets.QMessageBox.critical(self, "Daten Fehlerhaft!", f"In den angegebenen Daten sind Fehler:\n\n{error}")
            return
        except MissingValuesError as error:
            QtWidgets.QMessageBox.critical(self, "Daten Fehlerhaft!", f"In der angegebenen Daten Fehlen Werte:\n\n{error}")
            return
        except AttributeError as error:
            # Parent hat i_kontaktdaten_pfad nicht
            # Falls der Dialog ein anderer Parent hat, soll kein Fehler kommen
            self.close()

    def speicher_einstellungen(self, data: dict) -> str:
        """
        Speichert alle Werte in der entsprechenden JSON-Formatierung
        Speicherpfad wird vom User abgefragt

        Params:
            data (dict): Kontaktaden zum speichern

        Returns:
            str: Speicherpfad
        """

        speicherpfad = oeffne_file_dialog_save(self, "Kontaktdaten", self.standard_speicherpfad)

        speichern(speicherpfad, data)
        return speicherpfad

    def __button_clicked(self, button: QtWidgets.QPushButton):
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

    def __open_impfzentren(self):
        """
        Öffnet den Dialog um PLZ auszuwählen
        """

        impfzentren_dialog = QtImpfzentren(self)
        impfzentren_dialog.update_impfzentren_plz.connect(self.__set_impzentren_plz)
        impfzentren_dialog.show()
        impfzentren_dialog.exec_()

    def __set_impzentren_plz(self, plz: str):
        """
        Übergebener Text wird in das QLineEdit i_plz_impfzentren geschrieben

        Args:
            plz (str): Kommagetrennte PLZ der Impfzentren in einer Gruppe
        """

        self.i_plz_impfzentren.setText(plz)

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

        # PLZ der Zentren in Liste und "strippen"
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

    def __check_werte(self, kontaktdaten: dict):
        """
        Prüft mithilfe von den kontakt_tools ob alle Daten da und gültig sind

        Args:
            kontaktdaten (dict): Kontaktdaten

        Raises:
            ValidationError: Daten Fehlerhaft
            MissingValuesError: Daten Fehlen
        """

        kontakt_tools.check_kontaktdaten(kontaktdaten, self.modus)

        if self.modus == Modus.TERMIN_SUCHEN:
            kontakt_tools.validate_kontaktdaten(kontaktdaten)
        elif self.modus == Modus.CODE_GENERIEREN:
            kontakt_tools.validate_plz_impfzentren(kontaktdaten["plz_impfzentren"])
            kontakt_tools.validate_email(kontaktdaten["kontakt"]["notificationReceiver"])
            try:
                kontakt_tools.validate_phone(kontaktdaten["kontakt"]["phone"])
            except ValidationError as error:
                raise ValidationError("Telefonnummer: +49 nicht vergessen") from error

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

        # Telefon wieder mit Prefix befüllen
        self.i_telefon.setText("+49")
