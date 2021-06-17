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

from tools import Modus
from tools import kontaktdaten as kontak_tools
from tools.gui import oeffne_file_dialog_select, open_browser
from tools.gui.qtkontakt import QtKontakt
from tools.gui.qtterminsuche import QtTerminsuche
from tools.gui.qtcodegen import QtCodeGen
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
    #codeGenProzesse_layout
    #sucheProzesse_layout

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
        
        #Spawn for now (The parent process starts a fresh python interpreter process. The child process will only inherit those resources necessary to run the process object’s)
        multiprocessing.set_start_method('spawn')

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

        # Lade Systemsprache und passende Übersetzungen
        sys_lang = QtCore.QLocale.system()
        translator = QtCore.QTranslator()
        if translator.load(sys_lang, "qtbase", "_", QtCore.QLibraryInfo.location(QtCore.QLibraryInfo.TranslationsPath)):
            app.installTranslator(translator)


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
        try:
            self.setWindowTitle('vaccipy ' + get_current_version())
        except Exception as error:
            self.setWindowTitle('vaccipy')
            pass

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

        # Label deaktivieren
        self.findChild(QtWidgets.QLabel, name="suchProzesse_label").setVisible(False)


    def check_update(self):
        """
        Prüft auf neuere Version und gibt evtl. ne Benachrichtigung an den User
        """

        try:
            # Auf Update prüfen
            if update_available():
                url = f"https://github.com/iamnotturner/vaccipy/releases/tag/{get_latest_version()}"
                
                if get_current_version() != 'source': 
                    title = "Alte Version!"
                    text = "Bitte Update installieren"
                    info_text = f"Die Terminsuche funktioniert möglicherweise nicht, da du eine alte Version verwendest ({get_current_version()})"
                else:
                    title = "Sourcecode"
                    text = "Updateprüfung nicht möglich!"
                    info_text = "Du benutzt die nicht paketierten Skripte von Github. Die Terminsuche funktioniert möglicherweise nicht, da die Version veraltet sein könnten."

                msg = QtWidgets.QMessageBox()
                msg.setIcon(QtWidgets.QMessageBox.information)
                msg.setWindowTitle(title)
                msg.setText(text)
                msg.setInformativeText(info_text)
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
        Codegenerierung ohne interaktive Eingabe der Kontaktdaten

        :param kontaktdaten: Dictionary mit Kontaktdaten
        """

        try:
            kontaktdaten = self.__get_kontaktdaten(Modus.CODE_GENERIEREN)
            
            #return if no data was returned
            if not kontaktdaten:
                return

        except FileNotFoundError as error:
            QtWidgets.QMessageBox.critical(self, "Datei nicht gefunden!", f"Datei zum Laden konnte nicht gefunden werden\n\nBitte erstellen")
            return
        except ValidationError as error:
            QtWidgets.QMessageBox.critical(self, "Daten Fehlerhaft!", f"In der angegebenen Datei sind Fehler:\n\n{error}")
            return
        except MissingValuesError as error:
            QtWidgets.QMessageBox.critical(self, "Daten Fehlerhaft!", f"In der angegebenen Datei Fehlen Daten:\n\n{error}")
            return
            
        strProcName = "Codegen (+49****{phone2})".format(phone2=kontaktdaten["kontakt"]["phone"][-4:])

        # allow only 1 Code Gen at a time
        for subProzess in self.such_prozesse:
            if subProzess.name.find("Codegen") >= 0:
                QtWidgets.QMessageBox.information(self, "STOP", "Es läuft bereits eine Codegenerierung!")
                return False

        #start codegen process
        code_prozess = multiprocessing.Process(target=QtCodeGen.start_code_gen, 
            name=strProcName, daemon=True, kwargs={
                "kontaktdaten": kontaktdaten,
                "ROOT_PATH": PATH
            })

        #add code search to list of prozesses
        try:
            code_prozess.start()
            if not code_prozess.is_alive():
                raise RuntimeError(
                    f"Code suche wurde gestartet, lebt aber nicht mehr!"
                )
        except Exception as error:
            QtWidgets.QMessageBox.critical(self, "Fehler - Codegenerierung nicht gestartet!", str(error))
        else:
            self.such_prozesse.append(code_prozess)
            self.__add_prozess_in_gui(code_prozess)
            self.prozesse_counter += 1


        
    def __termin_suchen(self):
        """
        Startet den Prozess der terminsuche mit Impfterminservice.terminsuche in einem neuen Thread
        Dieser wird in self.such_threads hinzugefügt.
        Alle Threads sind deamon Thread (Sofort töten sobald der Bot beendet wird)
        """

        try:
            kontaktdaten = self.__get_kontaktdaten(Modus.TERMIN_SUCHEN)
            if not kontaktdaten:
                return
            zeitrahmen = kontaktdaten["zeitrahmen"]

        except FileNotFoundError as error:
            QtWidgets.QMessageBox.critical(self, "Datei nicht gefunden!", f"Datei zum Laden konnte nicht gefunden werden\n\nBitte erstellen")
            return
        except ValidationError as error:
            QtWidgets.QMessageBox.critical(self, "Daten fehlerhaft!", f"Es scheinen Infos in den Kontaktdaten zu fehlen."
                                                 " Bitte gehe zu Schritt 2 und passe deine Daten an.")
            return
        except MissingValuesError as error:
            QtWidgets.QMessageBox.critical(self, "Daten fehlerhaft!", f"Es scheinen Infos in den Kontaktdaten zu fehlen."
                                                 " Bitte gehe zu Schritt 2 und passe deine Daten an.")
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
        codes = kontaktdaten["codes"]
        name_stubb = kontaktdaten["kontakt"]["vorname"][:15]
        code_stubb = codes[0][-4:]
        strProcName = "{name} [*-{code}]:{id}".format(name=name_stubb,
                                                      code=code_stubb,
                                                      id=str(self.prozesse_counter))
        terminsuche_prozess = multiprocessing.Process(target=QtTerminsuche.start_suche, name=strProcName, daemon=True, kwargs={
                                                      "kontaktdaten": kontaktdaten,
                                                      "notifications": notifications,
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
                return

        if pfad is None:
            return

        self.pfad_kontaktdaten = pfad
        self.i_kontaktdaten_pfad.setText(self.pfad_kontaktdaten)

    def __add_prozess_in_gui(self, prozess: multiprocessing.Process,):
        """
        Die Prozesse werden in der GUI in dem prozesse_layout angezeigt
        """
        if prozess.name.find("Codegen") >= 0:
            self.findChild(QtWidgets.QLabel, name="keine_codeGen_label").setVisible(False)
            label = QtWidgets.QLabel(f"{prozess.name}")
            button = QtWidgets.QPushButton("Stoppen")
            button.setObjectName(prozess.name)
            button.clicked.connect(lambda: self.__stop_prozess(prozess))
            self.codeGenProzesse_layout.addRow(label, button)
        else:
            self.findChild(QtWidgets.QLabel, name="keine_suchProzesse_label").setVisible(False)
            self.findChild(QtWidgets.QLabel, name="suchProzesse_label").setVisible(True)
            label = QtWidgets.QLabel(f"{prozess.name[0:prozess.name.find(':')]}")
            button = QtWidgets.QPushButton("Stoppen")
            button.setObjectName(prozess.name)
            button.clicked.connect(lambda: self.__stop_prozess(prozess))
            self.sucheProzesse_layout.addRow(label, button)
        

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

        if prozess.name.find("Codegen") >= 0:
            self.findChild(QtWidgets.QLabel, name="keine_codeGen_label").setVisible(True)
            self.keine_codeGen_label.setVisible(True)
            self.codeGenProzesse_layout.removeRow( button)

        else:
            if len(self.such_prozesse) == 0:
                self.findChild(QtWidgets.QLabel, name="keine_suchProzesse_label").setVisible(True)
                self.findChild(QtWidgets.QLabel, name="suchProzesse_label").setVisible(False)
            elif len(self.such_prozesse) == 1:
                if self.such_prozesse[0].name.find("Codegen") >= 0:
                    self.findChild(QtWidgets.QLabel, name="keine_suchProzesse_label").setVisible(True)
                    self.findChild(QtWidgets.QLabel, name="suchProzesse_label").setVisible(False)
            self.sucheProzesse_layout.removeRow( button)


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

    def kontaktdaten_erstellen(self, modus: Modus = Modus.TERMIN_SUCHEN) -> bool:
        """
        Ruft den Dialog für die Kontaktdaten auf

        Args:
            modus (Modus): Abhängig vom Modus werden nicht alle Daten benötigt. Defalut TERMIN_SUCHEN

        Returns:
            bool: True bei Erfolg, False bei Abbruch
        """

        dialog = QtKontakt(self, modus, self.pfad_kontaktdaten, PATH)
        dialog.update_path.connect(self.__update_kontaktdaten_pfad)
        dialog.show()
        if dialog.exec_() == QtWidgets.QDialog.Rejected:
            return False
        else:
            return True

    def __get_kontaktdaten(self, modus: Modus) -> dict:
        """
        Ladet die Kontakdaten aus dem in der GUI hinterlegten Pfad

        Args:
            modus (Modus): Abhängig vom Modus werden nicht alle Daten benötigt.

        Returns:
            dict: Kontakdaten
        """
        if not os.path.isfile(self.pfad_kontaktdaten):
            if not self.kontaktdaten_erstellen(modus):
                return {}

        kontaktdaten = kontak_tools.get_kontaktdaten(self.pfad_kontaktdaten)
        kontak_tools.check_kontaktdaten(kontaktdaten, modus)
        
        if modus == Modus.TERMIN_SUCHEN:
            if not self.__check_old_kontakt_version(kontaktdaten):
                raise ValidationError("\"zeitrahmen\" fehlt -> Alte Version")
           
            if "codes" in kontaktdaten:
                if "XXXX-XXXX-XXXX" in kontaktdaten["codes"]:
                    raise ValidationError("Der Code is ungültig. Bitte trage einen korrekten Code ein!")

        return kontaktdaten



def main():
    """
    Startet die GUI-Anwendung
    """

    multiprocessing.freeze_support()
    HauptGUI.start_gui()


if __name__ == "__main__":
    main()
