import os

from PyQt5 import QtWidgets, uic
from PyQt5.QtCore import QTime, QDate, QDateTime
from PyQt5.QtGui import QIcon

from tools.gui import *

# Folgende Widgets stehen zur Verfügung:

### Checkboxes ###
# i_mo_check_box
# i_di_check_box
# i_mi_check_box
# i_do_check_box
# i_fr_check_box
# i_so_check_box
# i_sa_check_box
# i_erster_termin_check_box
# i_zweiter_termin_check_box

### QTimeEdit ###
# i_start_time_qtime
# i_end_time_qtime

### QDateEdit ###
# i_start_datum_qdate

### QDialogButtonBox ###
# buttonBox
# Apply
# Cancel
# Reset

### QFrame ###
# tage_frame

PATH = os.path.dirname(os.path.realpath(__file__))


class QtZeiten(QtWidgets.QDialog):
    """
    Klasse für das erstellen einer zeitspanne.json mithilfe einer GUI / PyQt5
    Diese erbt von QtWidgets.QDialog
    """

    def __init__(self, parent: QtWidgets.QWidget, standard_speicherpfad: str, ROOT_PATH: str, pfad_fenster_layout=os.path.join(PATH, "uhrzeiten.ui")):
        """
        Eingabe der Zeitkonfigurationen

        Args:
            standard_speicherpfad (str): standard speicherpfad der JSON-Datei
            pfad_fenster_layout (str, optional): Layout des Dialogs. Defaults to os.path.join(PATH, "uhrzeiten.ui").
        """

        super().__init__(parent=parent)

        # Startwerte setzten
        self.standard_speicherpfad = standard_speicherpfad
        self.pfad_fenster_layout = pfad_fenster_layout

        # Laden der .ui Datei und Anpassungen
        uic.loadUi(self.pfad_fenster_layout, self)
        self.setWindowIcon(QIcon(os.path.join(ROOT_PATH, "images/spritze.ico")))
        self.i_start_datum_qdate.setMinimumDateTime(QDateTime.currentDateTime())

        # Funktionen für Buttonbox zuweisen
        self.buttonBox.clicked.connect(self.__button_clicked)

    def bestaetigt(self):
        """
        Speichert die aktuellen Werte und schließt anschließend den Dialog
        Ändert zusätzlich den Text in self.parent().i_zeitspanne_pfad zum Pfad, falls möglich
        """

        try:
            speicherpfad = self.speicher_einstellungen()
            QtWidgets.QMessageBox.information(self, "Gepseichert", "Daten erfolgreich gespeichert")
            self.parent().i_zeitspanne_pfad.setText(speicherpfad)
            self.close()
        except ValueError as error:
            QtWidgets.QMessageBox.critical(self, "Ungültige Eingabe!", str(error))
        except (TypeError, IOError, FileNotFoundError) as error:
            QtWidgets.QMessageBox.critical(self, "Fehler beim Speichern!", "Bitte erneut versuchen!")
        except AttributeError as error:
            # Parent hat i_zeitspanne_pfad nicht
            # Falls der Dialog ein anderer Parent hat soll kein Fehler kommen
            self.close()

    def speicher_einstellungen(self) -> str:
        """
        Speichert alle Werte in der entsprechenden JSON-Formatierung
        Speicherpfad wird vom User abgefragt

        Returns:
            str: Speicherpfad
        """

        speicherpfad = oeffne_file_dialog_save(self, "Zeitspanne", self.standard_speicherpfad)
        data = self.__get_alle_werte()

        speichern(speicherpfad, data)
        return speicherpfad

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
        Gibt alle nötigen Daten richtig formatiert zum abspeichern

        Returns:
            dict: alle Daten
        """

        aktive_wochentage = self.__get_aktive_wochentage()
        uhrzeiten = self.__get_uhrzeiten()
        termine = self.__get_aktive_termine()
        start_datum = self.__get_start_datum()

        if termine:
            return {
                "von_datum": f"{start_datum.day()}.{start_datum.month()}.{start_datum.year()}",
                "von_uhrzeit": f"{uhrzeiten['startzeit']['h']}:{uhrzeiten['startzeit']['m']}",
                "bis_uhrzeit": f"{uhrzeiten['endzeit']['h']}:{uhrzeiten['endzeit']['m']}",
                "wochentage": aktive_wochentage,
                "einhalten_bei": "beide" if len(termine) > 1 else str(termine[0]),
            }
        else:
            return {}

    def __get_aktive_wochentage(self) -> list:
        """
        Alle "checked" Wochentage in der GUI

        Returns:
            list: Alle aktiven Wochentage
        """

        # Leere liste
        aktive_wochentage = list()

        # Alle Checkboxen der GUI selektieren und durchgehen
        checkboxes = self.tage_frame.findChildren(QtWidgets.QCheckBox)
        for num, checkboxe in enumerate(checkboxes, 0):
            if checkboxe.isChecked():
                aktive_wochentage.append(checkboxe.property("weekday"))

        return aktive_wochentage

    def __get_uhrzeiten(self) -> dict:
        """
        Erstellt ein Dict mit ensprechenden start und endzeiten

        Raises:
            ValueError: start uhrzeit < end uhrzeit

        Returns:
            dict: fertiges dict zum speichern mit startzeit und endzeit
        """

        start_uhrzeit: QTime = self.i_start_time_qtime.time()
        end_uhrzeit: QTime = self.i_end_time_qtime.time()

        if start_uhrzeit >= end_uhrzeit:
            raise ValueError("Start Uhrzeit is später als Enduhrzeit")

        uhrzeiten = {
            "startzeit": {
                "h": start_uhrzeit.hour(),
                "m": start_uhrzeit.minute()
            },
            "endzeit": {
                "h": end_uhrzeit.hour(),
                "m": end_uhrzeit.minute()
            }
        }
        return uhrzeiten

    def __get_start_datum(self) -> QDate:
        """
        Aktuallisiert das Startdatum
        """
        return self.i_start_datum_qdate.date()

    def __get_aktive_termine(self) -> list:
        """
        Liste mit den aktiven Terminen 1 = 1. Termin 2 = 2. Termin

        Returns:
            list: Termine
        """

        aktive_termine = list()

        if self.i_erster_termin_check_box.isChecked():
            aktive_termine.append(1)
        if self.i_zweiter_termin_check_box.isChecked():
            aktive_termine.append(2)
        return aktive_termine

    def __reset(self, widgets: list = None):
        """
        Setzt alle Werte in der GUI zurück
        """

        if widgets is None:
            self.__reset(self.children())
            return

        for widget in widgets:
            if isinstance(widget, QtWidgets.QCheckBox):
                widget.setChecked(True)
            elif isinstance(widget, QtWidgets.QDateEdit):
                widget.setDate(QDateTime.currentDateTime().date())
            elif isinstance(widget, QtWidgets.QTimeEdit):
                if widget == self.i_start_time_qtime:
                    widget.setTime(QTime(0, 1))
                else:
                    widget.setTime(QTime(23, 59))
            elif isinstance(widget, QtWidgets.QFrame):
                self.__reset(widget.children())
