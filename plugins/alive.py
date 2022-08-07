from pyrogram import Client, filters, types
from pyrogram import __version__
import time

def format_time(seconds):
    a=str(seconds//3600)
    b=str((seconds%3600)//60)
    c=str((seconds%3600)%60)
    d=["{} hours {} mins {} seconds".format(a, b, c)]
    return d



@Client.on_message(filters.command('alive'))
async def reply_alive(bot: Client, msg: types.Message):
    await msg.reply(
        f'Iam alive!\n\n'
        f'Uptime: `{format_time(round(time.time() - bot.start_time))}`'
        f'\n\nPyrogram Version: `{__version__}`')