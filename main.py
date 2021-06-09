#!/usr/bin/env python3

import argparse
import copy
import json
import os
import random
import string
import sys

import i18n

from tools.its import ImpfterminService
from tools.kontaktdaten import decode_wochentag, encode_wochentag, get_kontaktdaten, validate_kontaktdaten, validate_datum
from tools.utils import create_missing_dirs, get_latest_version, remove_prefix, update_available, get_current_version
from tools.exceptions import ValidationError
from pathlib import Path

PATH = os.path.dirname(os.path.realpath(__file__))


def update_kontaktdaten_interactive(
        known_kontaktdaten,
        command,
        filepath=None):
    """
    Interaktive Eingabe und anschließendes Abspeichern der Kontaktdaten.

    :param known_kontaktdaten: Bereits bekannte Kontaktdaten, die nicht mehr
        abgefragt werden sollen.
    :param command: Entweder "code" oder "search". Bestimmt, welche
        Kontaktdaten überhaupt benötigt werden.
    :param filepath: Pfad zur JSON-Datei zum Abspeichern der Kontaktdaten.
        Default: data/kontaktdaten.json im aktuellen Ordner
    :return: Dictionary mit Kontaktdaten
    """

    assert (command in ["code", "search"])

    # Werfe Fehler, falls die übergebenen Kontaktdaten bereits ungültig sind.
    validate_kontaktdaten(known_kontaktdaten)

    kontaktdaten = copy.deepcopy(known_kontaktdaten)

    with open(filepath, 'w', encoding='utf-8') as file:
        if "plz_impfzentren" not in kontaktdaten:
            print(i18n.t("i18n.InputPLZs"))
            input_kontaktdaten_key(kontaktdaten,
                                   ["plz_impfzentren"],
                                   f"> {i18n.t('i18n.PLZVacCenters')}: ",
                                   lambda x: list(set([plz.strip() for plz in x.split(",")])))

        if "code" not in kontaktdaten and command == "search":
            input_kontaktdaten_key(kontaktdaten, ["code"], "> Code: ")

        if "kontakt" not in kontaktdaten:
            kontaktdaten["kontakt"] = {}

        if "anrede" not in kontaktdaten["kontakt"] and command == "search":
            input_kontaktdaten_key(
                kontaktdaten, ["kontakt", "anrede"], f"> {i18n.t('i18n.Gender')}: ")

        if "vorname" not in kontaktdaten["kontakt"] and command == "search":
            input_kontaktdaten_key(
                kontaktdaten, ["kontakt", "vorname"], f"> {i18n.t('i18n.Firstname')}: ")

        if "nachname" not in kontaktdaten["kontakt"] and command == "search":
            input_kontaktdaten_key(
                kontaktdaten, ["kontakt", "nachname"], f"> {i18n.t('i18n.Lastname')}: ")

        if "strasse" not in kontaktdaten["kontakt"] and command == "search":
            input_kontaktdaten_key(
                kontaktdaten, ["kontakt", "strasse"], f"> {i18n.t('i18n.Street')}: ")

        if "hausnummer" not in kontaktdaten["kontakt"] and command == "search":
            input_kontaktdaten_key(
                kontaktdaten, ["kontakt", "hausnummer"], f"> {i18n.t('i18n.HouseNumber')}: ")

        if "plz" not in kontaktdaten["kontakt"] and command == "search":
            input_kontaktdaten_key(
                kontaktdaten, ["kontakt", "plz"], f"> {i18n.t('i18n.PLZ')}: ")

        if "ort" not in kontaktdaten["kontakt"] and command == "search":
            input_kontaktdaten_key(
                kontaktdaten, ["kontakt", "ort"], f"> {i18n.t('i18n.City')}: ")

        if "phone" not in kontaktdaten["kontakt"]:
            input_kontaktdaten_key(
                kontaktdaten,
                ["kontakt", "phone"],
                f"> {i18n.t('i18n.Phonenumber')}: +49",
                lambda x: x if x.startswith("+49") else f"+49{remove_prefix(x, '0')}")

        if "notificationChannel" not in kontaktdaten["kontakt"]:
            kontaktdaten["kontakt"]["notificationChannel"] = "email"

        if "notificationReceiver" not in kontaktdaten["kontakt"]:
            input_kontaktdaten_key(
                kontaktdaten, ["kontakt", "notificationReceiver"], "> Mail: ")

        if "zeitrahmen" not in kontaktdaten and command == "search":
            kontaktdaten["zeitrahmen"] = {}
            if input(f"> {i18n.t('i18n.ConstrainTimeSlot')}: ").lower() != "n":
                print()
                input_kontaktdaten_key(
                    kontaktdaten, ["zeitrahmen", "einhalten_bei"],
                    f"> {i18n.t('i18n.ForWhichAppointment')}: ")
                input_kontaktdaten_key(
                    kontaktdaten, ["zeitrahmen", "von_datum"],
                    f"> {i18n.t('i18n.FromDate')}: ",
                    lambda x: x if x else None)  # Leeren String zu None umwandeln
                input_kontaktdaten_key(
                    kontaktdaten, ["zeitrahmen", "bis_datum"],
                    f"> {i18n.t('i18n.ToDate')}: ",
                    lambda x: x if x else None)  # Leeren String zu None umwandeln
                input_kontaktdaten_key(
                    kontaktdaten, ["zeitrahmen", "von_uhrzeit"],
                    f"> {i18n.t('i18n.FromTime')}: ",
                    lambda x: x if x else None)  # Leeren String zu None umwandeln
                input_kontaktdaten_key(
                    kontaktdaten, ["zeitrahmen", "bis_uhrzeit"],
                    f"> {i18n.t('i18n.ToTime')}: ",
                    lambda x: x if x else None)  # Leeren String zu None umwandeln
                print(i18n.t("i18n.InputWeekday"))
                input_kontaktdaten_key(
                    kontaktdaten, ["zeitrahmen", "wochentage"],
                    f"> {i18n.t('i18n.AllowedWeekdays')}: ", parse_wochentage)

        json.dump(kontaktdaten, file, ensure_ascii=False, indent=4)

    return kontaktdaten


def parse_wochentage(string):
    wochentage = [wt.strip() for wt in string.split(",")]
    # Leere strings durch "if wt" rausfiltern
    nums = [decode_wochentag(wt) for wt in wochentage if wt]
    if not nums:
        # None zurückgeben, damit der Key nicht gesetzt wird.
        # Folglich wird der Default genutzt: Alle Wochentage sind zulässig.
        return None
    nums = sorted(set(nums))
    return [encode_wochentag(num) for num in nums]


def input_kontaktdaten_key(
        kontaktdaten,
        path,
        prompt,
        transformer=lambda x: x):
    target = kontaktdaten
    for key in path[:-1]:
        target = target[key]
    key = path[-1]
    while True:
        try:
            value = transformer(input(prompt).strip())
            # Wenn transformer None zurückgibt, setzen wir den Key nicht.
            if value is not None:
                target[key] = value
                validate_kontaktdaten(kontaktdaten)
            break
        except ValidationError as exc:
            print(f"\n{str(exc)}\n")


def run_search_interactive(kontaktdaten_path, check_delay):
    """
    Interaktives Setup für die Terminsuche:
    1. Ggf. zuerst Eingabe, ob Kontaktdaten aus kontaktdaten.json geladen
       werden sollen.
    2. Laden der Kontaktdaten aus kontaktdaten.json.
    3. Bei unvollständigen Kontaktdaten: Interaktive Eingabe der fehlenden
       Kontaktdaten.
    4. Terminsuche

    :param kontaktdaten_path: Pfad zur JSON-Datei mit Kontaktdaten. Default: data/kontaktdaten.json im aktuellen Ordner
    """

    print(i18n.t("i18n.InputVacCodeAndContactdata", filename=os.path.basename(kontaktdaten_path)))

    kontaktdaten = {}
    if os.path.isfile(kontaktdaten_path):
        daten_laden = input(
            f"> {i18n.t('i18n.ShouldContactdataBeLoaded',filename=os.path.basename(kontaktdaten_path))}: ").lower()
        if daten_laden.lower() != "n":
            kontaktdaten = get_kontaktdaten(kontaktdaten_path)

    print()
    kontaktdaten = update_kontaktdaten_interactive(
        kontaktdaten, "search", kontaktdaten_path)
    return run_search(kontaktdaten, check_delay, kontaktdaten_path)


def run_search(kontaktdaten, check_delay):
    """
    Nicht-interaktive Terminsuche

    :param kontaktdaten: Dictionary mit Kontaktdaten
    """

    try:
        code = kontaktdaten["code"]

        # Hinweis, wenn noch alte Version der Kontaktdaten.json verwendet wird
        if kontaktdaten.get("plz"):
            print(i18n.t("i18n.InputAttentionOldVersionOfContactdata",filename="kontaktdaten.json")) # Kontaktdaten_path not available
            plz_impfzentren = [kontaktdaten.get("plz")]
        else:
            plz_impfzentren = kontaktdaten["plz_impfzentren"]

        kontakt = kontaktdaten["kontakt"]
        print(f"{i18n.t('i18n.ContactdataLoadedFor',firstname=kontakt['vorname'],lastname=kontakt['nachname'])}\n")

        zeitrahmen = kontaktdaten["zeitrahmen"]
    except KeyError as exc:
        raise ValueError(i18n.t('i18n.ContactdataCouldNotBeLoaded',filename='kontaktdaten.json')) from exc # Kontaktdaten_path not available

    ImpfterminService.terminsuche(code=code, plz_impfzentren=plz_impfzentren, kontakt=kontakt,
                                  zeitrahmen=zeitrahmen, check_delay=check_delay, PATH=PATH)


def gen_code_interactive(kontaktdaten_path):
    """
    Interaktives Setup für die Codegenerierung:
    1. Ggf. zuerst Eingabe, ob Kontaktdaten aus kontaktdaten.json geladen
       werden sollen.
    2. Laden der Kontaktdaten aus kontaktdaten.json.
    3. Bei unvollständigen Kontaktdaten: Interaktive Eingabe derjenigen
       fehlenden Kontaktdaten, die für die Codegenerierung benötigt werden.
    4. Codegenerierung

    :param kontaktdaten_path: Pfad zur JSON-Datei mit Kontaktdaten. Default: kontaktdaten.json im aktuellen Ordner
    """

    print(i18n.t('i18n.InfoVacCode',filename=os.path.basename(kontaktdaten_path)))

    kontaktdaten = {}
    if os.path.isfile(kontaktdaten_path):
        daten_laden = input(
            f"> {i18n.t('i18n.ShouldContactdataBeLoaded',filename=os.path.basename(kontaktdaten_path))}?: ").lower()
        if daten_laden.lower() != "n":
            kontaktdaten = get_kontaktdaten(kontaktdaten_path)

    print()
    kontaktdaten = update_kontaktdaten_interactive(
        kontaktdaten, "code", kontaktdaten_path)
    return gen_code(kontaktdaten)


def gen_code(kontaktdaten):
    """
    Codegenerierung ohne interaktive Eingabe der Kontaktdaten

    :param kontaktdaten: Dictionary mit Kontaktdaten
    """

    try:
        plz_impfzentrum = kontaktdaten["plz_impfzentren"][0]
        mail = kontaktdaten["kontakt"]["notificationReceiver"]
        telefonnummer = kontaktdaten["kontakt"]["phone"]
        if not telefonnummer.startswith("+49"):
            telefonnummer = f"+49{remove_prefix(telefonnummer, '0')}"
    except KeyError as exc:
        raise ValueError(
            i18n.t("i18n.ContactdataCouldNotBeLoaded",filename='kontaktdata.json')) from exc # Kontaktdaten_path not available here

    # Erstelle Zufallscode nach Format XXXX-YYYY-ZZZZ
    # für die Cookie-Generierung
    code_chars = string.ascii_uppercase + string.digits
    one = 'VACC'
    two = 'IPY' + random.choice(code_chars)
    three = ''.join(random.choices(code_chars, k=4))
    random_code = f"{one}-{two}-{three}"
    print(i18n.t('i18n.UsingRandomCodeForCookieGeneration') + f" ({random_code}).\n")

    its = ImpfterminService(random_code, [plz_impfzentrum], {}, PATH)

    print(f"{i18n.t('i18n.PleaseEnterBirthday')}.\n{i18n.t('i18n.Example')}: 02.03.1982\n")
    while True:
        try:
            geburtsdatum = input(f"> {i18n.t('i18n.Birthday')}: ")
            validate_datum(geburtsdatum)
            break
        except ValidationError as exc:
            print(i18n.t("i18n.InvalidBirthdayFormat"))

    print()
    # cookies erneuern und code anfordern
    its.renew_cookies_code()
    token = its.code_anfordern(mail, telefonnummer, plz_impfzentrum, geburtsdatum)

    if token is not None:
        # code bestätigen
        print(f"\n{i18n.t('i18n.ReceiveSMSCode')}")

        # 3 Versuche für die SMS-Code-Eingabe
        for _ in range(3):
            sms_pin = input("> SMS-Code: ").replace("-", "")
            if its.code_bestaetigen(token, sms_pin):
                print(f"\n{i18n.t('i18n.ContinueSearchForAppointment')}.\n")
                return True

    print(f"\n{i18n.t('i18n.CodeGenerationFailed')}.\n")
    return False


def subcommand_search(args):
    if args.configure_only:
        update_kontaktdaten_interactive(
            get_kontaktdaten(args.file), "search", args.file)
    elif args.read_only:
        run_search(get_kontaktdaten(args.file), check_delay=args.retry_sec)
    else:
        run_search_interactive(args.file, check_delay=args.retry_sec)


def subcommand_code(args):
    if args.configure_only:
        update_kontaktdaten_interactive(
            get_kontaktdaten(args.file), "code", args.file)
    elif args.read_only:
        gen_code(get_kontaktdaten(args.file))
    else:
        gen_code_interactive(args.file)


def validate_args(args):
    """
    Raises ValueError if args contain invalid settings.
    """

    if args.configure_only and args.read_only:
        raise ValueError(i18n.t("i18n.ConfigureOnlyReadOnlyNotBoth"))


def main():
    create_missing_dirs(PATH)

    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(help="commands", dest="command")

    base_subparser = argparse.ArgumentParser(add_help=False)
    base_subparser.add_argument(
        "-f",
        "--file",
        help=i18n.t("i18n.PathContactData"))
    base_subparser.add_argument(
        "-c",
        "--configure-only",
        action='store_true',
        help=i18n.t("i18n.ConfigureOnlyDescription"))
    base_subparser.add_argument(
        "-r",
        "--read-only",
        action='store_true',
        help=i18n.t("i18n.ReadOnlyDescription"))

    parser_search = subparsers.add_parser(
        "search", parents=[base_subparser], help=i18n.t("i18n.SearchForAppointment"))
    parser_search.add_argument(
        "-s",
        "--retry-sec",
        type=int,
        default=60,
        help=i18n.t("i18n.RetrySecDescription"))

    parser_code = subparsers.add_parser(
        "code",
        parents=[base_subparser],
        help=i18n.t("i18n.GenerateVacCode"))

    args = parser.parse_args()

    if not hasattr(args, "file") or args.file is None:
        args.file = os.path.join(PATH, "data/kontaktdaten.json")
    if not hasattr(args, "configure_only"):
        args.configure_only = False
    if not hasattr(args, "read_only"):
        args.read_only = False
    if not hasattr(args, "retry_sec"):
        args.retry_sec = 60

    try:
        validate_args(args)
    except ValueError as exc:
        parser.error(str(exc))
        # parser.error terminates the program with status code 2.

    if args.command is not None:
        try:
            if args.command == "search":
                subcommand_search(args)
            elif args.command == "code":
                subcommand_code(args)
            else:
                assert False
        except ValidationError as exc:
            print(i18n.t('i18n.ErrorIn') + f" {json.dumps(args.file)}:\n{str(exc)}")

    else:
        extended_settings = False

        while True:
            print(
                i18n.t("Menu") + "?\n"
                f"[1] {i18n.t('i18n.SearchForAppointment')}\n"
                f"[2] {i18n.t('i18n.GenerateVacCode')}\n"
                f"[x] {i18n.t('i18n.HideAdvancedSettings') if extended_settings else i18n.t('i18n.ShowAdvancedSettings')}\n")

            if extended_settings:
                print(
                    f"[c] --configure-only {i18n.t('i18n.deactivate') if args.configure_only else i18n.t('i18n.activate')}\n"
                    f"[r] --read-only {i18n.t('i18n.deactivate') if args.read_only else i18n.t('i18n.activate')}\n"
                    f"[s] --retry-sec {i18n.t('i18n.set')}\n")

            option = input("> Option: ").lower()
            print()

            try:
                if option == "1":
                    subcommand_search(args)
                elif option == "2":
                    subcommand_code(args)
                elif option == "x":
                    extended_settings = not extended_settings
                elif extended_settings and option == "c":
                    new_args = copy.copy(args)
                    new_args.configure_only = not new_args.configure_only
                    validate_args(new_args)
                    args = new_args
                    print(
                        f"--configure-only {i18n.t('i18n.deactivate') if not args.read_only else i18n.t('i18n.activate')}.")
                elif extended_settings and option == "r":
                    new_args = copy.copy(args)
                    new_args.read_only = not new_args.read_only
                    validate_args(new_args)
                    args = new_args
                    print(
                        f"--read-only {i18n.t('i18n.deactivate') if not args.read_only else i18n.t('i18n.activate')}.")
                elif extended_settings and option == "s":
                    args.retry_sec = int(input("> --retry-sec="))
                else:
                    print(i18n.t('i18n.InvalidInputPleaseTryAgain') + ".")
                print()
            except Exception as exc:
                print(f"\n{i18n.t('i18n.Error')}:\n{str(exc)}\n")


if __name__ == "__main__":
    print("""
                                _                 
                               (_)                
 __   __   __ _    ___    ___   _   _ __    _   _ 
 \ \ / /  / _` |  / __|  / __| | | | '_ \  | | | |
  \ V /  | (_| | | (__  | (__  | | | |_) | | |_| |
   \_/    \__,_|  \___|  \___| |_| | .__/   \__, |
                                   | |       __/ |
                                   |_|      |___/ 
""")
    # Lade Sprachen
    i18n.load_path.append(os.path.join(PATH, "i18n"))
    i18n.set('fallback', 'de')

    # Auf aktuelle Version prüfen
    try:
        if not update_available():
            print(i18n.t('i18n.YouAreUsingTheLatestVersionOfVaccipy') + ': ' + get_current_version())
        else:
            print(i18n.t('i18n.YouAreUsingAnOldVersionOfVaccipy') + get_latest_version())
    except:
        print(i18n.t('i18n.CannotVerifyIfVaccipyIsRunningInItsLatestVersion'))

    print()

    print(i18n.t('i18n.CheckIfYouAreAllowedForVaccination'))
    main()
