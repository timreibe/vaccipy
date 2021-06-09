import os

from PyQt5 import QtWidgets, uic
from PyQt5.QtCore import QTime, QDate, QDateTime, pyqtSignal
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

### QComboBox ###
# i_anrede_combo_box

### QDialogButtonBox ###
# buttonBox
# Apply
# Cancel
# Reset

### QWidget ###
# kontaktdaten_tab
# zeitrahmen_tab

### Buttons ###
# b_impfzentren_waehlen

PATH = os.path.dirname(os.path.realpath(__file__))


class QtKontakt(QtWidgets.QDialog):

    # Signal welches geworfen wird, wenn man gespeichert hat
    # Gibt einen String mit dem Speicherort der Datei
    update_path = pyqtSignal(str)

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
        self.buttonBox.clicked.connect(self.__button_box_clicked)

        # Funktion vom Button zuordnen
        self.b_impfzentren_waehlen.clicked.connect(self.__open_impfzentren)

        # Versuche Kontakdaten zu laden 
        self.__lade_alle_werte()

    def setup(self):
        """
        Aktiviert abhänig vom Modus die Eingabefelder

        Raises:
            RuntimeError: Modus ungültig
        """

        # Startdatum setzten auf heute
        self.i_start_datum_qdate.setMinimumDateTime(QDateTime.currentDateTime())

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

            # Neuer Pfad in der Main GUI übernehmen
            self.update_path.emit(speicherpfad)

            # Fenster schließen
            self.close()

        except (TypeError, IOError, FileNotFoundError) as error:
            QtWidgets.QMessageBox.critical(self, "Fehler beim Speichern!", "Bitte erneut versuchen!")
            return

        except ValidationError as error:
            QtWidgets.QMessageBox.critical(self, "Daten Fehlerhaft!", f"In den angegebenen Daten sind Fehler:\n\n{error}")
            return

        except MissingValuesError as error:
            QtWidgets.QMessageBox.critical(self, "Daten Fehlerhaft!", f"In der angegebenen Daten Fehlen Werte:\n\n{error}")
            return

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


    def __lade_einstellungen(self):
        """
        Lädt alle Werte aus einer JSON-Datei
        Speicherpfad wird vom User angefragt
        """
        try:
            speicherpfad = oeffne_file_dialog_select(self, "Kontaktdaten", self.standard_speicherpfad)
        except FileNotFoundError:
            self.__oeffne_error(title="Kontaktdaten", text="Datei konnte nicht geöffnet werden.",
                                info="Die von Ihnen gewählte Datei konne nicht geöffnet werden.")
            return

        self.standard_speicherpfad = speicherpfad
        self.update_path.emit(speicherpfad)

        self.__lade_alle_werte()


    def __button_box_clicked(self, button: QtWidgets.QPushButton):
        """
        Zuweisung der einzelnen Funktionen der Buttons in der ButtonBox

        Args:
            button (PyQt5.QtWidgets.QPushButton): Button welcher gedrückt wurde
        """

        clicked_button = self.buttonBox.standardButton(button)
        if clicked_button == QtWidgets.QDialogButtonBox.Save:
            self.bestaetigt()
        elif clicked_button == QtWidgets.QDialogButtonBox.Reset:
            self.__reset_kontakdaten()
            self.__reset_zeitrahmen()
        elif clicked_button == QtWidgets.QDialogButtonBox.Open:
            self.__lade_einstellungen()
        elif clicked_button == QtWidgets.QDialogButtonBox.Cancel:
            self.close()

    def __get_alle_werte(self) -> dict:
        """
        Holt sich alle Werte aus der GUI und gibt diese fertig zum speichern zurück

        Returns:
            dict: User eingaben
        """

        plz_zentrum_raw = self.i_plz_impfzentren.text()
        codes = [self.i_code_impfzentren.text().strip()]
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
            "codes": codes,
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
            },
            "zeitrahmen": self.__get_zeitrahmen()
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


    def __lade_alle_werte(self):
        """
        Lädt alle Kontaktdaten und den Suchzeitraum in das GUI
        """

        try:
            kontaktdaten = kontakt_tools.get_kontaktdaten(self.standard_speicherpfad)

            if not kontaktdaten:
                # ToDo: Evtl. Meldung anzeigen
                return
            
            self.__check_werte(kontaktdaten)

            self.i_plz_impfzentren.setText(self.__get_impfzentren_plz(kontaktdaten["plz_impfzentren"]))
            self.i_telefon.setText(kontaktdaten["kontakt"]["phone"])
            self.i_mail.setText(kontaktdaten["kontakt"]["notificationReceiver"])
            
            if self.modus == Modus.CODE_GENERIEREN:
                # Versuche alle Werte zu laden, wenn möglich
                try:
                    kontakt_tools.check_kontaktdaten(kontaktdaten, Modus.TERMIN_SUCHEN)
                    kontakt_tools.validate_kontaktdaten(kontaktdaten)
                except MissingValuesError as exc:
                    return
                except ValidationError as exc:
                    return
            
            # Wird nur bei Terminsuche benötigt
            self.i_code_impfzentren.setText(kontaktdaten["code"])
            self.i_anrede_combo_box.setEditText(kontaktdaten["kontakt"]["anrede"])
            self.i_vorname.setText(kontaktdaten["kontakt"]["vorname"])
            self.i_nachname.setText(kontaktdaten["kontakt"]["nachname"])
            self.i_strasse.setText(kontaktdaten["kontakt"]["strasse"])
            self.i_hausnummer.setText(kontaktdaten["kontakt"]["hausnummer"])
            self.i_plz_wohnort.setText(kontaktdaten["kontakt"]["plz"])
            self.i_wohnort.setText(kontaktdaten["kontakt"]["ort"])

            try:
                self.__set_zeitrahmen(kontaktdaten["zeitrahmen"])
                # Subkeys von "zeitrahmen" brauchen nicht gecheckt werden, da
                # `kontaktdaten["zeitrahmen"] == {}` zulässig ist.

            except ValueError:
                self.__reset_zeitrahmen()
                self.__oeffne_error(title="Kontaktdaten", text="Falscher Suchzeitraum",
                                info= "Der Suchzeitraum Ihrer Kontaktdaten ist fehlerhaft."
                                      " Überprüfen Sie die Daten im Reiter Zeitrahmen und"
                                      " speichern Sie die Kontaktdaten.")
                pass
         
        except MissingValuesError as exc:
            self.__reset_kontakdaten()
            self.__reset_zeitrahmen()
            self.__oeffne_error(title="Kontaktdaten", text="Falsches Format",
                info= "Die von Ihnen gewählte Datei hat ein falsches Format. "
                       "Laden Sie eine andere Datei oder überschreiben Sie die "
                       "Datei, indem Sie auf Speichern klicken.")

        except ValidationError as exc:
            self.__reset_kontakdaten()
            self.__reset_zeitrahmen()
            self.__oeffne_error(title="Kontaktdaten", text="Falsches Format",
                info= "Die von Ihnen gewählte Datei hat ein falsches Format. "
                       "Laden Sie eine andere Datei oder überschreiben Sie die "
                       "Datei, indem Sie auf Speichern klicken.")






    ##############################
    #        Kontakdaten         #
    ##############################

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

    def __reset_kontakdaten(self):
        """
        Setzt alle Werte für die Kontaktdaten in der GUI zurück
        """

        for widget in self.kontaktdaten_tab.children():
            if isinstance(widget, QtWidgets.QLineEdit):
                widget.setText("")
            elif isinstance(widget, QtWidgets.QComboBox):
                widget.setCurrentText("Bitte Wählen")

        # Telefon wieder mit Prefix befüllen
        self.i_telefon.setText("+49")

    def __get_impfzentren_plz(self, plzList : list) -> str: 
        """
        Erstellt ein String aus einer Liste an PLZ für die GUI

        Args:
            plzList: List der PLZ

        Returns:
            String mit allen PLZ der Impfzentren

        """
        plz_zentrum_raw = ''
        for plz in plzList:
            plz_zentrum_raw += plz + ', '
        return plz_zentrum_raw[:-2]


    ##############################
    #        Zeitrahmen          #
    ##############################

    def __get_zeitrahmen(self) -> dict:
        """
        Gibt alle nötigen Daten richtig formatiert zum abspeichern

        Returns:
            dict: alle Daten
        """

        aktive_wochentage = self.__get_aktive_wochentage()
        uhrzeiten = self.__get_uhrzeiten()
        termine = self.__get_aktive_termine()
        start_datum = self.i_start_datum_qdate.date()

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

    def __reset_zeitrahmen(self, widgets: list = None):
        """
        Setzt alle Werte für den Zeitrahmen in der GUI zurück
        """

        if widgets is None:
            self.__reset_zeitrahmen(self.zeitrahmen_tab.children())
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
                self.__reset_zeitrahmen(widget.children())

    def __set_zeitrahmen(self, zeitrahmen: dict):
        """
        Setzt den Suchzeitraum in der GUI

        Args:
            zeitrahmen: Dict mit allen Daten für den Suchzeitraum

        Raise:
            ValueError: Suchzeitraum unvollständig oder fehlerhaft
        """

        if not zeitrahmen:
            # Leeres Dict -> Keine Restriktionen
            return

        try:
            von_datum = str(zeitrahmen["von_datum"])
            von_uhr = zeitrahmen["von_uhrzeit"]
            bis_uhr = zeitrahmen["bis_uhrzeit"]
            wochentage = zeitrahmen["wochentage"]
            einhalten_bei = zeitrahmen["einhalten_bei"]

        except KeyError:
            raise ValueError("Die Zeitangaben sind unvollständig.")

        self.__set_einhalten_bei(einhalten_bei)
        self.__set_wochentage(wochentage)

        try:
            self.__set_start_datum(von_datum)
            self.__set_uhrzeit_datum(bis_uhr, self.i_end_time_qtime)
            self.__set_uhrzeit_datum(von_uhr, self.i_start_time_qtime)

        except AssertionError:
            raise ValueError("Das Datum oder die Uhrzeiten haben ein falsches Format.")
        
    def __set_einhalten_bei(self, einhalten: str):
        """
        Setzt die Termine, welche von den Restriktionen betroffen sind
        in der GUI

        Args:
            einhalten: str bei welchen Terminen die Restriktionen gelten
        """
        
        if einhalten == "beide":
            self.i_erster_termin_check_box.setChecked(True)
            self.i_zweiter_termin_check_box.setChecked(True)
        elif einhalten == "1":
            self.i_erster_termin_check_box.setChecked(True)
            self.i_zweiter_termin_check_box.setChecked(False)
        elif einhalten == "2":
            self.i_erster_termin_check_box.setChecked(False)
            self.i_zweiter_termin_check_box.setChecked(True)
            

    def __set_wochentage(self, wochentage: list):
        """
        Setzt die in den Kotaktdaten gespeicherten Wochentage in der GUI

        Args:
            wochentage: list mit allen Wochentagen
        """

        alle_wochentage = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]

        deaktivere_tage = [tag for tag in alle_wochentage if tag not in wochentage]

        for tag in deaktivere_tage:
            if tag == "Mo":
                self.i_mo_check_box.setChecked(False)
            elif tag == "Di":
                self.i_di_check_box.setChecked(False)
            elif tag == "Mi":
                self.i_mi_check_box.setChecked(False)
            elif tag == "Do":
                self.i_do_check_box.setChecked(False)
            elif tag == "Fr":
                self.i_fr_check_box.setChecked(False)
            elif tag == "Sa":
                self.i_sa_check_box.setChecked(False)
            elif tag == "So":
                self.i_so_check_box.setChecked(False)

    def __set_start_datum(self, von_datum: str):
        """
        Setzt das Startdatum in der GUI.
        
        Args:
            von_datum: Startdatum der Suche

        Raise:
            AssertionError: Datum fehlerhaft
        """

        datum = QDate.fromString(von_datum, 'd.M.yyyy')
        assert(QDate.isValid(datum))
        self.i_start_datum_qdate.setDate(datum)


        
    def __set_uhrzeit_datum(self, uhrzeit: str, widget: QtWidgets.QTimeEdit):
        """
        Setzt die Uhrzeit in einem QTimeEdit in der GUI.
        
        Args:
            uhrzeit: Uhrzeit des Termins im Format h:m
            widget: QTimeEdit, welches gesezt wird

        Raise:
            AssertionError: Zeitangabe fehlerhaft
        """

        time = QTime.fromString(uhrzeit, 'h:m')
        assert(QTime.isValid(time))
        widget.setTime(time)


    def __oeffne_error(self, title: str, text: str, info: str):
        """
            Öffnet eine Warnung

            Args:
                title: Titel des Fensters
                text: Überschrift der Warnung
                info: Infotext der Warnung
        """
        try:
            msg = QtWidgets.QMessageBox(self)
            msg.setIcon(QtWidgets.QMessageBox.Warning)
            msg.setWindowTitle(title)
            msg.setText(text)
            msg.setInformativeText(info)
            msg.addButton(msg.Close)
            msg.exec_()
        except Exception as error:
            pass