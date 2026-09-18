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

"""Logging utilities for AutoAnimeBot."""

import asyncio
import logging
from traceback import format_exc

from telethon import TelegramClient
from telethon.errors.rpcerrorlist import FloodWaitError

from functions.config import Var

logging.basicConfig(
    format="%(asctime)s || %(name)s [%(levelname)s] : %(message)s",
    handlers=[
        logging.FileHandler("AutoAnimeBot.log", mode="a", encoding="utf-8"),
        logging.StreamHandler(),
    ],
    level=logging.INFO,
    datefmt="%m/%d/%Y, %H:%M:%S",
)
LOGS = logging.getLogger("AutoAnimeBot")
TelethonLogger = logging.getLogger("Telethon")
TelethonLogger.setLevel(logging.INFO)

LOGS.info("""
                            Auto Anime Bot
                ©️ t.me/kAiF_00z (github.com/kaif-00z)
                        {Var.__version__} (original)
                             (2023-26)
                        [All Rigths Reserved]

    """)


class Reporter:
    """Reporter for logging and status updates."""

    def __init__(self, client: TelegramClient, file_name: str):
        """Initialize reporter.

        Args:
            client: Telegram client instance.
            file_name: Name of the file being processed.
        """
        self.client: TelegramClient = client
        self.file_name = file_name
        self.msg = None

    async def alert_new_file_founded(self):
        """Send initial alert for new file found."""
        await self.awake()
        msg = await self.client.send_message(
            Var.MAIN_CHANNEL if Var.LOG_ON_MAIN else Var.LOG_CHANNEL,
            f"**New Anime Released**\n\n **File Name:** ```{self.file_name}```\n\n**STATUS:** `Downloading...`",
        )
        self.msg = msg

    async def started_compressing(self):
        """Update message for compression started."""
        self.msg = await self.msg.edit(
            f"**Successfully Downloaded The Anime**\n\n **File Name:** ```{self.file_name}```\n\n**STATUS:** `Encoding...`",
        )
        return self.msg

    async def started_renaming(self):
        """Update message for renaming started."""
        self.msg = await self.msg.edit(
            f"**Successfully Downloaded The Anime**\n\n **File Name:** ```{self.file_name}```\n\n**STATUS:** `Renaming...`",
        )

    async def started_uploading(self):
        """Update message for upload started."""
        self.msg = await self.msg.edit(
            f"**Successfully Encoded The Anime**\n\n **File Name:** ```{self.file_name}```\n\n**STATUS:** `Uploading...`"
        )

    async def started_gen_ss(self):
        """Update message for sample/screenshot generation."""
        self.msg = await self.msg.edit(
            f"**Successfully Uploaded The Anime**\n\n **File Name:** ```{self.file_name}```\n\n**STATUS:** `Generating Sample And Screen Shot...`"
        )

    async def all_done(self):
        """Finalize and mark task as complete."""
        done_msg = (
            f"**Successfully Completed All Task Related To The Anime**\n\n "
            f"**File Name:** ```{self.file_name}```\n\n**STATUS:** `DONE`"
        )
        try:
            self.msg = await self.msg.edit(done_msg)
        except Exception:
            pass  # ValueError Sometimes From telethon
        if Var.LOG_ON_MAIN:
            await self.msg.delete()

    async def awake(self):
        """Ensure client is connected."""
        if not self.client.is_connected():
            await self.client.connect()

    async def report_error(self, msg, log=False):
        """Report error to log channel.

        Args:
            msg: Error message.
            log: Whether to log to LOGS.
        """
        txt = f"[ERROR] {msg}"
        if log:
            LOGS.error(txt)
        try:
            await self.client.send_message(Var.LOG_CHANNEL, f"```{txt[:4096]}```")
        except FloodWaitError as fwerr:
            await self.client.disconnect()
            LOGS.info("Sleeping Becoz Of Floodwait...")
            await asyncio.sleep(fwerr.seconds + 10)
            await self.client.connect()
        except ConnectionError:
            await self.client.connect()
        except Exception:
            LOGS.exception(format_exc())
