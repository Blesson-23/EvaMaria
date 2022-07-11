import shutil
import aiohttp
import aiofiles
from typing import List, Tuple
from bs4 import BeautifulSoup
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, InputMediaPhoto
from PIL import Image, ImageDraw, ImageFont


STATUS = {}
URI = "https://www.brandcrowd.com/maker/logos"
HEADERS = {"User-Agent": 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) '
                         'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/37'
                         '.0.2062.124 Safari/537.36'}


#logo
async def logo_maker(text: str, keyword: str = "name"):
    """ fetch logos from website """
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        resp = await session.get(
            URI, params={'text': text, 'SearchText': keyword}
        )
        soup = BeautifulSoup(await resp.text(), "lxml")
    embed = soup.findAll("div", {'class': "responsive-embed"})
    img_tags = [(i.find("img"), i.find("a")) for i in embed]
    logos = []
    for img in img_tags:
        src = img[0].get("src")
        if src:
            logos.append(
                (src, getattr(img[1], 'get', {}.get)("href", ""))
            )
    return logos


async def download(uri: str, file_name: str):
    """ download a uri """
    if not os.path.exists("temp_logos/"):
        os.mkdir("temp_logos/")
    async with \
            aiofiles.open(file_name, "wb+") as file, \
            aiohttp.ClientSession(headers=HEADERS) as session, \
            session.get(uri) as response:
        while 1:
            chunk = await response.content.read(512)
            if not chunk:
                return file_name
            await file.write(chunk)


async def dispatch(message: Message, logos: List[Tuple[str]]):
    """ dispatch logos to chat """
    global STATUS  # pylint: disable=global-statement
    global check
    group: List[InputMediaPhoto] = []
    paths: List[str] = []
    src: str = "Source: <a href='https://www.brandcrowd.com{}'>Here</a>"
    count: int = 1
    file_name: str = "temp_logos/logo_{}.jpg"
    status = await check.edit("`Beginning To Dispatch Content...`")
    batch = 1
    for logo in logos:
        direct, source = logo
        try:
            loc = await download(direct, file_name.format(count))
            paths.append(loc)
            group.append(InputMediaPhoto(loc, caption=src.format(source)))
            if len(group) == 10:
                try:
                    await check.edit(
                        f"`Uploading Batch {batch}/{round(len(logos) / 10)}...`")
                    await message.reply_media_group(group)
                except Exception as pyro:
                    print(pyro)
                batch += 1
                group.clear()
            count += 1
        except Exception as e:
            print(e)

    if len(group) >= 2:
        await check.edit(
            f"`Uploading Batch {batch}/{round(len(logos)/10)}`")
        await message.reply_media_group(group)
    elif len(group) == 1:
        await message.reply_photo(group[0].media, caption=group[0].caption)
    await check.delete()
    STATUS = False
    if os.path.exists("temp_logos/"):
        shutil.rmtree("temp_logos/", ignore_errors=True)

@Client.on_message(filters.private & filters.command("logo"))
async def jv_logo_maker(bot, message: Message):
    global STATUS  # pylint: disable=global-statement
    global check
    try:
        jv_text = (message.text.split(" ", 1))[1]
    except:
        await message.reply("Use Command with name Eg: `/logo BotBot`")
        return False
    if STATUS:
        return await message.reply("Let the current process be completed!!")
    STATUS = True
    jv_text = (message.text.split(" ", 1))[1]
    if not jv_text:
        return await message.reply("Input Required!!")
    check = await message.reply("Please wait...")

    type_keyword = "name"
    type_text = jv_text
    if ':' in jv_text:
        type_text, type_keyword = jv_text.split(":", 1)
    try:
        logos = await logo_maker(type_text, type_keyword)
    except Exception as e:
        print(e)
        STATUS = False
        return await message.reply("No Logos for Ya 😒😒😏")
    await dispatch(message, logos)
