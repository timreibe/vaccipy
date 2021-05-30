import os
import json
from enum import Enum, auto
from PyQt5 import QtWidgets, uic
from PyQt5.QtWidgets import QMessageBox

from tools.exceptions import FehlendeDatenException


class Modus(Enum):
    CODE_GENERIEREN = auto()
    TERMIN_SUCHEN = auto()


def check_alle_kontakt_daten_da(modus: Modus, data: dict):
    """
    Nur für Kontaktdaten!
    Überprüft ob alle Key vorhanden sind und ob die Values kein leeren String enthalten

    Args:
        modus (Modus): Entsprechend werden Daten überprüft
        data (dict): Inhalt der JSON

    Raises:
        FehlendeDatenException: Es wird ein Key oder Value vermisst
    """

    if modus == Modus.TERMIN_SUCHEN:
        try:
            # Daten vorhanden
            data["plz_impfzentren"]
            data["code"]
            data["kontakt"]["anrede"]
            data["kontakt"]["vorname"]
            data["kontakt"]["nachname"]
            data["kontakt"]["strasse"]
            data["kontakt"]["hausnummer"]
            data["kontakt"]["plz"]
            data["kontakt"]["ort"]
            data["kontakt"]["phone"]
            data["kontakt"]["notificationChannel"]
            data["kontakt"]["notificationReceiver"]

            # Daten enthalten kein leerer String
            # PLZ
            for plz in data["plz_impfzentren"]:
                if not plz.strip():
                    raise FehlendeDatenException("Wert fuer \"plz_impfzentren\" fehlerhaft!")
            if not data["code"].strip():
                raise FehlendeDatenException("Wert fuer \"code\" fehlt!")
            # 2. Ebene
            for key, value in data["kontakt"].items():
                if not value.strip():
                    raise FehlendeDatenException(f"Wert fuer \"{key}\" fehlt!")
        except KeyError as error:
            raise FehlendeDatenException("Schluesselwort Fehlt!") from error

    elif modus == Modus.CODE_GENERIEREN:
        try:
            # Daten vorhanden
            data["plz_impfzentren"]
            data["kontakt"]["phone"]
            data["kontakt"]["notificationChannel"]
            data["kontakt"]["notificationReceiver"]

            # Daten enthalten kein leerer String
            for key, values in data.items():
                if values.strip() == "":
                    raise FehlendeDatenException(f"Wert fuer \"{key}\" fehlt!")
        except KeyError as error:
            raise FehlendeDatenException("Schluesselwort Fehlt!") from error


def oeffne_file_dialog_save(parent_widged: QtWidgets.QWidget, titel: str, standard_speicherpfad: str, dateityp="JSON Files (*.json)") -> str:
    """
    Öffnet ein File Dialog, der entsprechend einen Pfad zurück gibt, wohin gespeichert werden soll

    Args:
        parent_widged (PyQt5.QtWidgets.QWidget): 
        titel (str): Titel des Dialogs
        standard_speicherpfad (str): Pfad welcher direkt geöffnet wird als Vorschlag
        dateityp (str, optional): selectedFilter example: "Images (*.png *.xpm *.jpg)". Defaults to "JSON Files (*.json)".

    Raises:
        FileNotFoundError: Wird geworfen, wenn der Dateipfad leer ist

    Returns:
        str: Vollständiger Pfad
    """

    options = QtWidgets.QFileDialog.Options()
    options |= QtWidgets.QFileDialog.DontUseNativeDialog
    datei_data = QtWidgets.QFileDialog.getSaveFileName(parent=parent_widged, caption=titel, directory=standard_speicherpfad, filter=dateityp, options=options)
    dateipfad = datei_data[0]  # (Pfad, Dateityp)

    dateipfad = dateipfad.replace("/", os.path.sep)

    if not dateipfad:
        raise FileNotFoundError

    return dateipfad


def oeffne_file_dialog_select(parent_widged: QtWidgets.QWidget, titel: str, standard_oeffnungspfad: str, dateityp="JSON Files (*.json)") -> str:
    """
    Öffnet einen File Dialog um eine existierende Datei auszuwählen

    Args:
        parent_widged (QtWidgets.QWidget): Parent QWidget an das der Dialog gehängt werden soll
        titel (str): Titel des Dialogs
        standard_oeffnungspfad (str): Pfad welcher direkt geöffnet wird als Vorschlag
        dateityp (str, optional): selectedFilter example: "Images (*.png *.xpm *.jpg)". Defaults to "JSON Files (*.json)".

    Raises:
        FileNotFoundError: Wird geworfen, wenn der Dateipfad leer ist

    Returns:
        str: Vollständiger Pfad zur Datei
    """

    # Öffnet den "File-Picker" vom System um ein bereits existierende Datei auszuwählen
    options = QtWidgets.QFileDialog.Options()
    options |= QtWidgets.QFileDialog.DontUseNativeDialog
    datei_data = QtWidgets.QFileDialog.getOpenFileName(parent=parent_widged, caption=titel, directory=standard_oeffnungspfad, filter=dateityp, options=options)
    dateipfad = datei_data[0]  # (pfad, typ)

    dateipfad = dateipfad.replace("/", os.path.sep)

    if not dateipfad:
        raise FileNotFoundError

    return dateipfad


def speichern(speicherpfad: str, data: dict):
    """
    Speichert die Daten mittels json.dump an den entsprechenden Ort

    Args:
        speicherpfad (str): speicherort
        data (dict): Speicherdaten
    """

    with open(speicherpfad, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
