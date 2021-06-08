#!/usr/bin/env python3

import json
import multiprocessing
import os
import threading
import time
import sys

from PyQt5 import QtCore, QtWidgets, uic
from PyQt5.QtGui import QIcon
from tools.exceptions import ValidationError, MissingValuesError
from tools.gui import oeffne_file_dialog_select


from tools import Modus
from tools import kontaktdaten as kontak_tools
from tools.exceptions import MissingValuesError, ValidationError
from tools.gui import oeffne_file_dialog_select, open_browser
from tools.gui.qtkontakt import QtKontakt
from tools.gui.qtterminsuche import QtTerminsuche
from tools.utils import create_missing_dirs, update_available, get_latest_version, get_current_version

PATH = os.path.dirname(os.path.realpath(__file__))


class HauptGUI(QtWidgets.QMainWindow):

    # Folgende Widgets stehen zur Verfügung:

    ### QLineEdit ###
    # i_kontaktdaten_pfad

    ### Buttons ###
    # b_termin_suchen
    # b_code_generieren
    # b_dateien_kontaktdaten
    # b_neue_kontaktdaten

    ### Layouts ###
    # prozesse_layout

    ### QSpinBox ###
    # i_interval

    def __init__(self, pfad_fenster_layout: str = os.path.join(PATH, "tools/gui/main.ui")):
        """
        Main der GUI Anwendung

        Args:
            pfad_fenster_layout (str, optional): Ladet das angegebene Layout (wurde mit QT Designer erstellt https://www.qt.io/download).
            Defaults to os.path.join(PATH, "tools/gui/main.ui").
        """

        super().__init__()

        create_missing_dirs(PATH)

        # Laden der .ui Datei und Anpassungen
        self.setup(pfad_fenster_layout)

        # GUI anzeigen
        self.show()

        # Workaround, damit das Fenster hoffentlich im Vordergrund ist
        self.activateWindow()

        # Auf neuere Version prüfen
        self.check_update()

    ##############################
    #     Allgemein Fenster      #
    ##############################

    @staticmethod
    def start_gui():
        """
        Startet die GUI Anwendung
        """

        app = QtWidgets.QApplication(list())
        app.setAttribute(QtCore.Qt.AA_X11InitThreads)
        window = HauptGUI()
        app.exec_()

    def setup(self, pfad_fenster_layout: str):
        """
        Standard Konfig für die GUI erstellen, bevor sie angezeigt werden kann

        Args:
            pfad_fenster_layout (str): Pfad zur .ui Datei
        """

        ### Allgemein ###
        create_missing_dirs(PATH)

        # Standard Pfade
        self.pfad_kontaktdaten: str = os.path.join(PATH, "data", "kontaktdaten.json")

        ### GUI ###
        uic.loadUi(pfad_fenster_layout, self)
        self.setWindowIcon(QIcon(os.path.join(PATH, "images/spritze.ico")))
        self.setWindowTitle('vaccipy ' + get_current_version())

        # Meldung falls alte Daten von alter Version
        self.__check_old_kontakt_version()

        # Funktionen den Buttons zuweisen
        self.b_termin_suchen.clicked.connect(self.__termin_suchen)
        self.b_code_generieren.clicked.connect(self.__code_generieren)
        self.b_dateien_kontaktdaten.clicked.connect(self.__update_kontaktdaten_pfad)
        self.b_neue_kontaktdaten.clicked.connect(lambda: self.kontaktdaten_erstellen(Modus.TERMIN_SUCHEN))

        # Pfade in der GUI anpassen
        self.i_kontaktdaten_pfad.setText(self.pfad_kontaktdaten)

        # Speichert alle termin_suchen Prozesse
        self.such_prozesse = list(list())
        self.prozesse_counter = 0

        # Überwachnung der Prozesse
        self.prozess_bewacher = threading.Thread(target=self.__check_status_der_prozesse, daemon=True)
        self.prozess_bewacher.start()

    def check_update(self):
        """
        Prüft auf neuere Version und gibt evtl. ne Benachrichtigung an den User
        """

        try:
            # Auf Update prüfen
            if update_available():
                url = f"https://github.com/iamnotturner/vaccipy/releases/tag/{get_latest_version()}"

                msg = QtWidgets.QMessageBox()
                msg.setIcon(QtWidgets.QMessageBox.Warning)
                msg.setWindowTitle("Alte Version!")
                msg.setText("Bitte Update installieren")
                msg.setInformativeText(f"Die Terminsuche funktioniert möglicherweise nicht, da du eine alte Version verwendest ({get_current_version()})")
                msg.addButton(msg.Close)
                btn_download = msg.addButton("Download", msg.ApplyRole)

                btn_download.clicked.connect(lambda: open_browser(url))

                msg.exec_()
        except Exception as error:
            # warum auch immer konnte nicht überprüft werden
            # einfach nichts machen
            pass

    def __code_generieren(self):
        """
        Startet den Prozess der Codegenerierung
        """

        # TODO: code generierung implementieren
        QtWidgets.QMessageBox.information(self, "Noch nicht verfügbar", "Funktion nur über Konsolenanwendung verfügbar")

    def __termin_suchen(self):
        """
        Startet den Prozess der terminsuche mit Impfterminservice.terminsuche in einem neuen Thread
        Dieser wird in self.such_threads hinzugefügt.
        Alle Threads sind deamon Thread (Sofort töten sobald der Bot beendet wird)
        """

        try:
            kontaktdaten = self.__get_kontaktdaten(Modus.TERMIN_SUCHEN)
            zeitrahmen = kontaktdaten["zeitrahmen"]

        except FileNotFoundError as error:
            QtWidgets.QMessageBox.critical(self, "Datei nicht gefunden!", f"Datei zum Laden konnte nicht gefunden werden\n\nBitte erstellen")
            return
        except ValidationError as error:
            QtWidgets.QMessageBox.critical(self, "Daten Fehlerhaft!", f"In der angegebenen Datei sind Fehler:\n\n{error}")
            return
        except MissingValuesError as error:
            QtWidgets.QMessageBox.critical(self, "Daten Fehlerhaft!", f"In der angegebenen Datei Fehlen Daten:\n\n{error}")
            return

        self.__start_terminsuche(kontaktdaten, zeitrahmen)

    def __start_terminsuche(self, kontaktdaten: dict, zeitrahmen: dict):
        """
        Startet die Terminsuche. Dies nur mit einem Thread starten, da die GUI sonst hängt

        Args:
            kontaktdaten (dict): kontakdaten aus kontaktdaten.json
            zeitrahmen (dict): zeitrahmen aus zeitrahmen.json
        """

        check_delay = self.i_interval.value()
        code = kontaktdaten["code"]
        terminsuche_prozess = multiprocessing.Process(target=QtTerminsuche.start_suche, name=f"{code}-{self.prozesse_counter}", daemon=True, kwargs={
                                                      "kontaktdaten": kontaktdaten,
                                                      "zeitrahmen": zeitrahmen,
                                                      "ROOT_PATH": PATH,
                                                      "check_delay": check_delay})
        try:
            terminsuche_prozess.start()
            if not terminsuche_prozess.is_alive():
                raise RuntimeError(
                    f"Terminsuche wurde gestartet, lebt aber nicht mehr!\n\nTermin mit Code: {terminsuche_prozess.getName()}\nBitte Daten Prüfen!"
                )

        except Exception as error:
            QtWidgets.QMessageBox.critical(self, "Fehler - Suche nicht gestartet!", str(error))

        else:
            # QtWidgets.QMessageBox.information(self, "Suche gestartet", "Terminsuche wurde gestartet!\nWeitere Infos in der Konsole")
            self.such_prozesse.append(terminsuche_prozess)
            self.__add_prozess_in_gui(terminsuche_prozess)
            self.prozesse_counter += 1

    def __update_kontaktdaten_pfad(self, pfad: str):
        """
        Holt sich mithilfe des QFileDialogs eine bereits vorhandene Datei.
        Dieser Pfad wird in der GUI ersetzt und im Attribut der Kasse gespeichert.

        Wird ein Pfad bereits mit übergeben, wird dieser verwendet

        Args:
            pfad (str): if pfad - dann Wert übernehmen
        """

        if pfad:
            self.pfad_kontaktdaten = pfad
        else:
            try:
                pfad = oeffne_file_dialog_select(self, "Kontakdaten", self.pfad_kontaktdaten)
            except FileNotFoundError:
                pass

        self.pfad_kontaktdaten = pfad
        self.i_kontaktdaten_pfad.setText(self.pfad_kontaktdaten)

    def __add_prozess_in_gui(self, prozess: multiprocessing.Process):
        """
        Die Prozesse werden in der GUI in dem prozesse_layout angezeigt
        """

        label = QtWidgets.QLabel(f"Prozess: {prozess.name}")
        button = QtWidgets.QPushButton("Stoppen")
        button.setObjectName(prozess.name)
        button.clicked.connect(lambda: self.__stop_prozess(prozess))

        self.prozesse_layout.addRow(label, button)

    def __stop_prozess(self, prozess: multiprocessing.Process):
        """
        Stopped den übergebenen Prozess und löscht diesen aus der GUI

        Args:
            prozess (multiprocessing.Process): Prozess welcher getötet werden soll
        """
        prozess.kill()
        self.such_prozesse.remove(prozess)
        self.__remove_prozess_von_gui(prozess)

    def __remove_prozess_von_gui(self, prozess: multiprocessing.Process):
        """
        Entfernt die Anzeige des Prozesses aus der GUI

        Args:
            prozess (multiprocessing.Process): Prozess welcher entfernt werden soll
            warnung (bool, optional): Warnung an den User ausgeben, dass der Prozess weg ist. Defaults to False.
        """

        button = self.findChild(QtWidgets.QPushButton, prozess.name)
        self.prozesse_layout.removeRow(button)

    def __check_status_der_prozesse(self):
        """
        Wird von einem Thread dauerhaft durchlaufen um zu prüfen ob ein Prozess sich beendet hat
        """

        while True:
            for prozess in self.such_prozesse:
                if not prozess.is_alive():
                    self.__remove_prozess_von_gui(prozess)
                    self.such_prozesse.remove(prozess)
            time.sleep(1.5)

    def __check_old_kontakt_version(self, kontaktdaten: dict = None) -> bool:
        """
        Schaut ob zeitspanne.json vorhanden ist - wenn ja löschen und Warnung ausgeben
        Schaut ob ["zeitrahmen"] in den Kontakdaten ist - wenn ja Warnung ausgeben

        Args:
            kontaktdaten (dict, optional): Kontakdaten wo geladen werden. Defaults to None.

        Returns:
            bool: Alte Version -> False; Alles richtig -> True
        """
        if kontaktdaten:
            try:
                kontaktdaten["zeitrahmen"]
                return True
            except KeyError as error:
                # Zeitrahmen nicht vorhanden - Warnung ausgeben
                pass
        else:
            # Prüfen ob alte Datei vorhanden ist - ggf. löschen
            old_zeitrahmen_path = os.path.join(PATH, "data", "zeitspanne.json")
            if os.path.isfile(old_zeitrahmen_path):
                os.remove(old_zeitrahmen_path)
            else:
                return True

        QtWidgets.QMessageBox.critical(self, "Alte Version von Kontaktdaten!",
                                       "Die Kontakdaten scheinen von einer älteren Version zu sein.\nKontakdaten und Zeitspanne sind nun in einer Datei.\n\nBitte Datei neu erstellen!")
        return False

    ##############################
    #        Kontaktdaten        #
    ##############################

    def kontaktdaten_erstellen(self, modus: Modus = Modus.TERMIN_SUCHEN):
        """
        Ruft den Dialog für die Kontaktdaten auf

        Args:
            modus (Modus): Abhängig vom Modus werden nicht alle Daten benötigt. Defalut TERMIN_SUCHEN
        """

        dialog = QtKontakt(self, modus, self.pfad_kontaktdaten, PATH)
        dialog.update_path.connect(self.__update_kontaktdaten_pfad)
        dialog.show()
        dialog.exec_()

    def __get_kontaktdaten(self, modus: Modus) -> dict:
        """
        Ladet die Kontakdaten aus dem in der GUI hinterlegten Pfad

        Args:
            modus (Modus): Abhängig vom Modus werden nicht alle Daten benötigt.

        Returns:
            dict: Kontakdaten
        """

        if not os.path.isfile(self.pfad_kontaktdaten):
            self.kontaktdaten_erstellen(modus)

        kontaktdaten = kontak_tools.get_kontaktdaten(self.pfad_kontaktdaten)
        if not self.__check_old_kontakt_version(kontaktdaten):
            raise ValidationError("\"zeitrahmen\" fehlt -> Alte Version")

        return kontaktdaten


def main():
    """
    Startet die GUI-Anwendung
    """

    multiprocessing.freeze_support()
    HauptGUI.start_gui()


if __name__ == "__main__":
    main()
