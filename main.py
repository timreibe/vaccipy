#!/usr/bin/env python3

import argparse
import copy
import json
import os
import platform
import sys
import time
import traceback
from base64 import b64encode
from datetime import datetime
from random import choice
from threading import Thread
from typing import Dict, List

import cloudscraper
from plyer import notification
from selenium.webdriver import ActionChains
from selenium.webdriver import Chrome
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from tools.clog import CLogger
from tools.utils import retry_on_failure, remove_prefix

PATH = os.path.dirname(os.path.realpath(__file__))


class ImpfterminService():
    def __init__(self, code: str, plz_impfzentren: list, kontakt: dict):
        self.code = str(code).upper()
        self.splitted_code = self.code.split("-")

        # PLZ's zu String umwandeln
        self.plz_impfzentren = sorted([str(plz) for plz in plz_impfzentren])
        self.plz_termin = None

        self.kontakt = kontakt
        self.authorization = b64encode(bytes(f":{code}", encoding='utf-8')).decode("utf-8")

        # Logging einstellen
        self.log = CLogger("impfterminservice")
        self.log.set_prefix(f"*{self.code[-4:]} | {', '.join(self.plz_impfzentren)}")

        # Session erstellen
        self.s = cloudscraper.create_scraper()
        self.s.headers.update({
            'Authorization': f'Basic {self.authorization}',
            # 'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 11_2_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.82 Safari/537.36',
        })

        # Ausgewähltes Impfzentrum prüfen
        self.verfuegbare_impfzentren = {}
        self.impfzentrum = {}
        self.domain = None
        if not self.impfzentren_laden():
            main()

        # Verfügbare Impfstoffe laden
        self.verfuegbare_qualifikationen: List[Dict] = []
        while not self.impfstoffe_laden():
            self.log.warn("Erneuter Versuch in 60 Sekunden")
            time.sleep(60)

        # OS
        self.operating_system = platform.system().lower()

        # Sonstige
        self.terminpaar = None
        self.qualifikationen = []
        self.app_name = str(self)

    def __str__(self) -> str:
        return "ImpfterminService"

    @retry_on_failure()
    def impfzentren_laden(self):
        """
        Laden aller Impfzentren zum Abgleich der eingegebenen PLZ.

        :return: bool
        """

        url = "https://www.impfterminservice.de/assets/static/impfzentren.json"

        res = self.s.get(url, timeout=15)
        if res.ok:
            # Antwort-JSON umformatieren für einfachere Handhabung
            formatierte_impfzentren = {}
            for bundesland, impfzentren in res.json().items():
                for impfzentrum in impfzentren:
                    formatierte_impfzentren[impfzentrum["PLZ"]] = impfzentrum

            self.verfuegbare_impfzentren = formatierte_impfzentren
            self.log.info(f"{len(self.verfuegbare_impfzentren)} Impfzentren verfügbar")

            # Prüfen, ob Impfzentren zur eingetragenen PLZ existieren
            plz_geprueft = []
            for plz in self.plz_impfzentren:
                self.impfzentrum = self.verfuegbare_impfzentren.get(plz)
                if self.impfzentrum:
                    self.domain = self.impfzentrum.get("URL")
                    self.log.info("'{}' in {} {} ausgewählt".format(
                        self.impfzentrum.get("Zentrumsname").strip(),
                        self.impfzentrum.get("PLZ"),
                        self.impfzentrum.get("Ort")))
                    plz_geprueft.append(plz)

            if plz_geprueft:
                self.plz_impfzentren = plz_geprueft
                return True
            else:
                self.log.error("Kein Impfzentrum zu eingetragenen PLZ's verfügbar.")
                return False
        else:
            self.log.error("Impfzentren können nicht geladen werden")
        return False

    @retry_on_failure(1)
    def impfstoffe_laden(self):
        """
        Laden der verfügbaren Impstoff-Qualifikationen.
        In der Regel gibt es 3 Qualifikationen, die je nach Altersgruppe verteilt werden.

        :return:
        """
        path = "assets/static/its/vaccination-list.json"

        res = self.s.get(self.domain + path, timeout=15)
        if res.ok:
            res_json = res.json()

            for qualifikation in res_json:
                qualifikation["impfstoffe"] = qualifikation.get("tssname",
                                                                "N/A").replace(" ", "").split(",")
                self.verfuegbare_qualifikationen.append(qualifikation)

            # Ausgabe der verfügbaren Impfstoffe:
            for qualifikation in self.verfuegbare_qualifikationen:
                q_id = qualifikation["qualification"]
                alter = qualifikation.get("age", "N/A")
                intervall = qualifikation.get("interval", " ?")
                impfstoffe = str(qualifikation["impfstoffe"])
                self.log.info(
                    f"[{q_id}] Altersgruppe: {alter} (Intervall: {intervall} Tage) --> {impfstoffe}")
            print("")
            return True

        self.log.error("Keine Impfstoffe im ausgewählten Impfzentrum verfügbar")
        return False

    @retry_on_failure()
    def cookies_erneuern(self, terminbuchung=False):
        """
        Cookies der Session erneuern, wenn sie abgelaufen sind.
        Inklusive Backup-Prozess für die Terminbuchung, wenn diese im Bot fehlschlägt.

        :param terminbuchung: Startet den Backup-Prozess der Terminbuchung
        :return:
        """

        if terminbuchung == False:
            self.log.info("Browser-Cookies generieren")
        else:
            self.log.info("Termin über Selenium buchen")
        # Chromedriver anhand des OS auswählen
        chromedriver = os.getenv("VACCIPY_CHROMEDRIVER")
        if not chromedriver:
            if 'linux' in self.operating_system:
                if "64" in platform.architecture() or sys.maxsize > 2 ** 32:
                    chromedriver = os.path.join(PATH, "tools/chromedriver/chromedriver-linux-64")

                else:
                    chromedriver = os.path.join(PATH, "tools/chromedriver/chromedriver-linux-32")
            elif 'windows' in self.operating_system:
                chromedriver = os.path.join(PATH, "tools/chromedriver/chromedriver-windows.exe")
            elif 'darwin' in self.operating_system:
                if "arm" in platform.processor().lower():
                    chromedriver = os.path.join(PATH, "tools/chromedriver/chromedriver-mac-m1")
                else:
                    chromedriver = os.path.join(PATH, "tools/chromedriver/chromedriver-mac-intel")

        path = "impftermine/service?plz={}".format(choice(self.plz_impfzentren))

        # deaktiviere Selenium Logging
        chrome_options = Options()
        chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])

        with Chrome(chromedriver, options=chrome_options) as driver:
            driver.get(self.domain + path)

            # Queue Bypass
            queue_cookie = driver.get_cookie("akavpwr_User_allowed")
            if queue_cookie:
                self.log.info("Im Warteraum, Seite neuladen")
                queue_cookie["name"] = "akavpau_User_allowed"
                driver.add_cookie(queue_cookie)

                # Seite neu laden
                driver.get(self.domain + path)
                driver.refresh()

            # Klick auf "Auswahl bestätigen" im Cookies-Banner
            # Warteraum-Support: Timeout auf 1 Stunde
            button_xpath = ".//html/body/app-root/div/div/div/div[2]/div[2]/div/div[1]/a"
            button = WebDriverWait(driver, 60 * 60).until(
                EC.element_to_be_clickable((By.XPATH, button_xpath)))
            action = ActionChains(driver)
            action.move_to_element(button).click().perform()

            # Klick auf "Vermittlungscode bereits vorhanden"
            button_xpath = "/html/body/app-root/div/app-page-its-login/div/div/div[2]/app-its-login-user/" \
                           "div/div/app-corona-vaccination/div[2]/div/div/label[1]/span"
            button = WebDriverWait(driver, 1).until(
                EC.element_to_be_clickable((By.XPATH, button_xpath)))
            action = ActionChains(driver)
            action.move_to_element(button).click().perform()

            # Auswahl des ersten Code-Input-Feldes
            input_xpath = "/html/body/app-root/div/app-page-its-login/div/div/div[2]/app-its-login-user/" \
                          "div/div/app-corona-vaccination/div[3]/div/div/div/div[1]/app-corona-vaccination-yes/" \
                          "form[1]/div[1]/label/app-ets-input-code/div/div[1]/label/input"
            input_field = WebDriverWait(driver, 1).until(
                EC.element_to_be_clickable((By.XPATH, input_xpath)))
            action = ActionChains(driver)
            action.move_to_element(input_field).click().perform()

            # Code eintragen
            input_field.send_keys(self.code)
            time.sleep(.1)

            # Klick auf "Termin suchen"
            button_xpath = "/html/body/app-root/div/app-page-its-login/div/div/div[2]/app-its-login-user/" \
                           "div/div/app-corona-vaccination/div[3]/div/div/div/div[1]/app-corona-vaccination-yes/" \
                           "form[1]/div[2]/button"
            button = WebDriverWait(driver, 1).until(
                EC.element_to_be_clickable((By.XPATH, button_xpath)))
            action = ActionChains(driver)
            action.move_to_element(button).click().perform()

            # Maus-Bewegung hinzufügen (nicht sichtbar)
            action.move_by_offset(10, 20).perform()

            # Backup Prozess, wenn die Terminbuchung mit dem Bot nicht klappt
            # wird das Browserfenster geöffnet und die Buchung im Browser beendet
            if terminbuchung:
                # Klick auf "Termin suchen"
                button_xpath = "/html/body/app-root/div/app-page-its-search/div/div/div[2]/div/div/div[5]/div/div[1]/div[2]/div[2]/button"
                button = WebDriverWait(driver, 1).until(
                    EC.element_to_be_clickable((By.XPATH, button_xpath)))
                action = ActionChains(driver)
                action.move_to_element(button).click().perform()
                time.sleep(.5)

                # Termin auswählen
                button_xpath = '//*[@id="itsSearchAppointmentsModal"]/div/div/div[2]/div/div/form/div[1]/div[2]/label/div[2]/div'
                button = WebDriverWait(driver, 1).until(
                    EC.element_to_be_clickable((By.XPATH, button_xpath)))
                action = ActionChains(driver)
                action.move_to_element(button).click().perform()
                time.sleep(.5)

                # Klick Button "AUSWÄHLEN"
                button_xpath = '//*[@id="itsSearchAppointmentsModal"]/div/div/div[2]/div/div/form/div[2]/button[1]'
                button = WebDriverWait(driver, 1).until(
                    EC.element_to_be_clickable((By.XPATH, button_xpath)))
                action = ActionChains(driver)
                action.move_to_element(button).click().perform()
                time.sleep(.5)

                # Klick Daten erfassen
                button_xpath = '/html/body/app-root/div/app-page-its-search/div/div/div[2]/div/div/div[5]/div/div[2]/div[2]/div[2]/button'
                button = WebDriverWait(driver, 1).until(
                    EC.element_to_be_clickable((By.XPATH, button_xpath)))
                action = ActionChains(driver)
                action.move_to_element(button).click().perform()
                time.sleep(.5)

                # Klick Anrede
                button_xpath = '//*[@id="itsSearchContactModal"]/div/div/div[2]/div/form/div[1]/app-booking-contact-form/div[1]/div/div/div[1]/label[2]/span'
                button = WebDriverWait(driver, 1).until(
                    EC.element_to_be_clickable((By.XPATH, button_xpath)))
                action = ActionChains(driver)
                action.move_to_element(button).click().perform()

                # Input Vorname
                input_xpath = '/html/body/app-root/div/app-page-its-search/app-its-search-contact-modal/div/div/div/div[2]/div/form/div[1]/app-booking-contact-form/div[2]/div[1]/div/label/input'
                input_field = WebDriverWait(driver, 1).until(
                    EC.element_to_be_clickable((By.XPATH, input_xpath)))
                action.move_to_element(input_field).click().perform()
                input_field.send_keys(self.kontakt['vorname'])

                # Input Nachname
                input_field = driver.find_element_by_xpath(
                    '//*[@id="itsSearchContactModal"]/div/div/div[2]/div/form/div[1]/app-booking-contact-form/div[2]/div[2]/div/label/input')
                input_field.send_keys(self.kontakt['nachname'])

                # Input PLZ
                input_field = driver.find_element_by_xpath(
                    '//*[@id="itsSearchContactModal"]/div/div/div[2]/div/form/div[1]/app-booking-contact-form/div[3]/div[1]/div/label/input')
                input_field.send_keys(self.kontakt['plz'])

                # Input City
                input_field = driver.find_element_by_xpath(
                    '//*[@id="itsSearchContactModal"]/div/div/div[2]/div/form/div[1]/app-booking-contact-form/div[3]/div[2]/div/label/input')
                input_field.send_keys(self.kontakt['ort'])

                # Input Strasse
                input_field = driver.find_element_by_xpath(
                    '//*[@id="itsSearchContactModal"]/div/div/div[2]/div/form/div[1]/app-booking-contact-form/div[4]/div[1]/div/label/input')
                input_field.send_keys(self.kontakt['strasse'])

                # Input Hasunummer
                input_field = driver.find_element_by_xpath(
                    '//*[@id="itsSearchContactModal"]/div/div/div[2]/div/form/div[1]/app-booking-contact-form/div[4]/div[2]/div/label/input')
                input_field.send_keys(self.kontakt['hausnummer'])

                # Input Telefonnummer
                input_field = driver.find_element_by_xpath(
                    '//*[@id="itsSearchContactModal"]/div/div/div[2]/div/form/div[1]/app-booking-contact-form/div[4]/div[3]/div/label/div/input')
                input_field.send_keys(self.kontakt['phone'].replace("+49", ""))

                # Input Mail
                input_field = driver.find_element_by_xpath(
                    '//*[@id="itsSearchContactModal"]/div/div/div[2]/div/form/div[1]/app-booking-contact-form/div[5]/div/div/label/input')
                input_field.send_keys(self.kontakt['notificationReceiver'])

                # Klick Button "ÜBERNEHMEN"
                button_xpath = '//*[@id="itsSearchContactModal"]/div/div/div[2]/div/form/div[2]/button[1]'
                button = WebDriverWait(driver, 1).until(
                    EC.element_to_be_clickable((By.XPATH, button_xpath)))
                action = ActionChains(driver)
                action.move_to_element(button).click().perform()
                time.sleep(.7)

                # Termin buchen
                button_xpath = '/html/body/app-root/div/app-page-its-search/div/div/div[2]/div/div/div[5]/div/div[3]/div[2]/div[2]/button'
                button = WebDriverWait(driver, 1).until(
                    EC.element_to_be_clickable((By.XPATH, button_xpath)))
                action = ActionChains(driver)
                action.move_to_element(button).click().perform()
                time.sleep(3)
                if "Ihr Termin am" in str(driver.page_source):
                    msg = "Termin erfolgreich gebucht!"
                    self.log.success(msg)
                    self._desktop_notification("Terminbuchung:", msg)
                    return True

            # prüfen, ob Cookies gesetzt wurden und in Session übernehmen
            try:
                cookie = driver.get_cookie("bm_sz")
                if cookie:
                    self.s.cookies.clear()
                    self.s.cookies.update({c['name']: c['value'] for c in driver.get_cookies()})
                    self.log.info("Browser-Cookie generiert: *{}".format(cookie.get("value")[-6:]))
                    return True
                else:
                    self.log.error("Cookies können nicht erstellt werden!")
                    return False
            except:
                return False

    @retry_on_failure()
    def login(self):
        """Einloggen mittels Code, um qualifizierte Impfstoffe zu erhalten.
        Dieser Schritt ist wahrscheinlich nicht zwingend notwendig, aber schadet auch nicht.

        :return: bool
        """

        path = f"rest/login?plz={choice(self.plz_impfzentren)}"

        res = self.s.get(self.domain + path, timeout=15)
        if res.ok:
            # Checken, welche Impfstoffe für das Alter zur Verfügung stehen
            self.qualifikationen = res.json().get("qualifikationen")

            if self.qualifikationen:
                zugewiesene_impfstoffe = set()

                for q in self.qualifikationen:
                    for verfuegbare_q in self.verfuegbare_qualifikationen:
                        if verfuegbare_q["qualification"] == q:
                            zugewiesene_impfstoffe.update(verfuegbare_q["impfstoffe"])

                self.log.info("Erfolgreich mit Code eingeloggt")
                self.log.info(f"Mögliche Impfstoffe: {list(zugewiesene_impfstoffe)}")
                print(" ")

                return True
            else:
                self.log.warn("Keine qualifizierten Impfstoffe verfügbar")
        else:
            self.log.warn("Einloggen mit Code nicht möglich")
        print(" ")
        return False

    @retry_on_failure()
    def termin_suchen(self, plz):
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

        path = f"rest/suche/impfterminsuche?plz={plz}"

        while True:
            res = self.s.get(self.domain + path, timeout=15)
            if not res.ok or 'Virtueller Warteraum des Impfterminservice' not in res.text:
                break
            self.log.info('Warteraum... zZz...')
            time.sleep(30)

        if res.ok:
            res_json = res.json()
            terminpaare = res_json.get("termine")
            if terminpaare:
                # Auswahl des erstbesten Terminpaares
                self.terminpaar = choice(terminpaare)
                self.plz_termin = plz
                self.log.success(f"Terminpaar gefunden!")
                self.impfzentrum = self.verfuegbare_impfzentren.get(plz)
                self.log.success("'{}' in {} {}".format(
                    self.impfzentrum.get("Zentrumsname").strip(),
                    self.impfzentrum.get("PLZ"),
                    self.impfzentrum.get("Ort")))
                for num, termin in enumerate(self.terminpaar, 1):
                    ts = datetime.fromtimestamp(termin["begin"] / 1000).strftime(
                        '%d.%m.%Y um %H:%M Uhr')
                    self.log.success(f"{num}. Termin: {ts}")
                return True, 200
            else:
                self.log.info(f"Keine Termine verfügbar in {plz}")
        else:
            self.log.error(f"Terminpaare können nicht geladen werden: {res.text}")
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
            "plz": self.plz_termin,
            "slots": [termin.get("slotId") for termin in self.terminpaar],
            "qualifikationen": self.qualifikationen,
            "contact": self.kontakt
        }

        res = self.s.post(self.domain + path, json=data, timeout=15)

        if res.status_code == 201:
            msg = "Termin erfolgreich gebucht!"
            self.log.success(msg)
            self._desktop_notification("Terminbuchung:", msg)
            return True

        if res.statuscode == 429:
            msg = "Anfrage wurde von der Botprotection geblockt."
        elif res.status_code >= 400:
            data = res.json()
            try:
                error = data['errors']['status']
            except KeyError:
                error = ''
            if 'nicht mehr verfügbar' in error:
                msg = f"Diesen Termin gibts nicht mehr: {error}"
            else:
                msg = f"Termin konnte nicht gebucht werden: {data}"
        else:
            msg = f"Unbekannter Statuscode: {res.status_code}"

        self.log.error(msg)
        self._desktop_notification("Terminbuchung:", msg)
        return False

    @retry_on_failure()
    def code_anfordern(self, mail, telefonnummer, plz_impfzentrum, leistungsmerkmal):
        """
        SMS-Code beim Impfterminservice anfordern.

        :param mail: Mail für Empfang des Codes
        :param telefonnummer: Telefonnummer für SMS-Code
        :param plz_impfzentrum: PLZ des Impfzentrums, für das ein Code erstellt werden soll
        :param leistungsmerkmal: gewählte Impfgruppe (bspw. L921)
        :return:
        """

        path = "rest/smspin/anforderung"

        data = {
            "email": mail,
            "leistungsmerkmal": leistungsmerkmal,
            "phone": "+49" + telefonnummer,
            "plz": plz_impfzentrum
        }
        while True:
            res = self.s.post(self.domain + path, json=data, timeout=15)
            if res.ok:
                token = res.json().get("token")
                return token
            elif res.status_code == 429:
                self.log.error(
                    "Anfrage wurde von der Botprotection geblockt. Es werden manuelle Cookies aus dem Browser benötigt. Bitte Anleitung im FAQ in GITHUB beachten!")
                cookies = input("> Manuelle Cookies: ").strip()
                optional_prefix = "Cookie: "
                if cookies.startswith(optional_prefix):
                    cookies = cookies[len(optional_prefix):]
                self.s.headers.update({
                    'Cookie': cookies
                })

            else:
                self.log.error(f"Code kann nicht angefragt werden: {res.text}")
                return None

    @retry_on_failure()
    def code_bestaetigen(self, token, sms_pin):
        """
        Bestätigung der Code-Generierung mittels SMS-Code

        :param token: Token der Code-Erstellung
        :param sms_pin: 6-stelliger SMS-Code
        :return:
        """

        path = f"rest/smspin/verifikation"
        data = {
            "token": token,
            "smspin": sms_pin

        }
        res = self.s.post(self.domain + path, json=data, timeout=15)
        if res.ok:
            self.log.success("Der Impf-Code wurde erfolgreich angefragt, bitte prüfe deine Mails!")
            return True
        else:
            self.log.error(f"Code-Verifikation fehlgeschlagen: {res.text}")
            return False

    @staticmethod
    def terminsuche(code: str, plz_impfzentren: list, kontakt: dict, check_delay: int = 30):
        """
        Workflow für die Terminbuchung.

        :param code: 14-stelliger Impf-Code
        :param plz_impfzentren: Liste mit PLZ von Impfzentren
        :param kontakt: Kontaktdaten der zu impfenden Person als JSON
        :param check_delay: Zeit zwischen Iterationen der Terminsuche
        :return:
        """

        its = ImpfterminService(code, plz_impfzentren, kontakt)
        its.cookies_erneuern()

        # login ist nicht zwingend erforderlich
        its.login()

        while True:
            termin_gefunden = False
            while not termin_gefunden:

                # durchlaufe jede eingegebene PLZ und suche nach Termin
                for plz in its.plz_impfzentren:
                    termin_gefunden, status_code = its.termin_suchen(plz)

                    # Durchlauf aller PLZ unterbrechen, wenn Termin gefunden wurde
                    if termin_gefunden:
                        break
                    # Cookies erneuern
                    elif status_code >= 400:
                        its.cookies_erneuern()
                    # Suche pausieren
                    if not termin_gefunden:
                        time.sleep(check_delay)

            # Programm beenden, wenn Termin gefunden wurde
            if its.termin_buchen():
                return True

            # Cookies erneuern und pausieren, wenn Terminbuchung nicht möglich war
            # Anschließend nach neuem Termin suchen
            if its.cookies_erneuern(terminbuchung=True):
                return True

    def _desktop_notification(self, title: str, message: str):
        """
        Starts a thread and creates a desktop notification using plyer.notification
        """

        if 'windows' not in self.operating_system:
            return

        try:
            Thread(target=notification.notify(
                app_name=self.app_name,
                title=title,
                message=message)
            ).start()
        except Exception as exc:
            self.log.error("Error in _desktop_notification: " + str(exc.__class__.__name__)
                           + traceback.format_exc())


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
        Default: kontaktdaten.json im aktuellen Ordner
    :return: Dictionary mit Kontaktdaten
    """

    assert(command in ["code", "search"])

    if filepath is None:
        filepath = os.path.join(PATH, "kontaktdaten.json")

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

    :param filepath: Pfad zur JSON-Datei mit Kontaktdaten. Default: kontaktdaten.json im aktuellen Ordner
    :return: Dictionary mit Kontaktdaten
    """

    if filepath is None:
        filepath = os.path.join(PATH, "kontaktdaten.json")

    with open(filepath) as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}


def run_search_interactive():
    """
    Interaktives Setup für die Terminsuche:
    1. Ggf. zuerst Eingabe, ob Kontaktdaten aus kontaktdaten.json geladen
       werden sollen.
    2. Laden der Kontaktdaten aus kontaktdaten.json.
    3. Bei unvollständigen Kontaktdaten: Interaktive Eingabe der fehlenden
       Kontaktdaten.
    4. Terminsuche
    """

    print(
        "Bitte trage zunächst deinen Impfcode und deine Kontaktdaten ein.\n"
        "Die Daten werden anschließend lokal in der Datei 'kontaktdaten.json' abgelegt.\n"
        "Du musst sie zukünftig nicht mehr eintragen.\n")

    kontaktdaten = {}

    kontaktdaten_path = os.path.join(PATH, "kontaktdaten.json")
    if os.path.isfile(kontaktdaten_path):
        daten_laden = input(
            "> Sollen die vorhandenen Daten aus 'kontaktdaten.json' geladen werden (y/n)?: ").lower()
        if daten_laden.lower() != "n":
            kontaktdaten = get_kontaktdaten(kontaktdaten_path)

    print()
    kontaktdaten = update_kontaktdaten_interactive(
        kontaktdaten, "search", kontaktdaten_path)
    print()
    return run_search(kontaktdaten)


def run_search(kontaktdaten, check_delay=30):
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
        print(
            "Kontaktdaten konnten nicht aus 'kontaktdaten.json' geladen werden.\n"
            "Bitte überprüfe, ob sie im korrekten JSON-Format sind oder gebe "
            "deine Daten beim Programmstart erneut ein.\n")
        raise exc

    ImpfterminService.terminsuche(code=code, plz_impfzentren=plz_impfzentren, kontakt=kontakt,
                                  check_delay=check_delay)


def gen_code_interactive():
    """
    Interaktives Setup für die Codegenerierung:
    1. Ggf. zuerst Eingabe, ob Kontaktdaten aus kontaktdaten.json geladen
       werden sollen.
    2. Laden der Kontaktdaten aus kontaktdaten.json.
    3. Bei unvollständigen Kontaktdaten: Interaktive Eingabe derjenigen
       fehlenden Kontaktdaten, die für die Codegenerierung benötigt werden.
    4. Codegenerierung

    :return:
    """

    print(
        "Du kannst dir jetzt direkt einen Impf-Code erstellen.\n"
        "Dazu benötigst du eine Mailadresse, Telefonnummer und die PLZ deines Impfzentrums.\n"
        "Die Daten werden anschließend lokal in der Datei 'kontaktdaten.json' abgelegt.\n"
        "Du musst sie zukünftig nicht mehr eintragen.\n")

    kontaktdaten = {}

    kontaktdaten_path = os.path.join(PATH, "kontaktdaten.json")
    if os.path.isfile(kontaktdaten_path):
        daten_laden = input(
            "> Sollen die vorhandenen Daten aus 'kontaktdaten.json' geladen werden (y/n)?: ").lower()
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

    its = ImpfterminService("PLAT-ZHAL-TER1", [plz_impfzentrum], {})

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
        print("Du erhälst gleich eine SMS mit einem Code zur Bestätigung deiner Telefonnummer.\n"
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


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(help="commands", dest="command")

    parser_search = subparsers.add_parser("search", help="Termin suchen")
    parser_search.add_argument(
        "-f", "--file", help="Pfad zur JSON-Datei für Kontaktdaten")
    parser_search.add_argument(
        "--configure-only",
        action='store_true',
        help="Nur Kontaktdaten erfassen und in JSON-Datei abspeichern")
    parser_search.add_argument(
        "--retry-sec", "-r",
        type=int,
        default=30,
        help="Wartezeit zwischen zwei Versuchen (in Sekunden)")

    parser_code = subparsers.add_parser("code", help="Impf-Code generieren")
    parser_code.add_argument(
        "-f",
        "--file",
        help="Pfad zur JSON-Datei für Kontaktdaten")
    parser_code.add_argument(
        "--configure-only",
        action='store_true',
        help="Nur Kontaktdaten erfassen und in JSON-Datei abspeichern")

    args = parser.parse_args()

    if args.command == "search":
        if args.configure_only:
            update_kontaktdaten_interactive({}, "search", args.file)
        elif args.file:
            run_search(get_kontaktdaten(args.file), check_delay=args.retry_sec)
        else:
            run_search_interactive()

    elif args.command == "code":
        if args.configure_only:
            update_kontaktdaten_interactive({}, "code", args.file)
        elif args.file:
            gen_code(get_kontaktdaten(args.file))
        else:
            gen_code_interactive()

    else:
        print("Was möchtest du tun?\n"
              "[1] Termin suchen\n"
              "[2] Impf-Code generieren\n")

        option = input("> Option: ")
        print(" ")

        if option == "1":
            run_search_interactive()
        elif option == "2":
            gen_code_interactive()
            main()
        else:
            print("Falscheingabe! Bitte erneut versuchen:")
            main()

        # Für Windows: Fenster 1 Stunde offen halten nach Ausführung
        time.sleep(60 * 60)


if __name__ == "__main__":
    print("vaccipy - Automatische Terminbuchung für den Corona Impfterminservice\n")
    main()
