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

# if you are using this following code then don't forgot to give proper
# credit to t.me/kAiF_00z (github.com/kaif-00z)

import re
from traceback import format_exc

import anitopy

from libs.kitsu import RawAnimeInfo
from libs.logger import LOGS

# Optional TypeSafe pre-parsed extraction (cookbook: pre_parsed_value_extraction).
# anitopy stays the primary parser; TypeSafe is only a confirmer when anitopy
# found nothing. Calls run off the event loop and only with a real API key.
try:
    from functions.typesafe_integration import (
        TYPESAFE_ENABLED,
        pick_episode_async,
        pick_quality_async,
        find_candidates,
        EPISODE_RE,
        QUALITY_RE,
    )
except Exception:
    TYPESAFE_ENABLED = False


class AnimeInfo:
    def __init__(self, name):
        self.kitsu = RawAnimeInfo()
        self.CAPTION = """
**{}
━━━━━━━━━━━━━━━
‣ Language:** `Japanese [ESub]`
**‣ Quality:** `480p|720p|1080p`
**‣ Season:** `{}`
**‣ Episode:** `{}`
**━━━━━━━━━━━━━━━**
"""
        self.proper_name = self.get_proper_name_for_func(name)
        self.name = name
        self.data = anitopy.parse(name)
        self._kitsu_cache = None

    async def _get_kitsu_data(self):
        """Fetch and cache Kitsu search result for this anime."""
        if self._kitsu_cache is not None:
            return self._kitsu_cache
        try:
            self._kitsu_cache = await self.kitsu.search(self.proper_name) or {}
        except Exception:
            LOGS.error(str(format_exc()))
            self._kitsu_cache = {}
        return self._kitsu_cache

    async def get_english(self):
        anime_name = self.data.get("anime_title")
        try:
            anime = await self._get_kitsu_data()
            return anime.get("english_title") or anime_name
        except Exception:
            LOGS.error(str(format_exc()))
            return anime_name.strip()

    async def get_poster(self):
        try:
            if self.proper_name:
                anime_poster = await self._get_kitsu_data()
                return anime_poster.get("poster_img") or None
        except Exception:
            LOGS.error(str(format_exc()))

    async def get_cover(self):
        try:
            if self.proper_name:
                anime_poster = await self._get_kitsu_data()
                if anime_poster.get("anilist_id"):
                    return anime_poster.get("anilist_poster")
                return None
        except Exception:
            LOGS.error(str(format_exc()))

    async def get_caption(self):
        try:
            if self.proper_name or self.data:
                return self.CAPTION.format(
                    (await self.get_english()),
                    str(self.data.get("anime_season") or 1).zfill(2),
                    (str(self.data.get("episode_number")).zfill(2) if self.data.get("episode_number") else "N/A"),
                )
        except Exception:
            LOGS.error(str(format_exc()))
            return ""

    @staticmethod
    def _sanitize_filename(name):
        # Characters unsafe for filenames: \ / : * ? " < > |
        return re.sub(r'[\\/:*?"<>|]', " ", name).strip()

    async def rename(self, original=False):
        try:
            # Optional TypeSafe confirmation: only asked when anitopy missed
            # a value, and run off the event loop via asyncio.to_thread.
            episode_num = None
            quality_tag = None
            if TYPESAFE_ENABLED and self.name:
                try:
                    if not self.data.get("episode_number"):
                        ep_candidates = find_candidates(EPISODE_RE, self.name)
                        if ep_candidates:
                            ep_result = await pick_episode_async(self.name, ep_candidates)
                            if ep_result.get("choice") and ep_result.get("choice") != "none":
                                episode_num = ep_result["choice"]
                    if not self.data.get("video_resolution"):
                        q_candidates = find_candidates(QUALITY_RE, self.name)
                        if q_candidates:
                            q_result = await pick_quality_async(self.name, q_candidates)
                            if q_result.get("choice") and q_result.get("choice") != "none":
                                quality_tag = q_result["choice"]
                except Exception:
                    # TypeSafe call failed; fall through to anitopy data
                    LOGS.error("TypeSafe confirmation failed:\n%s", format_exc())

            # anitopy parsed data is primary; TypeSafe only fills gaps above
            anime_name = self.data.get("anime_title")
            parsed_ep = self.data.get("episode_number")
            parsed_qual = self.data.get("video_resolution")

            episode_num = episode_num or parsed_ep
            quality_tag = quality_tag or parsed_qual
            season = self.data.get("anime_season") or 1

            if anime_name and episode_num:
                name = (
                    f"[S{season}-{str(episode_num).zfill(2)}] "
                    f"{(await self.get_english())} [{quality_tag or '???'}].mkv".replace(
                        "‘", ""
                    )
                    .replace("’", "")
                    .strip()
                )
                return self._sanitize_filename(name)
            if anime_name:
                name = (
                    f"{(await self.get_english())} [{quality_tag or parsed_qual or '???'}].mkv".replace("‘", "")
                    .replace("’", "")
                    .strip()
                )
                return self._sanitize_filename(name)
            return self._sanitize_filename(self.name)
        except Exception as error:
            LOGS.error(str(error))
            LOGS.exception(format_exc())
            return self._sanitize_filename(self.name)

    def get_proper_name_for_func(self, name):
        try:
            data = anitopy.parse(name)
            anime_name = data.get("anime_title")
            if anime_name and data.get("episode_number"):
                return (
                    f"{anime_name} S{data.get('anime_season')} {data.get('episode_title')}"
                    if data.get("anime_season") and data.get("episode_title")
                    else (f"{anime_name} S{data.get('anime_season')}" if data.get("anime_season") else anime_name)
                )
            return anime_name
        except Exception as error:
            LOGS.error(str(error))
            LOGS.exception(format_exc())
