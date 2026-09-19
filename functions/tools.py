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

"""Utility functions for file operations, encoding, and media processing."""

import asyncio
import hashlib
import json
import math
import os
import re
import shutil
import time
from contextlib import suppress
from traceback import format_exc

import aiofiles
import aiohttp
import requests
from html_telegraph_poster import TelegraphPoster
from telethon.errors.rpcerrorlist import MessageNotModifiedError

from functions.config import Var
from libs.logger import LOGS
from libs.subprocess_utils import run_subprocess, run_subprocess_stream

_telegraph_client: TelegraphPoster | None = None
_telegraph_token: str | None = None


class Tools:
    """Utility class for various media processing tasks."""

    def __init__(self):
        if Var.DEV_MODE:
            self.ffmpeg_threads = int(os.cpu_count() or 0) + 2
        else:
            self.ffmpeg_threads = 2
        self._http_session: aiohttp.ClientSession | None = None
        self._temp_dirs = ["encode", "thumbs", "downloads"]

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._http_session is None or self._http_session.closed:
            timeout = aiohttp.ClientTimeout(total=30, connect=10)
            self._http_session = aiohttp.ClientSession(timeout=timeout)
        return self._http_session

    async def close_session(self):
        if self._http_session and not self._http_session.closed:
            await self._http_session.close()

    async def async_searcher(
        self,
        url: str,
        post: bool = None,
        headers: dict = None,
        params: dict = None,
        json: dict = None,
        data: dict = None,
        ssl=None,
        re_json: bool = False,
        re_content: bool = False,
        real: bool = False,
        *args,
        **kwargs,
    ):
        session = await self._get_session()
        if post:
            data = await session.post(url, json=json, data=data, ssl=ssl, *args, **kwargs)
        else:
            data = await session.get(url, params=params, ssl=ssl, *args, **kwargs)
        if re_json:
            return await data.json()
        if re_content:
            return await data.read()
        if real:
            return data
        return await data.text()

    async def cover_dl(self, link):
        """Download cover image from URL."""
        try:
            if not link:
                return None
            image = await self.async_searcher(link, re_content=True)
            clean_link = link.split("?")[0]
            filename = clean_link.split("/")[-1]
            if len(filename) > 30 or not filename.lower().endswith((".jpg", ".png", ".jpeg")):
                filename = hashlib.md5(link.encode()).hexdigest() + ".jpg"
            fn = f"thumbs/{filename}"
            async with aiofiles.open(fn, "wb") as file:
                await file.write(image)
            return fn
        except Exception as exc:  # pylint: disable=broad-except
            LOGS.exception(exc)
            LOGS.error(str(exc))

    async def mediainfo(self, file, bot):
        """Generate mediainfo HTML and post to Telegraph."""
        try:
            process = await asyncio.create_subprocess_exec(
                "mediainfo",
                file,
                "--Output=HTML",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()
            out = stdout.decode()
            global _telegraph_client, _telegraph_token
            if _telegraph_client is None:
                _telegraph_client = TelegraphPoster(use_api=True)
                _telegraph_token = await _telegraph_client.create_api_token("AutoAnimeBot")
            page = _telegraph_client.post(
                title="Mediainfo",
                author=((await bot.get_me()).first_name),
                author_url=f"https://t.me/{((await bot.get_me()).username)}",
                text=out,
            )
            return page.get("url")
        except Exception as exc:  # pylint: disable=broad-except
            LOGS.exception(exc)
            LOGS.error(str(exc))

    async def _poster(self, bot, anime_info, channel_id=None):
        thumb = await self.cover_dl((await anime_info.get_cover()))
        caption = await anime_info.get_caption()
        return await bot.upload_poster(
            thumb or "assest/poster_not_found.jpg",
            caption,
            channel_id if channel_id else None,
        )

    async def get_chat_info(self, bot, anime_info, dB):
        try:
            chat_info = await dB.get_anime_channel_info(anime_info.proper_name)
            if not chat_info:
                chat_id = await bot.create_channel(
                    (await anime_info.get_english()),
                    (await self.cover_dl((await anime_info.get_poster()))),
                )
                invite_link = await bot.generate_invite_link(chat_id)
                chat_info = {"chat_id": chat_id, "invite_link": invite_link}
                await dB.add_anime_channel_info(anime_info.proper_name, chat_info)
            return chat_info
        except Exception:
            LOGS.error(str(format_exc()))

    def init_dir(self):
        """Initialize required directories and default thumbnail."""
        try:
            if not os.path.exists("thumb.jpg"):
                content = requests.get(Var.THUMB, timeout=10).content
                with open("thumb.jpg", "wb") as f:
                    f.write(content)
            for dir_name in self._temp_dirs:
                if not os.path.isdir(dir_name):
                    os.mkdir(dir_name)
        except Exception as exc:  # pylint: disable=broad-except
            LOGS.exception(exc)
            LOGS.error(str(exc))

    def cleanup_dirs(self):
        """Clean up temporary directories."""
        for dir_name in self._temp_dirs:
            with suppress(Exception):
                shutil.rmtree(dir_name)
        with suppress(Exception):
            os.remove("thumb.jpg")

    def hbs(self, size):
        """Convert bytes to human readable string."""
        if not size:
            return ""
        power = 2**10
        raised_to_pow = 0
        dict_power_n = {0: "", 1: "K", 2: "M", 3: "G", 4: "T", 5: "P"}
        while size > power:
            size /= power
            raised_to_pow += 1
        return str(round(size, 2)) + " " + dict_power_n[raised_to_pow] + "B"

    def ts(self, milliseconds: int) -> str:
        """Convert milliseconds to human readable time string."""
        seconds, milliseconds = divmod(int(milliseconds), 1000)
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        days, hours = divmod(hours, 24)
        tmp = (
            ((str(days) + "d:") if days else "")
            + ((str(hours) + "h:") if hours else "")
            + ((str(minutes) + "m:") if minutes else "")
            + ((str(seconds) + "s:") if seconds else "")
            + ((str(milliseconds) + "ms:") if milliseconds else "")
        )
        return tmp[:-1]

    async def rename_file(self, dl, out):
        """Rename/move a file."""
        try:
            os.rename(dl, out)
        except Exception as exc:  # pylint: disable=broad-except
            return False, str(exc)
        return True, out

    async def bash_(self, cmd, run_code=0):
        """Run a command and capture output.

        Args:
            cmd: Command as list or string.
            run_code: If 0, treat non-empty stderr as error.

        Returns:
            Tuple of (stdout, stderr or error_code).
        """
        out, err = await run_subprocess(cmd)
        if not run_code and err:
            if match := re.match(r"\/bin\/sh: (.*): ?(\w+): not found", err):
                return out, f"{match.group(2).upper()}_NOT_FOUND"
        return out, err

    async def frame_counts(self, dl):
        """Get frame count from video file using mediainfo."""
        _x, _y = await self.bash_(["mediainfo", "--fullscan", dl])
        if _y and _y.endswith("NOT_FOUND"):
            LOGS.error(f"ERROR: `{_y}`")
            return False
        # Parse frame count from mediainfo output
        for line in _x.split("\n"):
            if "Frame count" in line:
                return line.split(":")[1].strip()
        return False

    async def compress(self, dl, out, log_msg):
            """Compress video using ffmpeg with progress tracking."""
            total_frames = await self.frame_counts(dl)
            if not total_frames:
                return False, "Unable to Count The Frames!"
            _progress = f"progress-{time.time()}.txt"
            ffmpeg_cmd = [
                Var.FFMPEG,
                "-hide_banner",
                "-loglevel",
                "quiet",
                "-progress",
                _progress,
                "-i",
                dl,
                "-metadata",
                "Encoded By=https://github.com/kaif-00z/AutoAnimeBot/",
                "-preset",
                "ultrafast",
                "-c:v",
                "libx265",
                "-crf",
                str(int(Var.CRF)),
                "-map",
                "0:v",
                "-c:a",
                "aac",
                "-map",
                "0:a",
                "-c:s",
                "copy",
                "-map",
                "0:s?",
                "-threads",
                str(self.ffmpeg_threads),
                out,
                "-y",
            ]
            process = await asyncio.create_subprocess_exec(
                *ffmpeg_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            d_time = time.time()
            _new_log_msg = log_msg
            while process.returncode is None:
                await asyncio.sleep(5)
                try:
                    with open(_progress, "r+", encoding="utf-8") as fil:
                        text = fil.read()
                        frames = re.findall(r"frame=(\d+)", text)
                        size = re.findall(r"total_size=(\d+)", text)
                        speed = 0
                        if not os.path.exists(out) or os.path.getsize(out) == 0:
                            return False, "Unable To Encode This Video!"
                        if len(frames):
                            elapse = int(frames[-1])
                        if len(size):
                            size = int(size[-1])
                            per = elapse * 100 / int(total_frames)
                            time_diff = time.time() - d_time
                            speed = round(elapse / time_diff, 2)
                        if int(speed) != 0:
                            some_eta = ((int(total_frames) - elapse) / speed) * 1000
                            text = (
                                f"**Successfully Downloaded The Anime**\n\n "
                                f"**File Name:** ```{dl.split('/')[-1]}```\n\n**STATUS:** \n"
                            )
                            progress_str = "`[{0}{1}] {2}%\n\n`".format(
                                "".join("\u25cf" for _ in range(math.floor(per / 5))),
                                "".join("" for _ in range(20 - math.floor(per / 5))),
                                round(per, 2),
                            )
                            e_size = f"{self.hbs(size)} of ~{self.hbs((size / per) * 100)}"
                            eta = f"~{self.ts(some_eta)}"
                            try:
                                _new_log_msg = await log_msg.edit(
                                    text + progress_str + "`" + e_size + "`" + "\n\n`" + eta + "`"
                                )
                            except MessageNotModifiedError:
                                pass
                except Exception:
                    pass
            try:
                os.remove(_progress)
            except Exception:
                pass
            return True, _new_log_msg

    async def genss(self, file):
        """Get video duration in seconds using mediainfo."""
        process = await asyncio.create_subprocess_exec(
            shutil.which("mediainfo"),
            file,
            "--Output=JSON",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        out = stdout.decode().strip()
        z = json.loads(out)
        p = z["media"]["track"][0]["Duration"]
        return int(p.split(".")[-2])

    def stdr(self, seconds: int) -> str:
        """Format seconds as HH:MM:SS."""
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        if len(str(minutes)) == 1:
            minutes = "0" + str(minutes)
        if len(str(hours)) == 1:
            hours = "0" + str(hours)
        if len(str(seconds)) == 1:
            seconds = "0" + str(seconds)
        dur = (
            ((str(hours) + ":") if hours else "00:")
            + ((str(minutes) + ":") if minutes else "00:")
            + ((str(seconds)) if seconds else "")
        )
        return dur

    async def duration_s(self, file):
        """Get two timestamps for sample video generation."""
        tsec = await self.genss(file)
        x = round(tsec / 5)
        y = round(tsec / 5 + 30)
        pin = self.stdr(x)
        if y < tsec:
            pon = self.stdr(y)
        else:
            pon = self.stdr(tsec)
        return pin, pon

    async def gen_ss_sam(self, _hash, filename):
        """Generate screenshots and sample video."""
        try:
            ss_path, sp_path = None, None
            os.mkdir(_hash)
            tsec = await self.genss(filename)
            fps = 10 / tsec
            # Use create_subprocess_exec for ffmpeg screenshots
            ncmd = [
                "ffmpeg",
                "-i",
                filename,
                "-vf",
                f"fps={fps}",
                "-vframes",
                "10",
                f"{_hash}/pic%01d.png",
            ]
            process = await asyncio.create_subprocess_exec(
                *ncmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()
            ss, dd = await self.duration_s(filename)
            __ = filename.split(".mkv")[-2]
            out = __ + "_sample.mkv"
            _ncmd = [
                "ffmpeg",
                "-i",
                filename,
                "-preset",
                "ultrafast",
                "-ss",
                ss,
                "-to",
                dd,
                "-c:v",
                "libx265",
                "-crf",
                "27",
                "-map",
                "0:v",
                "-c:a",
                "aac",
                "-map",
                "0:a",
                "-c:s",
                "copy",
                "-map",
                "0:s?",
                out,
                "-y",
            ]
            process = await asyncio.create_subprocess_exec(
                *_ncmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            er = stderr.decode().strip()
            try:
                if er:
                    if not os.path.exists(out) or os.path.getsize(out) == 0:
                        LOGS.error(str(er))
                        return (ss_path, sp_path)
            except Exception:
                pass
            return _hash, out
        except Exception as exc:  # pylint: disable=broad-except
            LOGS.error(str(exc))
            LOGS.exception(exc)
