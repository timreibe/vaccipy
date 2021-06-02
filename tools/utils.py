import os
import time
import traceback
from json import JSONDecodeError
from pathlib import Path
from threading import Thread

import requests
from plyer import notification
from requests.exceptions import ReadTimeout, ConnectionError, ConnectTimeout

from tools.exceptions import DesktopNotificationError


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

                    if function.__name__ != "renew_cookies":
                        self.renew_cookies()

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
                        self.renew_cookies()

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


def desktop_notification(operating_system: str, title: str, message: str):
    """
    Starts a thread and creates a desktop notification using plyer.notification
    """

    if 'windows' not in operating_system:
        return

    try:
        Thread(target=notification.notify(
            app_name="Impfterminservice",
            title=title,
            message=message)
        ).start()
    except Exception as exc:
        raise DesktopNotificationError(
            "Error in _desktop_notification: " + str(exc.__class__.__name__)
            + traceback.format_exc()
        ) from exc


def create_missing_dirs(base_path):
    """
    Erstellt benötigte Ordner, falls sie fehlen:

    - ./data
    """
    Path(os.path.join(base_path, "data")).mkdir(parents=True, exist_ok=True)


def get_grouped_impfzentren() -> dict:
    """
    Gibt ein dict mit allen Impfzentren Grupiert nach den gültigen Codes

    Returns:
        dict: Informationen über die Impfzentren
    """

    url = "https://www.impfterminservice.de/assets/static/impfzentren.json"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 11_2_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.82 Safari/537.36',
    }
    impfzentren_sortiert = {}
    res = requests.get(url, timeout=15, headers=headers)
    if res.ok:
        for bundesland, impfzentren in res.json().items():
            for impfzentrum in impfzentren:
                url = impfzentrum["URL"]
                # liste von impfzentren_sortiert oder leere liste
                impfzentren_gruppiert = impfzentren_sortiert.get(url, [])
                # impfzentrum zur liste hinzufügen
                impfzentren_gruppiert.append(impfzentrum)
                # liste in dict abspeichern
                impfzentren_sortiert[url] = impfzentren_gruppiert
    result = {}
    for gruppe, impfzentren in enumerate(impfzentren_sortiert.values(), start=1):
        result[f"Gruppe {gruppe}"] = impfzentren
    return result
