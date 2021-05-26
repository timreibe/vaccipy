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

**Ausführung Windows:** 
- .zip Ordner entpacken
- Im `windows-terminservice\`-Ordner die `windows-terminservice.exe` ausführen. 

**Ausführung Linux:**
- .zip Ordner entpacken
- Eventuell notwendig: Die Terminservice- und Driver-Executable ausführbar machen.
Dazu das Terminal zum `linux-64-terminservice`-Ordner navigieren und folgende Befehle ausführen:  
  `sudo -- sh -c 'chmod +x ./linux-64-terminservice; chmod +x ./tools/chromedriver/chromedriver-linux-64'`
- Im `linux-64-terminservice`-Ordner die `./linux-64-terminsvervice` executable per Terminal ausführen. 

Für mehr Info zum Verteilen und Erstellen der Distributionen: [Shipping](#Shipping)

### Shipping
#### Workflows
Um den Buildprozess zu vereinfachen gibt es verschiedene Buildpipelines, welche bei push Events in den Masterbranch ausgeführt werden.   
Die pipelines sind im `.github/workflows` Ordner zu finden. 

Aktuelle Pipelines:
- [x] [Windows Build-Pipeline](https://github.com/iamnotturner/vaccipy/actions/workflows/build_windows.yaml)
- [x] [Linux 64 Build-Pipeline](https://github.com/iamnotturner/vaccipy/actions/workflows/build_linux.yaml)

#### Generell

Zum Erstellen der Distributionen wird [pyinstaller](https://pyinstaller.readthedocs.io/en/stable/index.html) verwendet.  
Schritte zum Erstellen einer Distribution: 
- Erstelle eine .spec Datei für die main.py (einmalig)  

- Erstelle die Distribution basierend auf der erstellten .spec Datei:
    ```shell
    pyinstaller --clean specs/SPECNAME.spec
    ```
    Nachdem mit pyinstaller die Distribution erstellt wurde, ist diese in im `dist/` folder zu finden.  


#### Windows

.spec Datei erstellen und anschließend Distribution erstellen:  
```shell
pyi-makespec main.py --specpath "specs//" --add-binary "..\tools\chromedriver\chromedriver-windows.exe;tools\chromedriver\" --name windows-terminservice --hidden-import plyer.platforms.win.notification --hidden-import cloudscraper --add-data "../tools/cloudscraper;./cloudscraper/" --icon "..images\spritze.ico"

pyinstaller --clean specs/windows-terminservice.spec
```

#### Linux
```shell 
pyi-makespec main.py --specpath "specs//" --add-binary "../tools/chromedriver/chromedriver-linux-64:tools/chromedriver/" --name linux-64-terminservice --hidden-import cloudscraper --add-data "../tools/cloudscraper;./cloudscraper/" --icon "..images\spritze.ico"

pyinstaller --clean specs/linux-64-terminservice.spec

```

#### Resources
- [pyinstaller docs](https://pyinstaller.readthedocs.io/en/stable/index.html)
