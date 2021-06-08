import calendar
import datetime
import json
import os
import re

from email.utils import parseaddr
from tools.exceptions import ValidationError, MissingValuesError
from tools import Modus

WOCHENTAG_ABBRS = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
WOCHENTAG_NAMES = [
    "Montag",
    "Dienstag",
    "Mittwoch",
    "Donnerstag",
    "Freitag",
    "Samstag",
    "Sonntag"]


def get_kontaktdaten(filepath: str):
    """
    Lade Kontaktdaten aus Datei.

    :param filepath: Pfad zur JSON-Datei mit Kontaktdaten.
    :return: Dictionary mit Kontaktdaten

    :raise ValidationError: Falls Validierung der gelesenen Kontaktdaten fehlschlägt
    """

    try:
        with open(filepath, encoding='utf-8') as f:
            try:
                kontaktdaten = json.load(f)

                # Backwards Compatibility: "code"
                if "code" in kontaktdaten:
                    code = kontaktdaten.pop("code")
                    if "codes" not in kontaktdaten:
                        kontaktdaten["codes"] = []
                    kontaktdaten["codes"].append(code)

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
            kontaktdaten["codes"]
            kontaktdaten["kontakt"]["anrede"]
            kontaktdaten["kontakt"]["vorname"]
            kontaktdaten["kontakt"]["nachname"]
            kontaktdaten["kontakt"]["strasse"]
            kontaktdaten["kontakt"]["hausnummer"]
            kontaktdaten["kontakt"]["plz"]
            kontaktdaten["kontakt"]["ort"]

            kontaktdaten["zeitrahmen"]
            # Subkeys von "zeitrahmen" brauchen nicht gecheckt werden, da
            # `kontaktdaten["zeitrahmen"] == {}` zulässig ist.

        # Rest wird immer benötigt
        kontaktdaten["plz_impfzentren"]
        kontaktdaten["kontakt"]["phone"]
        kontaktdaten["kontakt"]["notificationChannel"]
        kontaktdaten["kontakt"]["notificationReceiver"]

    except KeyError as exc:
        raise MissingValuesError("Schlüsselwort fehlt!") from exc


def validate_kontaktdaten(kontaktdaten: dict):
    """
    Validiert Kontaktdaten.
    Leere Werte werden als Fehler angesehen.

    :raise ValidationError: Typ ist nicht dict
    :raise ValidationError: Einer der enthaltenen Keys ist unbekannt
    :raise ValidationError: Eine der enthaltenen Values ist ungültig
    """

    if not isinstance(kontaktdaten, dict):
        raise ValidationError("Muss ein Dictionary sein")

    for key, value in kontaktdaten.items():
        try:
            if key == "codes":
                validate_codes(value)
            elif key == "plz_impfzentren":
                validate_plz_impfzentren(value)
            elif key == "kontakt":
                validate_kontakt(value)
            elif key == "zeitrahmen":
                validate_zeitrahmen(value)
            else:
                raise ValidationError(f"Nicht unterstützter Key")
        except ValidationError as exc:
            raise ValidationError(
                f"Ungültiger Key {json.dumps(key)}:\n{str(exc)}")


def validate_codes(codes: list):
    """
    Validiert eine Liste an Impf-Codes vom Schema XXXX-XXXX-XXXX

    :raise ValidationError: Typ ist nicht list
    :raise ValidationError: Liste enthält vom Schema abweichendes Element
    """

    if not isinstance(codes, list):
        raise ValidationError("Muss eine Liste sein")

    for code in codes:
        if not isinstance(code, str):
            raise ValidationError("Darf nur Zeichenketten enthalten")
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
    Validiert "kontakt"-Key aus Kontaktdaten.
    Leere Werte werden als Fehler angesehen.

    :raise ValidationError: Typ ist nicht dict
    :raise ValidationError: Einer der enthaltenen Keys ist unbekannt
    :raise ValidationError: Eine der enthaltenen Values ist ungültig
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
    Validiert eine E-Mail-Adresse.

    :raise ValidationError: Typ ist nicht str
    :raise ValidationError: Zeichenkette ist offensichtlich keine gültige E-Mail-Adresse
    """

    if not isinstance(email, str):
        raise ValidationError("Muss eine Zeichenkette sein")

    # https://stackoverflow.com/a/14485817/7350842
    parsed_email = parseaddr(email)[1]
    if '@' not in parsed_email:
        raise ValidationError(f"Ungültige E-Mail-Adresse {json.dumps(email)}")

    # Gmail erlaubt Plus-Zeichen (https://support.google.com/a/users/answer/9308648?hl=en),
    # der Impfterminservice leider nicht.
    if '+' in parsed_email:
        raise ValidationError(f"Ungültige E-Mail-Adresse {json.dumps(email)} (Plus-Zeichen nicht möglich)")


def validate_zeitrahmen(zeitrahmen: dict):
    """
    Validiert "zeitrahmen"-Key aus Kontaktdaten.

    :raise ValidationError: Typ ist nicht dict
    :raise ValidationError: Einer der enthaltenen Keys ist unbekannt
    :raise ValidationError: Eine der enthaltenen Values ist ungültig
    """

    if not isinstance(zeitrahmen, dict):
        raise ValidationError("Muss ein Dictionary sein")

    if zeitrahmen == {}:
        return

    # Ein ganz leerer Zeitrahmen ist zulässig (s.o.), aber ansonsten muss der
    # Key "einhalten_bei" vorhanden sein.
    if "einhalten_bei" not in zeitrahmen:
        raise ValidationError(
            'Ein gesetzter Zeitrahmen braucht zwingend den Key "einhalten_bei"')

    for key, value in zeitrahmen.items():
        try:
            if key in ["von_datum", "bis_datum"]:
                validate_datum(value)
            elif key in ["von_uhrzeit", "bis_uhrzeit"]:
                validate_uhrzeit(value)
            elif key == "wochentage":
                if not isinstance(value, list):
                    raise ValidationError("Muss eine Liste sein")
                if not value:
                    raise ValidationError("Darf keine leere Liste sein")
                for weekday in value:
                    validate_wochentag(weekday)
            elif key == "einhalten_bei":
                validate_einhalten_bei(value)
            else:
                raise ValidationError(f"Nicht unterstützter Key")
        except ValidationError as exc:
            raise ValidationError(
                f"Ungültiger Key {json.dumps(key)}:\n{str(exc)}")

    if "von_datum" in zeitrahmen and "bis_datum" in zeitrahmen:
        von_datum = datetime.datetime.strptime(
            zeitrahmen["von_datum"], "%d.%m.%Y")
        bis_datum = datetime.datetime.strptime(
            zeitrahmen["bis_datum"], "%d.%m.%Y")
        if von_datum > bis_datum:
            raise ValidationError(
                "Ungültige Kombination von Datums: "
                'von_datum" liegt nach "bis_datum"')

    if "von_uhrzeit" in zeitrahmen and "bis_uhrzeit" in zeitrahmen:
        von_uhrzeit = datetime.datetime.strptime(
            zeitrahmen["von_uhrzeit"], "%H:%M")
        bis_uhrzeit = datetime.datetime.strptime(
            zeitrahmen["bis_uhrzeit"], "%H:%M")
        if von_uhrzeit > bis_uhrzeit:
            raise ValidationError(
                "Ungültige Kombination von Uhrzeiten: "
                '"von_uhrzeit" liegt nach "bis_uhrzeit"')


def validate_datum(date: str):
    """
    Validiert ein Datum im erwarteten Format "30.11.1970".

    :raise ValidationError: Typ ist nicht str
    :raise ValidationError: Zeichenkette hat nicht das richtige Format
    """

    if not isinstance(date, str):
        raise ValidationError("Muss eine Zeichenkette sein")

    try:
        datetime.datetime.strptime(date, "%d.%m.%Y")
    except ValueError as exc:
        raise ValidationError(str(exc)) from exc


def validate_uhrzeit(time: str):
    """
    Validiert eine Uhrzeit im erwarteten Format "14:35".

    :raise ValidationError: Typ ist nicht str
    :raise ValidationError: Zeichenkette hat nicht das richtige Format
    """

    if not isinstance(time, str):
        raise ValidationError("Muss eine Zeichenkette sein")

    try:
        datetime.datetime.strptime(time, "%H:%M")
    except ValueError as exc:
        raise ValidationError(str(exc)) from exc


def validate_wochentag(wochentag: str):
    """
    Validiert einen Wochentag.
    Erlaubt sind "Montag" bis "Sonntag".
    Es sind auch Präfixe vom Wochentag-Namen zulässig, solange diese mindestens
    zwei Zeichen lang sind, z. B. "Mo", "Mon", "Mont", usw.

    :raise ValidationError: Typ ist nicht str
    :raise ValidationError: Zeichenkette hat nicht das richtige Format
    """

    if not isinstance(wochentag, str):
        raise ValidationError("Muss eine Zeichenkette sein")

    try:
        decode_wochentag(wochentag)
    except ValueError as exc:
        raise ValidationError(str(exc)) from exc


def validate_einhalten_bei(einhalten_bei: str):
    """
    Validiert "zeitrahmen"."einhalten_bei"-Key aus Kontaktdaten.
    Erlaubte Parameter sind: "1", "2", "beide"

    :raise ValidationError: Parameter ist nicht erlaubt (s.o.)
    """

    if not isinstance(einhalten_bei, str):
        raise ValidationError("Muss eine Zeichenkette sein")

    if einhalten_bei not in ["1", "2", "beide"]:
        raise ValidationError('Erlaubt sind: "1", "2", "beide"')


def decode_wochentag(wochentag: str):
    """
    Wandelt einen Wochentag-Namen in seinen Index um, d. h. "Montag" -> 0,
    "Dienstag" -> 1, usw.
    Es sind auch Präfixe vom Wochentag-Namen zulässig, solange diese mindestens
    zwei Zeichen lang sind, z. B. "Mo", "Mon", "Mont", usw.
    """

    num = None
    if len(wochentag) >= 2:
        num = next((i for i, wt in enumerate(WOCHENTAG_NAMES)
                    if wt.lower().startswith(wochentag.lower())), None)
    if num is None:
        raise ValueError(
            f"Ungültiger Wochentag: {json.dumps(wochentag)}"
            ' - erlaubt sind: "Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"')
    return num


def encode_wochentag(num: int):
    """
    Wandelt einen Wochentag-Index in den zugehörigen Namen um.
    Es werden nur die ersten zwei Zeichen vom Namen zurückgegeben, d. h.
    0 -> "Mo", 1 -> "Di", usw.
    Dies ist kompatibel mit decode_wochentag, wo zwei Zeichen genügen.
    """

    return WOCHENTAG_ABBRS[num]
