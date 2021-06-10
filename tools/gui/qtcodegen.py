#!/usr/bin/env python3

import sys
import os


from PyQt5 import QtWidgets, uic, QtCore, QtGui
from PyQt5.QtCore import QObject, QThread, pyqtSignal
from PyQt5.QtGui import QIcon
from tools.gui import *
from tools.its import ImpfterminService
from tools.kontaktdaten import validate_datum
from tools.exceptions import MissingValuesError, ValidationError


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
    signalShowDlg = pyqtSignal(str,str)
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
        self.signalGot = False

        self.kontaktdaten = kontaktdaten
        self.ROOT_PATH = ROOT_PATH
        
        self.geburtsdatum = ""
        self.plz_impfzentrum = ""
        self.mail = ""
        self.telefonnummer = ""
        self.sms_pin = ""
        
        # connect to signals
        self.signalUpdateData.connect(self.updateData)
        self.signalStop.connect(self.stop)


    def __del__(self):
        print("Worker quit")

    def stop(self):
        self.stopped = True

    # send a signal and wait for received return
    def sendSignalAndWait(self, strSignal, strSigParam):
        if strSignal == "signalShowInput":
            self.signalShowInput.emit(strSigParam)

        while True and self.stopped is False:
            if self.signalGot is True:
                break
            QtCore.QThread.msleep(100)
        #reset member for next signal
        self.signalGot = False


    def updateData(self, strmode, txt):
        if strmode == "GEBURTSDATUM":
            print(txt)
            self.geburtsdatum = txt
        elif strmode == "SMSCODE":
            print(txt)
            self.sms_pin = txt
            
        self.signalGot = True
        return True
        
    def code_gen(self):
        """
        Startet den Prozess der Codegenerierung
        """
        """
        Codegenerierung ohne interaktive Eingabe der Kontaktdaten
        :param kontaktdaten: Dictionary mit Kontaktdaten
        """
        try:
            self.plz_impfzentrum = self.kontaktdaten["plz_impfzentren"][0]
            self.mail = self.kontaktdaten["kontakt"]["notificationReceiver"]
            self.telefonnummer = self.kontaktdaten["kontakt"]["phone"]
        except KeyError as error:
            self.signalShowDlg.emit("MISSING_KONTAKT","")
            self.stop()
           
        if self.stopped is True:
            return False
            
        its = ImpfterminService([], {}, self.ROOT_PATH)
        
        # send signal for GUI
        self.sendSignalAndWait("signalShowInput","GEBURTSDATUM")

        #stop requested in the meanwhile?
        if self.stopped is True:
            return False
            
        # code anfordern
        try:
            token, cookies = its.code_anfordern(self.mail, self.telefonnummer,  self.plz_impfzentrum, self.geburtsdatum)
        except RuntimeError as exc:
            print(
                f"\nDie Code-Generierung war leider nicht erfolgreich:\n{str(exc)}")
            self.signalShowDlg.emit("CRITICAL_CLOSE",f"\nDie Code-Generierung war leider nicht erfolgreich:\n{str(exc)}")
            while True and self.stopped is False:
                QtCore.QThread.msleep(100)
            return False

        # code bestätigen            
        # 3 Versuche für die SMS-Code-Eingabe
        self.sendSignalAndWait("signalShowInput","SMSCODE")
            
        #stop requested in the meanwhile?
        if self.stopped is True:
            return False
            
        if its.code_bestaetigen(token, cookies, self.sms_pin, self.plz_impfzentrum):
            self.sendSignalAndWait("signalShowInput","SMSCODE_OK")
            return True

        print("\nSMS-Code ungültig")
        print("Die Code-Generierung war leider nicht erfolgreich.")

        self.signalShowDlg.emit("CRITICAL_CLOSE",f"SMS-Code ungültig.\n\nDie Code-Generierung war leider nicht erfolgreich")
        return False




class QtCodeGen(QtWidgets.QDialog):
    # Folgende Widgets stehen zur Verfügung:
    def __init__(self, kontaktdaten: dict, ROOT_PATH: str, parent = None):
        super().__init__(parent)
        uic.loadUi(os.path.join(PATH, "ui_qtcodegen.ui"), self)
        self.setupUi(self)
        
        self.parent = parent
        self._hardClose = False
        
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
        
    def setupUi(self, QtCodeGen, ROOT_PATH):
        self.setObjectName("QtCodeGen")
        self.setWindowModality(QtCore.Qt.WindowModal)
        self.setModal(False)
        self.resize(700, 300)
        self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowContextHelpButtonHint);
        self.setWindowIcon(QIcon(os.path.join(ROOT_PATH, "images/spritze.ico")))

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
        self.thread.started.connect(self.worker.code_gen)
        self.worker.signalShowInput.connect(self.showInputDlg)
        self.worker.signalShowDlg.connect(self.showDlg)


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
                        self.hardClose()
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
            else:
                self.hardClose()
        elif dlgType == "SMSCODE_OK":
            QtWidgets.QMessageBox.information(self, "Erfolgreich", "Code erfolgreich generiert. Du kannst jetzt mit der Terminsuche fortfahren.")
            self.worker.signalUpdateData.emit("SMSCODE_OK","") 
            
    def showDlg(self, strMode, strTxt):
        if strMode == "MISSING_KONTAKT":
            ret = QtWidgets.QMessageBox.critical(self, "Kontaktdaten ungültig",
                "Die Kontakdaten sind nicht korrekt!.\n\nBitte Datei neu erstellen!", QMessageBox.StandardButton.Ok)
            if ret == QMessageBox.StandardButton.Ok:
                self.hardClose()
        elif strMode == "CRITICAL_CLOSE":
            ret = QtWidgets.QMessageBox.critical(self, "Error", strTxt, QMessageBox.StandardButton.Ok)
            if ret == QMessageBox.StandardButton.Ok:
                self.hardClose()

                
    # force to close the dialog without confirmation
    def hardClose(self):
        self._hardClose = True
        self.close()
         
    def closeEvent(self, event):
        """
        Wird aufgerufen, wenn die Anwendung geschlossen wird
        """

        if self.thread.isRunning():
            if self._hardClose is False:
                res = QtWidgets.QMessageBox.warning(self, "Suche beenden", "Suche wirklich beenden?\n",
                                                    (QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel))

                if res != QMessageBox.StandardButton.Ok:
                    event.ignore()
                    return
                
            
        #exit
        if self.parent is not None:
            self.parent.enableCodeBtn.emit() # enable Code Btn again

        #stop worker
        self.worker.stop()
        self.worker.deleteLater()

        #stop thread
        self.thread.quit()
        self.thread.wait(3000)
        self.thread.terminate()

        # Streams wieder korrigieren, damit kein Fehler kommt
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__

        self.deleteLater()
        event.accept()

    @staticmethod
    def start_code_gen(kontaktdaten: dict,  ROOT_PATH: str):
        app = QtWidgets.QApplication(list())
        window = QtCodeGen(kontaktdaten, ROOT_PATH)
        app.exec_()
        
