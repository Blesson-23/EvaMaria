# Kanged From @TroJanZheX
import asyncio
import re
import ast
from datetime import datetime
from pyrogram.errors.exceptions.bad_request_400 import MediaEmpty, PhotoInvalidDimensions, WebpageMediaEmpty
from Script import script
import pyrogram
from database.connections_mdb import active_connection, all_connections, delete_connection, if_active, make_active, \
    make_inactive
from info import ADMINS, AUTH_CHANNEL, AUTH_USERS, CUSTOM_FILE_CAPTION, AUTH_GROUPS, P_TTI_SHOW_OFF, IMDB, DELETE_TIME, \
    UNAUTHORIZED_CALLBACK_TEXT, SINGLE_BUTTON, SPELL_CHECK_REPLY, IMDB_TEMPLATE
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram import Client, filters
from pyrogram.errors import FloodWait, UserIsBlocked, MessageNotModified, PeerIdInvalid
from utils import get_size, is_subscribed, get_poster, search_gagala, temp, get_settings, save_group_settings
from database.users_chats_db import db
from database.ia_filterdb import Media, get_file_details, get_search_results
from database.filters_mdb import (
    del_all,
    find_filter,
    get_filters,
)
from pytz import timezone
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)

BUTTONS = {}
SPELL_CHECK = {}



@Client.on_message((filters.group | filters.private) & filters.text & ~filters.edited & filters.incoming)
async def give_filter(client, message):
    k = await manual_filters(client, message)
    if k == False:
        await auto_filter(client, message)

@Client.on_callback_query(filters.regex(r"^next"))
async def next_page(bot, query: CallbackQuery):
    ident, req, key, offset = query.data.split("_")
    if int(req) not in [query.from_user.id, 0]:
        return await query.answer("oKda", show_alert=True)
    try:
        offset = int(offset)
    except:
        offset = 0
    search = BUTTONS.get(key)
    if not search:
        await query.answer("You are using one of my old messages, please send the request again.", show_alert=True)
        return

    files, n_offset, total = await get_search_results(search, offset=offset, filter=True)
    try:
        n_offset = int(n_offset)
    except:
        n_offset = 0

    if not files:
        return
    settings = await get_settings(query.message.chat.id)
    pre = 'Chat' if settings.get('redirect_to') == 'Chat' else 'files'

    if settings['button']:
        btn = [
            [
                InlineKeyboardButton(
                    text=f"⬛️ [{get_size(file.file_size)}] {file.file_name}", callback_data=f'{pre}#{file.file_id}#{query.from_user.id}'
                ),
            ]
            for file in files
        ]
    else:
        btn = [
            [
                InlineKeyboardButton(
                    text=f"⬛️ [{get_size(file.file_size)}] {file.file_name}", callback_data=f'{pre}#{file.file_id}#{query.from_user.id}'
                ),
            ]
            for file in files
        ]
    try:
        btn.insert(0, query.message.reply_markup.inline_keyboard[1])
        btn.insert(0, query.message.reply_markup.inline_keyboard[0])
    except Exception as e:
        logger.error(e)
        pass

    if 0 < offset <= 5:
        off_set = 0
    elif offset == 0:
        off_set = None
    else:
        off_set = offset - 5
    if n_offset == 0:
        btn.append(
            [InlineKeyboardButton("📖 BACK", callback_data=f"next_{req}_{key}_{off_set}"),
             InlineKeyboardButton(f"📃 Pages {round(int(offset) / 5) + 1} / {round(total / 5)}",
                                  callback_data="pages")]
        )
    elif off_set is None:
        btn.append(
            [InlineKeyboardButton(f"🗓 {round(int(offset) / 5) + 1} / {round(total / 5)}", callback_data="pages"),
             InlineKeyboardButton("NEXT 📖", callback_data=f"next_{req}_{key}_{n_offset}")])
    else:
        btn.append(
            [
                InlineKeyboardButton("📖 BACK", callback_data=f"next_{req}_{key}_{off_set}"),
                InlineKeyboardButton(f"🗓 {round(int(offset) / 5) + 1} / {round(total / 5)}", callback_data="pages"),
                InlineKeyboardButton("NEXT 📖", callback_data=f"next_{req}_{key}_{n_offset}")
            ],
        )
    try:
        await query.edit_message_reply_markup(
            reply_markup=InlineKeyboardMarkup(btn)
        )
    except MessageNotModified:
        pass
    await query.answer()


@Client.on_callback_query(filters.regex(r"^spolling"))
async def advantage_spoll_choker(bot, query):
    _, user, movie_ = query.data.split('#')
    if int(user) != 0 and query.from_user.id != int(user):
        return await query.answer("okDa", show_alert=True)
    if movie_ == "close_spellcheck":
        return await query.message.delete()
    movies = SPELL_CHECK.get(query.message.reply_to_message.message_id)
    if not movies:
        return await query.answer("You are clicking on an old button which is expired.", show_alert=True)
    movie = movies[(int(movie_))]
    await query.answer('Checking for Movie in database...')
    k = await manual_filters(bot, query.message, text=movie)
    if k == False:
        files, offset, total_results = await get_search_results(movie, offset=0, filter=True)
        if files:
            k = (movie, files, offset, total_results)
            await auto_filter(bot, query, k)
        else:
            k = await query.message.edit('This Movie Not Found In DataBase')
            await asyncio.sleep(10)
            await k.delete()


@Client.on_callback_query()
async def cb_handler(client: Client, query: CallbackQuery):
    if query.data == "close_data":
        await query.message.delete()
    elif query.data == "delallconfirm":
        userid = query.from_user.id
        chat_type = query.message.chat.type

        if chat_type == "private":
            grpid = await active_connection(str(userid))
            if grpid is not None:
                grp_id = grpid
                try:
                    chat = await client.get_chat(grpid)
                    title = chat.title
                except:
                    await query.message.edit_text("Make sure I'm present in your group!!", quote=True)
                    return await query.answer('Piracy Is Crime')
            else:
                await query.message.edit_text(
                    "I'm not connected to any groups!\nCheck /connections or connect to any groups",
                    quote=True
                )
                return await query.answer('Piracy Is Crime')

        elif chat_type in ["group", "supergroup"]:
            grp_id = query.message.chat.id
            title = query.message.chat.title

        else:
            return await query.answer('Piracy Is Crime')

        st = await client.get_chat_member(grp_id, userid)
        if (st.status == "creator") or (str(userid) in ADMINS):
            await del_all(query.message, grp_id, title)
        else:
            await query.answer("You need to be Group Owner or an Auth User to do that!", show_alert=True)
    elif query.data == "delallcancel":
        userid = query.from_user.id
        chat_type = query.message.chat.type

        if chat_type == "private":
            await query.message.reply_to_message.delete()
            await query.message.delete()

        elif chat_type in ["group", "supergroup"]:
            grp_id = query.message.chat.id
            st = await client.get_chat_member(grp_id, userid)
            if (st.status == "creator") or (str(userid) in ADMINS):
                await query.message.delete()
                try:
                    await query.message.reply_to_message.delete()
                except:
                    pass
            else:
                await query.answer("That's not for you!!", show_alert=True)
    elif "groupcb" in query.data:
        await query.answer()

        group_id = query.data.split(":")[1]

        act = query.data.split(":")[2]
        hr = await client.get_chat(int(group_id))
        title = hr.title
        user_id = query.from_user.id

        if act == "":
            stat = "CONNECT"
            cb = "connectcb"
        else:
            stat = "DISCONNECT"
            cb = "disconnect"

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"{stat}", callback_data=f"{cb}:{group_id}"),
             InlineKeyboardButton("DELETE", callback_data=f"deletecb:{group_id}")],
            [InlineKeyboardButton("BACK", callback_data="backcb")]
        ])

        await query.message.edit_text(
            f"Group Name : **{title}**\nGroup ID : `{group_id}`",
            reply_markup=keyboard,
            parse_mode="md"
        )
        return await query.answer('Piracy Is Crime')
    elif "connectcb" in query.data:
        await query.answer()

        group_id = query.data.split(":")[1]

        hr = await client.get_chat(int(group_id))

        title = hr.title

        user_id = query.from_user.id

        mkact = await make_active(str(user_id), str(group_id))

        if mkact:
            await query.message.edit_text(
                f"Connected to **{title}**",
                parse_mode="md"
            )
        else:
            await query.message.edit_text('Some error occurred!!', parse_mode="md")
        return await query.answer('Piracy Is Crime')
    elif "disconnect" in query.data:
        await query.answer()

        group_id = query.data.split(":")[1]

        hr = await client.get_chat(int(group_id))

        title = hr.title
        user_id = query.from_user.id

        mkinact = await make_inactive(str(user_id))

        if mkinact:
            await query.message.edit_text(
                f"Disconnected from **{title}**",
                parse_mode="md"
            )
        else:
            await query.message.edit_text(
                f"Some error occurred!!",
                parse_mode="md"
            )
        return await query.answer('Piracy Is Crime')
    elif "deletecb" in query.data:
        await query.answer()

        user_id = query.from_user.id
        group_id = query.data.split(":")[1]

        delcon = await delete_connection(str(user_id), str(group_id))

        if delcon:
            await query.message.edit_text(
                "Successfully deleted connection"
            )
        else:
            await query.message.edit_text(
                f"Some error occurred!!",
                parse_mode="md"
            )
        return await query.answer('Piracy Is Crime')
    elif query.data == "backcb":
        await query.answer()

        userid = query.from_user.id

        groupids = await all_connections(str(userid))
        if groupids is None:
            await query.message.edit_text(
                "There are no active connections!! Connect to some groups first.",
            )
            return await query.answer('Piracy Is Crime')
        buttons = []
        for groupid in groupids:
            try:
                ttl = await client.get_chat(int(groupid))
                title = ttl.title
                active = await if_active(str(userid), str(groupid))
                act = " - ACTIVE" if active else ""
                buttons.append(
                    [
                        InlineKeyboardButton(
                            text=f"{title}{act}", callback_data=f"groupcb:{groupid}:{act}"
                        )
                    ]
                )
            except:
                pass
        if buttons:
            await query.message.edit_text(
                "Your connected group details ;\n\n",
                reply_markup=InlineKeyboardMarkup(buttons)
            )
    elif "alertmessage" in query.data:
        grp_id = query.message.chat.id
        i = query.data.split(":")[1]
        keyword = query.data.split(":")[2]
        reply_text, btn, alerts, fileid = await find_filter(grp_id, keyword)
        if alerts is not None:
            alerts = ast.literal_eval(alerts)
            alert = alerts[int(i)]
            alert = alert.replace("\\n", "\n").replace("\\t", "\t")
            await query.answer(alert, show_alert=True)

    if query.data.startswith("file"):
        ident, file_id, rid = query.data.split("#")

        if int(rid) not in [query.from_user.id, 0]:
            return await query.answer(UNAUTHORIZED_CALLBACK_TEXT, show_alert=True)

        files_ = await get_file_details(file_id)
        if not files_:
            return await query.answer('No such file exist.')
        files = files_[0]
        title = files.file_name
        size = get_size(files.file_size)
        f_caption = files.caption
        settings = await get_settings(query.message.chat.id)
        if CUSTOM_FILE_CAPTION:
            try:
                f_caption = CUSTOM_FILE_CAPTION.format(file_name='' if title is None else title,
                                                       file_size='' if size is None else size,
                                                       file_caption='' if f_caption is None else f_caption)
            except Exception as e:
                logger.exception(e)
            f_caption = f_caption
        if f_caption is None:
            f_caption = f"{files.file_name}"

        try:
            if AUTH_CHANNEL and not await is_subscribed(client, query):
                await query.answer(url=f"https://t.me/{temp.U_NAME}?start={ident}_{file_id}")
                return
            elif settings['botpm']:
                await query.answer(url=f"https://t.me/TG_Animated_bot?start={ident}_{file_id}")
                return
            else:
                await client.send_cached_media(
                    chat_id=query.from_user.id,
                    file_id=file_id,
                    caption=f_caption,
                    protect_content=True if ident == "filep" else False 
                )
                if query.message.chat.type != "private":
                    await query.answer('Check PM, I have sent files in pm', show_alert=True)
                else:
                    await query.answer()
        except UserIsBlocked:
            await query.answer('Unblock the bot mahn !', show_alert=True)
        except PeerIdInvalid:
            await query.answer(url=f"https://t.me/TG_Animated_bot?start={ident}_{file_id}")
        except Exception as e:
            await query.answer(url=f"https://t.me/TG_Animated_bot?start={ident}_{file_id}")

    # https://github.com/AlbertEinsteinTG/EvaMaria-Mod/blob/b8f72d384bc900cf5399f820805ab0b9b42abd11/plugins/pm_filter.py#L393
    elif query.data.startswith("Chat"): 
        ident, file_id, rid = query.data.split("#")

        if int(rid) not in [query.from_user.id, 0]:
            return await query.answer(UNAUTHORIZED_CALLBACK_TEXT, show_alert=True)

        files_ = await get_file_details(file_id)
        if not files_:
            return await query.answer('No such file exist.')
        files = files_[0]
        title = files.file_name
        size = get_size(files.file_size)
        f_caption = files.caption
        settings = await get_settings(query.message.chat.id)
        if CUSTOM_FILE_CAPTION:
            try:
                f_caption = CUSTOM_FILE_CAPTION.format(file_name='' if title is None else title,
                                                       file_size='' if size is None else size,
                                                       file_caption='' if f_caption is None else f_caption)
            except Exception as e:
                logger.exception(e)
            f_caption = f_caption
        if f_caption is None:
            f_caption = f"{files.file_name}"

        try:
            if AUTH_CHANNEL and not await is_subscribed(client, query):
                await query.answer(url=f"https://t.me/{temp.U_NAME}?start={ident}_{file_id}")
                return
            elif settings['botpm']:
                await query.answer(url=f"https://t.me/{temp.U_NAME}?start={ident}_{file_id}")
                return
            else:
                await client.send_cached_media(
                    chat_id=query.from_user.id,
                    file_id=file_id,
                    caption=f_caption,
                    protect_content=True if ident == "filep" else False 
                )
                await query.answer('𝗖𝗛𝗘𝗖𝗞 𝗣𝗠 , 𝗜 𝗛𝗔𝗩𝗘 𝗦𝗘𝗡𝗧 𝗙𝗜𝗟𝗘𝗦 𝗢𝗡 𝗬𝗢𝗨𝗥 𝗣𝗠', show_alert=True)
        except UserIsBlocked:
            await query.answer('Unblock the bot mahn !', show_alert=True)
        except PeerIdInvalid:
            await query.answer(url=f"https://t.me/{temp.U_NAME}?start={ident}_{file_id}")
        except Exception as e:
            await query.answer(url=f"https://t.me/{temp.U_NAME}?start={ident}_{file_id}")
    elif query.data.startswith("checksub"):
        if AUTH_CHANNEL and not await is_subscribed(client, query):
            await query.answer("𝗔𝗬𝗬𝗔𝗗𝗔 𝗡𝗘𝗘 𝗢𝗥𝗨 𝗞𝗜𝗟𝗟𝗔𝗗𝗜 𝗧𝗛𝗔𝗡𝗡𝗘 , 𝗣𝗢𝗬𝗜 𝗝𝗢𝗜𝗡 𝗖𝗛𝗘𝗬𝗧𝗛𝗜𝗧 𝗜𝗩𝗜𝗗𝗘 𝗡𝗝𝗘𝗞𝗞 𝗦𝗘𝗧𝗧𝗔𝗬𝗜 !", show_alert=True)
            return
        ident, file_id = query.data.split("#")
        files_ = await get_file_details(file_id)
        if not files_:
            return await query.answer('𝗔𝗬𝗬𝗢𝗗𝗔 𝗠𝗢𝗡𝗘 , 𝗔𝗧𝗛 𝗜𝗣𝗣𝗢 𝗜𝗟𝗟𝗔.')
        files = files_[0]
        title = files.file_name
        size = get_size(files.file_size)
        f_caption = files.caption
        if CUSTOM_FILE_CAPTION:
            try:
                f_caption = CUSTOM_FILE_CAPTION.format(file_name='' if title is None else title,
                                                       file_size='' if size is None else size,
                                                       file_caption='' if f_caption is None else f_caption)
            except Exception as e:
                logger.exception(e)
                f_caption = f_caption
        if f_caption is None:
            f_caption = f"{title}"
        await query.answer()
        await client.send_cached_media(
            chat_id=query.from_user.id,
            file_id=file_id,
            caption=f_caption,
            protect_content=True if ident == 'checksubp' else False
        )
    elif query.data == "pages":
        await query.answer()
    elif query.data == "start":
        await query.message.delete()
        buttons = [[
            InlineKeyboardButton('🟥𝗔𝗗𝗗 𝗠𝗘 𝗧𝗢 𝗬𝗢𝗨𝗥 𝗚𝗥𝗢𝗨𝗣 ➕', url=f'http://t.me/{temp.U_NAME}?startgroup=true')
        ], [
            InlineKeyboardButton('Search🔎', switch_inline_query_current_chat='')
        ], [
            InlineKeyboardButton('🌈Help', callback_data='help'),
            InlineKeyboardButton('📣ᴀʙᴏᴜᴛ', callback_data='about')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await client.send_sticker(
            sticker="CAACAgUAAxkBAAEER65i3VOkR5v5cKMvXF7MhrxDRnEc1gAC-AYAAnly6VZVNMIwo-_zvh4E",
            chat_id=query.message.chat.id,
            reply_markup=reply_markup
           # parse_mode='html'
        )
        await query.answer('Piracy Is Crime')
    elif query.data == "help":
        await query.message.delete()
        buttons = [[
            InlineKeyboardButton('Help', callback_data='help_2'),
            InlineKeyboardButton('👩‍🦯 Back', callback_data='start')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await client.send_sticker(
            sticker="CAACAgUAAxkBAAEERzdi3UsUn-qQC6X7l-guRUYB0iarnwACDQYAAhoK8VY7LV1GrM1MNB4E",
            chat_id=query.message.chat.id,
            reply_markup=reply_markup
            #parse_mode='html'
        )
    elif query.data == "about":
        await query.message.delete()
        buttons = [[
            InlineKeyboardButton('🟥ᴀʙᴏᴜᴛ', callback_data='button')
            ],[
            InlineKeyboardButton('🏘️Home', callback_data='start'),
            InlineKeyboardButton('🚪Close', callback_data='close_data')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await client.send_sticker(
            sticker="CAACAgUAAxkBAAEER5Zi3VJkYdV7ckpHFZtoYWK_p66lagACjwUAAgw28VaLZ-5l3tR2ex4E",
            chat_id=query.message.chat.id,
            reply_markup=reply_markup
            #parse_mode='html'
        )
    elif query.data == "source":
        await query.message.delete()
        buttons = [[
            InlineKeyboardButton('👩‍🦯 Back', callback_data='about')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await client.send_message(
            text=script.SOURCE_TXT,
            chat_id=query.message.chat.id,
            reply_markup=reply_markup,
            parse_mode='html'
        )
    elif query.data == "help_2":
        await query.message.delete()
        buttons = [[
            InlineKeyboardButton('Basic', callback_data='basic'),
            InlineKeyboardButton('TTS', callback_data='txtts'),
            InlineKeyboardButton('Logo', callback_data='logo')
            ],[
            InlineKeyboardButton('Carbon', callback_data='carb'),
            InlineKeyboardButton('Fun', callback_data='fu_n'),
            InlineKeyboardButton('IMDB', callback_data='i_md_b')
            ],[
            InlineKeyboardButton('Lyrics', callback_data='lyric'),
            InlineKeyboardButton('Telegraph', callback_data='telegra'),
            InlineKeyboardButton('Sticker Id', callback_data='stick')
            ],[
            InlineKeyboardButton('Google Translation', callback_data='g_tran'),
            InlineKeyboardButton('Misc', callback_data='mis'),
            InlineKeyboardButton('Time', callback_data='timeHelp')
            ],[
            InlineKeyboardButton('👩‍🦯 Back', callback_data='help')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await client.send_message(
            text=script.HELP_TXT.format(query.from_user.mention),
            chat_id=query.message.chat.id,
            reply_markup=reply_markup,
            disable_web_page_preview=True,
            parse_mode='html'
        )
    elif query.data == "help_3":
        buttons = [[
            InlineKeyboardButton('Basic', callback_data='basic'),
            InlineKeyboardButton('TTS', callback_data='txtts'),
            InlineKeyboardButton('Logo', callback_data='logo')
            ],[
            InlineKeyboardButton('Carbon', callback_data='carb'),
            InlineKeyboardButton('Fun', callback_data='fu_n'),
            InlineKeyboardButton('IMDB', callback_data='i_md_b')
            ],[
            InlineKeyboardButton('Lyrics', callback_data='lyric'),
            InlineKeyboardButton('Telegraph', callback_data='telegra'),
            InlineKeyboardButton('Sticker Id', callback_data='stick')
            ],[
            InlineKeyboardButton('Google Translation', callback_data='g_tran'),
            InlineKeyboardButton('Misc', callback_data='mis'),
            InlineKeyboardButton('Time', callback_data='timeHelp')
            ],[
            InlineKeyboardButton('👩‍🦯 Back', callback_data='help')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.HELP_TXT.format(query.from_user.mention),
            reply_markup=reply_markup,
            disable_web_page_preview=True,
            parse_mode='html')

    elif query.data == "basic":
        buttons = [[
            InlineKeyboardButton('Back', callback_data='help_3')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.BASIC,
            reply_markup=reply_markup,
            disable_web_page_preview=True,
            parse_mode='md'
        )
    elif query.data == "timeHelp":
        buttons = [[
            InlineKeyboardButton('Back', callback_data='help_3')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            '__Get Current date and time of any given timezone.__'
            '\n\nUsage Example: `/time Asia/Kolkata` - To get current time and date of Asia/Kolkata'
            '\nRefer this list for [full list](https://telegra.ph/Country-Codes-07-13) of available timezones.',
            reply_markup=reply_markup,
            disable_web_page_preview=True,
            parse_mode='md'
        )
    
    elif query.data == "txtts":
        buttons = [[
            InlineKeyboardButton('Back', callback_data='help_3')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.TTS,
            reply_markup=reply_markup,
            disable_web_page_preview=True,
            parse_mode='md'
        )
    elif query.data == "logo":
        buttons = [[
            InlineKeyboardButton('Back', callback_data='help_3')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.LOGO,
            reply_markup=reply_markup,
            disable_web_page_preview=True,
            parse_mode='md'
        )
    elif query.data == "carb":
        buttons = [[
            InlineKeyboardButton('Back', callback_data='help_3')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.CARBON,
            reply_markup=reply_markup,
            disable_web_page_preview=True,
            parse_mode='md'
        )
    elif query.data == "fu_n":
        buttons = [[
            InlineKeyboardButton('Back', callback_data='help_3')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.FUN,
            reply_markup=reply_markup,
            disable_web_page_preview=True,
            parse_mode='md'
        )
    elif query.data == "i_md_b":
        buttons = [[
            InlineKeyboardButton('Back', callback_data='help_3')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.IMDB,
            reply_markup=reply_markup,
            disable_web_page_preview=True,
            parse_mode='md'
        )
    elif query.data == "lyric":
        buttons = [[
            InlineKeyboardButton('Back', callback_data='help_3')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.LYRIC,
            reply_markup=reply_markup,
            disable_web_page_preview=True,
            parse_mode='md'
        )
    elif query.data == "telegra":
        buttons = [[
            InlineKeyboardButton('Back', callback_data='help_3')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.TELEGRAPH,
            reply_markup=reply_markup,
            disable_web_page_preview=True,
            parse_mode='md'
        )
    elif query.data == "stick":
        buttons = [[
            InlineKeyboardButton('Back', callback_data='help_3')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.STICKER_ID,
            reply_markup=reply_markup,
            disable_web_page_preview=True,
            parse_mode='md'
        )
    elif query.data == "g_tran":
        buttons = [[
            InlineKeyboardButton('Back', callback_data='help_3')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.G_TRANS,
            reply_markup=reply_markup,
            disable_web_page_preview=True,
            parse_mode='md'
        )
    elif query.data == "mis":
        buttons = [[
            InlineKeyboardButton('Back', callback_data='help_3')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.MISC,
            reply_markup=reply_markup,
            disable_web_page_preview=True,
            parse_mode='md'
        )

    elif query.data == "button":
        await query.message.delete()
        buttons = [[
            InlineKeyboardButton('👩‍🦯 Back', callback_data='about')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await client.send_message(
            text=script.ABOUT_TXT,
            chat_id=query.message.chat.id,
            reply_markup=reply_markup,
            disable_web_page_preview=True,
            parse_mode='html'
        )
    elif query.data == "autofilter":
        await query.message.delete()
        buttons = [[
            InlineKeyboardButton('👩‍🦯 Back', callback_data='help')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await client.send_message(
            text=script.AUTOFILTER_TXT,
            chat_id=query.message.chat.id,
            reply_markup=reply_markup,
            parse_mode='html'
        )
    elif query.data == "coct":
        await query.message.delete()
        buttons = [[
            InlineKeyboardButton('👩‍🦯 Back', callback_data='help')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await client.send_message(
            text=script.CONNECTION_TXT,
            chat_id=query.message.chat.id,
            reply_markup=reply_markup,
            parse_mode='html'
        )
    elif query.data == "extra":
        await query.message.delete()
        buttons = [[
            InlineKeyboardButton('👩‍🦯 Back', callback_data='help'),
            InlineKeyboardButton('👮‍♂️ Admin', callback_data='admin')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await client.send_message(
            text=script.EXTRAMOD_TXT,
            chat_id=query.message.chat.id,
            reply_markup=reply_markup,
            parse_mode='html'
        )
    elif query.data == "admin":
        await query.message.delete()
        buttons = [[
            InlineKeyboardButton('👩‍🦯 Back', callback_data='extra')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await client.send_message(
            text=script.ADMIN_TXT,
            chat_id=query.message.chat.id,
            reply_markup=reply_markup,
            parse_mode='html'
        )
    elif query.data == "stats":
        await query.message.delete()
        buttons = [[
            InlineKeyboardButton('👩‍🦯 Back', callback_data='help'),
            InlineKeyboardButton('♻️', callback_data='rfrsh')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        total = await Media.count_documents()
        users = await db.total_users_count()
        chats = await db.total_chat_count()
        monsize = await db.get_db_size()
        free = 536870912 - monsize
        monsize = get_size(monsize)
        free = get_size(free)
        await client.send_message(
            text=script.STATUS_TXT.format(total, users, chats, monsize, free),
            chat_id=query.message.chat.id,
            reply_markup=reply_markup,
            parse_mode='html'
        )
    elif query.data == "rfrsh":
        await query.answer("Fetching MongoDb DataBase")
        buttons = [[
            InlineKeyboardButton('👩‍🦯 Back', callback_data='help'),
            InlineKeyboardButton('♻️', callback_data='rfrsh')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        total = await Media.count_documents()
        users = await db.total_users_count()
        chats = await db.total_chat_count()
        monsize = await db.get_db_size()
        free = 536870912 - monsize
        monsize = get_size(monsize)
        free = get_size(free)
        await query.message.edit_text(
            text=script.STATUS_TXT.format(total, users, chats, monsize, free),
            reply_markup=reply_markup,
            parse_mode='html'
        )
    elif query.data.startswith("useless"):
        _, n = query.data.split("_")
        TEXTZ = {
            'info': "🚨𝗜𝗡𝗙𝗢𝗥𝗠𝗔𝗧𝗜𝗢𝗡\n\nRead 😌👇\n\nIF Y𝗼𝘂 DIDN'T  G𝗲𝘁 𝘆𝗼𝘂𝗿 REQYESTED M𝗼𝘃𝗶𝗲 / S𝗲𝗿𝗶𝗲𝘀 𝗰𝗹𝗶𝗰𝗸 𝗼𝗻 𝘁𝗵𝗲 𝗻𝗲𝘅𝘁 𝗽𝗮𝗴𝗲 𝗯𝘂𝘁𝘁𝗼𝗻 𝗮𝗻𝗱 𝗰𝗵𝗲𝗰𝗸 𝗶𝘁... 🌚✌️",
            'request': "𝗠𝗼𝘃𝗶𝗲 𝗿𝗲𝗾𝘂𝗲𝘀𝘁 𝗳𝗼𝗿𝗺𝗮𝘁\n\n𝗚𝗼 𝘁𝗼 𝗴𝗼𝗼𝗴𝗹𝗲 ➢ 𝗧𝘆𝗽𝗲 𝗺𝗼𝘃𝗶𝗲 𝗻𝗮𝗺𝗲 ➣ 𝗰𝗼𝗽𝘆 𝗰𝗼𝗿𝗿𝗲𝗰𝘁 𝗻𝗮𝗺𝗲 ➤ 𝗽𝗮𝘀𝘁𝗲 𝗼𝗻 𝗴𝗿𝗼𝘂𝗽\n\n𝗘𝘅𝗮𝗺𝗽𝗹𝗲 𝗺𝗮𝗹𝗶𝗸 2021\n\n𝗗𝗼𝗻'𝘁 𝘂𝘀𝗲 (/!,)"}
        await query.answer(TEXTZ[n], show_alert=True)
    elif query.data.startswith("setgs"):
        ident, set_type, status, grp_id = query.data.split("#")
        grpid = await active_connection(str(query.from_user.id))

        if str(grp_id) != str(grpid):
            await query.message.edit("Your Active Connection Has Been Changed. Go To /settings.")
            return await query.answer('Piracy Is Crime')

        if status == "True":
            await save_group_settings(grpid, set_type, False)
        else:
            await save_group_settings(grpid, set_type, True)

        settings = await get_settings(grpid)

        if settings is not None:
            buttons = [
                [
                    InlineKeyboardButton('Filter Button',
                                         callback_data=f'setgs#button#{settings["button"]}#{str(grp_id)}'),
                    InlineKeyboardButton('Single' if settings["button"] else 'Double',
                                         callback_data=f'setgs#button#{settings["button"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('Bot PM', callback_data=f'setgs#botpm#{settings["botpm"]}#{str(grp_id)}'),
                    InlineKeyboardButton('✅ Yes' if settings["botpm"] else '❌ No',
                                         callback_data=f'setgs#botpm#{settings["botpm"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('File Secure',
                                         callback_data=f'setgs#file_secure#{settings["file_secure"]}#{str(grp_id)}'),
                    InlineKeyboardButton('✅ Yes' if settings["file_secure"] else '❌ No',
                                         callback_data=f'setgs#file_secure#{settings["file_secure"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('IMDB', callback_data=f'setgs#imdb#{settings["imdb"]}#{str(grp_id)}'),
                    InlineKeyboardButton('✅ Yes' if settings["imdb"] else '❌ No',
                                         callback_data=f'setgs#imdb#{settings["imdb"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('Spell Check',
                                         callback_data=f'setgs#spell_check#{settings["spell_check"]}#{str(grp_id)}'),
                    InlineKeyboardButton('✅ Yes' if settings["spell_check"] else '❌ No',
                                         callback_data=f'setgs#spell_check#{settings["spell_check"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('Welcome', callback_data=f'setgs#welcome#{settings["welcome"]}#{str(grp_id)}'),
                    InlineKeyboardButton('✅ Yes' if settings["welcome"] else '❌ No',
                                         callback_data=f'setgs#welcome#{settings["welcome"]}#{str(grp_id)}')
                ]
            ]
            reply_markup = InlineKeyboardMarkup(buttons)
            await query.message.edit_reply_markup(reply_markup)
    await query.answer('Piracy Is Crime')


async def auto_filter(client, msg, spoll=False):
    if not spoll:
        message = msg
        settings = await get_settings(message.chat.id)
        if message.text.startswith("/"): return  # ignore commands
        if re.findall("((^\/|^,|^!|^\.|^[\U0001F600-\U000E007F]).*)", message.text):
            return
        if 2 < len(message.text) < 100:
            search = message.text
            files, offset, total_results = await get_search_results(search.lower(), offset=0, filter=True)
            if not files:
                if settings["spell_check"]:
                    return await advantage_spell_chok(msg)
                else:
                    return
        else:
            return
    else:
        settings = await get_settings(msg.message.chat.id)
        message = msg.message.reply_to_message  # msg will be callback query
        search, files, offset, total_results = spoll

    pre = 'filep' if settings['file_secure'] else 'file'
    pre = 'Chat' if settings.get('redirect_to') == 'Chat' else pre # https://github.com/AlbertEinsteinTG/EvaMaria-Mod/blob/b8f72d384bc900cf5399f820805ab0b9b42abd11/plugins/pm_filter.py#L767

    if settings["button"]:
        btn = [
            [
                InlineKeyboardButton(
                    text=f"⬛️ [{get_size(file.file_size)}] {file.file_name}", callback_data=f'{pre}#{file.file_id}#{msg.from_user.id if msg.from_user is not None else 0}'
                ),
            ]
            for file in files
        ]
    else:
        btn = [
            [
                InlineKeyboardButton(
                    text=f"⬛️ [{get_size(file.file_size)}] {file.file_name}", callback_data=f'{pre}#{file.file_id}#{msg.from_user.id if msg.from_user is not None else 0}'
                ),
            ]
            for file in files
        ]

    if offset != "":
        key = f"{message.chat.id}-{message.message_id}"
        BUTTONS[key] = search
        req = message.from_user.id if message.from_user else 0
        btn.append(
            [InlineKeyboardButton(text=f"🗓 1/{round(int(total_results) / 5)}", callback_data="pages"),
             InlineKeyboardButton(text="NEXT 📖", callback_data=f"next_{req}_{key}_{offset}")]
        )
    else:
        btn.append(
            [InlineKeyboardButton(text="🗓 1/1", callback_data="pages")]
        )
    
    imdb = await get_poster(search, file=(files[0]).file_name) if settings["imdb"] else None
    btn.insert(0, [InlineKeyboardButton('🎈 INFO 🎈', callback_data='useless_info'), InlineKeyboardButton('📺 REQUEST 📺', callback_data='useless_request')])
    TEMPLATE = IMDB_TEMPLATE
    _name = imdb['title'] if imdb else search
    btn.insert(0, [InlineKeyboardButton(_name, callback_data='null')])
    if imdb:
        cap = TEMPLATE.format(
            query=search,
            title=imdb['title'],
            votes=imdb['votes'],
            aka=imdb["aka"],
            seasons=imdb["seasons"],
            box_office=imdb['box_office'],
            localized_title=imdb['localized_title'],
            kind=imdb['kind'],
            imdb_id=imdb["imdb_id"],
            cast=imdb["cast"],
            runtime=imdb["runtime"],
            countries=imdb["countries"],
            certificates=imdb["certificates"],
            languages=imdb["languages"],
            director=imdb["director"],
            writer=imdb["writer"],
            producer=imdb["producer"],
            composer=imdb["composer"],
            cinematographer=imdb["cinematographer"],
            music_team=imdb["music_team"],
            distributors=imdb["distributors"],
            release_date=imdb['release_date'],
            year=imdb['year'],
            genres=imdb['genres'],
            poster=imdb['poster'],
            plot=imdb['plot'],
            rating=imdb['rating'],
            url=imdb['url'],
            time=datetime.now(timezone('Asia/Kolkata')).strftime("%d/%m/%Y, %H:%M:%S"),
            **locals()
        )
    else:
        cap = f"Here is what i found for your query {search}"
    """if imdb:
        try:
            await message.reply_photo(photo=imdb.get('poster'), caption=cap[:1024],
                                      reply_markup=InlineKeyboardMarkup(btn))
        except (MediaEmpty, PhotoInvalidDimensions, WebpageMediaEmpty):
            pic = imdb.get('poster')
            poster = pic.replace('.jpg', "._V1_UX360.jpg")
            await message.reply_photo(photo=poster, caption=cap[:1024], reply_markup=InlineKeyboardMarkup(btn))
        except Exception as e:
            logger.exception(e)
            await message.reply_text(cap, reply_markup=InlineKeyboardMarkup(btn))
    else:"""
    await message.reply_text(cap, reply_markup=InlineKeyboardMarkup(btn), disable_web_page_preview=True)
    if spoll:
        await msg.message.delete()

async def advantage_spell_chok(msg):
    query = re.sub(
        r"\b(pl(i|e)*?(s|z+|ease|se|ese|(e+)s(e)?)|((send|snd|giv(e)?|gib)(\sme)?)|movie(s)?|new|latest|br((o|u)h?)*|^h(e|a)?(l)*(o)*|mal(ayalam)?|t(h)?amil|file|that|find|und(o)*|kit(t(i|y)?)?o(w)?|thar(u)?(o)*w?|kittum(o)*|aya(k)*(um(o)*)?|full\smovie|any(one)|with\ssubtitle(s)?)",
        "", msg.text, flags=re.IGNORECASE)  # plis contribute some common words
    query = query.strip() + " movie"
    g_s = await search_gagala(query)
    g_s += await search_gagala(msg.text)
    gs_parsed = []
    if not g_s:
        k = await msg.reply("I couldn't find any movie in that name.")
        await asyncio.sleep(8)
        await k.delete()
        return
    regex = re.compile(r".*(imdb|wikipedia).*", re.IGNORECASE)  # look for imdb / wiki results
    gs = list(filter(regex.match, g_s))
    gs_parsed = [re.sub(
        r'\b(\-([a-zA-Z-\s])\-\simdb|(\-\s)?imdb|(\-\s)?wikipedia|\(|\)|\-|reviews|full|all|episode(s)?|film|movie|series)',
        '', i, flags=re.IGNORECASE) for i in gs]
    if not gs_parsed:
        reg = re.compile(r"watch(\s[a-zA-Z0-9_\s\-\(\)]*)*\|.*",
                         re.IGNORECASE)  # match something like Watch Niram | Amazon Prime
        for mv in g_s:
            match = reg.match(mv)
            if match:
                gs_parsed.append(match.group(1))
    user = msg.from_user.id if msg.from_user else 0
    movielist = []
    gs_parsed = list(dict.fromkeys(gs_parsed))  # removing duplicates https://stackoverflow.com/a/7961425
    if len(gs_parsed) > 3:
        gs_parsed = gs_parsed[:3]
    if gs_parsed:
        for mov in gs_parsed:
            imdb_s = await get_poster(mov.strip(), bulk=True)  # searching each keyword in imdb
            if imdb_s:
                movielist += [movie.get('title') for movie in imdb_s]
    movielist += [(re.sub(r'(\-|\(|\)|_)', '', i, flags=re.IGNORECASE)).strip() for i in gs_parsed]
    movielist = list(dict.fromkeys(movielist))  # removing duplicates
    if not movielist:
        k = await msg.reply("I couldn't find anything related to that. Check your spelling")
        await asyncio.sleep(8)
        await k.delete()
        return
    SPELL_CHECK[msg.message_id] = movielist
    btn = [[
        InlineKeyboardButton(
            text=movie.strip(),
            callback_data=f"spolling#{user}#{k}",
        )
    ] for k, movie in enumerate(movielist)]
    btn.append([InlineKeyboardButton(text="Close", callback_data=f'spolling#{user}#close_spellcheck')])
    await msg.reply("I couldn't find anything related to that\nDid you mean any one of these?",
                    reply_markup=InlineKeyboardMarkup(btn), quote=True)

async def manual_filters(client, message, text=False):
    group_id = message.chat.id
    name = text or message.text
    reply_id = message.reply_to_message.message_id if message.reply_to_message else message.message_id
    keywords = await get_filters(group_id)
    for keyword in reversed(sorted(keywords, key=len)):
        pattern = r"( |^|[^\w])" + re.escape(keyword) + r"( |$|[^\w])"
        if re.search(pattern, name, flags=re.IGNORECASE):
            reply_text, btn, alert, fileid = await find_filter(group_id, keyword)

            if reply_text:
                reply_text = reply_text.replace("\\n", "\n").replace("\\t", "\t")

            if btn is not None:
                try:
                    if fileid == "None":
                        if btn == "[]":
                            await client.send_message(group_id, reply_text, disable_web_page_preview=True)
                        else:
                            button = eval(btn)
                            await client.send_message(
                                group_id,
                                reply_text,
                                disable_web_page_preview=True,
                                reply_markup=InlineKeyboardMarkup(button),
                                reply_to_message_id=reply_id
                            )
                    elif btn == "[]":
                        await client.send_cached_media(
                            group_id,
                            fileid,
                            caption=reply_text or "",
                            reply_to_message_id=reply_id
                        )
                    else:
                        button = eval(btn)
                        await message.reply_cached_media(
                            fileid,
                            caption=reply_text or "",
                            reply_markup=InlineKeyboardMarkup(button),
                            reply_to_message_id=reply_id
                        )
                except Exception as e:
                    logger.exception(e)
                break
    else:
        return False
