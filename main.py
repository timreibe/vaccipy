#!/usr/bin/env python3

import argparse
import copy
import json
import os

from tools.utils import create_missing_dirs, remove_prefix
from tools.its import ImpfterminService

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

    if filepath is None:
        filepath = os.path.join(PATH, "data/kontaktdaten.json")

    kontaktdaten = copy.deepcopy(known_kontaktdaten)

    with open(filepath, 'w', encoding='utf-8') as file:
        if "plz_impfzentren" not in kontaktdaten:
            print(
                "Mit einem Code kann in mehreren Impfzentren gleichzeitig nach einem Termin gesucht werden.\n"
                "Eine Übersicht über die Gruppierung der Impfzentren findest du hier:\n"
                "https://github.com/iamnotturner/vaccipy/wiki/Ein-Code-fuer-mehrere-Impfzentren\n\n"
                "Trage nun die PLZ deines Impfzentrums ein. Für mehrere Impfzentren die PLZ's kommagetrennt nacheinander.\n"
                "Beispiel: 68163, 69124, 69469\n")
            plz_impfzentren = input("> PLZ's der Impfzentren: ")
            kontaktdaten["plz_impfzentren"] = list(
                set([plz.strip() for plz in plz_impfzentren.split(",")]))

        if "code" not in kontaktdaten and command == "search":
            kontaktdaten["code"] = input("> Code: ")

        if "kontakt" not in kontaktdaten:
            kontaktdaten["kontakt"] = {}

        if "anrede" not in kontaktdaten["kontakt"] and command == "search":
            kontaktdaten["kontakt"]["anrede"] = input(
                "> Anrede (Frau/Herr/...): ")

        if "vorname" not in kontaktdaten["kontakt"] and command == "search":
            kontaktdaten["kontakt"]["vorname"] = input("> Vorname: ")

        if "nachname" not in kontaktdaten["kontakt"] and command == "search":
            kontaktdaten["kontakt"]["nachname"] = input("> Nachname: ")

        if "strasse" not in kontaktdaten["kontakt"] and command == "search":
            kontaktdaten["kontakt"]["strasse"] = input("> Strasse: ")

        if "hausnummer" not in kontaktdaten["kontakt"] and command == "search":
            kontaktdaten["kontakt"]["hausnummer"] = input("> Hausnummer: ")

        if "plz" not in kontaktdaten["kontakt"] and command == "search":
            # Sicherstellen, dass die PLZ ein valides Format hat.
            _wohnort_plz_valid = False
            while not _wohnort_plz_valid:
                wohnort_plz = input("> PLZ des Wohnorts: ")
                wohnort_plz = wohnort_plz.strip()
                if len(wohnort_plz) == 5 and wohnort_plz.isdigit():
                    _wohnort_plz_valid = True
                else:
                    print(
                        f"Die eingegebene PLZ {wohnort_plz} scheint ungültig. Genau 5 Stellen und nur Ziffern sind erlaubt.")
            kontaktdaten["kontakt"]["plz"] = wohnort_plz

        if "ort" not in kontaktdaten["kontakt"] and command == "search":
            kontaktdaten["kontakt"]["ort"] = input("> Wohnort: ")

        if "phone" not in kontaktdaten["kontakt"]:
            telefonnummer = input("> Telefonnummer: +49")
            # Anführende Zahlen und Leerzeichen entfernen
            telefonnummer = telefonnummer.strip()
            telefonnummer = remove_prefix(telefonnummer, "+49")
            telefonnummer = remove_prefix(telefonnummer, "0")
            kontaktdaten["kontakt"]["phone"] = f"+49{telefonnummer}"

        if "notificationChannel" not in kontaktdaten["kontakt"]:
            kontaktdaten["kontakt"]["notificationChannel"] = "email"

        if "notificationReceiver" not in kontaktdaten["kontakt"]:
            kontaktdaten["kontakt"]["notificationReceiver"] = input("> Mail: ")

        json.dump(kontaktdaten, file, ensure_ascii=False, indent=4)

    return kontaktdaten


def get_kontaktdaten(filepath=None):
    """
    Lade Kontaktdaten aus Datei.

    :param filepath: Pfad zur JSON-Datei mit Kontaktdaten. Default: data/kontaktdaten.json im aktuellen Ordner
    :return: Dictionary mit Kontaktdaten
    """

    if filepath is None:
        filepath = os.path.join(PATH, "data/kontaktdaten.json")

    with open(filepath) as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}


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

    if kontaktdaten_path is None:
        kontaktdaten_path = os.path.join(PATH, "data/kontaktdaten.json")

    print(
        "Bitte trage zunächst deinen Impfcode und deine Kontaktdaten ein.\n"
        f"Die Daten werden anschließend lokal in der Datei '{os.path.basename(kontaktdaten_path)}' abgelegt.\n"
        "Du musst sie zukünftig nicht mehr eintragen.\n")

    kontaktdaten = {}
    if os.path.isfile(kontaktdaten_path):
        daten_laden = input(
            f"> Sollen die vorhandenen Daten aus '{os.path.basename(kontaktdaten_path)}' geladen werden (y/n)?: ").lower()
        if daten_laden.lower() != "n":
            kontaktdaten = get_kontaktdaten(kontaktdaten_path)

    print()
    kontaktdaten = update_kontaktdaten_interactive(
        kontaktdaten, "search", kontaktdaten_path)
    print()
    return run_search(kontaktdaten, check_delay)


def run_search(kontaktdaten, check_delay):
    """
    Nicht-interaktive Terminsuche

    :param kontaktdaten: Dictionary mit Kontaktdaten
    """

    try:
        code = kontaktdaten["code"]

        # Hinweis, wenn noch alte Version der Kontaktdaten.json verwendet wird
        if kontaktdaten.get("plz"):
            print(
                "ACHTUNG: Du verwendest noch die alte Version der 'Kontaktdaten.json'!\n"
                "Lösche vor dem nächsten Ausführen die Datei und fülle die Kontaktdaten bitte erneut aus.\n")
            plz_impfzentren = [kontaktdaten.get("plz")]
        else:
            plz_impfzentren = kontaktdaten["plz_impfzentren"]

        kontakt = kontaktdaten["kontakt"]
        print(
            f"Kontaktdaten wurden geladen für: {kontakt['vorname']} {kontakt['nachname']}\n")
    except KeyError as exc:
        raise ValueError(
            "Kontaktdaten konnten nicht aus 'kontaktdaten.json' geladen werden.\n"
            "Bitte überprüfe, ob sie im korrekten JSON-Format sind oder gebe "
            "deine Daten beim Programmstart erneut ein.\n") from exc

    ImpfterminService.terminsuche(code=code, plz_impfzentren=plz_impfzentren, kontakt=kontakt,
                                  check_delay=check_delay,PATH=PATH)


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

    if kontaktdaten_path is None:
        kontaktdaten_path = os.path.join(PATH, "data/kontaktdaten.json")

    print(
        "Du kannst dir jetzt direkt einen Impf-Code erstellen.\n"
        "Dazu benötigst du eine Mailadresse, Telefonnummer und die PLZ deines Impfzentrums.\n"
        f"Die Daten werden anschließend lokal in der Datei '{os.path.basename(kontaktdaten_path)}' abgelegt.\n"
        "Du musst sie zukünftig nicht mehr eintragen.\n")

    kontaktdaten = {}
    if os.path.isfile(kontaktdaten_path):
        daten_laden = input(
            f"> Sollen die vorhandenen Daten aus '{os.path.basename(kontaktdaten_path)}' geladen werden (y/n)?: ").lower()
        if daten_laden.lower() != "n":
            kontaktdaten = get_kontaktdaten(kontaktdaten_path)

    print()
    kontaktdaten = update_kontaktdaten_interactive(
        kontaktdaten, "code", kontaktdaten_path)
    print()
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
        telefonnummer = telefonnummer.strip()
        telefonnummer = remove_prefix(telefonnummer, "+49")
        telefonnummer = remove_prefix(telefonnummer, "0")
    except KeyError as exc:
        print(
            "Kontaktdaten konnten nicht aus 'kontaktdaten.json' geladen werden.\n"
            "Bitte überprüfe, ob sie im korrekten JSON-Format sind oder gebe "
            "deine Daten beim Programmstart erneut ein.\n")
        raise exc

    its = ImpfterminService("PLAT-ZHAL-TER1", [plz_impfzentrum], {},PATH)

    print("Wähle nachfolgend deine Altersgruppe aus (L920, L921, L922 oder L923).\n"
          "Es ist wichtig, dass du die Gruppe entsprechend deines Alters wählst, "
          "ansonsten wird dir der Termin vor Ort abesagt.\n"
          "In den eckigen Klammern siehst du, welche Impfstoffe den Gruppe jeweils zugeordnet sind.\n"
          "Beispiel: L921\n")

    while True:
        leistungsmerkmal = input("> Leistungsmerkmal: ").upper()
        if leistungsmerkmal in ["L920", "L921", "L922", "L923"]:
            break
        print("Falscheingabe! Bitte erneut versuchen:")

    # cookies erneuern und code anfordern
    its.cookies_erneuern()
    token = its.code_anfordern(mail, telefonnummer, plz_impfzentrum, leistungsmerkmal)

    if token is not None:
        # code bestätigen
        print("\nDu erhälst gleich eine SMS mit einem Code zur Bestätigung deiner Telefonnummer.\n"
              "Trage diesen hier ein. Solltest du dich vertippen, hast du noch 2 weitere Versuche.\n"
              "Beispiel: 123-456\n")

        # 3 Versuche für die SMS-Code-Eingabe
        for _ in range(3):
            sms_pin = input("> SMS-Code: ").replace("-", "")
            if its.code_bestaetigen(token, sms_pin):
                print("\nDu kannst jetzt mit der Terminsuche fortfahren.\n")
                return True

    print("\nDie Code-Generierung war leider nicht erfolgreich.\n")
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
        raise ValueError("Kann nicht --configure-only und --read-only gleichzeitig verwenden")


def main():
    create_missing_dirs()

    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(help="commands", dest="command")

    base_subparser = argparse.ArgumentParser(add_help=False)
    base_subparser.add_argument(
        "-f",
        "--file",
        help="Pfad zur JSON-Datei für Kontaktdaten")
    base_subparser.add_argument(
        "-c",
        "--configure-only",
        action='store_true',
        help="Nur Kontaktdaten erfassen und in JSON-Datei abspeichern")
    base_subparser.add_argument(
        "-r",
        "--read-only",
        action='store_true',
        help="Es wird nicht nach fehlenden Kontaktdaten gefragt. Stattdessen wird ein Fehler angezeigt, falls benötigte Kontaktdaten in der JSON-Datei fehlen.")

    parser_search = subparsers.add_parser(
        "search", parents=[base_subparser], help="Termin suchen")
    parser_search.add_argument(
        "-s",
        "--retry-sec",
        type=int,
        default=60,
        help="Wartezeit zwischen zwei Versuchen (in Sekunden)")

    parser_code = subparsers.add_parser(
        "code",
        parents=[base_subparser],
        help="Impf-Code generieren")

    args = parser.parse_args()

    if not hasattr(args, "file"):
        args.file = None
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

    if args.command == "search":
        subcommand_search(args)

    elif args.command == "code":
        subcommand_code(args)

    else:
        extended_settings = False

        while True:
            print(
                "Was möchtest du tun?\n"
                "[1] Termin suchen\n"
                "[2] Impf-Code generieren\n"
                f"[x] Erweiterte Einstellungen {'verbergen' if extended_settings else 'anzeigen'}\n")

            if extended_settings:
                print(
                    f"[c] --configure-only {'de' if args.configure_only else ''}aktivieren\n"
                    f"[r] --read-only {'de' if args.read_only else ''}aktivieren\n"
                    "[s] --retry-sec setzen\n")

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
                        f"--configure-only {'de' if not args.configure_only else ''}aktiviert.")
                elif extended_settings and option == "r":
                    new_args = copy.copy(args)
                    new_args.read_only = not new_args.read_only
                    validate_args(new_args)
                    args = new_args
                    print(
                        f"--read-only {'de' if not args.read_only else ''}aktiviert.")
                elif extended_settings and option == "s":
                    args.retry_sec = int(input("> --retry-sec="))
                else:
                    print("Falscheingabe! Bitte erneut versuchen.")
                print()
            except Exception as exc:
                print(f"\nFehler: {str(exc)}\n")


if __name__ == "__main__":
    print("vaccipy - Automatische Terminbuchung für den Corona Impfterminservice\n")
    main()
