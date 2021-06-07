from telegram.ext import Updater
from telegram.ext import CommandHandler
from telegram.ext import MessageHandler
from telegram.ext import CallbackQueryHandler
from telegram.ext import Filters
from telegram import InlineKeyboardButton
from telegram import InlineKeyboardMarkup
from telegram import utils




class Backend:
    def __init__(self, use_userfile=True,api_token=None):
        #Setting up the dispatcher in which the available
        #bot messages will be stored

        if api_token is None:
            import tools.PythonTelegramWraper.config as config
            token=config.telegramToken
        else:
            token=api_token

        self.updater = Updater(token, use_context=True)
        self.dispatcher = self.updater.dispatcher

        if use_userfile:
            import tools.PythonTelegramWraper.user as user
            #Setting up cache
            self.users=user.loadUser()