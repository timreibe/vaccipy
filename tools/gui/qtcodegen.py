#!/usr/bin/env python3

import sys
import os
import time

from PyQt5 import QtWidgets, uic, QtCore, QtGui
from PyQt5.QtCore import QObject, QThread, pyqtSignal
from PyQt5.QtGui import QIcon
from tools.gui import *
from tools.its import ImpfterminService
from tools.kontaktdaten import validate_datum
from tools.exceptions import MissingValuesError, ValidationError
from tools.utils import gen_random_code

PATH = os.path.dirname(os.path.realpath(__file__))

            
class EigenerStream(QtCore.QObject):
        
    """
    Klasse wenn auf write() zugegriffen wird, dann wird das Signal textWritten ausgelöst
    """

    # Signal welches ausgelöst werden kann
    text_schreiben = pyqtSignal(str)

    def write(self, stream):
        """
        Löst das Signal text_schreiben aus und übergibt das Argument text weiter
        """
        
        self.text_schreiben.emit(str(stream))

class Worker(QObject):
    """
    Worker, der nichts anderes macht, als den Termin mithilfe its.py zu suchen
    sobald die Suche beendet wurde, wird ein "fertig" Signal geworfen, welches den Rückgabewert von its übergibt
    """

    # Signal wenn Suche abgeschlossen oder fehlgeschlagen
    signalShowInput = pyqtSignal(str)
    signalUpdateData = pyqtSignal(str,str)
    signalStop = pyqtSignal()

    def __init__(self, kontaktdaten: dict, ROOT_PATH: str):
        """
        Args:
            kontaktdaten (dict): kontakdaten aus kontaktdaten.jso
            ROOT_PATH (str): Pfad zur main.py / gui.py
        """
        super().__init__()
        
        self.stopped = False

        self.kontaktdaten = kontaktdaten
        self.ROOT_PATH = ROOT_PATH
        
        self.signalUpdateData.connect(self.updateData)
        self.signalStop.connect(self.stop)
        
        self.geburtsdatum = ""
        self.plz_impfzentrum = ""
        self.mail = ""
        self.telefonnummer = ""
        self.sms_pin = ""
        
        self.signalGot = False
        
    def __del__(self):
        print("Worker quit")
        
    def stop(self):
        self.stopped = True
        
    def updateData(self, strmode, txt):
        if strmode == "GEBURTSDATUM":
            print(txt)
            self.geburtsdatum = txt
        elif strmode == "SMSCODE":
            print(txt)
            self.sms_pin = txt
            
        self.signalGot = True
        return True
        
    def run(self):

        """
        Startet den Prozess der Codegenerierung
        """
        """
        Codegenerierung ohne interaktive Eingabe der Kontaktdaten
        :param kontaktdaten: Dictionary mit Kontaktdaten
        """
        
        self.plz_impfzentrum = self.kontaktdaten["plz_impfzentren"][0]
        self.mail = self.kontaktdaten["kontakt"]["notificationReceiver"]
        self.telefonnummer = self.kontaktdaten["kontakt"]["phone"]

        # Erstelle Zufallscode nach Format XXXX-YYYY-ZZZZ
        # für die Cookie-Generierung
        random_code = gen_random_code()
        print(f"Für die Cookies-Generierung wird ein zufälliger Code verwendet ({random_code}).\n")

        its = ImpfterminService(random_code, [self.plz_impfzentrum], {}, self.ROOT_PATH)
        
        # send signal for GUI
        self.signalShowInput.emit("GEBURTSDATUM")
        while True:
            if self.signalGot is True:
                break

        #reset member for next signal
        self.signalGot = False
        
        #stop requested in the meanwhile?
        if self.stopped is True:
            return False
            
        # cookies erneuern und code anfordern
        its.renew_cookies_code()
        token = its.code_anfordern(self.mail, self.telefonnummer,  self.plz_impfzentrum, self.geburtsdatum)

        if token is not None:
            # code bestätigen            
            # 3 Versuche für die SMS-Code-Eingabe
            self.signalShowInput.emit("SMSCODE")
            while True:
                if self.signalGot is True:
                    break
            #stop requested in the meanwhile?
            if self.stopped is True:
                return False
                
            if its.code_bestaetigen(token, self.sms_pin):
                self.signalShowInput.emit("SMSCODE_OK")
                return True

        print( "Die Code-Generierung war leider nicht erfolgreich.")
        return False




class QtCodeGen(QtWidgets.QDialog):

    # Folgende Widgets stehen zur Verfügung:

    def __init__(self, parent, kontaktdaten: dict,  ROOT_PATH: str):
        super().__init__(parent)
        uic.loadUi(os.path.join(PATH, "ui_qtcodegen.ui"), self)
        self.setupUi(self)
        
        self.parent = parent
        
        # Attribute erstellen
        self.kontaktdaten = kontaktdaten
        self.ROOT_PATH = ROOT_PATH

        # std.out & error auf das Textfeld umleiten
        sys.stdout = EigenerStream(text_schreiben=self.update_ausgabe)
        sys.stderr = EigenerStream(text_schreiben=self.update_ausgabe)

    
        # Entsprechend Konfigurieren
        self.setup_thread()
        self.thread.start()
        
        # show gui
        self.show()
  
    def __del__(self):
        print("QtCodeGen destruct")
        
    def setupUi(self, QtCodeGen):
        self.setObjectName("QtCodeGen")
        self.setWindowModality(QtCore.Qt.WindowModal)
        self.setModal(False)
        self.resize(700, 300)


    def setup_thread(self):
        """
        Thread + Worker erstellen und Konfigurieren
        """
        self.thread = QThread(parent=self)
        self.thread.setTerminationEnabled(True)
        self.worker = Worker(self.kontaktdaten, self.ROOT_PATH)
        
        # Worker und Thread verbinden
        self.worker.moveToThread(self.thread)
        
        # Signale setzen
        self.thread.started.connect(self.worker.run)
        self.worker.signalShowInput.connect(self.showInputDlg)


    def update_ausgabe(self, text):
        """
        Fügt den übergeben Text dem textAusgabe hinzu

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

        cursor = self.textAusgabe.textCursor()
        cursor.movePosition(QtGui.QTextCursor.End)
        cursor.insertHtml(str(text))
        cursor.insertText(str("\n"))
        self.textAusgabe.setTextCursor(cursor)
        self.textAusgabe.ensureCursorVisible()
        
        
    def showInputDlg(self, dlgType):
        
        if dlgType == "GEBURTSDATUM":
           while True:
                try:
                    text, ok = QtWidgets.QInputDialog.getText(self, 'Geburtsdatum', 'Bitte trage nachfolgend dein Geburtsdatum im Format DD.MM.YYYY ein.\n'
                        'Beispiel: 02.03.1982\n')
                    if ok:
                        geburtsdatum = str(text)
                        validate_datum(geburtsdatum)
                        self.worker.signalUpdateData.emit("GEBURTSDATUM",geburtsdatum)
                        break
                    else:
                        self.worker.signalStop.emit()
                        break
                except ValidationError as exc:
                    QtWidgets.QMessageBox.critical(self, "Geburtsdatum ungültiges Format", "Das Datum entspricht nicht dem richtigen Format (DD.MM.YYYY).")
                    
        elif dlgType == "SMSCODE":
            text, ok = QtWidgets.QInputDialog.getText(self, 'SMS Code', 
                'Du erhältst gleich eine SMS mit einem Code zur Bestätigung deiner Telefonnummer\n'
                'Bitte trage nachfolgend den SMS-Code ein.\n'
                'Beispiel: 551-550\n')
            if ok:
                sms_pin = str(text).replace("-", "")
                self.worker.signalUpdateData.emit("SMSCODE",sms_pin) 
        elif dlgType == "SMSCODE_OK":
            QtWidgets.QMessageBox.information(self, "Erfolgreich", "Code erfolgreich generiert. Du kannst jetzt mit der Terminsuche fortfahren.")
            
        self.worker.signalUpdateData.emit("DUMMY","")

 

    def closeEvent(self, event):
        """
        Wird aufgerufen, wenn die Anwendung geschlossen wird
        """

        if self.thread.isRunning():
            res = QtWidgets.QMessageBox.warning(self, "Suche beenden", "Suche wirklich beenden?\n",
                                                (QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel))

            if res != QMessageBox.StandardButton.Ok:
                event.ignore()
                return
                
            event.accept()
            
        #exit
        self.parent.enableCodeBtn.emit() # enable Code Btn again
        
        #stop worker
        self.worker.stop()
        self.worker.deleteLater()
        
        #stop thread
        self.thread.quit()
        self.thread.wait()
        self.thread.terminate()
       
        
        # Streams wieder korrigieren, damit kein Fehler kommt
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__

        self.deleteLater()
        event.accept()
