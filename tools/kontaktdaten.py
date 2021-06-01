import json
import os
import re

from email.utils import parseaddr
from tools.exceptions import ValidationError, MissingValuesError
from tools import Modus


def get_kontaktdaten(filepath: str):
    """
    Lade Kontaktdaten aus Datei.

    :param filepath: Pfad zur JSON-Datei mit Kontaktdaten.
    :return: Dictionary mit Kontaktdaten

    :raise: ValidationError: Wird geworfen wenn eine Datei ungültige Values besitzt
    """

    try:
        with open(filepath, encoding='utf-8') as f:
            try:
                kontaktdaten = json.load(f)
                validate_kontaktdaten(kontaktdaten)
                return kontaktdaten
            except json.JSONDecodeError:
                return {}
    except FileNotFoundError:
        return {}


def check_kontaktdaten(kontaktdaten: dict, mode: Modus):
    """
    Überprüft ob alle Keys vorhanden sind

    Args:
        mode (Modus): Entsprechend werden Daten überprüft
        kontaktdaten (dict): Inhalt der JSON

    Raises:
        MissingValuesError: Es wird ein Key vermisst
    """

    try:
        if mode == Modus.TERMIN_SUCHEN:
            # Wird nur bei Terminsuche benötigt
            kontaktdaten["code"]
            kontaktdaten["kontakt"]["anrede"]
            kontaktdaten["kontakt"]["vorname"]
            kontaktdaten["kontakt"]["nachname"]
            kontaktdaten["kontakt"]["strasse"]
            kontaktdaten["kontakt"]["hausnummer"]
            kontaktdaten["kontakt"]["plz"]
            kontaktdaten["kontakt"]["ort"]

        # Rest wird immer benötigt
        kontaktdaten["plz_impfzentren"]
        kontaktdaten["kontakt"]["phone"]
        kontaktdaten["kontakt"]["notificationChannel"]
        kontaktdaten["kontakt"]["notificationReceiver"]

    except KeyError as exc:
        raise MissingValuesError("Schlüsselwort fehlt!") from exc


def validate_kontaktdaten(kontaktdaten: dict):
    """
    Erhebt ValidationError, falls Kontaktdaten ungültig sind.
    Leere Werte werden als Fehler angesehen

    :param kontaktdaten: Dictionary mit Kontaktdaten
    """

    if not isinstance(kontaktdaten, dict):
        raise ValidationError("Muss ein Dictionary sein")

    for key, value in kontaktdaten.items():
        try:
            if key == "code":
                validate_code(value)
            elif key == "plz_impfzentren":
                validate_plz_impfzentren(value)
            elif key == "kontakt":
                validate_kontakt(value)
            else:
                raise ValidationError(f"Nicht unterstützter Key")
        except ValidationError as exc:
            raise ValidationError(
                f"Ungültiger Key {json.dumps(key)}:\n{str(exc)}")


def validate_code(code: str):
    """
    Überprüft, ob der Code Valide ist

    Args:
        code (str): impf-code

    Raises:
        ValidationError: Code ist keine Zeichenkette oder entspricht nicht dem Schema
    """

    if not isinstance(code, str):
        raise ValidationError("Muss eine Zeichenkette sein")

    c = "[0-9a-zA-Z]"
    if not re.match(f"^{4 * c}-{4 * c}-{4 * c}$", code):
        raise ValidationError(
            f"{json.dumps(code)} entspricht nicht dem Schema \"XXXX-XXXX-XXXX\"")


def validate_plz_impfzentren(plz_impfzentren: list):
    """
    Validiert eine Gruppe von PLZs mithilfe con validate_plz

    Args:
        plz_impfzentren (dict): PLZs

    Raises:
        ValidationError: PLZs ist keine Liste
    """

    if not isinstance(plz_impfzentren, list):
        raise ValidationError("Muss eine Liste sein")

    for plz in plz_impfzentren:
        validate_plz(plz)


def validate_plz(plz: str):
    """
    Validiert die PLZ auf: Typ, Länge, "leer"

    Args:
        plz (str): PLZ

    Raises:
        ValidationError: PLZ ist kein String
        ValidationError: Besteht nicht aus genau 5 Ziffern
    """

    if not isinstance(plz, str):
        raise ValidationError("Muss eine Zeichenkette sein")

    if not re.match(f"^{5 * '[0-9]'}$", plz):
        raise ValidationError(
            f"Ungültige PLZ {json.dumps(plz)} - muss aus genau 5 Ziffern bestehen")


def validate_kontakt(kontakt: dict):
    """
    Validiert die Kontaktdaten auf Plausibilität.
    Leere Werte werden als Fehler angesehen.
    Wenn ein Key zu viel ist, wird dies nicht als Fehler erachtet

    Args:
        kontakt (dict): Kontakt Daten aus der JSON

    Raises:
        ValidationError: Kontakt ist kein dict
        ValidationError: Einer der Values ist ungültig
    """

    if not isinstance(kontakt, dict):
        raise ValidationError("Muss ein Dictionary sein")

    for key, value in kontakt.items():
        try:
            if key in ["anrede", "vorname", "nachname", "strasse", "ort"]:
                if not isinstance(value, str):
                    raise ValidationError("Muss eine Zeichenkette sein")
                if value.strip() == "":
                    raise ValidationError(f"Darf nicht leer sein")
            elif key == "plz":
                validate_plz(value)
            elif key == "hausnummer":
                validate_hausnummer(value)
            elif key == "phone":
                validate_phone(value)
            elif key == "notificationChannel":
                if value != "email":
                    raise ValidationError("Muss auf \"email\" gesetzt werden")
            elif key == "notificationReceiver":
                validate_email(value)
            else:
                raise ValidationError(f"Nicht unterstützter Key")
        except ValidationError as exc:
            raise ValidationError(
                f"Ungültiger Key {json.dumps(key)}:\n{str(exc)}")


def validate_phone(phone: str):
    """
    Validiert Telefonnummer auf: Typ, Präfix, "leer"

    Args:
        phone (str): Telefonnummer

    Raises:
        ValidationError: Typ ist nicht str
        ValidationError: Telefonnummer ungültig
    """

    if not isinstance(phone, str):
        raise ValidationError("Muss eine Zeichenkette sein")

    if not re.match(r"^\+49[1-9][0-9]+$", phone):
        raise ValidationError(
            f"Ungültige Telefonnummer {json.dumps(phone)}")


def validate_hausnummer(hausnummer: str):
    """
    Validiert Hausnummer auf: Typ, Länge, "leer"

    Args:
        hausnummer (str): hausnummer

    Raises:
        ValidationError: Typ ist nicht str
        ValidationError: Zeichenkette ist länger als 20 Zeichen
        ValidationError: Zeichenkette ist leer
    """

    if not isinstance(hausnummer, str):
        raise ValidationError("Muss eine Zeichenkette sein")

    if len(hausnummer) > 20:
        raise ValidationError(
            f"Hausnummer {json.dumps(hausnummer)} ist zu lang - maximal 20 Zeichen erlaubt")

    if hausnummer.strip() == "":
        raise ValidationError("Hausnummer ist leer")


def validate_email(email: str):
    """
    Validiert eMail auf: Typ, gültigkeit, "leer"

    Args:
        email (str): email

    Raises:
        ValidationError: Typ ist nicht str
        ValidationError: Zeichenkette enhält kein @
        ValidationError: Zeichenkette ist leer
    """

    if not isinstance(email, str):
        raise ValidationError("Muss eine Zeichenkette sein")

    if '@' not in parseaddr(email)[1]:
        raise ValidationError(f"Ungültige E-Mail-Adresse {json.dumps(email)}")

    if email.strip() == "":
        raise ValidationError("E-Mail-Adresse ist leer")
