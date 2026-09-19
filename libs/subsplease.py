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

"""SubsPlease RSS feed monitor for new anime releases."""

import asyncio
import hashlib
import shutil
import sys
from itertools import count
from traceback import format_exc

import anitopy
from feedparser import parse

from database import DataBase
from libs.logger import LOGS


class SubsPlease:
    """SubsPlease RSS feed monitor for new anime releases."""

    def __init__(self, db: DataBase):
        self.db = db

    def digest(self, string: str):
        """Generate SHA256 hash of string."""
        return hashlib.sha256(string.encode()).hexdigest()

    def exit(self):
        """Clean up and exit."""
        LOGS.info("Stopping The Bot...")
        try:
            [shutil.rmtree(fold) for fold in ["downloads", "thumbs", "encode"]]
        except Exception as exc:  # pylint: disable=broad-except
            LOGS.error(str(exc))
        sys.exit(0)

    async def rss_feed_data(self):
        """Fetch RSS feed data for 1080p, 720p, and 480p.

        Returns:
            Tuple of parsed feed data or (None, None, None) on error.
        """
        try:
            loop = asyncio.get_event_loop()
            d1080, d720, d480 = await asyncio.gather(
                loop.run_in_executor(None, parse, "https://subsplease.org/rss/?r=1080"),
                loop.run_in_executor(None, parse, "https://subsplease.org/rss/?r=720"),
                loop.run_in_executor(None, parse, "https://subsplease.org/rss/?r=sd"),
            )
            return d1080, d720, d480
        except KeyboardInterrupt:
            self.exit()
        except Exception as exc:  # pylint: disable=broad-except
            LOGS.error(str(exc))
            return None, None, None

    async def feed_optimizer(self):
        """Optimize feed data to find matching releases across qualities.

        Returns:
            Dictionary with uid and release entries or None.
        """
        d1080, d720, d480 = await self.rss_feed_data()
        if not d1080 or not d720 or not d480:
            return None
        for i in range(2, -1, -1):
            try:
                f1080, f720, f480 = (
                    d1080.entries[i],
                    d720.entries[i],
                    d480.entries[i],
                )
                a1080, a720, a480 = (
                    (anitopy.parse(f1080.title)).get("anime_title"),
                    (anitopy.parse(f720.title)).get("anime_title"),
                    (anitopy.parse(f480.title)).get("anime_title"),
                )
                if a1080 == a720 == a480:
                    if "[Batch]" in f1080.title or "[Batch]" in f720.title or "[Batch]" in f480.title:
                        continue
                    uid = self.digest(f1080.title + f720.title + f480.title)
                    if not await self.db.is_anime_uploaded(uid):
                        return {
                            "uid": uid,
                            "1080p": f1080,
                            "720p": f720,
                            "480p": f480,
                        }
            except Exception as exc:  # pylint: disable=broad-except
                LOGS.error(str(exc))
                return None

    async def on_new_anime(self, function):
        """Monitor RSS feed and call function on new anime.

        Args:
            function: Callback function to process new anime data.
        """
        for i in count():
            try:
                data = await self.feed_optimizer()
                if data:
                    await function(data)
                    await self.db.add_anime(data.get("uid"))
            except KeyboardInterrupt:
                self.exit()
            except Exception as exc:  # pylint: disable=broad-except
                LOGS.error("[RSS Loop] Error in cycle %s: %s", i, exc)
            await asyncio.sleep(5)
