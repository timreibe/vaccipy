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

    def __init__(self, standard_speicherpfad:str, pfad_fenster_layout=os.path.join(PATH, "uhrzeiten.ui")):
        """
        Ladet das angegebene Layout (wurde mit QT Designer erstellt https://www.qt.io/download)
        Das Fenster wird automtaisch nach dem erstellen der Klasse geöffnet

        Args:
            pfad_fester_layout (str): Speicherort der .ui - Datei
        """

        super(QtZeiten, self).__init__()

        self.standard_speicherpfad = standard_speicherpfad
        self.pfad_fenster_layout = pfad_fenster_layout

        # Laden der .ui Datei und Anpassungen
        uic.loadUi(self.pfad_fenster_layout, self)
        self.i_start_datum_qdate.setMinimumDateTime(QDateTime.currentDateTime())


        # Funktionen für Buttonbox zuweisen
        self.buttonBox.clicked.connect(self.__button_clicked)

    def bestaetigt(self):
        """
        Aktuallisiert alle Werte und Speichert gleichzeig die Aktuellen Werte
        """

        try:
            self.speicher_einstellungen()
            self.close()
        except ValueError as error:
            QtWidgets.QMessageBox.critical(self, "Ungültige Eingabe!", "Start-Uhrzeit ist später als End-Uhrzeit!")
        except (TypeError, IOError, FileNotFoundError) as error:
            QtWidgets.QMessageBox.critical(self, "Fehler beim Speichern!", "Bitte erneut versuchen!")
        

    def speicher_einstellungen(self):
        """
        Speichert alle Werte in der entsprechenden JSON-Formatierung
        Speicherpfad wird vom User abgefragt
        """

        speicherpfad = self.__oeffne_file_dialog()

        data = self.__get_alle_werte()

        with open(speicherpfad, 'w', encoding='utf-8') as f:
            try:
                json.dump(data, f, ensure_ascii=False, indent=4)
                QtWidgets.QMessageBox.information(self, "Gepseichert", "Daten erfolgreich gespeichert")

            except (TypeError, IOError, FileNotFoundError) as error:
                QtWidgets.QMessageBox.critical(self, "Fehler!", "Daten konnten nicht gespeichert werden.")
                raise error

    def __button_clicked(self, button):
        clicked_button = self.buttonBox.standardButton(button)
        if clicked_button == QtWidgets.QDialogButtonBox.Apply:
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

        zeitspanne = {
            "wochentage": aktive_wochentage,
            "startzeit": uhrzeiten["startzeit"],
            "endzeiten": uhrzeiten["endzeit"],
            "einhalten_bei": termine
        }
        return zeitspanne

    def __get_aktive_wochentage(self) -> list:
        """
        Alle "checked" Wochentage in der GUI

        Returns:
            list: Alle aktiven Wochentage
        """

        # Leere liste
        aktive_wochentage = list()

        # Alle Checkboxen der GUI selektieren und durchgehen
        # BUG: Wenn die reihenfolge im Layout geändert wird, stimmen die Wochentage nicht mehr 0 = Mo ... 6 = So
        checkboxes = self.i_mo_check_box.parent().findChildren(QtWidgets.QCheckBox)
        for num, checkboxe in enumerate(checkboxes, 0):
            if checkboxe.isChecked():
                aktive_wochentage.append(num)

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
            raise ValueError

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

    def __oeffne_file_dialog(self) -> str:
        """
        Öffnet einen File Dialog, der den Speicherort festlegt

        Returns:
            str: Speicherpfad
        """

        datei_data = QtWidgets.QFileDialog.getSaveFileName(self, "Zeitspanne", self.standard_speicherpfad, "JSON Files (*.json)")
        dateipfad = datei_data[0]  # (Pfad, Dateityp)
        return dateipfad

    def __reset(self):
        #TODO: Reset
        pass


if __name__ == "__main__":
    app = QtWidgets.QApplication(list())
    window = QtZeiten(".\\zeitspanne.json")
    window.show()
    app.exec_()
