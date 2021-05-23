# vaccipy
[![build-windows](https://github.com/iamnotturner/vaccipy/actions/workflows/build_windows.yaml/badge.svg?branch=master)](https://github.com/iamnotturner/vaccipy/actions/workflows/build_windows.yaml)
[![build-linux-64](https://github.com/iamnotturner/vaccipy/actions/workflows/build_linux.yaml/badge.svg)](https://github.com/iamnotturner/vaccipy/actions/workflows/build_linux.yaml)

Automatisierte Impfterminbuchung auf [www.impfterminservice.de](https://www.impfterminservice.de/).</br>

> **Disclaimer**
> 
> `vaccipy` garantiert dir keinen Impftermin, sondern dient lediglich als Unterstützung bei der Suche und Buchung.
> Ebenso stellt ein Termin keine Berechtigung zur Impfung dar. Bitte die aktuellen Impfbestimmungen beachten.

## Features
* Automatisches suchen und buchen von verfügbaren Impfterminen
* Suche bei mehreren Impfzentren gleichzeitig
* Warteschlange umgehen
* Dauerhaft Impf-Code's generieren - egal wo, egal für wen!
* [Beta Branch (neue, aber noch nicht final getestete Features)](https://github.com/iamnotturner/vaccipy/tree/beta)

**[Wusstest du: Du kannst mit einem Impf-Code in mehreren Impfzentren gleichzeitig nach freien Terminen suchen!](https://github.com/iamnotturner/vaccipy/wiki/Ein-Code-fuer-mehrere-Impfzentren)**

## Downloads
<a href="https://cntr.click/9ypzBLb">
<img width="100" height="90" src="https://upload.wikimedia.org/wikipedia/de/thumb/c/c2/Microsoft_Windows_7_logo.svg/2000px-Microsoft_Windows_7_logo.svg.png">
</a>
<a href="https://cntr.click/6Q0PXkK">
<img width="180" heigth="60"src=https://logos-world.net/wp-content/uploads/2020/11/Ubuntu-Emblem.png>
</a>

## Distributionen

Für eine bessere Nutzererfahrung erstellen wir verschiedene Distributionen, die ohne installation von Python direkt ausgeführt werden können. 
Die Unterfolder von `dist/` sind jeweils Distributionen die geteilt werden können und eigenständig funktionieren.

Zum Ausführen des Programms, einfach die passende Distribution (basierend auf dem eigenen Betriebssysstem) auswählen und die folgende Datei ausführen. 

*Hinweis: Es wird jeweils immer der gesamte Ordner benötigt!* 

### Download 
Verfügbare Distributionen:
- [x] [Windows](https://cntr.click/9ypzBLb)  
- [x] [Linux](https://cntr.click/6Q0PXkK) 
- [ ] MacOS Intel
- [ ] MacOS M1

Für mehr Info zum Verteilen und Erstellen der Distributionen: [Shipping](#Shipping)

## Shipping
### Workflows
Um den Buildprozess zu vereinfachen gibt es verschiedene Buildpipelines, welche bei push Events in den Masterbranch ausgeführt werden.   
Die pipelines sind im `.github/workflows` Ordner zu finden. 

Aktuelle Pipelines:
- [x] [Windows Build-Pipeline](https://github.com/iamnotturner/vaccipy/actions/workflows/build_windows.yaml)

### Generell

Zum Erstellen der Distributionen wird [pyinstaller](https://pyinstaller.readthedocs.io/en/stable/index.html) verwendet.  
Schritte zum Erstellen einer Distribution: 
- Erstelle eine .spec Datei für die main.py (einmalig)  
    ⚠️ACHTUNG⚠️: Beim erstellen der .spec den python code für `cloudscraper` nicht löschen! 

- Erstelle die Distribution basierend auf der erstellten .spec Datei:
    ```shell
    pyinstaller --clean specs/SPECNAME.spec
    ```
    Nachdem mit pyinstaller die Distribution erstellt wurde, ist diese in im `dist/` folder zu finden.  


### Windows

.spec Datei erstellen und anschließend Distribution erstellen:  
⚠️ACHTUNG⚠️: Beim erstellen der .spec den python code für `cloudscraper` nicht löschen! 
```shell
pyi-makespec main.py --specpath "specs//" --add-binary "..\tools\chromedriver\chromedriver-windows.exe;tools\chromedriver\" --name windows-terminservice --hidden-import plyer.platforms.win.notification --hidden-import cloudscraper

pyinstaller --clean specs/windows-terminservice.spec
```     

### Linux
```shell 
pyi-makespec main.py --specpath "specs//" --add-binary "../tools/chromedriver/chromedriver-linux-64;tools/chromedriver/" --name linux-64-terminservice --hidden-import cloudscraper

pyinstaller --clean specs/linux-64-terminservice.spec

```


### Resources
- [pyinstaller docs](https://pyinstaller.readthedocs.io/en/stable/index.html)
