import json
import os
import re

from email.utils import parseaddr
from tools.exceptions import ValidationError, MissingValuesError
from tools import Modus


def get_kontaktdaten(filepath: str, mode: Modus = Modus.TERMIN_SUCHEN):
    """
    Lade Kontaktdaten aus Datei.

    :param filepath: Pfad zur JSON-Datei mit Kontaktdaten.
    :param modus: Unterschiedliche Kriterien ob key / values vorhanden sein müssen
    :return: Dictionary mit Kontaktdaten

    :raise: ValidationError: Wird geworfen wenn eine Datei ungültige Values besitzt
    :raise: MissingValuesError: Wird geworfen, wenn benötigte Key / Values nicht da sind
    """

    try:
        with open(filepath, encoding='utf-8') as f:
            try:
                kontaktdaten = json.load(f)
                check_kontaktdaten(kontaktdaten, mode)
                validate_kontaktdaten(kontaktdaten)
                return kontaktdaten
            except json.JSONDecodeError:
                return {}
    except FileNotFoundError:
        return {}


def check_kontaktdaten(kontaktdaten: dict, mode: Modus):
    """
    Überprüft ob alle Keys vorhanden sind und ob die Values kein leeren String enthalten

    Args:
        mode (Modus): Entsprechend werden Daten überprüft
        kontaktdaten (dict): Inhalt der JSON

    Raises:
        MissingValuesError: Es wird ein Key oder Value vermisst
    """

    if mode == Modus.TERMIN_SUCHEN:
        try:
            # Daten vorhanden
            kontaktdaten["plz_impfzentren"]
            kontaktdaten["code"]
            kontaktdaten["kontakt"]["anrede"]
            kontaktdaten["kontakt"]["vorname"]
            kontaktdaten["kontakt"]["nachname"]
            kontaktdaten["kontakt"]["strasse"]
            kontaktdaten["kontakt"]["hausnummer"]
            kontaktdaten["kontakt"]["plz"]
            kontaktdaten["kontakt"]["ort"]
            kontaktdaten["kontakt"]["phone"]
            kontaktdaten["kontakt"]["notificationChannel"]
            kontaktdaten["kontakt"]["notificationReceiver"]

            # Daten enthalten kein leerer String
            # PLZ
            for plz in kontaktdaten["plz_impfzentren"]:
                if not plz.strip():
                    raise MissingValuesError("Wert fuer \"plz_impfzentren\" fehlerhaft!")
            if not kontaktdaten["code"].strip():
                raise MissingValuesError("Wert fuer \"code\" fehlt!")

            # 2. Ebene von Kontakt
            for key, value in kontaktdaten["kontakt"].items():
                if not value.strip():
                    raise MissingValuesError(f"Wert fuer \"{key}\" fehlt!")
        except KeyError as error:
            raise MissingValuesError("Schluesselwort Fehlt!") from error

    elif mode == Modus.CODE_GENERIEREN:
        try:
            # Daten vorhanden
            kontaktdaten["plz_impfzentren"]
            kontaktdaten["kontakt"]["phone"]
            kontaktdaten["kontakt"]["notificationChannel"]
            kontaktdaten["kontakt"]["notificationReceiver"]

            # PLZ
            for plz in kontaktdaten["plz_impfzentren"]:
                if not plz.strip():
                    raise MissingValuesError("Plz der Impfzentren fehlerhaft!")

            # Daten enthalten kein leerer String
            if kontaktdaten["kontakt"]["phone"].strip() == "":
                raise MissingValuesError(f"Telefonnummer fehlt!")

            if kontaktdaten["kontakt"]["notificationChannel"].strip() == "":
                raise MissingValuesError(f"Wert fuer notificationChannel fehlt!")

            if kontaktdaten["kontakt"]["notificationReceiver"].strip() == "":
                raise MissingValuesError(f"Mail fehlt!")

        except KeyError as error:
            raise MissingValuesError("Schluesselwort Fehlt!") from error


def validate_kontaktdaten(kontaktdaten):
    """
    Erhebt ValidationError, falls Kontaktdaten ungültig sind.
    Unvollständige Kontaktdaten sind ok und führen hier nicht zum Fehler.

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


def validate_code(code):
    if not isinstance(code, str):
        raise ValidationError("Muss eine Zeichenkette sein")

    c = "[0-9a-zA-Z]"
    if not re.match(f"^{4 * c}-{4 * c}-{4 * c}$", code):
        raise ValidationError(
            f"{json.dumps(code)} entspricht nicht dem Schema \"XXXX-XXXX-XXXX\"")


def validate_plz_impfzentren(plz_impfzentren):
    if not isinstance(plz_impfzentren, list):
        raise ValidationError("Muss eine Liste sein")

    for plz in plz_impfzentren:
        validate_plz(plz)


def validate_plz(plz):
    if not isinstance(plz, str):
        raise ValidationError("Muss eine Zeichenkette sein")

    if not re.match(f"^{5 * '[0-9]'}$", plz):
        raise ValidationError(
            f"Ungültige PLZ {json.dumps(plz)} - muss aus genau 5 Ziffern bestehen")


def validate_kontakt(kontakt):
    if not isinstance(kontakt, dict):
        raise ValidationError("Muss ein Dictionary sein")

    for key, value in kontakt.items():
        try:
            if key in ["anrede", "vorname", "nachname", "strasse", "ort"]:
                if not isinstance(value, str):
                    raise ValidationError("Muss eine Zeichenkette sein")
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


def validate_phone(phone):
    if not isinstance(phone, str):
        raise ValidationError("Muss eine Zeichenkette sein")

    if not re.match(r"^\+49[1-9][0-9]+$", phone):
        raise ValidationError(
            f"Ungültige Telefonnummer {json.dumps(phone)}")


def validate_hausnummer(hausnummer):
    if not isinstance(hausnummer, str):
        raise ValidationError("Muss eine Zeichenkette sein")

    if len(hausnummer) > 20:
        raise ValidationError(
            f"Hausnummer {json.dumps(hausnummer)} ist zu lang - maximal 20 Zeichen erlaubt")


def validate_email(email):
    if not isinstance(email, str):
        raise ValidationError("Muss eine Zeichenkette sein")

    if '@' not in parseaddr(email)[1]:
        raise ValidationError(f"Ungültige E-Mail-Adresse {json.dumps(email)}")
