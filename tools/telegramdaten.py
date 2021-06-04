import json

def load(filepath: str):
    try:
        with open(filepath) as f:
            inp = f.read()
            try:
                telegram_json=json.loads(inp)

                if telegram_json["token"] != "" and telegram_json["chatid"]:
                    print("Telegram data successfully loaded, telegram will be used")
                    print()
                    return telegram_json
                
            except json.JSONDecodeError:
                print("Error: Fehler beim parsen der telegram daten")
            except KeyError:
                print("Error: telegram.json muss 'token' und 'chatid' beinhalten")
    except:
        pass    
    
    return None