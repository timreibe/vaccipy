# FAQ

## Was bedeutet "Einloggen mit Code nicht möglich"?
Das einloggen mit dem Code ist optional. Die Terminabfrage und Buchung wird dennoch durchgeführt. 

## Was kann ich machen, wenn ich keine SMS beim Code generieren erhalte?
Der Impfterminservice blockiert temporär E-mail Adressen und Telefonnummern. Um den Block zu umgehen muss eine alternative E-Mail Adresse und Telefonnummer verwenden werden oder bis zu 24 Stunden abgewartet werden.   

## Wie erzeuge ich manuelle Cookies die für das Code generieren benötigt werden?  

1. Skript läuft in Botprotecion Fehler:
![image](https://user-images.githubusercontent.com/48892674/119194323-30f86780-ba83-11eb-8c9f-3ba709036752.png)
2.  Impterminservice im Browser (Chrome) öffnen beispielsweise: https://www.impfterminservice.de/impftermine 

3. Chrome Entwickler-Konsole öffnen über F12 

4. In den Tab "**Network**" gehen und Seite neu laden, sodass Requests zu sehen sind:
![image](https://user-images.githubusercontent.com/48892674/119194687-c09e1600-ba83-11eb-88d6-a7c440de8bdd.png)

5. Erster Request auswählen und unter **Request Headers** den Wert "**Cookie**" kopieren. (Ohne **"Cookie:"** lediglich der **Wert nach dem Doppeltpunkt**)
![image](https://user-images.githubusercontent.com/48892674/119194979-2e4a4200-ba84-11eb-8391-bfa52aaa74d6.png)

6. Wert in die Konsole kopieren und mit Enter bestätigen

### **ACHTUNG!!!**
Cookies sind nur valide, wenn der Impfterminservice mindestens eine halbe Stunde oder länger im Browser geöffnet ist und ein normales Verhalten (Klicks, Seitenaufrufe, Eingaben) ausgeführt wurde. Nachdem Cookies gelöscht wurden oder wenn der Impfterminservice das erste Mal im Browser geöffnet wird muss abgewartet werden bis die Cookies valide sind und im Skript funktionieren:

![image](https://user-images.githubusercontent.com/48892674/119195883-9ea59300-ba85-11eb-982d-e00eb55de313.png)
  


