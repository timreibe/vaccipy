import os
import platform
import sys
import time
import traceback
from json import JSONDecodeError
from random import choice
from threading import Thread

from plyer import notification
from requests.exceptions import ReadTimeout, ConnectionError, ConnectTimeout
from selenium.webdriver import ActionChains
from selenium.webdriver import Chrome
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


def retry_on_failure(retries=10):
    """Decorator zum Errorhandling beim Ausführen einer Methode im Loop.
    Timeout's, wie beispiel bei Serverüberlastung, werden ignoriert.

    :param retries: Anzahl der Wiederholungsversuche, bevor abgebrochen wird.
    :return:
    """

    def retry_function(function):
        def wrapper(self, *args, **kwargs):
            total_rounds = retries
            rounds = total_rounds
            while rounds > 0:
                r = total_rounds - rounds + 1
                try:
                    return function(self, *args, **kwargs)

                except (TimeoutError, ReadTimeout):
                    # ein Timeout-Error kann passieren,
                    # wenn die Server überlastet sind sind
                    # hier erfolgt ein Timeout-Error meist,
                    # wenn die Cookies abgelaufen sind

                    self.log.error("Timeout exception raised", prefix=function.__name__)

                    if function.__name__ != "cookies_erneuern":
                        self.cookies_erneuern()

                except (ConnectTimeout, ConnectionError):
                    # Keine Internetverbindung
                    self.log.error("Connection exception | Es besteht keine Internetverbindung,"
                                   "erneuter Versuch in 30 Sekunden",
                                   prefix=function.__name__)
                    time.sleep(30)

                except JSONDecodeError:
                    # die API gibt eine nicht-JSON-Response,
                    # wenn die IP (temporär) gebannt ist, oder die Website
                    # sich im Wartungsmodus befindet

                    self.log.error("JSON parsing exception | IP gebannt oder Website down, "
                                   "erneuter Versuch in 30 Sekunden",
                                   prefix=function.__name__)
                    time.sleep(30)

                    # Cookies erneuern bei der Terminsuche
                    if function.__name__ == "terminsuche":
                        self.cookies_erneuern(False)

                except Exception as e:
                    exc = type(e).__name__
                    self.log.error(f"{exc} exception raised - retry {r}",
                                   prefix=function.__name__)
                    if rounds == 1:
                        err = "\n".join(
                            x.strip() for x in traceback.format_exc().splitlines()[-3:])
                        self.log.error(err)
                        return False
                    rounds -= 1
            return False

        return wrapper

    return retry_function


def remove_prefix(text, prefix):
    """
    Entfernt einen gegebenen String vom Angang des Textes.
    """
    if text.startswith(prefix):
        return text[len(prefix):]
    return text


def desktop_notification(session, title: str, message: str):
    """
    Starts a thread and creates a desktop notification using plyer.notification
    """

    if 'windows' not in session.operating_system:
        return

    try:
        Thread(target=notification.notify(
            app_name=session.app_name,
            title=title,
            message=message)
        ).start()
    except Exception as exc:
        session.log.error("Error in _desktop_notification: " + str(exc.__class__.__name__)
                          + traceback.format_exc())


def cookies_erneuern(
        session,
        basepath,
        terminbuchung=False):
    """
    Cookies der Session erneuern, wenn sie abgelaufen sind.
    Inklusive Backup-Prozess für die Terminbuchung, wenn diese im Bot fehlschlägt.

    :param terminbuchung: Startet den Backup-Prozess der Terminbuchung
    :return:
    """

    if terminbuchung == False:
        session.log.info("Browser-Cookies generieren")
    else:
        session.log.info("Termin über Selenium buchen")
    # Chromedriver anhand des OS auswählen
    chromedriver = os.getenv("VACCIPY_CHROMEDRIVER")
    if not chromedriver:
        if 'linux' in session.operating_system:
            if "64" in platform.architecture() or sys.maxsize > 2 ** 32:
                chromedriver = os.path.join(basepath, "tools/chromedriver/chromedriver-linux-64")

            else:
                chromedriver = os.path.join(basepath, "tools/chromedriver/chromedriver-linux-32")
        elif 'windows' in session.operating_system:
            chromedriver = os.path.join(basepath, "tools/chromedriver/chromedriver-windows.exe")
        elif 'darwin' in session.operating_system:
            if "arm" in platform.processor().lower():
                chromedriver = os.path.join(basepath, "tools/chromedriver/chromedriver-mac-m1")
            else:
                chromedriver = os.path.join(basepath, "tools/chromedriver/chromedriver-mac-intel")

    path = "impftermine/service?plz={}".format(choice(session.plz_impfzentren))

    # deaktiviere Selenium Logging
    chrome_options = Options()
    chrome_options.add_argument('disable-infobars')
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])

    with Chrome(chromedriver, options=chrome_options) as driver:
        driver.get(session.domain + path)

        # Queue Bypass
        queue_cookie = driver.get_cookie("akavpwr_User_allowed")
        if queue_cookie:
            session.log.info("Im Warteraum, Seite neuladen")
            queue_cookie["name"] = "akavpau_User_allowed"
            driver.add_cookie(queue_cookie)

            # Seite neu laden
            driver.get(session.domain + path)
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
        input_field.send_keys(session.code)
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
            try:
                button_xpath = "/html/body/app-root/div/app-page-its-search/div/div/div[2]/div/div/div[5]/div/div[1]/div[2]/div[2]/button"
                button = WebDriverWait(driver, 1).until(
                    EC.element_to_be_clickable((By.XPATH, button_xpath)))
                action = ActionChains(driver)
                action.move_to_element(button).click().perform()
                time.sleep(.5)
            except:
                self.log.error("Termine können nicht gesucht werden")
                pass

            # Termin auswählen
            try:
                button_xpath = '//*[@id="itsSearchAppointmentsModal"]/div/div/div[2]/div/div/form/div[1]/div[2]/label/div[2]/div'
                button = WebDriverWait(driver, 1).until(
                    EC.element_to_be_clickable((By.XPATH, button_xpath)))
                action = ActionChains(driver)
                action.move_to_element(button).click().perform()
                time.sleep(.5)
            except:
                self.log.error("Termine können nicht ausgewählt werden")
                pass

            # Klick Button "AUSWÄHLEN"
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
            except:
                self.log.error("Kontaktdaten können nicht eingegeben werden")
                pass

            # Klick Button "ÜBERNEHMEN"
            try:
                button_xpath = '//*[@id="itsSearchContactModal"]/div/div/div[2]/div/form/div[2]/button[1]'
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
            if "Ihr Termin am" in str(driver.page_source):
                msg = "Termin erfolgreich gebucht!"
                session.log.success(msg)
                session._desktop_notification("Terminbuchung:", msg)
                return True
            else:
                self.log.error("Automatisierte Terminbuchung fehlgeschlagen. Termin manuell im Fenster oder im Browser buchen.")
                print("Link für manuelle Buchung im Browser:", self.domain + path)
                time.sleep(10*60)

        # prüfen, ob Cookies gesetzt wurden und in Session übernehmen
        try:
            cookie = driver.get_cookie("bm_sz")
            if cookie:
                session.s.cookies.clear()
                session.s.cookies.update({c['name']: c['value'] for c in driver.get_cookies()})
                session.log.info("Browser-Cookie generiert: *{}".format(cookie.get("value")[-6:]))
                return True
            else:
                session.log.error("Cookies können nicht erstellt werden!")
                return False
        except:
            return False
