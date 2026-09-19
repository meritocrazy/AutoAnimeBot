#    This file is part of the AutoAnime distribution.
#    Copyright (c) 2026 Kaif_00z
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, version 3.
#
#    This program is distributed in the hope that it will be useful, but
#    WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
#    General Public License for more details.
#
# License can be found in <
# https://github.com/kaif-00z/AutoAnimeBot/blob/main/LICENSE > .
#
# if you are using this following code then don't forgot to give proper
# credit to t.me/kAiF_00z (github.com/kaif-00z)

"""AutoAnimeBot main entry point.

This module initializes all components and starts the bot.
"""

from traceback import format_exc

from telethon import Button, events

from core.bot import Bot
from core.executors import Executors
from database import DataBase
from functions.info import AnimeInfo
from functions.schedule import ScheduleTasks, Var
from functions.tools import Tools, asyncio
from functions.utils import AdminUtils
from libs.ariawarp import Torrent
from libs.logger import LOGS, Reporter
from libs.subsplease import SubsPlease

tools = Tools()
tools.init_dir()
bot = Bot()
DB = DataBase()
subsplease = SubsPlease(DB)
torrent = Torrent()
schedule = ScheduleTasks(bot)
admin = AdminUtils(DB, bot)


@bot.on(events.NewMessage(incoming=True, pattern=r"^/start ?(.*)", func=lambda e: e.is_private))
async def _start(event):
    """Handle /start command."""
    xnx = await event.reply("`Please Wait...`")
    msg_id = event.pattern_match.group(1)
    await DB.add_broadcast_user(event.sender_id)
    if Var.FORCESUB_CHANNEL and Var.FORCESUB_CHANNEL_LINK:
        is_user_joined = await bot.is_joined(Var.FORCESUB_CHANNEL, event.sender_id)
        if is_user_joined:
            pass
        else:
            return await xnx.edit(
                "**Please Join The Following Channel To Use This Bot 🫡**",
                buttons=[
                    [Button.url("🚀 JOIN CHANNEL", url=Var.FORCESUB_CHANNEL_LINK)],
                    [
                        Button.url(
                            "♻️ REFRESH",
                            url=f"https://t.me/{((await bot.get_me()).username)}?start={msg_id}",
                        )
                    ],
                ],
            )
    if msg_id:
        if msg_id.isdigit():
            msg = await bot.get_messages(Var.BACKUP_CHANNEL, ids=int(msg_id))
            sent_msg = await event.reply(msg)
            if Var.DELETE_FILES_FROM_PMS:
                notice = await sent_msg.reply(
                    "__This file will be automatically deleted after 10 minutes.\n"
                    "Please save or forward it immediately.__"
                )
                asyncio.create_task(bot.delete_after([notice, sent_msg]))
        else:
            items = await DB.get_store_items(msg_id)
            if items:
                for item_id in items:
                    msg = await bot.get_messages(Var.CLOUD_CHANNEL, ids=item_id)
                    if msg:
                        await event.reply(file=list(msg))
    else:
        if event.sender_id == Var.OWNER:
            return await xnx.edit(
                "__Browse Admin Options:__",
                buttons=admin.admin_panel(),
            )
        await event.reply(
            "**Enjoy Ongoing Anime's Best Encode 24/7 🫡**",
            buttons=[
                [
                    Button.url("👨‍💻 DEV", url="t.me/kaif_00z"),
                    Button.url(
                        "💖 OPEN SOURCE",
                        url="https://github.com/kaif-00z/AutoAnimeBot/",
                    ),
                ]
            ],
        )
    await xnx.delete()


@bot.on(events.NewMessage(incoming=True, pattern=r"^/about", func=lambda e: e.is_private))
async def _about(e):
    """Handle /about command."""
    await admin.about(e)


@bot.on(events.callbackquery.CallbackQuery(data="slog"))
async def _logs(e):
    """Handle slog callback."""
    await admin.logs(e)


@bot.on(events.callbackquery.CallbackQuery(data="sret"))
async def _restart(e):
    """Handle sret callback."""
    await admin.restart(e, schedule)


@bot.on(events.callbackquery.CallbackQuery(data="entg"))
async def _encode_t(e):
    """Handle entg callback."""
    await admin.encode_t(e)


@bot.on(events.callbackquery.CallbackQuery(data="sstg"))
async def _ss_t(e):
    """Handle sstg callback."""
    await admin.ss_t(e)


@bot.on(events.callbackquery.CallbackQuery(data="butg"))
async def _btn_t(e):
    """Handle butg callback."""
    await admin.btn_t(e)


@bot.on(events.callbackquery.CallbackQuery(data="scul"))
async def _sep_c_t(e):
    """Handle sculpt callback."""
    await admin.sep_c_t(e)


@bot.on(events.callbackquery.CallbackQuery(data="cast"))
async def _broadcast(e):
    """Handle cast callback."""
    await admin.broadcast_bt(e)


@bot.on(events.callbackquery.CallbackQuery(data="bek"))
async def _back(e):
    """Handle bek callback."""
    await e.edit(
        "** <                ADMIN PANEL                 > **",
        buttons=admin.admin_panel(),
    )


async def anime(data):
    """Process new anime entry from RSS feed.

    Args:
        data: Dictionary containing anime info (480p, 720p, 1080p entries).
    """
    try:
        torr = [data.get("480p"), data.get("720p"), data.get("1080p")]
        anime_info = AnimeInfo(torr[0].title)
        poster = await tools._poster(bot, anime_info)
        if await DB.is_separate_channel_upload():
            chat_info = await tools.get_chat_info(bot, anime_info, DB)
            await poster.edit(
                buttons=[
                    [
                        Button.url(
                            f"EPISODE {anime_info.data.get('episode_number', '')}".strip(),
                            url=chat_info["invite_link"],
                        )
                    ]
                ]
            )
            poster = await tools._poster(bot, anime_info, chat_info["chat_id"])
        btn = [[]]
        original_upload = await DB.is_original_upload()
        button_upload = await DB.is_button_upload()
        for i in torr:
            try:
                filename = f"downloads/{i.title}"
                reporter = Reporter(bot, i.title)
                await reporter.alert_new_file_founded()
                await torrent.download_magnet(i.link, "./downloads/", reporter)
                exe = Executors(
                    bot,
                    DB,
                    {
                        "original_upload": original_upload,
                        "button_upload": button_upload,
                    },
                    filename,
                    AnimeInfo(i.title),
                    reporter,
                )
                result, _btn = await exe.execute()
                if result:
                    if _btn:
                        if len(btn[0]) == 2:
                            btn.append([_btn])
                        else:
                            btn[0].append(_btn)
                        await poster.edit(buttons=btn)
                    asyncio.create_task(exe.further_work())
                    continue
                await reporter.report_error(_btn, log=True)
                await reporter.msg.delete()
            except Exception as exc:  # pylint: disable=broad-except
                await reporter.report_error(str(exc), log=True)
                await reporter.msg.delete()
    except Exception as exc:  # pylint: disable=broad-except
        LOGS.error("Error in anime handler: %s", exc)


try:
    bot.loop.create_task(subsplease.on_new_anime(anime))
    bot.run()
except KeyboardInterrupt:
    subsplease.exit()
