#!/usr/bin/env python3

import sys
import os

from PyQt5 import QtWidgets, uic, QtCore, QtGui
from PyQt5.QtCore import QObject, QThread, pyqtSignal
from PyQt5.QtGui import QIcon
from tools.gui import *
from tools.its import ImpfterminService

PATH = os.path.dirname(os.path.realpath(__file__))


class EigenerStream(QtCore.QObject):
    """
    Klasse wenn auf write() zugegriffen wird, dann wird das Siganl textWritten ausgelöst
    """

    # Signal welches ausgelöst werden kann
    text_schreiben = pyqtSignal(str)

    def write(self, stream):
        """
        Löst das Signal text_schreiben aus und übergibt das Argumet text weiter
        """
        self.text_schreiben.emit(str(stream))


class Worker(QObject):
    """
    Worker, der nichts anderes macht, als den Termin mithilfe its.py zu suchen
    sobald die Suche beendet wurde, wird ein "fertig" Signal geworfen, welches den Rückgabewert von its übergibt
    """

    # Signal wenn Suche abgeschlossen oder fehlgeschlagen
    fertig = pyqtSignal()
    fehlschlag = pyqtSignal(Exception)

    def __init__(self, kontaktdaten: dict, zeitrahmen: dict, ROOT_PATH: str, check_delay: int):
        """
        Args:
            kontaktdaten (dict): kontakdaten aus kontaktdaten.json
            zeitrahmen (dict): zeitrahmen
            ROOT_PATH (str): Pfad zur main.py / gui.py
        """
        super().__init__()

        self.kontaktdaten = kontaktdaten
        self.zeitrahmen = zeitrahmen
        self.ROOT_PATH = ROOT_PATH
        self.check_delay = check_delay

    def suchen(self):
        """
        Startet die Terminsuche. Dies nur mit einem Thread starten, da die GUI sonst hängt
        """

        kontakt = self.kontaktdaten["kontakt"]
        codes = self.kontaktdaten["codes"]
        plz_impfzentren = self.kontaktdaten["plz_impfzentren"]

        try:
            ImpfterminService.terminsuche(codes=codes, plz_impfzentren=plz_impfzentren, kontakt=kontakt,
                                          PATH=self.ROOT_PATH, check_delay=self.check_delay, zeitrahmen=self.zeitrahmen)

            self.fertig.emit()

        except Exception as error:
            self.fehlschlag.emit(error)


class QtTerminsuche(QtWidgets.QMainWindow):

    # Folgende Widgets stehen zur Verfügung:

    ### QLabel ###
    # code_label
    # vorname_label
    # nachname_label
    # interval_label

    ### ButtonBox ###
    # buttonBox
    # Close

    ### QTextEdit (readonly) ###
    # console_text_edit

    def __init__(self, kontaktdaten: dict, zeitrahmen: dict, ROOT_PATH: str, check_delay: int, pfad_fenster_layout=os.path.join(PATH, "terminsuche.ui")):

        super().__init__()

        # Laden der .ui Datei und Anpassungen
        uic.loadUi(pfad_fenster_layout, self)
        self.setWindowIcon(QIcon(os.path.join(ROOT_PATH, "images/spritze.ico")))

        self.buttonBox.rejected.connect(self.close)

        # Attribute erstellen
        self.kontaktdaten = kontaktdaten
        self.zeitrahmen = zeitrahmen
        self.ROOT_PATH = ROOT_PATH
        self.check_delay = check_delay

        # std.out & error auf das Textfeld umleiten
        sys.stdout = EigenerStream(text_schreiben=self.update_ausgabe)
        sys.stderr = EigenerStream(text_schreiben=self.update_ausgabe)

        # Entsprechend Konfigurieren
        self.setup_thread()

        # Infos setzten
        self.setup_infos()

        # GUI anzeigen
        self.show()

        # Terminsuche starten
        self.thread.start()

    @staticmethod
    def start_suche(kontaktdaten: dict, zeitrahmen: dict, ROOT_PATH: str, check_delay: int):
        """
        Startet die Suche in einem eigenen Fenster mit Umlenkung der Konsolenausgabe in das Fenster

        Args:
            kontaktdaten (dict): kontaktdaten aus JSON
            zeitrahmen (dict): zeitrahmen aus JSON
            ROOT_PATH (str): Pfad zum Root Ordner, damit dieser an its übergeben werden kann
            check_delay (int): Interval in Sekunden zwischen jeder Terminsuche
        """
        app = QtWidgets.QApplication(list())
        app.setAttribute(QtCore.Qt.AA_X11InitThreads)
        window = QtTerminsuche(kontaktdaten, zeitrahmen, ROOT_PATH, check_delay)
        app.exec_()

    def setup_infos(self):
        """
        Setzt die entsprechende Labels
        """
        self.interval_label.setText(f"{self.check_delay} Sekunden")
        self.code_label.setText(", ".join(self.kontaktdaten["codes"]))
        self.vorname_label.setText(self.kontaktdaten["kontakt"]["vorname"])
        self.nachname_label.setText(self.kontaktdaten["kontakt"]["nachname"])

    def setup_thread(self):
        """
        Thread + Worker erstellen und Konfigurieren
        """

        self.thread = QThread(parent=self)
        self.worker = Worker(self.kontaktdaten, self.zeitrahmen, self.ROOT_PATH, self.check_delay)

        # Worker und Thread verbinden
        self.worker.moveToThread(self.thread)

        # Signale setzen
        self.worker.fertig.connect(self.suche_beendet)
        self.worker.fertig.connect(self.thread.quit)
        self.worker.fertig.connect(self.worker.deleteLater)

        self.worker.fehlschlag.connect(self.suche_beendet)
        self.worker.fehlschlag.connect(self.thread.quit)
        self.worker.fehlschlag.connect(self.worker.deleteLater)

        self.thread.started.connect(self.worker.suchen)

    def update_ausgabe(self, text):
        """
        Fügt den übergeben Text dem console_text_edit hinzu

        Args:
            text (str): Text welcher hinzukommen soll
        """
        # Austausch der Farbcodes / Ascii Zeichen aus der Shell
        listeCodes = ['\033[95m', '\033[91m', '\033[33m', '\x1b[0m', '\033[94m', '\033[32m', '\033[0m']
        for farbcode in listeCodes:
            if farbcode in text:
                if farbcode == '\033[95m' or farbcode == '\033[91m':
                    text = f"<div style='color:red'>{text}</div>"
                elif farbcode == '\033[33m':
                    text = f"<div style='color:orange'>{text}</div>"
                elif farbcode == '\x1b[0m':
                    text = f"<div>{text}</div>"
                elif farbcode == '\033[94m':
                    text = f"<div style='color:blue'>{text}</div>"
                elif farbcode == '\033[32m':
                    text = f"<div style='color:green'>{text}</div>"
                text = text.replace(farbcode, '')

        cursor = self.console_text_edit.textCursor()
        cursor.movePosition(QtGui.QTextCursor.End)
        cursor.insertHtml(str(text))
        cursor.insertText(str("\n"))
        self.console_text_edit.setTextCursor(cursor)
        self.console_text_edit.ensureCursorVisible()

    def suche_beendet(self, error: Exception = None):
        """
        Wird aufgerufen, sobald die Suche vom Worker beendet wurde
        Entsprechend auf übergebenen Fehler wird eine Meldung auf erfolg oder Fehlschlag ausgegeben

        Args:
            error (Exception, optional): Fehler der bei der Suche auftauchte. Defaults to None.
        """

        if error:
            QtWidgets.QMessageBox.critical(self, "Suche Fehlgeschlagen!", f"Suche wurde abgebrochen:\n{str(error)}")
        else:
            QtWidgets.QMessageBox.information(self, "Termin gefunden!", "Termin gefunden!\nAusgabe Prüfen!")

    def closeEvent(self, event):
        """
        Wird aufgerufen, wenn die Anwendung geschlossen wird

        Args:
            event: Schließen Event von QT
        """

        if self.thread.isRunning():
            res = QtWidgets.QMessageBox.warning(self, "Suche beenden", "Suche wirklich beenden?\n",
                                                (QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel))

            if res != QMessageBox.StandardButton.Ok:
                event.ignore()
                return
            else:
                self.thread.quit()

        # Streams wieder korrigieren, damit kein Fehler kommt
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__

        event.accept()
