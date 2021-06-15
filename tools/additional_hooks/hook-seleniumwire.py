"""
This is a needed workaround for pyinstaller missing out on seleniumwire.

GitHub issue comnment: https://github.com/wkeeling/selenium-wire/issues/84#issuecomment-624389859

Pyinstaller docu: https://pyinstaller.readthedocs.io/en/stable/hooks.html#providing-pyinstaller-hooks-with-your-package
"""

from PyInstaller.utils.hooks import collect_data_files

datas = collect_data_files('seleniumwire')