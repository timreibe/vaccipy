import json

def load(filepath: str):
    try:
        with open(filepath) as f:
            inp = f.read()
            try:
                telegram_json=json.loads(inp)

                if telegram_json["token"] != "" and telegram_json["chatid"] != "":
                    print("Telegram daten erfolgreich geladen. Telegram-Benachrichtigungen aktiviert!")
                    print()
                    return telegram_json
                else:
                    print("Error: Token und ChatID dürfen nicht leer sein")
                
            except json.JSONDecodeError:
                print("Error: Fehler beim parsen der telegram daten")
            except KeyError:
                print("Error: telegram.json muss 'token' und 'chatid' beinhalten")
    except:
        pass 
       
    print()
    return None