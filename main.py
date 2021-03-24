import json
import os
import platform
import time
from base64 import b64encode
from datetime import datetime

import requests
from selenium.webdriver import Chrome

from tools.clog import CLogger
from tools.utils import retry_on_failure


class ImpfterminService():
    def __init__(self, code: str, plz: str, kontakt: dict):
        self.code = str(code).upper()
        self.plz = str(plz)
        self.kontakt = kontakt
        self.authorization = b64encode(bytes(f":{code}", encoding='utf-8')).decode("utf-8")

        # Logging einstellen
        self.log = CLogger("impfterminservice")
        self.log.set_prefix(f"*{self.code[-4:]}")

        # Session erstellen
        self.s = requests.Session()
        self.s.headers.update({
            'Authorization': f'Basic {self.authorization}',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 11_2_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.82 Safari/537.36',
        })

        # Ausgewähltes Impfzentrum prüfen
        self.verfuegbare_impfzentren = {}
        self.impfzentrum = {}
        self.domain = None
        if not self.impfzentren_laden():
            quit()

        # Verfügbare Impfstoffe laden
        self.verfuegbare_impfstoffe = {}
        if not self.impfstoffe_laden():
            quit()

        # Sonstige
        self.terminpaar = None
        self.qualifikationen = []

    @retry_on_failure()
    def impfzentren_laden(self):
        """Laden aller Impfzentren zum Abgleich der eingegebenen PLZ.

        :return: bool
        """
        url = "https://www.impfterminservice.de/assets/static/impfzentren.json"

        res = self.s.get(url)
        if res.ok:
            # Antwort-JSON umformattieren für einfachere Handhabung
            formattierte_impfzentren = {}
            for bundesland, impfzentren in res.json().items():
                for impfzentrum in impfzentren:
                    formattierte_impfzentren[impfzentrum["PLZ"]] = impfzentrum

            self.verfuegbare_impfzentren = formattierte_impfzentren
            self.log.info(f"{len(self.verfuegbare_impfzentren)} Impfzentren verfügbar")

            # Prüfen, ob Impfzentrum zur eingetragenen PLZ existiert
            self.impfzentrum = self.verfuegbare_impfzentren.get(self.plz)
            if self.impfzentrum:
                self.domain = self.impfzentrum.get("URL")
                self.log.info("'{}' in {} {} ausgewählt".format(
                    self.impfzentrum.get("Zentrumsname").strip(),
                    self.impfzentrum.get("PLZ"),
                    self.impfzentrum.get("Ort")))
                return True
            else:
                self.log.error(f"Kein Impfzentrum in PLZ {self.plz} verfügbar")
        else:
            self.log.error("Impfzentren können nicht geladen werden")
        return False

    @retry_on_failure()
    def impfstoffe_laden(self):
        """Laden der verfügbaren Impstoff-Qualifikationen.
        In der Regel gibt es 3 Qualifikationen, die je nach Altersgruppe verteilt werden.

        """
        path = "assets/static/its/vaccination-list.json"
        res = self.s.get(self.domain + path)

        if res.ok:
            res_json = res.json()
            self.log.info(f"{len(res_json)} Impfstoffe am Impfzentrum verfügbar")

            for impfstoff in res_json:
                qualifikation = impfstoff.get("qualification")
                name = impfstoff.get("name", "N/A")
                alter = impfstoff.get("age")
                intervall = impfstoff.get("interval")
                self.verfuegbare_impfstoffe[qualifikation] = name
                self.log.info(f"{qualifikation}: {name} --> Altersgruppe: {alter} --> Intervall: {intervall} Tage")
            print(" ")

            return True
        self.log.error("Keine Impfstoffe im ausgewählten Impfzentrum verfügbar")
        return False

    def cookies_erneuern(self):
        """Erneuern des bm_sz Cookies mit Selenium. Dazu wird die Suche-Seite aufgerufen.
        Der Cookie muss alle 10 Minuten oder alle 5 Terminsuche-Requests erneuert werden.

        :return: bool
        """
        # Chromedriver anhand des OS auswählen
        chromedriver = None
        operating_system = platform.system().lower()
        if 'linux' in operating_system:
            chromedriver = "./tools/chromedriver/chromedriver-linux"
        elif 'windows' in operating_system:
            chromedriver = "./tools/chromedriver/chromedriver-windows.exe"
        elif 'darwin' in operating_system:
            if "arm" in platform.processor().lower():
                chromedriver = "./tools/chromedriver/chromedriver-mac-m1"
            else:
                chromedriver = "./tools/chromedriver/chromedriver-mac-intel"

        path = f"impftermine/suche/{self.code}/{self.plz}"
        with Chrome(chromedriver) as driver:
            driver.get(self.domain + path)

            # Aus Erfahrung ist die Cookie-Generierung zuverlässiger,
            # wenn man kurz wartet
            time.sleep(3)

            # bm_sz-Cookie extrahieren und abspeichern
            cookie = driver.get_cookie("bm_sz")
            if cookie:
                self.s.cookies.update({c['name']: c['value'] for c in driver.get_cookies()})
                self.log.info("Cookie generiert: *{}".format(cookie.get("value")[-6:]))
                return True
            else:
                self.log.error("Cookie kann nicht erstellt werden!")
                return False

    @retry_on_failure()
    def login(self):
        """Einloggen mittels Code, um qualifizierte Impfstoffe zu erhalten.
        Dieser Schritt ist wahrscheinlich nicht zwigend notwendig, aber schadet auch nicht.

        :return: bool
        """
        path = f"rest/login?plz={self.plz}"
        res = self.s.get(self.domain + path)
        if res.ok:
            # Checken, welche Impfstoffe für das Alter zur Verfügung stehen
            self.qualifikationen = res.json().get("qualifikationen")
            if self.qualifikationen:
                zugewiesene_impfstoffe = " ".join([self.verfuegbare_impfstoffe.get(q, "N/A")
                                                   for q in self.qualifikationen])
                self.log.info("Erfolgreich mit Code eingeloggt")
                self.log.info(f"Qualifizierte Impfstoffe: {zugewiesene_impfstoffe}")
                print(" ")

                return True
            else:
                self.log.error("Keine qualifizierten Impfstoffe verfügbar!")
        else:
            self.log.error("Einloggen mit Code nicht möglich!")
        return False

    @retry_on_failure()
    def terminsuche(self):
        """Es wird nach einen verfügbaren Termin in der gewünschten PLZ gesucht.
        Ausgewählt wird der erstbeste Termin (!).
        Zurückgegeben wird das Ergebnis der Abfrage und der Status-Code.
        Bei Status-Code > 400 müssen die Cookies erneuert werden.

        Beispiel für ein Termin-Paar:

        [{
            'slotId': 'slot-56817da7-3f46-4f97-9868-30a6ddabcdef',
            'begin': 1616999901000,
            'bsnr': '005221080'
        }, {
            'slotId': 'slot-d29f5c22-384c-4928-922a-30a6ddabcdef',
            'begin': 1623999901000,
            'bsnr': '005221080'
        }]

        :return: bool, status-code
        """
        path = f"rest/suche/terminpaare?plz={self.plz}"

        res = self.s.get(self.domain + path)
        if res.ok:
            res_json = res.json()

            terminpaare = res_json.get("terminpaare")
            if terminpaare:
                # Auswahl des erstbesten Terminpaares
                self.terminpaar = terminpaare[0]
                self.log.success("Terminpaar gefunden!")

                for num, termin in enumerate(self.terminpaar, 1):
                    ts = datetime.fromtimestamp(termin["begin"] / 1000).strftime('%d.%m.%Y um %H:%M Uhr')
                    self.log.success(f"{num}. Termin: {ts}")
                return True, 200
            else:
                self.log.info("Keine Termine verfügbar")
        else:
            self.log.error("Terminpaare können nicht geladen werden")
        return False, res.status_code

    @retry_on_failure()
    def termin_buchen(self):
        """Termin wird gebucht für die Kontaktdaten, die beim Starten des
        Programms eingetragen oder aus der JSON-Datei importiert wurden.

        :return: bool
        """
        path = "rest/buchung"

        # Daten für Impftermin sammeln
        data = {
            "plz": self.plz,
            "slots": [self.terminpaar[0].get("slotId"), self.terminpaar[1].get("slotId")],
            "qualifikationen": self.qualifikationen,
            "contact": self.kontakt
        }

        res = self.s.post(self.domain + path, json=data)
        if res.status_code == 201:
            self.log.success("Termin erfolgreich gebucht!")
            return True
        else:
            self.log.error("Termin konnte nicht gebucht werden")
            return False

    @staticmethod
    def run(code: str, plz: str, kontakt: json, check_delay: int = 60):
        """Workflow für die Terminbuchung.

        :param code: 14-stelliger Impf-Code
        :param plz: PLZ des Impfzentrums
        :param kontakt: Kontaktdaten der zu impfenden Person als JSON
        :param check_delay: Zeit zwischen Iterationen der Terminsuche
        :return:
        """

        its = ImpfterminService(code, plz, kontakt)
        its.cookies_erneuern()
        while not its.login():
            its.cookies_erneuern()
            time.sleep(3)

        termin_gefunden = False
        while not termin_gefunden:
            termin_gefunden, status_code = its.terminsuche()
            if status_code >= 400:
                its.cookies_erneuern()
            else:
                time.sleep(check_delay)

        its.termin_buchen()


if __name__ == "__main__":
    print("vaccipy 1.0\n")

    # Check, ob die Datei "kontaktdaten.json" existiert
    kontaktdaten_erstellen = True
    if os.path.isfile("kontaktdaten.json"):
        daten_laden = input("Sollen die vorhandene Daten aus 'kontaktdaten.json' geladen werden (y/n)?: ").lower()
        if daten_laden != "n":
            kontaktdaten_erstellen = False

    if kontaktdaten_erstellen:
        print("Bitte trage zunächst deinen Impfcode und deine Kontaktdaten ein.\n"
              "Die Daten werden anschließend lokal in der Datei 'kontaktdaten.json' abgelegt.\n"
              "Du musst sie zukünftig nicht mehr eintragen.\n")
        code = input("Code: ")
        plz = input("PLZ des Impfzentrums: ")

        anrede = input("Anrede (Frau/Herr/...): ")
        vorname = input("Vorname: ")
        nachname = input("Nachname: ")
        strasse = input("Strasse: ")
        hausnummer = input("Hausnummer: ")
        wohnort_plz = input("PLZ des Wohnorts: ")
        wohnort = input("Wohnort: ")
        telefonnummer = input("Telefonnummer: ")
        mail = input("Mail: ")

        kontakt = {
            "anrede": anrede,
            "vorname": vorname,
            "nachname": nachname,
            "strasse": strasse,
            "hausnummer": hausnummer,
            "plz": wohnort_plz,
            "ort": wohnort,
            "phone": "+49" + str(telefonnummer),
            "notificationChannel": "email",
            "notificationReceiver": mail,
        }

        kontaktdaten = {
            "code": code,
            "plz": plz,
            "kontakt": kontakt
        }

        with open('kontaktdaten.json', 'w', encoding='utf-8') as f:
            json.dump(kontaktdaten, f, ensure_ascii=False, indent=4)

    else:
        with open("kontaktdaten.json") as f:
            kontaktdaten = json.load(f)

    try:
        code = kontaktdaten["code"]
        plz = kontaktdaten["plz"]
        kontakt = kontaktdaten["kontakt"]
        print(f"Kontaktdaten wurden geladen für: {kontakt['vorname']} {kontakt['nachname']}\n")
        ImpfterminService.run(code=code, plz=plz, kontakt=kontakt, check_delay=60)
    except KeyError:
        print("Kontaktdaten konnten nicht aus 'kontaktdaten.json' geladen werden."
              "Bitte überprüfe, ob sie im korrekten JSON-Format sind oder gebe"
              "deine Daten beim Programmstart erneut ein.")
