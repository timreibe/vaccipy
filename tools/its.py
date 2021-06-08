# Alphabetisch sortiert:
import cloudscraper
import copy
import os
import platform
import string
import sys
import time

# Alphabetisch sortiert:
from base64 import b64encode
from datetime import datetime, date, timedelta
from datetime import time as dtime
from json import JSONDecodeError
from pathlib import Path
from random import choice, choices, randint
from requests.exceptions import RequestException
from selenium.common.exceptions import WebDriverException
from selenium.webdriver import ActionChains
from selenium.webdriver import Chrome
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from tools.clog import CLogger
from tools.exceptions import AppointmentGone, BookingError, LoginFailed, TimeframeMissed, UnmatchingCodeError
from tools.kontaktdaten import decode_wochentag, validate_codes, validate_kontakt, validate_zeitrahmen
from tools.utils import desktop_notification, update_available
from typing import Dict, List

try:
    import beepy

    ENABLE_BEEPY = True
except ImportError:
    ENABLE_BEEPY = False


class ImpfterminService():
    def __init__(self, codes: list, kontakt: dict, PATH: str):
        self.PATH = PATH
        self.kontakt = kontakt
        self.operating_system = platform.system().lower()

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

        # Zunächst alle Codes zu allen URLs zuordnen. Aussortiert wird später.
        self.codes = {
            url: copy.copy(codes)
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
        #chrome_options.add_argument("-no-sandbox");
        chrome_options.add_argument("-disable-dev-shm-usage");

        # Chrome head is only required for the backup booking process.
        # User-Agent is required for headless, because otherwise the server lets us hang.
        chrome_options.add_argument("user-agent=Mozilla/5.0")
        
        chromebin_from_env = os.getenv("VACCIPY_CHROME_BIN")
        if chromebin_from_env:
            chrome_options.binary_location = os.getenv("VACCIPY_CHROME_BIN")

        chrome_options.headless = headless

        return Chrome(self.get_chromedriver_path(), options=chrome_options)

    def driver_enter_code(self, driver, impfzentrum, code):
        """
        TODO xpath code auslagern
        """

        self.log.info("Code eintragen und Mausbewegung / Klicks simulieren. "
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

        # Klick auf "Auswahl bestätigen" im Cookies-Banner
        button_xpath = "//a[contains(@class,'cookies-info-close')][1]"
        button = WebDriverWait(driver, 1).until(
            EC.element_to_be_clickable((By.XPATH, button_xpath)))
        action = ActionChains(driver)
        action.move_to_element(button).click().perform()

        # Klick auf "Vermittlungscode bereits vorhanden"
        button_xpath = "//input[@name=\"vaccination-approval-checked\"]/.."
        button = WebDriverWait(driver, 1).until(
            EC.element_to_be_clickable((By.XPATH, button_xpath)))
        action = ActionChains(driver)
        action.move_to_element(button).click().perform()

        # Auswahl des ersten Code-Input-Feldes
        input_xpath = "//input[@name=\"ets-input-code-0\"]"
        input_field = WebDriverWait(driver, 1).until(
            EC.element_to_be_clickable((By.XPATH, input_xpath)))
        action = ActionChains(driver)
        action.move_to_element(input_field).click().perform()

        # Code eintragen
        input_field.send_keys(code)
        time.sleep(.1)

        # Klick auf "Termin suchen"
        button_xpath = "//app-corona-vaccination-yes//button[@type=\"submit\"]"
        button = WebDriverWait(driver, 1).until(
            EC.element_to_be_clickable((By.XPATH, button_xpath)))
        action = ActionChains(driver)
        action.move_to_element(button).click().perform()

        # Maus-Bewegung hinzufügen (nicht sichtbar)
        action = ActionChains(driver)
        for i in range(3):
            try:
                action.move_by_offset(randint(1, 100), randint(1, 100)).perform()
                time.sleep(randint(1, 3))
            except:
                pass

    def driver_get_cookies(self, driver, url, manual):
        # Erstelle zufälligen Impf-Code für die Cookie-Generierung
        legal_chars = string.ascii_uppercase + string.digits
        random_chars = "".join(choices(legal_chars, k=5))
        random_code = f"VACC-IPY{random_chars[0]}-{random_chars[1:]}"

        # Kann WebDriverException nach außen werfen:
        self.driver_enter_code(
            driver, choice(self.impfzentren[url]), random_code)
        if manual:
            self.log.warn(
                "Du hast jetzt 30 Sekunden Zeit möglichst viele Elemente im Chrome Fenster anzuklicken. Das Fenster schließt sich automatisch.")
            time.sleep(30)

        required = ["bm_sz", "akavpau_User_allowed"]

        cookies = {
            c["name"]: c["value"]
            for c in driver.get_cookies()
            if c["name"] in required
        }

        # prüfen, ob Cookies gesetzt wurden und in Session übernehmen
        for name in required:
            if name not in cookies:
                raise RuntimeError(f"{name} fehlt!")

        self.log.success(f"Browser-Cookie generiert: *{cookies['bm_sz'][-6:]}")
        return cookies

    def driver_termin_buchen(self, driver, reservierung):
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        filepath = os.path.join(self.PATH, "tools\\log\\")

        try:
            self.driver_enter_code(
                driver, reservierung["impfzentrum"], reservierung["code"])
        except BaseException as exc:
            self.log.error(f"Code kann nicht eingegeben werden: {str(exc)}")
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
                driver.save_screenshot(filepath + "errorterminsuche" + timestamp + ".png")
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
                with open(filepath + "errorterminauswahl" + timestamp + ".html", 'w', encoding='utf-8') as file:
                    file.write(str(driver.page_source))
                driver.save_screenshot(filepath + "errorterminauswahl" + timestamp + ".png")
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
            arrAnreden = ["Herr","Frau","Kind","Divers"]
            if self.kontakt['anrede'] in arrAnreden:
                button_xpath = '//*[@id="itsSearchContactModal"]//app-booking-contact-form//div[contains(@class,"ets-radio-wrapper")]/label[@class="ets-radio-control"]/span[contains(text(),"'+self.kontakt['anrede']+'")]'
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
                driver.save_screenshot(filepath + "errordateneingeben" + timestamp + ".png")
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
        Einloggen mittels Code, um qualifizierte Impfstoffe zu erhalten.

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
                "Login in {plz_impfzentrum} nicht erfolgreich: "
                f"Impf-Code nicht gültig für diese PLZ")
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

    def reservierung_finden(self, plz_impfzentren: list, zeitrahmen: dict):
        for url in self.impfzentren:
            ausgewaehlte_impfzentren = [
                iz for iz in self.impfzentren[url]
                if iz["PLZ"] in plz_impfzentren
            ]
            if not ausgewaehlte_impfzentren:
                continue

            iz = choice(ausgewaehlte_impfzentren)
            plz = iz["PLZ"]
            codes = self.codes[url]
            if not codes:
                self.log.warn(f"Kein gültiger Code mehr vorhanden für {plz}")
                continue

            try:
                reservierung = self.reservierung_hier_finden(
                    zeitrahmen, iz, codes[0])
                if reservierung is not None:
                    return reservierung
            except UnmatchingCodeError:
                code = codes.pop(0)
                plz_ausgeschlossen = [
                    iz["PLZ"] for iz in ausgewaehlte_impfzentren
                ]
                self.log.info(
                    f"Überspringe Code {code[:4]}* "
                    f"für {', '.join(plz_ausgeschlossen)}")
            except TimeframeMissed:
                self.rotiere_codes(url)
            except RuntimeError as exc:
                self.log.error(str(exc))

        return None

    def reservierung_hier_finden(
            self, zeitrahmen: dict, impfzentrum: dict, code: str):
        """Es wird nach einen verfügbaren Termin in der gewünschten PLZ gesucht.
        Ausgewählt wird der erstbeste Termin, welcher im entsprechenden Zeitraum liegt (!).
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

        url = impfzentrum["URL"]
        plz = impfzentrum["PLZ"]
        location = f"{url}rest/suche/impfterminsuche?plz={plz}"

        try:
            self.s.cookies.clear()
            res = self.s.get(location, headers=get_headers(code), timeout=5)
        except RequestException as exc:
            raise RuntimeError(
                f"Termine in {plz} können nicht geladen werden: {str(exc)}")
        if res.status_code == 401:
            raise UnmatchingCodeError(
                "Termine in {plz} können nicht geladen werden: "
                f"Impf-Code nicht gültig für diese PLZ")
        if not res.ok:
            raise RuntimeError(
                "Termine in {plz} können nicht geladen werden: "
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
            self.log.info('-' * 50)

        if not terminpaare_angenommen:
            raise TimeframeMissed()

        # Auswahl des erstbesten Terminpaares
        tp_angenommen = choice(terminpaare_angenommen)
        self.log.success(f"Termin gefunden!")
        self.log.success(f"'{zentrumsname}' in {plz} {ort}")
        for num, termin in enumerate(tp_angenommen, 1):
            ts = datetime.fromtimestamp(termin["begin"] / 1000).strftime(
                '%d.%m.%Y um %H:%M Uhr')
            self.log.success(f"{num}. Termin: {ts}")

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
            if res.status_code != 201:
                # Example res: {"errors":[{"code":"WP009","text":"Buchung bereits durchgefuehrt"}]}
                if '"code":"WP009"' in res.text:
                    raise AppointmentGone

                # Example res: {"errors":[{"code":"WP011","text":"Der ausgewählte Termin ist nicht mehr verfügbar. Bitte wählen Sie einen anderen Termin aus"}]}
                if '"code":"WP011"' in res.text:
                    raise AppointmentGone()

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
                    continue # Neuer Versuch in nächster Iteration

            try:
                self.s.cookies.clear()
                res = self.s.post(
                    location,
                    json=data,
                    cookies=cookies,
                    timeout=15)
            except RequestException as exc:
                self.log.error(f"Code kann nicht angefragt werden: {str(exc)}")
                self.log.info("Erneuter Versuch in 30 Sekunden")
                time.sleep(30)
                continue # Neuer Versuch in nächster Iteration

            if res.status_code == 429:
                self.log.error("Anfrage wurde von der Botprotection geblockt")
                self.log.error(
                    "Die Cookies müssen manuell im Browser generiert werden")
                cookies = None
                manual = True
                continue # Neuer Versuch in nächster Iteration

            if res.status_code == 400 and res.text == '{"error":"Anfragelimit erreicht."}':
                raise RuntimeError("Anfragelimit erreicht")

            if not res.ok:
                self.log.error(
                    "Code kann nicht angefragt werden: "
                    f"{res.status_code} {res.text}")
                self.log.info("Erneuter Versuch in 30 Sekunden")
                time.sleep(30)
                continue # Neuer Versuch in nächster Iteration

            try:
                token = res.json().get("token")
            except JSONDecodeError as exc:
                raise RuntimeError(f"JSONDecodeError: {str(exc)}") from exc

            return (token, cookies)

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
                    continue # Neuer Versuch in nächster Iteration

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
                continue # Neuer Versuch in nächster Iteration

            if res.status_code == 429:
                self.log.error("Anfrage wurde von der Botprotection geblockt")
                self.log.error(
                    "Die Cookies müssen manuell im Browser generiert werden")
                cookies = None
                manual = True
                continue # Neuer Versuch in nächster Iteration

            if res.status_code == 400:
                return False

            if not res.ok:
                self.log.error(
                    "Code-Verifikation fehlgeschlagen: "
                    f"{res.status_code} {res.text}")
                self.log.info("Erneuter Versuch in 30 Sekunden")
                time.sleep(30)
                continue # Neuer Versuch in nächster Iteration

            self.log.success(
                "Der Impf-Code wurde erfolgreich angefragt, "
                "bitte prüfe deine Mails!")
            return True

    def impfzentrum_in_plz(self, plz_impfzentrum):
        for url, gruppe in self.impfzentren.items():
            for iz in gruppe:
                if iz["PLZ"] == plz_impfzentrum:
                    return iz
        raise ValueError(
            f"Gewünschte PLZ {plz} wurde bei Initialisierung nicht angegeben")

    def rotiere_codes(self, url):
        codes = self.codes[url]
        self.codes[url] = codes[1:] + codes[:1]

    @staticmethod
    def terminsuche(codes: list, plz_impfzentren: list, kontakt: dict,
                    PATH: str, zeitrahmen: dict = dict(), check_delay: int = 30):
        """
        Sucht mit mehreren Impf-Codes bei einer Liste von Impfzentren nach
        Terminen und bucht den erstbesten, der dem Zeitrahmen entspricht,
        automatisch.

        :param codes: Liste an Impf-Codes vom Schma XXXX-XXXX-XXXX
        :param plz_impfzentren: Liste der PLZs der Impfzentren bei denen
            gesucht werden soll
        :param kontakt: Kontaktdaten der zu impfenden Person.
            Wird bei der Terminbuchung im JSON-Format an den Server übertragen.
            Zum Format, siehe tools.kontaktdaten.validate_kontakt.
        :param PATH: Dateipfad zum vaccipy-Repo.
            Wird verwendet, um die Chromedriver-Binary zu finden und Logs zu
            speichern.
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

        its = ImpfterminService(codes, kontakt, PATH)

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

        while True:
            its.log.set_prefix(" ".join([
                plz for plz in plz_impfzentren
                if its.codes[izs_by_plz[plz]["URL"]]
            ]))
            reservierung = its.reservierung_finden(plz_impfzentren, zeitrahmen)
            if reservierung is not None:
                url = reservierung["impfzentrum"]["URL"]
                try:
                    its.termin_buchen(reservierung)
                    msg = "Termin erfolgreich gebucht!"
                    its.log.success(msg)
                    desktop_notification(
                        operating_system=its.operating_system,
                        title="Terminbuchung:",
                        message=msg)
                    # Programm beenden, wenn Termin gefunden wurde
                    return
                except AppointmentGone:
                    msg = f"Termin ist nicht mehr verfügbar"
                    its.rotiere_codes(url)
                except BookingError:
                    msg = f"Termin konnte nicht gebucht werden."
                its.log.error(msg)
                desktop_notification(
                    operating_system=its.operating_system,
                    title="Terminbuchung:",
                    message=msg)

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
