import botLib
from config import TOKEN
import telebot
print(TOKEN)
bot = botLib.B(TOKEN)

@bot.bot.message_handler(commands=["start"])
def start(message):
    bot.start(message)

bot.bot.infinity_polling()