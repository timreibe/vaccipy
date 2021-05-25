import os
import json
from PyQt5 import QtWidgets, uic
from PyQt5.QtCore import QTime
from PyQt5.QtGui import QCloseEvent

# Folgende Widgets stehen zur Verfügung:

### Checkboxes ###
# mo_check_box
# di_check_box
# mi_check_box
# do_check_box
# fr_check_box
# so_check_box
# sa_check_box
# erster_termin_check_box
# zweiter_termin_check_box

### QTimeEdit ###
# start_time
# end_time

### Buttons ###
# pushButton

### Labels ###
# header_label
# wochentage_label
# termine_anwenden_label
# uhr_header_label
# uhr_start_label
# uhr_end_label
# und_label

PATH = os.path.dirname(os.path.realpath(__file__))

# TODO: [X] Beim Schließen vom Fenster werden die Daten gespeichert, falls sie noch nicht vorhanden sind
# TODO: [ ] .icon adden
# TODO: [X] Fenstergröße sollte man nicht verändern können
# TODO: [X] Fenster in den Vordergund bringen
# TODO: [X] Docstrings
# TODO: [X] Rückmeldung für erfolgreiches speichern


class QtTimer(QtWidgets.QMainWindow):
    """
    Klasse für das erstellen einer zeitspanne.json mithilfe einer GUI / PyQt5
    Diese erbt von QtWidgets.QMainWindow
    """

    def __init__(self, pfad_zeitspanne: str, pfad_fenster_layout: str):
        """
        Ladet das angegebene Layout (wurde mit QT Designer erstellt https://www.qt.io/download)
        Das Fenster wird automtaisch nach dem erstellen der Klasse geöffnet

        Args:
            pfad_zeitspanne (str): Speicherpfad für zeitspanne.json
            pfad_fester_layout (str): Speicherort der .ui - Datei
        """

        super(QtTimer, self).__init__()

        # Laden der .ui Datei und Anpassungen
        uic.loadUi(pfad_fenster_layout, self)
        self.setFixedSize(self.size())

        # self.bestaetigen() soll beim Klicken auf Bestätigen aufgerufen werden
        self.pushButton.clicked.connect(self.bestaetigt)

        # Setzte leere Werte
        self.aktive_wochentage = list()
        self.start_uhrzeit: QTime = None
        self.end_uhrzeit: QTime = None
        self.aktive_termine = list()
        self.speicherpfad = pfad_zeitspanne

        # GUI anzeigen
        self.show()
        # Workaround, damit das Fenster hoffentlich im Vordergrund ist
        self.activateWindow()

    @staticmethod
    def start(pfad_zeitspanne: str, pfad_fenster_layout=os.path.join(PATH, "qttimer.ui")):
        """
        Öffnet eine GUI in dem der User seine Parameter angeben kann
        Diese werden bei Bestätigung direkt in den mit übergebenen Pfad gespeichert
        Anschließend schließt sich das Fenster

        Args:
            pfad_zeitspanne (str): Speicherpfad für zeitspanne.json
            pfad_fester_layout (str): Speicherort der .ui - Datei. Default: .\\qttimer.ui
        """

        app = QtWidgets.QApplication(list())
        window = QtTimer(pfad_zeitspanne, pfad_fenster_layout)
        app.exec_()

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

        with open(self.speicherpfad, 'w', encoding='utf-8') as f:
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
        # Improvement: Wenn die reihenfolge im Layout geändert wird, stimmen die Wochentage nicht mehr 0 = Mo ... 6 = So
        checkboxes = self.mo_check_box.parent().findChildren(QtWidgets.QCheckBox)
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

    def closeEvent(self, event: QCloseEvent):
        """
        Wird automatisch aufgerufen, wenn das Fenster geschlossen wird

        Args:
            event (QCloseEvent): Close events are sent to widgets that the user wants to close, usually by choosing “Close” 
                                from the window menu, or by clicking the X title bar button. They are also sent when you 
                                call close() to close a widget programmatically.
        """
        # Erst fenster Speichern, wenn Daten gespeichert / schon vorhanden sind
        if os.path.isfile(self.speicherpfad):
            event.accept()
        else:
            self.bestaetigt()
            event.accept()


if __name__ == "__main__":
    QtTimer.start(f"{PATH}\\..\\zeitspanne.json")
