import os
import json
import platform

from PyQt5 import QtWidgets, uic
from PyQt5.QtWidgets import QMessageBox
from PyQt5.Qt import QUrl, QDesktopServices


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

    os_name: str = platform.system()
    options = QtWidgets.QFileDialog.Options()

    if os_name.lower() != "windows":
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
    os_name: str = platform.system()
    options = QtWidgets.QFileDialog.Options()
    if os_name.lower() != "windows":
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


def open_browser(url: str):
    """
    Öffnet den Standard Browser

    Args:
        url (str): URL welche geöffnet werden soll
    """

    qurl = QUrl(url)
    QDesktopServices.openUrl(qurl)
