
from PyQt5 import QtWidgets, uic
from PyQt5.QtCore import QTime


# Folgende Widgets stehen zur Verfügung:

### QLineEdit ####
# i_plz_impfzentren
# i_code_impfzentren
# i_vorname
# i_nachname
# i_strasse
# i_hausnummer
# i_wohnort
# i_plz_wohnort
# i_telefon
# i_mail

### QComboBox ###
# i_anrede_combo_box

### QDialogButtonBox ###
# buttonBox
# Apply
# Cancel
# Reset

class QtKontakt(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()