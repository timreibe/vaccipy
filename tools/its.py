# Alphabetisch sortiert:
import copy
import json
import os
import platform
import string
import sys
import time
# Alphabetisch sortiert:
from base64 import b64encode
from datetime import datetime, date, timedelta
from datetime import time as dtime
from itertools import cycle
from json import JSONDecodeError
from random import choice, choices, randint

import cloudscraper
from requests.exceptions import RequestException
from selenium.common.exceptions import WebDriverException
from selenium.webdriver import ActionChains
from selenium.webdriver import Chrome
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from seleniumwire import webdriver as selenium_wire

from tools.chromium_downloader import chromium_executable, check_chromium, webdriver_executable, check_webdriver
from tools.clog import CLogger
from tools.exceptions import AppointmentGone, BookingError, TimeframeMissed, UnmatchingCodeError
from tools.kontaktdaten import decode_wochentag, validate_codes, validate_kontakt, \
    validate_zeitrahmen
from tools.mousemover import move_mouse_to_coordinates
from tools.utils import fire_notifications, unique

try:
    import beepy

    ENABLE_BEEPY = True
except ImportError:
    ENABLE_BEEPY = False


class ImpfterminService():
    def __init__(self, codes: list, kontakt: dict, PATH: str, notifications: dict = dict()):
        self.PATH = PATH
        self.kontakt = kontakt
        self.operating_system = platform.system().lower()

        self.notifications = notifications

        # Logging einstellen
        self.log = CLogger("impfterminservice")

        # Session erstellen
        self.s = cloudscraper.create_scraper()
        self.s.headers.update({
            'User-Agent': 'Mozilla/5.0',
        })

        # Ausgewähltes Impfzentrum prüfen
        while True:
            try:
                self.impfzentren = self.impfzentren_laden()
                break
            except RuntimeError as exc:
                self.log.error(str(exc))
                self.log.info("Erneuter Versuch in 30 Sekunden")
                time.sleep(30)

        # Ein "Codepoint" ist ein dict, das einen Vermittlungscode ("code")
        # und den Zeitpunkt ("next_use") enthält, zu dem der Code frühestens
        # verwendet werden soll.
        # So kann man die Verwendung eines Codes z. B. für 10 Minuten
        # unterbinden.
        # Wir ordnen zunächst alle Codepoints zu allen URLs zu.
        # Aussortiert wird später, wenn die Verwendung von Codes fehlschlägt.
        codepoints = [
            {"code": code, "next_use": datetime.min}
            for code in unique(codes)
        ]
        self.codepoints = {
            url: copy.deepcopy(codepoints)
            for url in self.impfzentren
        }

        # Verfügbare Impfstoffe laden, aber nur um sie im Log auszugeben
        try:
            self.impfstoffe_laden(next(iter(self.impfzentren)))
        except RuntimeError as exc:
            # Wissen der verfügbare Impfstoffe wird nicht zwingend benötigt,
            # also nur ein Warning:
            self.log.warn(str(exc))

    def __str__(self) -> str:
        return "ImpfterminService"

    def impfzentren_laden(self):
        """
        Lädt alle Impfzentren, gruppiert nach URL.

        Beispiel (verkürzter Output, eigentlich gibt es mehr Impfzentren):
            self.impfzentren_laden(["68163", "69124", "69123"])
            {
                'https://001-iz.impfterminservice.de/': [
                    {
                        'Zentrumsname': 'Maimarkthalle',
                        'PLZ': '68163',
                        'Ort': 'Mannheim',
                        'Bundesland': 'Baden-Württemberg',
                        'URL': 'https://001-iz.impfterminservice.de/',
                        'Adresse': 'Xaver-Fuhr-Straße 113'
                    },
                    {
                        'Zentrumsname': 'Zentrales Impfzentrum Heidelberg - Commissary Patrick-Henry-Village',
                        'PLZ': '69124',
                        'Ort': 'Heidelberg',
                        'Bundesland': 'Baden-Württemberg',
                        'URL': 'https://001-iz.impfterminservice.de/',
                        'Adresse': 'South Gettysburg Avenue 45'
                    }
                ],
                'https://002-iz.impfterminservice.de/': [
                    {
                        'Zentrumsname': 'Gesellschaftshaus Pfaffengrund',
                        'PLZ': '69123',
                        'Ort': 'Heidelberg',
                        'Bundesland': 'Baden-Württemberg',
                        'URL': 'https://002-iz.impfterminservice.de/',
                        'Adresse': 'Schwalbenweg 1/2'
                    }
                ]
            }

        :return: Impfzentren gruppiert nach URL; siehe obiges Beispiel
        """

        location = "https://www.impfterminservice.de/assets/static/impfzentren.json"

        try:
            self.s.cookies.clear()
            res = self.s.get(location, timeout=15)
        except RequestException as exc:
            raise RuntimeError(
                f"Impfzentren können nicht geladen werden: {str(exc)}"
            ) from exc
        if not res.ok:
            raise RuntimeError(
                "Impfzentren können nicht geladen werden: "
                f"{res.status_code} {res.text}")

        # Antwort-JSON in Impfzentren-Liste umwandeln
        verfuegbare_impfzentren = [
            iz
            for bundesland, impfzentren in res.json().items()
            for iz in impfzentren
        ]
        self.log.info(f"{len(verfuegbare_impfzentren)} Impfzentren verfügbar")

        # Gefilterte Impfzentren-Liste nach URL gruppieren
        result = {}
        for iz in verfuegbare_impfzentren:
            url = iz["URL"]
            if url not in result:
                result[url] = []
            result[url].append(iz)
        return result

    def impfstoffe_laden(self, url):
        """
        Lädt die verfügbaren Impstoff-Qualifikationen

        Beispiel:
            self.impfstoffe_laden("https://001-iz.impfterminservice.de/")
            [
                {
                    'qualification': 'L920',
                    'name': 'Comirnaty (BioNTech)',
                    'short': 'BioNTech',
                    'tssname': 'BioNTech',
                    'interval': 40,
                    'age': '16+',
                    'tssage': '16-17'
                },
                {
                    'qualification': 'L921',
                    'name': 'mRNA-1273 (Moderna)',
                    'short': 'Moderna',
                    'tssname': 'Moderna, BioNTech',
                    'interval': 40,
                    'age': '18+',
                    'tssage': '18-59'
                },
                {
                    'qualification': 'L922',
                    'name': 'COVID-1912 (AstraZeneca)',
                    'short': 'AstraZeneca',
                    'tssname': 'Moderna, BioNTech, AstraZeneca',
                    'interval': 40,
                    'age': '60+',
                    'tssage': '60+'
                },
                {
                    'qualification': 'L923',
                    'name': 'COVID-19 Vaccine Janssen (Johnson & Johnson)',
                    'short': 'Johnson&Johnson',
                    'tssname': 'Johnson&Johnson',
                    'age': '60+'
                }
            ]

        :param url: URL des Servers, auf dem die verfügbaren
            Impfstoff-Qualifikationen abgerufen werden sollen

        :return: Liste an Impstoff-Qualifikationen; siehe obiges Beispiel
        """

        location = f"{url}assets/static/its/vaccination-list.json"

        try:
            self.s.cookies.clear()
            res = self.s.get(location, timeout=15)
        except RequestException as exc:
            raise RuntimeError(
                f"Impfstoffe können nicht geladen werden: {str(exc)}")
        if not res.ok:
            raise RuntimeError(
                f"Impfstoffe können nicht geladen werden: {res.status_code} {res.text}")

        qualifikationen = res.json()

        for qualifikation in qualifikationen:
            q_id = qualifikation.get("qualification")
            alter = qualifikation.get("age", "N/A")
            intervall = qualifikation.get("interval", " ?")
            impfstoffe = extrahiere_impfstoffe(qualifikation)
            self.log.info(
                f"[{q_id}] Altersgruppe: {alter} "
                f"(Intervall: {intervall} Tage) --> {str(impfstoffe)}")

        return qualifikationen

    def get_chromedriver_path(self):
        """
        :return: String mit Pfad zur chromedriver-Programmdatei
        """
        chromedriver_from_env = os.getenv("VACCIPY_CHROMEDRIVER")
        if chromedriver_from_env:
            return chromedriver_from_env
        if check_webdriver():
            return webdriver_executable()

        # Chromedriver anhand des OS auswählen
        if 'linux' in self.operating_system:
            if "64" in platform.architecture() or sys.maxsize > 2 ** 32:
                return os.path.join(self.PATH, "tools/chromedriver/chromedriver-linux-64")
            else:
                return os.path.join(self.PATH, "tools/chromedriver/chromedriver-linux-32")
        elif 'windows' in self.operating_system:
            return os.path.join(self.PATH, "tools/chromedriver/chromedriver-windows.exe")
        elif 'darwin' in self.operating_system:
            if "arm" in platform.processor().lower():
                return os.path.join(self.PATH, "tools/chromedriver/chromedriver-mac-m1")
            else:
                return os.path.join(self.PATH, "tools/chromedriver/chromedriver-mac-intel")
        else:
            raise ValueError(f"Nicht unterstütztes Betriebssystem {self.operating_system}")

    def get_chromedriver(self, headless):
        chrome_options = Options()

        # deaktiviere Selenium Logging
        chrome_options.add_argument('disable-infobars')
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])

        # Zur Behebung von "DevToolsActivePort file doesn't exist"
        # chrome_options.add_argument("-no-sandbox");
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--remote-debugging-port=9222")

        # Chrome head is only required for the backup booking process.
        # User-Agent is required for headless, because otherwise the server lets us hang.
        chrome_options.add_argument("user-agent=Mozilla/5.0")

        chromebin_from_env = os.getenv("VACCIPY_CHROME_BIN")
        if chromebin_from_env:
            chrome_options.binary_location = os.getenv("VACCIPY_CHROME_BIN")
        elif check_chromium():
            chrome_options.binary_location = str(chromium_executable())

        chrome_options.headless = headless

        return Chrome(self.get_chromedriver_path(), options=chrome_options)

    def driver_enter_code(self, driver, impfzentrum, code):
        """
        TODO xpath code auslagern
        """

        self.log.info("Vermittlungscode eintragen und Mausbewegung / Klicks simulieren. "
                      "Dieser Vorgang kann einige Sekunden dauern.")

        location = f"{impfzentrum['URL']}impftermine/service?plz={impfzentrum['PLZ']}"
        driver.get(location)  # Kann WebDriverException nach außen werfen.

        # Queue Bypass
        while True:
            queue_cookie = driver.get_cookie("akavpwr_User_allowed")

            if not queue_cookie \
                    or "Virtueller Warteraum" not in driver.page_source:
                break

            self.log.info("Im Warteraum, Seite neu laden")
            queue_cookie["name"] = "akavpau_User_allowed"
            driver.add_cookie(queue_cookie)

            # Seite neu laden
            time.sleep(5)
            driver.get(location)
            driver.refresh()


        # random start position
        current_mouse_positon = (randint(1, driver.get_window_size()["width"]-1),
                                 randint(1, driver.get_window_size()["height"]-1))
        # Simulation der Mausbewegung
        current_mouse_positon = move_mouse_to_coordinates(self.log, 0, 0, current_mouse_positon[0],
                                                          current_mouse_positon[1], driver)

        # Klick auf "Auswahl bestätigen" im Cookies-Banner
        button_xpath = "//a[contains(@class,'cookies-info-close')][1]"
        button = WebDriverWait(driver, 1).until(
            EC.element_to_be_clickable((By.XPATH, button_xpath)))
        action = ActionChains(driver)

        # Simulation der Mausbewegung
        element = driver.find_element_by_xpath(button_xpath)
        current_mouse_positon = move_mouse_to_coordinates(self.log, current_mouse_positon[0],
                                                          current_mouse_positon[1],
                                                          element.location['x'],
                                                          element.location['y'], driver)

        action.click(button).perform()
        
        
        # Klick auf "Vermittlungscode bereits vorhanden"
        button_xpath = "//input[@name=\"vaccination-approval-checked\"]/.."
        button = WebDriverWait(driver, 1).until(
            EC.element_to_be_clickable((By.XPATH, button_xpath)))
        action = ActionChains(driver)

        # Simulation der Mausbewegung
        element = driver.find_element_by_xpath(button_xpath)
        current_mouse_positon = move_mouse_to_coordinates(self.log, current_mouse_positon[0],
                                                          current_mouse_positon[1],
                                                          element.location['x'],
                                                          element.location['y'], driver)

        action.click(button).perform()

        # Auswahl des ersten Code-Input-Feldes
        input_xpath = "//input[@name=\"ets-input-code-0\"]"
        input_field = WebDriverWait(driver, 1).until(
            EC.element_to_be_clickable((By.XPATH, input_xpath)))
        action = ActionChains(driver)

        # Simulation der Mausbewegung
        element = driver.find_element_by_xpath(input_xpath)
        current_mouse_positon = move_mouse_to_coordinates(self.log, current_mouse_positon[0],
                                                          current_mouse_positon[1],
                                                          element.location['x'],
                                                          element.location['y'], driver)

        action.click(input_field).perform()

        # Code etwas realistischer eingeben
        # Zu schnelle Eingabe erzeugt ebenfalls manchmal "Ein unerwarteter Fehler ist aufgetreten"        
        for index, subcode in enumerate(code.split("-")):        
        
            if index == 0:
                # Auswahl des ersten Code-Input-Feldes
                input_xpath = "//input[@name=\"ets-input-code-0\"]"
            elif index == 1:
                # Auswahl des zweiten Code-Input-Feldes
                input_xpath = "//input[@name=\"ets-input-code-1\"]"
            elif index == 2:
                # Auswahl des dritten Code-Input-Feldes
                input_xpath = "//input[@name=\"ets-input-code-2\"]"

            # Input Feld auswählen
            input_field = WebDriverWait(driver, 1).until(EC.element_to_be_clickable((By.XPATH, input_xpath)))
            action = ActionChains(driver)
            action.move_to_element(input_field).click().perform()                
        
            # Chars einzeln eingeben mit kleiner Pause
            for char in subcode:                      
                input_field.send_keys(char)
                time.sleep(randint(500,1000)/1000)

        # Klick auf "Termin suchen"
        button_xpath = "//app-corona-vaccination-yes//button[@type=\"submit\"]"
        button = WebDriverWait(driver, 1).until(
            EC.element_to_be_clickable((By.XPATH, button_xpath)))
        action = ActionChains(driver)

        element = driver.find_element_by_xpath(button_xpath)
        # Simulation der Mausbewegung
        _ = move_mouse_to_coordinates(self.log, current_mouse_positon[0], current_mouse_positon[1],
                                      element.location['x'], element.location['y'], driver)
        action.click(button).perform()

        # Zweiter Klick-Versuch, falls Meldung "Es ist ein unerwarteter Fehler aufgetreten" erscheint
        answer_xpath = "//app-corona-vaccination-yes//span[@class=\"text-pre-wrap\"]"
        try:
            time.sleep(0.5)
            element = driver.find_element_by_xpath(answer_xpath)
            if element.text == "Es ist ein unerwarteter Fehler aufgetreten":
                action.click(button).perform()
        except Exception as e:
            pass

        time.sleep(1.5)
        

    def driver_get_cookies(self, driver, url, manual):
        # Erstelle zufälligen Vermittlungscode für die Cookie-Generierung
        legal_chars = string.ascii_uppercase + string.digits
        subcode1 = f"{choices(legal_chars)[0]}{choices(legal_chars)[0]}{choices(legal_chars)[0]}{choices(legal_chars)[0]}"
        subcode2 = f"{choices(legal_chars)[0]}{choices(legal_chars)[0]}{choices(legal_chars)[0]}{choices(legal_chars)[0]}"
        subcode3 = f"{choices(legal_chars)[0]}{choices(legal_chars)[0]}{choices(legal_chars)[0]}{choices(legal_chars)[0]}"
        random_code = f"{subcode1}-{subcode2}-{subcode3}"

        # Kann WebDriverException nach außen werfen:
        self.driver_enter_code(
            driver, choice(self.impfzentren[url]), random_code)
        if manual:
            self.log.warn(
                "Du hast jetzt 30 Sekunden Zeit möglichst viele Elemente im Chrome Fenster anzuklicken. Das Fenster schließt sich automatisch.")
            time.sleep(30)

        required = ["bm_sz", "akavpau_User_allowed"]
        optional = ["bm_sv", "bm_mi", "ak_bmsc", "_abck"]

        cookies = {
            c["name"]: c["value"]
            for c in driver.get_cookies()
            if c["name"] in required or c["name"] in optional
        }

        # prüfen, ob Cookies gesetzt wurden und in Session übernehmen
        for name in required:
            if name not in cookies:
                raise RuntimeError(f"{name} fehlt!")

        self.log.info(f"Browser-Cookie generiert: *{cookies['bm_sz'][-6:]}")
        return cookies

    def driver_termin_buchen(self, driver, reservierung):
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        filepath = os.path.join(self.PATH, "tools", "log")

        try:
            self.driver_enter_code(
                driver, reservierung["impfzentrum"], reservierung["code"])
        except BaseException as exc:
            self.log.error(f"Vermittlungscode kann nicht eingegeben werden: {str(exc)}")
            pass

        try:
            # Klick auf "Termin suchen"
            button_xpath = "//button[@data-target=\"#itsSearchAppointmentsModal\"]"
            button = WebDriverWait(driver, 1).until(
                EC.element_to_be_clickable((By.XPATH, button_xpath)))
            action = ActionChains(driver)
            action.move_to_element(button).click().perform()
        except:
            self.log.error("Termine können nicht gesucht werden")
            try:
                driver.save_screenshot(os.path.join(filepath, "errorterminsuche" + timestamp + ".png"))
            except:
                self.log.error("Screenshot konnte nicht gespeichert werden")
            pass

        # Termin auswählen
        try:
            time.sleep(3)
            button_xpath = '//*[@id="itsSearchAppointmentsModal"]/div/div/div[2]/div/div/form/div[1]/div[2]/label/div[2]/div'
            button = WebDriverWait(driver, 1).until(
                EC.element_to_be_clickable((By.XPATH, button_xpath)))
            action = ActionChains(driver)
            action.move_to_element(button).click().perform()
            time.sleep(.5)
        except:
            self.log.error("Termine können nicht ausgewählt werden")
            try:
                with open(os.path.join(filepath, "errorterminauswahl" + timestamp + ".html"), 'w',
                          encoding='utf-8') as file:
                    file.write(str(driver.page_source))
                driver.save_screenshot(os.path.join(filepath, "errorterminauswahl" + timestamp + ".png"))
            except:
                self.log.error("HTML und Screenshot konnten nicht gespeichert werden")
            pass

        # Klick Button "AUSWÄHLEN"
        try:
            button_xpath = '//*[@id="itsSearchAppointmentsModal"]//button[@type="submit"]'
            button = WebDriverWait(driver, 1).until(
                EC.element_to_be_clickable((By.XPATH, button_xpath)))
            action = ActionChains(driver)
            action.move_to_element(button).click().perform()
            time.sleep(.5)
        except:
            self.log.error("Termine können nicht ausgewählt werden (Button)")
            pass

        # Klick Daten erfassen
        try:
            button_xpath = '/html/body/app-root/div/app-page-its-search/div/div/div[2]/div/div/div[5]/div/div[2]/div[2]/div[2]/button'
            button = WebDriverWait(driver, 1).until(
                EC.element_to_be_clickable((By.XPATH, button_xpath)))
            action = ActionChains(driver)
            action.move_to_element(button).click().perform()
            time.sleep(.5)
        except:
            self.log.error("1. Daten können nicht erfasst werden")
            pass
        try:
            # Klick Anrede
            arrAnreden = ["Herr", "Frau", "Kind", "Divers"]
            if self.kontakt['anrede'] in arrAnreden:
                button_xpath = '//*[@id="itsSearchContactModal"]//app-booking-contact-form//div[contains(@class,"ets-radio-wrapper")]/label[@class="ets-radio-control"]/span[contains(text(),"' + \
                               self.kontakt['anrede'] + '")]'
            else:
                button_xpath = '//*[@id="itsSearchContactModal"]//app-booking-contact-form//div[contains(@class,"ets-radio-wrapper")]/label[@class="ets-radio-control"]/span[contains(text(),"Divers")]'

            button = WebDriverWait(driver, 1).until(
                EC.element_to_be_clickable((By.XPATH, button_xpath)))
            action = ActionChains(driver)
            action.move_to_element(button).click().perform()

            # Input Vorname
            input_xpath = '//*[@id="itsSearchContactModal"]//app-booking-contact-form//input[@formcontrolname="firstname"]'
            input_field = WebDriverWait(driver, 1).until(
                EC.element_to_be_clickable((By.XPATH, input_xpath)))
            action.move_to_element(input_field).click().perform()
            input_field.send_keys(self.kontakt['vorname'])

            # Input Nachname
            input_field = driver.find_element_by_xpath(
                '//*[@id="itsSearchContactModal"]//app-booking-contact-form//input[@formcontrolname="lastname"]')
            input_field.send_keys(self.kontakt['nachname'])

            # Input PLZ
            input_field = driver.find_element_by_xpath(
                '//*[@id="itsSearchContactModal"]//app-booking-contact-form//input[@formcontrolname="zip"]')
            input_field.send_keys(self.kontakt['plz'])

            # Input City
            input_field = driver.find_element_by_xpath(
                '//*[@id="itsSearchContactModal"]//app-booking-contact-form//input[@formcontrolname="city"]')
            input_field.send_keys(self.kontakt['ort'])

            # Input Strasse
            input_field = driver.find_element_by_xpath(
                '//*[@id="itsSearchContactModal"]//app-booking-contact-form//input[@formcontrolname="street"]')
            input_field.send_keys(self.kontakt['strasse'])

            # Input Hasunummer
            input_field = driver.find_element_by_xpath(
                '//*[@id="itsSearchContactModal"]//app-booking-contact-form//input[@formcontrolname="housenumber"]')
            input_field.send_keys(self.kontakt['hausnummer'])

            # Input Telefonnummer
            input_field = driver.find_element_by_xpath(
                '//*[@id="itsSearchContactModal"]//app-booking-contact-form//input[@formcontrolname="phone"]')
            input_field.send_keys(self.kontakt['phone'].replace("+49", ""))

            # Input Mail
            input_field = driver.find_element_by_xpath(
                '//*[@id="itsSearchContactModal"]//app-booking-contact-form//input[@formcontrolname="notificationReceiver"]')
            input_field.send_keys(self.kontakt['notificationReceiver'])
        except:
            self.log.error("Kontaktdaten können nicht eingegeben werden")
            try:
                driver.save_screenshot(os.path.join(filepath, "errordateneingeben" + timestamp + ".png"))
            except:
                self.log.error("Screenshot konnte nicht gespeichert werden")
            pass

        # Klick Button "ÜBERNEHMEN"
        try:
            button_xpath = '//*[@id="itsSearchContactModal"]//button[@type="submit"]'
            button = WebDriverWait(driver, 1).until(
                EC.element_to_be_clickable((By.XPATH, button_xpath)))
            action = ActionChains(driver)
            action.move_to_element(button).click().perform()
            time.sleep(.7)
        except:
            self.log.error("Button ÜBERNEHMEN kann nicht gedrückt werden")
            pass

        # Termin buchen
        try:
            button_xpath = '/html/body/app-root/div/app-page-its-search/div/div/div[2]/div/div/div[5]/div/div[3]/div[2]/div[2]/button'
            button = WebDriverWait(driver, 1).until(
                EC.element_to_be_clickable((By.XPATH, button_xpath)))
            action = ActionChains(driver)
            action.move_to_element(button).click().perform()
        except:
            self.log.error("Button Termin buchen kann nicht gedrückt werden")
            pass
        time.sleep(3)

        if "Ihr Termin am" not in str(driver.page_source):
            raise BookingError()

    def get_cookies(self, url, manual):
        """
        Cookies der Session erneuern, wenn sie abgelaufen sind.
        :return:
        """

        self.log.info("Browser-Cookies generieren")
        driver = self.get_chromedriver(headless=False)
        try:
            return self.driver_get_cookies(driver, url, manual)
        except WebDriverException as exc:
            raise RuntimeError(
                f"Cookies können nicht generiert werden: {str(exc)}") from exc
        finally:
            driver.quit()

    def selenium_termin_buchen(self, reservierung):
        """
        Backup Prozess:
        Wenn die Terminbuchung mit dem Bot nicht klappt, wird das
        Browserfenster geöffnet und die Buchung im Browser beendet
        :return:
        """

        self.log.info("Termin über Selenium buchen")
        driver = self.get_chromedriver(headless=False)
        try:
            self.driver_termin_buchen(driver, reservierung)
        except BookingError:
            url = reservierung["impfzentrum"]["URL"]
            plz_impfzentrum = reservierung["impfzentrum"]["PLZ"]
            code = reservierung["code"]
            self.log.error("Automatisierte Terminbuchung fehlgeschlagen")
            self.log.error("Termin manuell im Fenster oder im Browser buchen.")
            self.log.error(
                f"Link: {url}impftermine/suche/{code}/{plz_impfzentrum}")
            time.sleep(10 * 60)  # Sleep, um Fenster offen zu halten
            raise  # Ursprüngliche Exception reraisen
        finally:
            driver.quit()

    def login(self, plz_impfzentrum, code, cookies):
        """
        Einloggen mittels Vermittlungscode, um qualifizierte Impfstoffe zu erhalten.

        Beispiel:
            self.login("69123", "XXXX-XXXX-XXXX", cookies)
            {
                'kv': '52',
                'qualifikationen': ['L921'],
                'verknuepft': True
            }

        :return: Deserialisierte JSON-Antwort vom Server; siehe obiges Beispiel
        """

        url = self.impfzentrum_in_plz(plz_impfzentrum)["URL"]
        location = f"{url}rest/login?plz={plz_impfzentrum}"

        try:
            self.s.cookies.clear()
            res = self.s.get(
                location,
                headers=get_headers(code),
                cookies=cookies,
                timeout=15)
        except RequestException as exc:
            raise RuntimeError(f"Login mit Code fehlgeschlagen: {str(exc)}")
        if res.status_code == 401:
            raise UnmatchingCodeError(
                f"Login in {plz_impfzentrum} nicht erfolgreich: "
                f"Vermittlungscode nicht gültig für diese PLZ")
        if not res.ok:
            raise RuntimeError(
                f"Login mit Code fehlgeschlagen: {res.status_code} {res.text}")

        if "Virtueller Warteraum" in res.text:
            raise RuntimeError("Login mit Code fehlgeschlagen: Warteraum")

        try:
            return res.json()
        except JSONDecodeError as exc:
            raise RuntimeError(
                "Login mit Code fehlgeschlagen: "
                f"JSONDecodeError: {str(exc)}") from exc

    def reservierung_finden(self, zeitrahmen: dict, plz: str):
        url = self.impfzentrum_in_plz(plz)["URL"]
        codepoints = self.codepoints[url]
        if not codepoints:
            self.log.warn(f"Kein gültiger Vermittlungscode vorhanden für PLZ {plz}")
            return None

        now = datetime.now()
        usable_codepoints = [
            cp for cp in codepoints if cp["next_use"] <= now
        ]
        if not usable_codepoints:
            return None

        codepoint = usable_codepoints[0]
        code = codepoint["code"]

        try:
            reservierung = self.reservierung_finden_mit_code(
                zeitrahmen, plz, code)
            if reservierung is not None:
                return reservierung
        except UnmatchingCodeError:
            codepoints.remove(codepoint)
            self.log.info(f"Überspringe Code {code[:4]}* für {plz}")
        except TimeframeMissed:
            # Es wurden Termine gefunden und alle gefundenen Termine
            # abgelehnt.
            # Der verwendete Code soll frühestens in 10 Minuten erneut
            # verwendet werden, da sonst immer wieder die gleichen Termine
            # gefunden und abgelehnt werden.
            self.log.info(f"Pausiere Code {code[:4]}* für 10 Minuten")
            codepoint["next_use"] = now + timedelta(minutes=10)
        except RuntimeError as exc:
            self.log.error(str(exc))

        return None

    def reservierung_finden_mit_code(
            self, zeitrahmen: dict, plz: str, code: str):
        """
        Es wird überprüft, ob im Impfzentrum in der gegebenen PLZ ein oder
        mehrere Terminpaare (oder Einzeltermine) verfügbar sind, die dem
        Zeitrahmen entsprechen.
        Falls ja, wird ein zufälliger davon ausgewählt und zusammen mit
        Impfzentrum und Code zurückgegeben.
        Zum Format der Rückgabe, siehe Beispiel.

        Beispiel:
            zeitrahmen = {
                'einhalten_bei': '1',
                'von_datum': '29.03.2021'
            }

            self.reservierung_finden_mit_code(
                zeitrahmen, '68163', 'XXXX-XXXX-XXXX')
            {
                'code': 'XXXX-XXXX-XXXX',
                'impfzentrum': {
                    'Zentrumsname': 'Maimarkthalle',
                    'PLZ': '68163',
                    'Ort': 'Mannheim',
                    'URL': 'https://001-iz.impfterminservice.de/',
                },
                'terminpaar': [
                    {
                        'slotId': 'slot-56817da7-3f46-4f97-9868-30a6ddabcdef',
                        'begin': 1616999901000,
                        'bsnr': '005221080'
                    },
                    {
                        'slotId': 'slot-d29f5c22-384c-4928-922a-30a6ddabcdef',
                        'begin': 1623999901000,
                        'bsnr': '005221080'
                    }
                ]
            }

        :param zeitrahmen: Zeitrahmen, dem das Terminpaar entsprechen muss
        :param plz: PLZ des Impfzentrums, in dem geprüft wird
        :param code: Vermittlungscode, für den eventuell gefundene Terminpaare
            reserviert werden.
        :return: Reservierungs-Objekt (siehe obiges Beispiel), falls ein
            passender Termin gefunden wurde, sonst None.
        :raise RuntimeError: Termine können nicht geladen werden
        """

        impfzentrum = self.impfzentrum_in_plz(plz)
        url = impfzentrum["URL"]
        location = f"{url}rest/suche/impfterminsuche?plz={plz}"

        try:
            self.s.cookies.clear()
            res = self.s.get(location, headers=get_headers(code), timeout=5)
        except RequestException as exc:
            raise RuntimeError(
                f"Termine in {plz} können nicht geladen werden: {str(exc)}")
        if res.status_code == 401:
            raise UnmatchingCodeError(
                f"Termine in {plz} können nicht geladen werden: "
                f"Vermittlungscode nicht gültig für diese PLZ")
        if not res.ok:
            raise RuntimeError(
                f"Termine in {plz} können nicht geladen werden: "
                f"{res.status_code} {res.text}")

        if 'Virtueller Warteraum des Impfterminservice' in res.text:
            return None

        try:
            terminpaare = res.json().get("termine")
        except JSONDecodeError as exc:
            raise RuntimeError(
                f"Termine in {plz} können nicht geladen werden: "
                f"JSONDecodeError: {str(exc)}")
        if not terminpaare:
            self.log.info(f"Keine Termine verfügbar in {plz}")
            return None

        if ENABLE_BEEPY:
            beepy.beep('coin')
        else:
            print("\a")

        terminpaare_angenommen = [
            tp for tp in terminpaare
            if terminpaar_im_zeitrahmen(tp, zeitrahmen)
        ]
        terminpaare_abgelehnt = [
            tp for tp in terminpaare
            if tp not in terminpaare_angenommen
        ]

        zentrumsname = impfzentrum.get('Zentrumsname').strip()
        ort = impfzentrum.get('Ort')

        for tp_abgelehnt in terminpaare_abgelehnt:
            self.log.warn(
                "Termin gefunden - jedoch nicht im entsprechenden Zeitraum:")
            self.log.info('-' * 50)
            self.log.warn(f"'{zentrumsname}' in {plz} {ort}")
            for num, termin in enumerate(tp_abgelehnt, 1):
                ts = datetime.fromtimestamp(termin["begin"] / 1000).strftime(
                    '%d.%m.%Y um %H:%M Uhr')
                self.log.warn(f"{num}. Termin: {ts}")
            self.log.warn(f"Link: {url}impftermine/suche/{code}/{plz}")
            self.log.info('-' * 50)

        if not terminpaare_angenommen:
            raise TimeframeMissed()

        # Auswahl des erstbesten Terminpaares
        tp_angenommen = choice(terminpaare_angenommen)
        self.log.success(f"Termin gefunden!")
        self.log.success(f"'{zentrumsname}' in {plz} {ort}")
        msg = f"'{zentrumsname}' in {plz} {ort}\n"
        for num, termin in enumerate(tp_angenommen, 1):
            ts = datetime.fromtimestamp(termin["begin"] / 1000).strftime(
                '%d.%m.%Y um %H:%M Uhr')
            self.log.success(f"{num}. Termin: {ts}")
            msg += f"{num}. Termin: {ts}\n"
        self.log.success(f"Link: {url}impftermine/suche/{code}/{plz}")
        msg += f"Link: {url}impftermine/suche/{code}/{plz}"
        self.notify(title="Termin gefunden:", msg=msg)

        # Reservierungs-Objekt besteht aus Terminpaar und Impfzentrum
        return {
            "code": code,
            "impfzentrum": impfzentrum,
            "terminpaar": tp_angenommen,
        }

    def termin_buchen(self, reservierung):
        """Termin wird gebucht für die Kontaktdaten, die beim Starten des
        Programms eingetragen oder aus der JSON-Datei importiert wurden.

        :return: bool
        """

        # Daten für Impftermin sammeln
        data = {
            "plz": reservierung["impfzentrum"]["PLZ"],
            "slots": [termin.get("slotId") for termin in reservierung["terminpaar"]],
            "qualifikationen": [],
            "contact": self.kontakt
        }

        url = reservierung["impfzentrum"]["URL"]
        location = f"{url}rest/buchung"
        headers = get_headers(reservierung["code"])

        try:
            # get_cookies kann RuntimeError werfen
            cookies = self.get_cookies(url, manual=False)
            try:
                self.s.cookies.clear()
                res = self.s.post(
                    location,
                    json=data,
                    headers=headers,
                    cookies=cookies,
                    timeout=15)
            except RequestException as exc:
                raise RuntimeError(
                    f"Termin konnte nicht gebucht werden: {str(exc)}")
            if res.status_code == 400:
                # Example response data with status 400:
                # {"errors":[{"code":"BU004","text":"Slot nicht frei"}]}
                # {"errors":[{"code":"WP009","text":"Buchung bereits durchgefuehrt"}]}
                # {"errors":[{"code":"WP011","text":"Der ausgewählte Termin ist nicht mehr verfügbar. Bitte wählen Sie einen anderen Termin aus"}]}
                raise AppointmentGone()
            if res.status_code != 201:
                raise RuntimeError(
                    f"Termin konnte nicht gebucht werden: {res.status_code} {res.text}")
        except RuntimeError as exc:
            self.log.error(str(exc))
            self.log.info("Starte zweiten Versuch über Selenium ...")
            self.selenium_termin_buchen(reservierung)

    def code_anfordern(self, mail, telefonnummer,
                       plz_impfzentrum, geburtsdatum):
        """
        SMS-Code beim Impfterminservice anfordern.

        :param mail: Mail für Empfang des Codes
        :param telefonnummer: Telefonnummer für SMS-Code, inkl. Präfix +49
        :param plz_impfzentrum: PLZ des Impfzentrums, für das ein Code erstellt werden soll
        :param geburtsdatum: Geburtsdatum der Person
        :return:
        """

        url = self.impfzentrum_in_plz(plz_impfzentrum)["URL"]
        location = f"{url}rest/smspin/anforderung"

        data = {
            "plz": plz_impfzentrum,
            "email": mail,
            "phone": telefonnummer,
            "birthday": "{}-{:02d}-{:02d}".format(*reversed([int(d) for d
                                                             in geburtsdatum.split(".")])),
            "einzeltermin": False
        }

        cookies = None
        manual = False
        while True:
            if cookies is None:
                try:
                    cookies = self.get_cookies(url, manual=manual)
                except RuntimeError as exc:
                    self.log.error(str(exc))
                    continue  # Neuer Versuch in nächster Iteration

            try:
                self.s.cookies.clear()
                res = self.s.post(
                    location,
                    json=data,
                    cookies=cookies,
                    timeout=15)
            except RequestException as exc:
                self.log.error(f"Vermittlungscode kann nicht angefragt werden: {str(exc)}")
                self.log.info("Erneuter Versuch in 30 Sekunden")
                time.sleep(30)
                continue  # Neuer Versuch in nächster Iteration

            if res.status_code == 429:
                self.log.error("Anfrage wurde von der Botprotection geblockt")
                self.log.error(
                    "Die Cookies müssen manuell im Browser generiert werden")
                cookies = None
                manual = True
                continue  # Neuer Versuch in nächster Iteration

            if res.status_code == 400 and res.text == '{"error":"Anfragelimit erreicht."}':
                raise RuntimeError("Anfragelimit erreicht")

            if not res.ok:
                self.log.error(
                    "Code kann nicht angefragt werden: "
                    f"{res.status_code} {res.text}")
                self.log.info("Erneuter Versuch in 30 Sekunden")
                time.sleep(30)
                continue  # Neuer Versuch in nächster Iteration

            try:
                token = res.json().get("token")
            except JSONDecodeError as exc:
                raise RuntimeError(f"JSONDecodeError: {str(exc)}") from exc

            return (token, cookies)

    def selenium_code_anfordern(self, mail, telefonnummer,
                       plz_impfzentrum, geburtsdatum):
        """
        SMS-Code beim Impfterminservice via Selenium anfordern.

        :param mail: Mail für Empfang des Codes
        :param telefonnummer: Telefonnummer für SMS-Code, inkl. Präfix +49
        :param plz_impfzentrum: PLZ des Impfzentrums, für das ein Code erstellt werden soll
        :param geburtsdatum: Geburtsdatum der Person
        :return:
        """

        url = self.impfzentrum_in_plz(plz_impfzentrum)["URL"]
        location = f"{url}rest/smspin/anforderung"

        data = {
            "plz": plz_impfzentrum,
            "email": mail,
            "phone": telefonnummer,
            "birthday": "{}-{:02d}-{:02d}".format(*reversed([int(d) for d
                                                             in geburtsdatum.split(".")])),
            "einzeltermin": False
        }

        # Wire Selenium driver um request im webdriver auszulesen
        driver = selenium_wire.Chrome(self.get_chromedriver_path())

        while True:

            driver.get(f"{url}impftermine/service?plz={plz_impfzentrum}")
            self.log.info("Generierung eines Vermittlungscodes via Selenium gestartet.")

            # Queue Bypass
            while True:
                queue_cookie = driver.get_cookie("akavpwr_User_allowed")

                if not queue_cookie \
                        or "Virtueller Warteraum" not in driver.page_source:
                    break

                self.log.info("Im Warteraum, Seite neu laden")
                queue_cookie["name"] = "akavpau_User_allowed"
                driver.add_cookie(queue_cookie)

            # Seite des Impzentrums laden
            time.sleep(5)
            driver.get(f"{url}impftermine/service?plz={plz_impfzentrum}")
            driver.refresh()


            # ets-session-its-cv-quick-check im SessionStorage setzen um verfügbare Termine zu simulieren
            ets_session_its_cv_quick_check = '{"birthdate":"'+ data["birthday"] +'","slotsAvailable":{"pair":true,"single":false}}'
            driver.execute_script('window.sessionStorage.setItem("ets-session-its-cv-quick-check",\''+ ets_session_its_cv_quick_check +'\');')
            self.log.info("\"ets-session-its-cv-quick-check\" Key:Value zum sessionStorage hinzugefügt.")

            # Durch ets-session-its-cv-quick-check im SessionStorage kann direkt der Check aufgerufen werden
            driver.get(f"{url}impftermine/check")
            self.log.info("Überprüfung der Impfberechtigung übersprungen / Vorhandene Termine simuliert und impftermine/check geladen.")

            time.sleep(1)

            # Anpassen der HTML elemente im Browser um Nutzer aktuellen Status anzuzeigen
            check_h1_xpath = "//app-its-check-success//h1"
            check_h1 = driver.find_element_by_xpath(check_h1_xpath)
            driver.execute_script("arguments[0].setAttribute('style','color: #FF0000;font-weight: bold; font-size: 35px;')", check_h1)
            driver.execute_script(f"arguments[0].innerText='Vaccipy! - Bitte nichts eingeben oder anklicken.'", check_h1)
            check_p_xpath = "//app-its-check-success//p"
            check_p = driver.find_element_by_xpath(check_p_xpath)
            driver.execute_script("arguments[0].setAttribute('style','font-weight: bold; font-size: 25px;')", check_p)
            
            # random start position
            current_mouse_positon = (randint(1,driver.get_window_size()["width"]-1),
                                 randint(1,driver.get_window_size()["height"]-1))

            # Simulation der Mausbewegung
            driver.execute_script(f"arguments[0].innerText='Status: Maussimulation nach x:{current_mouse_positon[0]}, y:{current_mouse_positon[1]}'", check_p)
            current_mouse_positon = move_mouse_to_coordinates(self.log, 0, 0, current_mouse_positon[0],
                                                                current_mouse_positon[1], driver)
            

            # Klick auf "Auswahl bestätigen" im Cookies-Banner
            button_xpath = "//a[contains(@class,'cookies-info-close')][1]"
            button = WebDriverWait(driver, 1).until(
                EC.element_to_be_clickable((By.XPATH, button_xpath)))
            action = ActionChains(driver)

            # Simulation der Mausbewegung
            element = driver.find_element_by_xpath(button_xpath)
            driver.execute_script(f"arguments[0].innerText='Status: Maussimulation nach x: {element.location['x']}, y: {element.location['y']}'", check_p)
            current_mouse_positon = move_mouse_to_coordinates(self.log, current_mouse_positon[0],
                                                                current_mouse_positon[1],
                                                                element.location['x'],
                                                                element.location['y'], driver)
            driver.execute_script(f"arguments[0].innerText='Status: Cookie-Banner Anklicken'", check_p)
            action.click(button).perform()
            time.sleep(0.5)

            # Eingabe Mail
            input_xpath = "//input[@formcontrolname=\"email\"]"
            # Input Feld auswählen
            input_field = WebDriverWait(driver, 1).until(EC.element_to_be_clickable((By.XPATH, input_xpath)))
            action = ActionChains(driver)

            # Simulation der Mausbewegung
            element = driver.find_element_by_xpath(input_xpath)
            driver.execute_script(f"arguments[0].innerText='Status: Maussimulation nach x: {element.location['x']}, y: {element.location['y']}'", check_p)
            current_mouse_positon = move_mouse_to_coordinates(self.log, current_mouse_positon[0],
                                                                current_mouse_positon[1],
                                                                element.location['x'],
                                                                element.location['y'], driver)
            action.move_to_element(input_field).click().perform()

            # Chars einzeln eingeben mit kleiner Pause
            driver.execute_script(f"arguments[0].innerText='Status: E-Mail wird eingegeben'", check_p)
            for char in data['email']:
                input_field.send_keys(char)
                time.sleep(randint(500,1000)/1000)

            self.log.info("E-Mail Adresse eingegeben.")
            time.sleep(0.5)

            # Eingabe Phone
            input_xpath = "//input[@formcontrolname=\"phone\"]"
            # Input Feld auswählen
            input_field = WebDriverWait(driver, 1).until(EC.element_to_be_clickable((By.XPATH, input_xpath)))
            action = ActionChains(driver)

            # Simulation der Mausbewegung
            element = driver.find_element_by_xpath(input_xpath)
            driver.execute_script(f"arguments[0].innerText='Status: Maussimulation nach x: {element.location['x']}, y: {element.location['y']}'", check_p)
            current_mouse_positon = move_mouse_to_coordinates(self.log, current_mouse_positon[0],
                                                                current_mouse_positon[1],
                                                                element.location['x'],
                                                                element.location['y'], driver)
            action.move_to_element(input_field).click().perform()

            # Chars einzeln eingeben mit kleiner Pause
            driver.execute_script(f"arguments[0].innerText='Status: Phone wird eingegeben'", check_p)
            for char in data['phone'][3:]:
                input_field.send_keys(char)
                time.sleep(randint(500,1000)/1000)

            self.log.info("Telefonnummer eingegeben.")
            time.sleep(0.5)

            # Anfrage absenden
            button_xpath = "//app-its-check-success//button[@type=\"submit\"]"
            button = WebDriverWait(driver, 1).until(EC.element_to_be_clickable((By.XPATH, button_xpath)))
            action = ActionChains(driver)

            # Simulation der Mausbewegung
            element = driver.find_element_by_xpath(button_xpath)
            driver.execute_script(f"arguments[0].innerText='Status: Maussimulation nach x: {element.location['x']}, y: {element.location['y']}'", check_p)
            current_mouse_positon = move_mouse_to_coordinates(self.log, current_mouse_positon[0],
                                                                current_mouse_positon[1],
                                                                element.location['x'],
                                                                element.location['y'], driver)
            driver.execute_script(f"arguments[0].innerText='Status: Versuche Anfrage abzuschicken'", check_p)
            action.move_to_element(button).click().perform()

            # Zweiter Klick-Versuch, falls Meldung "Es ist ein unerwarteter Fehler aufgetreten" erscheint
            # Falls eine andere Meldung aufgetrteten ist -> Abbruch
            try:
                answer_xpath = "//app-its-check-success//span[@class=\"text-pre-wrap\"]"
                time.sleep(0.5)
                element = driver.find_element_by_xpath(answer_xpath)
            except Exception as e:
                element = None

            if element:
                if element.text == "Es ist ein unerwarteter Fehler aufgetreten":
                    driver.execute_script(f"arguments[0].innerText='Status: Zweiter Versuch Anfrage abzuschicken'", check_p)
                    action.move_to_element(button).click().perform()
                elif element.text == "Anfragelimit erreicht.":
                    driver.close()
                    raise RuntimeError("Anfragelimit erreicht")
                elif element.text == "Geburtsdatum ungueltig oder in der Zukunft":
                    driver.close()
                    raise RuntimeError("Geburtsdatum ungueltig oder in der Zukunft")

            time.sleep(2)

            # Prüfen ob SMS Verifizierung geladen wurde falls nicht Abbruch
            sms_verifizierung_h1_xpath = "//app-page-its-check-result//h1"
            sms_verifizierung_h1 = driver.find_element_by_xpath(sms_verifizierung_h1_xpath)
            if sms_verifizierung_h1.text != "SMS Verifizierung":
                driver.close()
                raise RuntimeError("Vermittlungscode kann derzeit nicht angefragt werden. Versuchen Sie es später erneut.")

            # Ab jetzt befinden wir uns auf der SMS Verifizierung Seite
            location = f"{url}rest/smspin/verifikation"
            self.log.info("SMS-Anfrage an Server versandt.")
            self.log.info("Bitte SMS-Code innerhalb der nächsten 60 Sekunden im Browser-Fenster eingeben.")
            
            # 90 Sekunden lang auf Antwort vom Server warten
            # Eventuell gibt User seinen Pin falsch ein etc.
            max_sms_code_eingabe_sekunden = 90
            while max_sms_code_eingabe_sekunden:

                # Verbleibende Zeit anzeigen
                driver.execute_script(f"arguments[0].innerText='Vaccipy! - Bitte SMS-Code im Browser eingeben. Noch {max_sms_code_eingabe_sekunden} Sekunden verbleibend.'", sms_verifizierung_h1)

                # Alle bisherigen Requests laden
                sms_verification_responses= []
                for request in driver.requests:
                    if request.url == location:
                        sms_verification_responses.append(request.response)

                if sms_verification_responses:

                    # Neuste Antowrt vom Server auslesen
                    # User kann z.B 2 mal den Pin falsch eingeben uns interessiert nur die neuste Antwort vom Server
                    latest_reponse = sms_verification_responses[-1]

                    if latest_reponse.status_code == 400:
                        try:
                            # error Laden
                            error = json.loads(latest_reponse.body.decode('utf-8'))['error']
                        except JSONDecodeError as exc:
                            raise RuntimeError(f"JSONDecodeError: {str(exc)}") from exc

                        if error == "Pin ungültig":
                            self.log.warning("Der eingegebene SMS-Code ist ungültig.")

                    elif latest_reponse.status_code == 200:
                        driver.close() 
                        raise RuntimeError("SMS-Code erfolgreich übermittelt. Bitte Prüfen Sie Ihre E-Mails.")
                    elif latest_reponse.status_code == 429:
                        driver.close() 
                        raise RuntimeError("SMS-Code konnte nicht übermittelt werden. Blockiert durch Botprotection.")

                time.sleep(1)
                max_sms_code_eingabe_sekunden -= 1
                
            # Temporäre Lösung einen Error zu werfen
            # TODO main.py -> gen_code() weiteren ablauf anpassen, da code_bestaetigen() in dem Fall nicht mehr ausgeführt wird
            driver.close()    
            raise RuntimeError("SMS-Verifikation nicht innerhalb von 60 Sekunden abgeschlossen. Versuchen Sie es später erneut.")


    def code_bestaetigen(self, token, cookies, sms_pin, plz_impfzentrum):
        """
        Bestätigung der Code-Generierung mittels SMS-Code

        :param token: Token der Code-Erstellung
        :param sms_pin: 6-stelliger SMS-Code
        :return: True falls SMS-Code korrekt war, sonst False
        """

        url = self.impfzentrum_in_plz(plz_impfzentrum)["URL"]
        location = f"{url}rest/smspin/verifikation"
        data = {
            "token": token,
            "smspin": sms_pin

        }

        manual = False
        while True:
            if cookies is None:
                try:
                    cookies = self.get_cookies(url, manual=manual)
                except RuntimeError as exc:
                    self.log.error(str(exc))
                    continue  # Neuer Versuch in nächster Iteration

            try:
                self.s.cookies.clear()
                res = self.s.post(
                    location,
                    json=data,
                    cookies=cookies,
                    timeout=15)
            except RequestException as exc:
                self.log.error(f"Code-Verifikation fehlgeschlagen: {str(exc)}")
                self.log.info("Erneuter Versuch in 30 Sekunden")
                time.sleep(30)
                continue  # Neuer Versuch in nächster Iteration

            if res.status_code == 429:
                self.log.error("Anfrage wurde von der Botprotection geblockt")
                self.log.error(
                    "Die Cookies müssen manuell im Browser generiert werden")
                cookies = None
                manual = True
                continue  # Neuer Versuch in nächster Iteration

            if res.status_code == 400:
                return False

            if not res.ok:
                self.log.error(
                    "Code-Verifikation fehlgeschlagen: "
                    f"{res.status_code} {res.text}")
                self.log.info("Erneuter Versuch in 30 Sekunden")
                time.sleep(30)
                continue  # Neuer Versuch in nächster Iteration

            self.log.success(
                "Der Vermittlungscode wurde erfolgreich angefragt, "
                "bitte prüfe deine Mails!")
            return True


    def impfzentrum_in_plz(self, plz_impfzentrum):
        for url, gruppe in self.impfzentren.items():
            for iz in gruppe:
                if iz["PLZ"] == plz_impfzentrum:
                    return iz
        raise ValueError(
            f"Gewünschte PLZ {plz_impfzentrum} wurde bei Initialisierung nicht angegeben")

    def rotiere_codepoints(self, url):
        codepoints = self.codepoints[url]
        self.codepoints[url] = codepoints[1:] + codepoints[:1]

    def notify(self, title: str, msg: str):
        fire_notifications(self.notifications, self.operating_system, title, msg)

    @staticmethod
    def terminsuche(codes: list, plz_impfzentren: list, kontakt: dict,
                    PATH: str, notifications: dict = {}, zeitrahmen: dict = dict(),
                    check_delay: int = 30):
        """
        Sucht mit mehreren Vermittlungscodes bei einer Liste von Impfzentren nach
        Terminen und bucht den erstbesten, der dem Zeitrahmen entspricht,
        automatisch.

        :param codes: Liste an Vermittlungscodes vom Schma XXXX-XXXX-XXXX
        :param plz_impfzentren: Liste der PLZs der Impfzentren bei denen
            gesucht werden soll
        :param kontakt: Kontaktdaten der zu impfenden Person.
            Wird bei der Terminbuchung im JSON-Format an den Server übertragen.
            Zum Format, siehe tools.kontaktdaten.validate_kontakt.
        :param PATH: Dateipfad zum vaccipy-Repo.
            Wird verwendet, um die Chromedriver-Binary zu finden und Logs zu
            speichern.
        :param notifications: Daten zur Authentifizierung bei Benachrichtigungs Providern
        :param zeitrahmen: Objekt, das den Zeitrahmen festlegt, in dem Termine
            gebucht werden.
            Zum Format, siehe tools.kontaktdaten.validate_zeitrahmen.
        :param check_delay: Zeit zwischen Iterationen der Terminsuche.
        :return:
        """

        validate_codes(codes)
        validate_kontakt(kontakt)
        validate_zeitrahmen(zeitrahmen)

        if len(plz_impfzentren) == 0:
            raise ValueError("Kein Impfzentrum ausgewählt")

        its = ImpfterminService(codes, kontakt, PATH, notifications)

        # Prüfen, ob in allen angegebenen PLZs ein Impfzentrum verfügbar ist
        izs_by_plz = {
            iz["PLZ"]: iz
            for gruppe in its.impfzentren.values()
            for iz in gruppe
        }
        for plz in plz_impfzentren:
            iz = izs_by_plz.get(plz)
            if iz is None:
                raise ValueError(f"Kein Impfzentrum in {plz} verfügbar")
            zentrumsname = iz.get("Zentrumsname")
            ort = iz.get("Ort")
            its.log.info(f"'{zentrumsname}' in {plz} {ort} ausgewählt")

        # Einmal Chrome starten, um früh einen Fehler zu erzeugen, falls die
        # erforderliche Software nicht installiert ist.
        its.log.info("Teste Chromedriver")
        its.get_chromedriver(headless=True).quit()

        for plz_impfzentrum in cycle(plz_impfzentren):
            its.log.set_prefix(" ".join([
                plz for plz in plz_impfzentren
                if its.codepoints[izs_by_plz[plz]["URL"]]
            ]))
            url = its.impfzentrum_in_plz(plz_impfzentrum)["URL"]
            reservierung = its.reservierung_finden(zeitrahmen, plz_impfzentrum)
            if reservierung is not None:
                try:
                    its.termin_buchen(reservierung)
                    msg = "Termin erfolgreich gebucht!"
                    its.log.success(msg)
                    its.log.info("[SPENDE] Unterstütze hier unsere Spendenkampagne für 'Ärzte ohne Grenzen': https://www.aerzte-ohne-grenzen.de/spenden-sammeln?cfd=pjs3m")
                    its.notify(title="Terminbuchung:", msg=msg)
                    # Programm beenden, wenn Termin gefunden wurde
                    return
                except AppointmentGone:
                    msg = f"Termin ist nicht mehr verfügbar"
                    its.log.error(msg)
                    its.notify(title="Terminbuchung:", msg=msg)
                    # Der verwendete Code soll frühestens in 10 Minuten erneut
                    # verwendet werden, da sonst immer wieder der gleiche
                    # Termin zu buchen versucht wird.
                    code = reservierung["code"]
                    its.log.info(f"Pausiere Code {code[:4]}* für 10 Minuten")
                    now = datetime.now()
                    for codepoint in its.codepoints[url]:
                        if codepoint["code"] == code:
                            codepoint["next_use"] = now + timedelta(minutes=10)
                except BookingError:
                    msg = f"Termin konnte nicht gebucht werden."
                    its.log.error(msg)
                    its.notify(title="Terminbuchung:", msg=msg)

            # Rotiere Codes, um in nächster Iteration andere Codes zu
            # verwenden.
            its.rotiere_codepoints(url)

            time.sleep(check_delay)


def terminpaar_im_zeitrahmen(terminpaar, zeitrahmen):
    """
    Checken ob Terminpaar im angegebenen Zeitrahmen liegt

    :param terminpaar: Terminpaar wie in ImpfterminService.termin_suchen
    :param zeitrahmen: Zeitrahmen-Dictionary wie in ImpfterminService.termin_suchen
    :return: True oder False
    """
    if not zeitrahmen:  # Teste auf leeres dict
        return True

    assert zeitrahmen["einhalten_bei"] in ["1", "2", "beide"]

    von_datum = datetime.strptime(
        zeitrahmen["von_datum"],
        "%d.%m.%Y").date() if "von_datum" in zeitrahmen else date.min
    bis_datum = datetime.strptime(
        zeitrahmen["bis_datum"],
        "%d.%m.%Y").date() if "bis_datum" in zeitrahmen else date.max
    von_uhrzeit = datetime.strptime(
        zeitrahmen["von_uhrzeit"],
        "%H:%M").time() if "von_uhrzeit" in zeitrahmen else dtime.min
    bis_uhrzeit = (
            datetime.strptime(zeitrahmen["bis_uhrzeit"], "%H:%M")
            + timedelta(seconds=59)
    ).time() if "bis_uhrzeit" in zeitrahmen else dtime.max
    wochentage = [decode_wochentag(wt) for wt in set(
        zeitrahmen["wochentage"])] if "wochentage" in zeitrahmen else range(7)

    # Einzelne Termine durchgehen
    for num, termin in enumerate(terminpaar, 1):
        if zeitrahmen["einhalten_bei"] in ["beide", str(num)]:
            termin_zeit = datetime.fromtimestamp(int(termin["begin"]) / 1000)

            if not (von_datum <= termin_zeit.date() <= bis_datum):
                return False

            if not (von_uhrzeit <= termin_zeit.time() <= bis_uhrzeit):
                return False

            if not termin_zeit.weekday() in wochentage:
                return False
    return True


def get_headers(code: str):
    b = bytes(f':{code}', encoding='utf-8')
    bearer = f"Basic {b64encode(b).decode('utf-8')}"
    return {"Authorization": bearer}


def extrahiere_impfstoffe(qualifikation: dict):
    return qualifikation.get("tssname", "N/A").replace(" ", "").split(",")
