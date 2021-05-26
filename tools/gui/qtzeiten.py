import os
import json
from PyQt5 import QtWidgets, uic
from PyQt5.QtCore import QTime, QDateTime

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

PATH = os.path.dirname(os.path.realpath(__file__))


class QtZeiten(QtWidgets.QDialog):
    """
    Klasse für das erstellen einer zeitspanne.json mithilfe einer GUI / PyQt5
    Diese erbt von QtWidgets.QDialog
    """

    def __init__(self, pfad_fenster_layout = os.path.join(PATH, "uhrzeiten.ui")):
        """
        Ladet das angegebene Layout (wurde mit QT Designer erstellt https://www.qt.io/download)
        Das Fenster wird automtaisch nach dem erstellen der Klasse geöffnet

        Args:
            pfad_fester_layout (str): Speicherort der .ui - Datei
        """

        super(QtZeiten, self).__init__()

        # Laden der .ui Datei und Anpassungen
        uic.loadUi(pfad_fenster_layout, self)
        self.i_start_datum_qdate.setMinimumDateTime(QDateTime.currentDateTime())

        # Funktionen den Buttons zuweisen
        self.buttonBox.accepted

        # Setzte leere Werte
        self.aktive_wochentage = list()
        self.start_uhrzeit: QTime = None
        self.end_uhrzeit: QTime = None
        self.aktive_termine = list()


    def bestaetigt(self):
        """
        Aktuallisiert alle Werte und Speichert gleichzeig die Aktuellen Werte
        """

        # Alle Werte von aus der GUI aktuallisieren
        self.__aktuallisiere_aktive_wochentage()
        self.__aktuallisiere_aktive_termine()

        if not self.__aktuallisiere_uhrzeiten():
            QtWidgets.QMessageBox.critical(self, "Ungültige Eingabe!", "Start-Uhrzeit ist später als End-Uhrzeit!")
            return

        # Speichert alle Werte ab
        self.speicher_einstellungen()

        self.close()

    def speicher_einstellungen(self):
        """
        Speichert alle Werte in der entsprechenden JSON-Formatierung
        Speicherpfad wurde beim erstellen der Klasse mit übergeben
        """

        speicherpfad = self.__oeffne_file_dialog()

        data = {
            "wochentage": self.aktive_wochentage,
            "startzeit": {
                "h": self.start_uhrzeit.hour(),
                "m": self.start_uhrzeit.minute()
            },
            "endzeit": {
                "h": self.end_uhrzeit.hour(),
                "m": self.end_uhrzeit.minute()
            },
            "einhalten_bei": self.aktive_termine
        }

        with open(speicherpfad, 'w', encoding='utf-8') as f:
            try:
                json.dump(data, f, ensure_ascii=False, indent=4)
                QtWidgets.QMessageBox.information(self, "Gepseichert", "Daten erfolgreich gespeichert")

            except (TypeError, IOError, FileNotFoundError) as error:
                QtWidgets.QMessageBox.critical(self, "Fehler!", "Daten konnten nicht gespeichert werden.")
                raise error


    def __aktuallisiere_aktive_wochentage(self):
        """
        Alle "checked" Wochentage in der GUI werden gesichert
        """
        # Zur sicherheit alte Werte löschen
        self.aktive_wochentage.clear()

        # Alle Checkboxen der GUI selektieren und durchgehen
        # BUG: Wenn die reihenfolge im Layout geändert wird, stimmen die Wochentage nicht mehr 0 = Mo ... 6 = So
        checkboxes = self.i_mo_check_box.parent().findChildren(QtWidgets.QCheckBox)
        for num, checkboxe in enumerate(checkboxes, 0):
            if checkboxe.isChecked():
                self.aktive_wochentage.append(num)

    def __aktuallisiere_uhrzeiten(self) -> bool:
        """
        Aktuallisert die eingegebenen Uhrzeiten der GUI
        """

        if self.start_time.time() < self.end_time.time():
            self.start_uhrzeit = self.start_time.time()
            self.end_uhrzeit = self.end_time.time()

            return True
        else:
            return False

    def __aktuallisiere_aktive_termine(self):
        """
        Aktuallisert die eingegebenen Uhrzeiten der GUI
        """

        # Zur sicherheit alte Werte löschen
        self.aktive_termine.clear()

        if self.erster_termin_check_box.isChecked():
            self.aktive_termine.append(1)
        if self.zweiter_termin_check_box.isChecked():
            self.aktive_termine.append(2)

    def __oeffne_file_dialog(self) -> str:
        datei_data = QtWidgets.QFileDialog.saveFileContent(self, "Zeitspanne", os.path.join(PATH, "data"), "JSON Files (*.json)")
        dateipfad = datei_data[0]
        return dateipfad


if __name__ == "__main__":
    app = QtWidgets.QApplication(list())
    window = QtZeiten()
    window.show()
    app.exec_()
