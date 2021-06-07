from telegram.ext import Updater
from telegram.ext import CommandHandler
from telegram.ext import MessageHandler
from telegram.ext import CallbackQueryHandler
from telegram.ext import Filters
from telegram import InlineKeyboardButton
from telegram import InlineKeyboardMarkup
from telegram import utils
import threading
import copy
import tools.PythonTelegramWraper.botBackend as backend

class Bot:
    def __init__(self,use_userfile=True,api_token=None):
        self.botBackend=backend.Backend(use_userfile,api_token)


    def chatID(self,update):
        '''
        Get the chat id of an update object
        '''
        return update.effective_chat.id

    #Specify command without slash e.g. "start"
    def addBotCommand(self,command, function):
        '''
        Normal Telegram command,
        e.g command = "subscribe" then this method will be called when someone types: "/subscribe"
        '''
        handle = CommandHandler(command, function)
        self.botBackend.dispatcher.add_handler(handle)

    #Filter param is e.g. Filters.photo
    def addBotMessage(self,filter, function):
        '''
        Filter param is e.g. Filters.photo
        '''
        handle = MessageHandler(filter, function)
        self.botBackend.dispatcher.add_handler(handle)


    def startBot(self):
        '''
        Starts the bot
        '''
        self.botBackend.updater.start_polling()
    
    def start_Bot_Async(self):
        '''
        Starts the bot without blocking
        '''
        x = threading.Thread(target=self.botBackend.updater.start_polling,daemon=True)
        x.start()

    def save(self):
        '''
        Stores the user data in the user.json
        '''
        self.botBackend.user.saveUser(self.botBackend.users)


    def modifyUser(self,chatID,data=None):
        '''
        Changes the data of a user to the supplied data, creates user if not existing
        '''
        self.botBackend.user.modifyUser(self.botBackend.users,chatID,data)


    def user(self,chatID):
        '''
        Gets the data of a user (None if not existing)
        '''
        return self.botBackend.user.getUser(self.botBackend.users,chatID)

    def removeUser(self,chatID):
        '''
        Removes a user
        '''
        self.botBackend.user.removeUser(self.botBackend.users,chatID)

    def sendMessage(self,chatID, message,isHTML=False,rpl_markup=None,no_web_page_preview=False):
        if not isHTML:
            self.botBackend.updater.bot.sendMessage(int(chatID), 
                        message, 
                        parse_mode="Markdown",reply_markup=rpl_markup,disable_web_page_preview=no_web_page_preview)
        else:
            self.botBackend.updater.bot.sendMessage(int(chatID), 
                        message, 
                        parse_mode="HTML",reply_markup=rpl_markup,disable_web_page_preview=no_web_page_preview)

    def sendPhoto(self,chatID, src, captionText=None):
        self.botBackend.dispatcher.bot.send_photo(chat_id=chatID, photo=src,caption=captionText,parse_mode="Markdown")

    #Return a copy of the user data
    #!Can be huge!
    def getUserData(self):
        '''
        Returns all users with their data -> chatID:<data>
        '''
        return copy.deepcopy(self.botBackend.users)

    def getUserDataOriginal(self):
        return self.botBackend.users

    def getBot(self):
        return self.botBackend.updater.bot

    def build_menu(self,buttons,
                n_cols,
                header_buttons=None,
                footer_buttons=None):
        menu = [buttons[i:i + n_cols] for i in range(0, len(buttons), n_cols)]
        if header_buttons:
            menu.insert(0, [header_buttons])
        if footer_buttons:
            menu.append([footer_buttons])
        return menu