## Distributionen

Für eine bessere Nutzererfahrung erstellen wir verschiedene Distributionen, die ohne installation von Python direkt ausgeführt werden können.  
Diese sind im Abschnitt `assets` des [neusten Release](https://github.com/iamnotturner/vaccipy/releases/latest 
) zu finden.  


### Download 
Verfügbare Distributionen:
- [x] [Windows](https://cntr.click/rS9Ds4R)  
- [x] [Linux](https://cntr.click/mN1MPzc) 
- [ ] MacOS Intel
- [ ] MacOS M1

**Ausführung Windows:** 
- installer ausführen
- vaccipy installieren
- vaccipy ausführen
- (INFO: Vaccipy kann später auch wieder deinstalliert werden)

**Ausführung Linux:**
- .zip Ordner entpacken
- Eventuell notwendig: Die Terminservice- und Driver-Executable ausführbar machen.
Dazu das Terminal zum `linux-64-terminservice`-Ordner navigieren und folgende Befehle ausführen:  
  `sudo -- sh -c 'chmod +x ./linux-64-terminservice; chmod +x ./tools/chromedriver/chromedriver-linux-64'`
- Im `linux-64-terminservice`-Ordner die `./linux-64-terminsvervice` executable per Terminal ausführen. 

Für mehr Info zum Verteilen und Erstellen der Distributionen: [Shipping und Releases](#Shipping-und-releases)

## Shipping und Releases

Es gibt aktuell zwei aktive Worklflows: 
* der [Build Workflow](https://github.com/iamnotturner/vaccipy/actions/workflows/build.yaml) wird bei jedem push gestartet und überprüft ob die aktuellen Änderungen auch in ein Build gebaut werden können.
* der [Deploy Workflow](https://github.com/iamnotturner/vaccipy/actions/workflows/deploy.yaml) wird bei jedem push eines [Tags](https://git-scm.com/book/en/v2/Git-Basics-Tagging) gestartet und erstellt ein neues Build sowie ein neues Release dazu.   
</br>

### Wie werden Releases erstellt ?

Um ein neues Release zu erstellen, muss ein neues Tag (dessen Name mit `v` starten und im Format vx.y.z ist bsp. `v1.1.0`) zu dem neuesten Stand (Commit) erst hinzugefügt und dann gepushed werden. Das startet den [Deploy Workflow](https://github.com/iamnotturner/vaccipy/actions/workflows/deploy.yaml).  
</br>

### Wie werden Distributionen erstellt ? 

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

### Windows Installer
Für den Windows installer wird aktuell [Inno Setup](https://jrsoftware.org/isinfo.php) verwendet.  
Im [Deploy Workflow](https://github.com/iamnotturner/vaccipy/actions/workflows/deploy.yaml) führt der Inno Setup Compiler das  `windows-terminservice.iss` Script aus, welches die zuvor von Pyinstaller gebaute Distribution, in einen Installer packt. 

**Tipp:** Zum erstellen und bearbeiten des .iss Scripts empfiehlt sich der `Inno Script Studio script editor` welcher im [QuickStart Pack](https://jrsoftware.org/download.php/ispack.exe) vorhanden ist. 

#### Resources
- [pyinstaller docs](https://pyinstaller.readthedocs.io/en/stable/index.html)
- [Inno Setup](https://jrsoftware.org/isinfo.php)
