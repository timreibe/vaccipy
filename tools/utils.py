import time
from threading import Thread
from plyer import notification
from tools.exceptions import DesktopNotificationError
import traceback
from json import JSONDecodeError

from requests.exceptions import ReadTimeout, ConnectionError, ConnectTimeout


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


def desktop_notification(operating_system:str, title: str, message: str):
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
            
        
