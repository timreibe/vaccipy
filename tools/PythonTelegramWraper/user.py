import json

def saveUser(users):
    with open('user.json', 'w') as f:
        json.dump(users, f)

def loadUser():
    users={}
    try:
        with open('user.json') as json_file:
            users = json.load(json_file)
    except:
        print("Loading error")
    return users

def modifyUser(users,chatID,data=None):
    users.update( {str(chatID) : data} )
    saveUser(users)

def removeUser(users,chatID):
    if str(chatID) in users:
        del users[str(chatID)]
        saveUser(users)

def getUser(users,chatID):
    if(str(chatID) in users):
        return users[str(chatID)]
    else:
        return None