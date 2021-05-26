# vaccipy
[![build-windows](https://github.com/iamnotturner/vaccipy/actions/workflows/build_windows.yaml/badge.svg?branch=master)](https://github.com/iamnotturner/vaccipy/actions/workflows/build_windows.yaml)
[![build-linux-64](https://github.com/iamnotturner/vaccipy/actions/workflows/build_linux.yaml/badge.svg)](https://github.com/iamnotturner/vaccipy/actions/workflows/build_linux.yaml)

Automatisierte Impfterminbuchung auf [www.impfterminservice.de](https://www.impfterminservice.de/).

> **Disclaimer**
> 
> `vaccipy` garantiert dir keinen Impftermin, sondern dient lediglich als Unterstützung bei der Suche und Buchung.
> 
> Ebenso stellt ein Termin keine Berechtigung zur Impfung dar. Bitte die aktuellen Impfbestimmungen beachten.

## Features
* Automatisches Suchen und Buchen von Impfterminen
* Suche bei mehreren Impfzentren gleichzeitig
* Warteschlange umgehen
* Dauerhaft Impf-Code's generieren - egal wo, egal für wen!
* [BETA Branch (neue, aber noch nicht final getestete Features)](https://github.com/iamnotturner/vaccipy/tree/beta)

**[Wusstest du: Du kannst mit einem Impf-Code in mehreren Impfzentren gleichzeitig nach freien Terminen suchen!](https://github.com/iamnotturner/vaccipy/wiki/Ein-Code-fuer-mehrere-Impfzentren)**


## Downloads

> ⚠️ Google Chrome muss auf dem PC installiert sein (Windows, Mac und Linux) 


<a href="https://cntr.click/pz01KSQ">
<img width="100" height="90" src="https://upload.wikimedia.org/wikipedia/de/thumb/c/c2/Microsoft_Windows_7_logo.svg/2000px-Microsoft_Windows_7_logo.svg.png">
</a>
<a href="https://cntr.click/6Q0PXkK">
<img width="180" heigth="60" src=https://logos-world.net/wp-content/uploads/2020/11/Ubuntu-Emblem.png>
</a>

#### BETA Version

Der BETA-Branch enthält neue, noch nicht final getestete Features. [Sollten Fehler auftreten könnt ihr hier ein Issue erstellen.](https://github.com/iamnotturner/vaccipy/issues)


<a href="https://cntr.click/C476snF">
<img width="60" height="50" src="https://upload.wikimedia.org/wikipedia/de/thumb/c/c2/Microsoft_Windows_7_logo.svg/2000px-Microsoft_Windows_7_logo.svg.png">
</a>
<a href="https://cntr.click/R83AXwY">
<img width="90" heigth="30" src=https://logos-world.net/wp-content/uploads/2020/11/Ubuntu-Emblem.png>
</a>


## Ausgangssituation

Unsere Großeltern möchten sich gerne impfen lassen, aber telefonsich unter 116117 kommen sie nicht durch und das Internet
ist auch noch immer irgendwie Neuland. Jetzt kommt es zum Konflikt: einerseits möchte man natürlich gerne bei der Terminbuchung helfen,
andererseits hat man aber auch keine Lust, deshalb nun den ganzen Tag vor dem Computer zu hocken und die Seite zu aktualisieren...

## Wie funktioniert vaccipy?

`vaccipy` imitiert die manuelle Terminsuche und -buchung im Browser und führt die Anfragen automatisch aus.  
Zunächst trägst du deinen "Impf-Code" (*Beispiel: A1B2-C3D4-E5F6*), die PLZ deines Impfzentrums 
und deine Daten (Anschrift, Telefon, Mail) ein, die bei der Terminbuchung angegeben werden sollen.
Du wirst zur Eingabe aufgefordert und deine Daten werden in der Datei `./data/kontaktdaten.json` gespeichert.


Nachfolgend werden die zwei Grundfunktionalitäten von `vaccipy` kurz beschrieben.

### [1] Automatisierte Terminbuchung

#### Du benötigst

Die folgenden Daten werden beim Programmstart benötigt:

* Ein Impf-Code
* [PLZ's eines oderer mehrerer Impfzentren](https://github.com/iamnotturner/vaccipy/wiki/Ein-Code-fuer-mehrere-Impfzentren)
* Kontaktdaten
   *  Anrede
   *  Vorname
   *  Nachname
   *  Straße
   *  Hausnummer
   *  PLZ des Wohnorts
   *  Wohnort
   *  Telefonnummer
   *  Mailadresse

#### Ablauf

`vaccipy` übernimmt für dich die Suche und Buchung eines Impftermin auf [www.impfterminservice.de](https://www.impfterminservice.de/).
Dazu musst du deinen Impf-Code, die PLZ's deiner gewählten Impfzentren und deine Daten beim Start des Tools eintragen. Anschließend beginnt `vaccipy` 
die Suche und frägt in regelmäßigen Abständen (alle 60 Sekunden) verfügbare Termine in den gewählten Impfzentren ab.

Sobald ein Termin verfügbar ist, wird dieser direkt mit den Anfangs eingegeben Daten gebucht und die Suche beendet.
Nach erfolgreicher Buchung erhälst du eine Bestätigungsmail vom Impfterminservice und kannst die Termine auch direkt unter [www.impfterminservice.de](https://www.impfterminservice.de/) einsehen (Bundesland wählen > Impfzentrum wählen > Buchung verwalten).

Sollte der gebuchte Termin nicht passen, kannst du ihn einfach wieder stornieren und erneut die Suche beginnen.

Eine genauere Beschreibung des Prozesses findest du im Abschnitt Workflow.

### [2] Code generieren

#### Du benötigst

Die folgenden Daten werden beim Programmstart benötigt:

* Mailadresse
* Telefonnummer
* [PLZ des gewünschten Impfzentrums](https://github.com/iamnotturner/vaccipy/wiki/Ein-Code-fuer-mehrere-Impfzentren)

#### Ablauf

`vaccipy` kann neben der Terminbuchung dir auch einen Impf-Code generieren - dauerhaft, für jede Person, in jedem Impfzentrum. 
Dazu musst du deine Mailadresse, deine Telefonnummer und die PLZ des gewünschten Impfzentrums eintragen. Anschließend frägt `vaccipy` einen Impf-Code
an und du erhälst eine SMS mit einem Bestätigungscode. Diesen Bestätigungscode kannst du anschließend im Tool eintragen. Der Impf-Code wird dir 
anschließend per Mail zugesendet.

> Es ist wichtig, dass du den Code entsprechend deiner Altersgruppe auswählst, ansonsten wird dir der Termin vor Ort abgesagt.
> Der Code wird auf [www.impfterminservice.de](https://www.impfterminservice.de/) generiert und ist gültig.


## Was passiert mit meinen Daten?

Deine Daten werden **lokal**, also nur bei dir auf dem Computer, in der Datei `./kontaktdaten.json` gespeichert.
Beim nächsten Start kannst du deine Daten direkt laden und musst sie nicht erneut eintragen.


## Workflow

<img src="https://github.com/iamnotturner/vaccipy/blob/master/images/workflow.png">

> `vaccipy` nutzt die selben Endpunkte zur Terminbuchung wie dein Browser.

1) Abruf aller Impfzentren und abgleich, ob für die eingetragene PLZ ein Impfzentrum existiert
2) Abruf der Impfstoffe, die im gewählten Impfzentrum verfügbar sind
3) Cookies generieren

> Zur Terminbuchung werden Cookies benötigt (`bm_sz`), die im Browser automatisch erzeugt werden.
> Damit wir diese auch im Script haben, wird zu Beginn eine Chrome-Instanz (im Prinzip ein separates Chrome-Fenster)
> geöffnet und eine Unterseite des [Impfterminservices](https://www.impfterminservice.de/) aufgerufen.
> Anschließend werden die Cookies extrahiert und im Script aufgenommen.
> 
> Sollte die Warteschlange aktiv sein, wird diese übersprungen.

4) Mit dem Code "einloggen", im Browser ist das der Schritt: Impfzentrum auswählen und Impf-Code eintragen

> Das Einloggen im Script erfolgt lediglich, um eine Übersicht über die zugewiesenen Impfstoffe zu erhalten.
> Sollte der Login mal nicht klappen, ist das nicht weiter tragisch. Die Terminsuche kann fortgesetzt werden.



> Die nachkommenden Schritte erfolgen im Loop. Alle 60 Sekunden werden verfügbare Termine abgerufen und, 
> sollten Termine verfügbar sein, ~~der erstbeste~~ ein zufälliger ausgewählt. 
> 
> Dieser Prozess kann eine längere Zeit. Sobald die Cookies abgelaufen sind, 
> wird wieder ein Chrome-Fenster geöffnet und neue Cookies erstellt.

5) Termine abrufen: Wenn Termine verfügbar sind, springe zu *Schritt 8*
 
6) (Option 1) Eine Minute warten 
 
*oder*

6) (Option 2) bei Ablauf Cookies erneuern 

> Wenn ein Termin verfügbar ist, wird dieser mit den eingetragenen Daten gebucht.
> 
> **Achtung! Im nächsten Schritt wird ein verbindlicher Impftermin gebucht!**

7) Buchen des Impftermins


## Termin gebucht, was nun?

Nachdem dein Termin erfolgreich gebucht wurde, erhälst du eine Mail, in der du zunächst deine 
Mail-Adresse bestätigen musst. Nachdem du die Mail bestätigt hast, erhälst du zu jedem Termin 
eine Buchungsbestätigung. That's it!

Du kannst alternativ deine Buchung auch im Browser einsehen. Dazu musst du dich auf
[www.impfterminservice.de](https://www.impfterminservice.de/) begeben, dein Impfzentrum auswählen
und anschließend rechts-oben auf "Buchung verwalten" klicken.

## Requirements

* Python 3 (getestet mit Python 3.8 und 3.9)
* pip (zur Installation der Python-Module, getestet mit pip3)
* Google Chrome oder Chromium

Die notwendigen Python-Module können mittels pip installiert werden.

```shell
pip3 install -r requirements.txt
```

## Ausführung unter Windows
1) [`vaccipy` downloaden](#Downloads)
2) .zip Ordner entpacken
3) Im `windows-terminservice\`-Ordner die `windows-terminservice.exe` ausführen. 

> Es kann sein, dass Virenprogramme beim Download oder der Ausführung anschlagen. Wir wissen davon, haben aktuell aber keine Lösung dafür. 
> **Grundsätzlich ist richtig und wichtig, dass Windows vor der Ausführung von unbekannten Programmen warnt.**
> 
> Das Programm beinhaltet keinen Virus. Um sicher zu gehen kannst du dir den Quellcode anschauen und das Tool direkt mit Python ausführen.
> [DASDING haben in ihrem Beitrag](https://www.dasding.de/update/wie-impftermin-einfacher-bekommen-100.html) einen Workaround vorgeschlagen:
> 
> "[...] Um das Tool dann zum Laufen zu bringen, könntest du zum Beispiel eine [Ausnahme in den Windows-Sicherheiteinstellungen hinzufügen.](https://support.microsoft.com/de-de/windows/hinzufügen-eines-ausschlusses-zu-windows-sicherheit-811816c0-4dfd-af4a-47e4-c301afe13b26)"

## Ausführung unter Linux 
1) [`vaccipy` downloaden](#Downloads)
2) .zip Ordner entpacken
3) Eventuell notwendig: Die Terminservice- und Driver-Executable ausführbar machen.
Dazu das Terminal zum `linux-64-terminservice`-Ordner navigieren und folgenden Befehl ausführen:  
  `sudo -- sh -c 'chmod +x ./linux-64-terminservice; chmod +x ./tools/chromedriver/chromedriver-linux-64'`
4) Im `linux-64-terminservice`-Ordner die `./linux-64-terminsvervice`-Executable per Terminal ausführen. 

## Ausführung in der Kommandozeile

`vaccipy` kannst du über die Kommandozeile oder in einer beliebigen python-Entwicklungsumgebung
ausgeführen.
Nach dem Programmstart kannst du interaktiv auswählen, ob du einen Impf-Code generieren möchtest,
oder einen Termin suchen möchtest.

```shell
python3 main.py
```

Alternativ kannst du Subkommandos verwenden, um deine Auswahl zu treffen:

```bash
# Kontaktdaten (für Impf-Code) eingeben und in kontaktdaten.json speichern:
python3 main.py code --configure-only

# Kontaktdaten (für Impf-Code) eingeben und in beliebiger Datei speichern:
python3 main.py code --configure-only -f max-mustermann.json

# Impf-Code generieren:
python3 main.py code

# Impf-Code generieren und dafür die Kontaktdaten aus beliebiger Datei verwenden:
python3 main.py code -f max-mustermann.json

# Kontaktdaten (für Terminsuche) eingeben und in kontaktdaten.json speichern:
python3 main.py search --configure-only

# Kontaktdaten (für Terminsuche) eingeben und in beliebiger Datei speichern:
python3 main.py search --configure-only -f max-mustermann.json

# Termin suchen:
python3 main.py search

# Termin suchen und dafür die Kontaktdaten aus beliebiger Datei verwenden:
python3 main.py search -f max-mustermann.json
```

### Optionale Umgebungsvariablen

* `VACCIPY_CHROMEDRIVER`:
  Name oder relativer Pfad der chromedriver Programmdatei, die du verwenden möchtest.
  Dies kann verwendet werden, falls du deine eigene chromedriver-Installation verwenden möchtest
  und wird z. B. auf NixOS benötigt.
  Beispiel: `chromedriver`


## Programmdurchlauf

<img src="https://github.com/iamnotturner/vaccipy/blob/master/images/beispiel_programmdurchlauf.png">


## [Informationen zu den Distributionen und Shipping findest du hier.](https://github.com/iamnotturner/vaccipy/blob/master/docs/distribution.md)

## Das könnte noch kommen

Es gibt noch ein paar Features, die cool wären. Die Ideen werden hier mal gesammelt und
werden (von uns oder euch - feel free!) irgendwann hinzukommen:

- [ ] Datum eingrenzen bei der Terminwahl
- [ ] Github Pages
- [ ] Macosx Build / Pipeline (Mac currently blocks the app: [Branch](https://github.com/iamnotturner/vaccipy/tree/mac-intel-build))
- [ ] Code Zertifikate für Windows (gegen Virusmeldung)
- [ ] Artifacts, Packages und Releases

## Das kann vaccipy NICHT - und wird es auch nie können

`vaccipy` dient lediglich als Unterstützung bei der Impftermin-Buchung **EINER EINZELNEN PERSON**,
weshalb folgende Automatisierungen und Erweiterungen **NICHT** kommen werden:

* Möglichkeit zum Eintragen mehrerer Impf-Codes und Kontaktdaten
* Headless Selenium Support



## Bedanken?

<a href="https://www.aerzte-ohne-grenzen.de/spenden-sammeln?cfd=pjs3m">
<img align="right" width="150" height="150" src="https://www.doctorswithoutborders.org/sites/default/files/badge_2.png">
</a>
.. musst du dich nicht. Es freut uns sehr, wenn wir dir die Terminsuche etwas erleichtern konnten. 

Für den Fall, dass du dein Dank gerne in Geld ausdrücken möchtest, haben wir [hier eine Spendenaktion](https://www.aerzte-ohne-grenzen.de/spenden-sammeln?cfd=pjs3m) eingerichtet. [ÄRZTE OHNE GRENZEN](https://www.aerzte-ohne-grenzen.de) leistet weltweit medizinische Nothilfe in Krisen- und Kriegsgebieten und nach Naturkatastrophen.

Es wäre mega cool, wenn du dich daran beteiligst - ist aber vollkommen freiwillig, also no pressure 😉

# Seid vernünftig und missbraucht das Tool nicht.
save da world. my final message. goodbye.

### Shoutouts

- [DASDING: HOW TO IMPFTERMIN - DIESE TOOLS HELFEN DIR](https://www.dasding.de/update/wie-impftermin-einfacher-bekommen-100.html) - Danke an Dani Rapp!
- [Deutschlandfunk: Portale und Tools sollen bei Suche nach Impfterminen helfen](https://www.deutschlandfunk.de/corona-pandemie-portale-und-tools-sollen-bei-suche-nach.1939.de.html?drn:news_id=1261638)
- [WDR: Per Klick zum Impftermin](https://www1.wdr.de/nachrichten/themen/coronavirus/impftermine-online-buchen-100.html)

<a href="https://www.dasding.de/update/wie-impftermin-einfacher-bekommen-100.html">
<img width=100 src=https://github.com/iamnotturner/vaccipy/blob/master/images/2000px-Das_Ding_(2008).svg.png>
</a>
<a href="https://www.deutschlandfunk.de/corona-pandemie-portale-und-tools-sollen-bei-suche-nach.1939.de.html?drn:news_id=1261638">
<img width=100 src=https://www.deutschlandradio.de/themes/dradio/dlr2018/icons/dlf_logo.svg>
</a>
<a href="https://www1.wdr.de/nachrichten/themen/coronavirus/impftermine-online-buchen-100.html">
<img width=100 src=https://upload.wikimedia.org/wikipedia/commons/thumb/9/9b/WDR_Dachmarke.svg/2000px-WDR_Dachmarke.svg.png>
</a>

