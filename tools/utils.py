import traceback

from requests.exceptions import ReadTimeout


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
                    self.log.error("Timeout exception raised",
                                   prefix=function.__name__)

                    # ein Timeout-Error kann passieren,
                    # wenn die Server überlastet sind sind
                    # hier erfolgt ein Timeout-Error meist,
                    # wenn die Cookies abgelaufen sind

                    if function.__name__ != "cookies_erneuern":
                        self.cookies_erneuern()

                except Exception as e:
                    exc = type(e).__name__
                    self.log.error(f"{exc} exception raised - retry {r}",
                                   prefix=function.__name__)
                    if rounds == 1:
                        err = "\n".join(x.strip() for x in traceback.format_exc().splitlines()[-3:])
                        self.log.error(err)
                        return False
                    rounds -= 1
            return False

        return wrapper

    return retry_function
