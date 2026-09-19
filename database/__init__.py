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

"""MongoDB database operations for AutoAnimeBot."""

import sys
from traceback import format_exc

from motor.motor_asyncio import AsyncIOMotorClient

from functions.config import Var
from libs.logger import LOGS


class DataBase:
    """MongoDB database operations for AutoAnimeBot."""

    def __init__(self):
        """Initialize MongoDB connection and collections."""
        try:
            LOGS.info("Trying To Connect With MongoDB")
            self.client = AsyncIOMotorClient(
                Var.MONGO_SRV,
                maxPoolSize=50,
                minPoolSize=10,
                maxIdleTimeMS=30000,
                connectTimeoutMS=10000,
                serverSelectionTimeoutMS=10000,
            )
            self.file_info_db = self.client["ONGOINGANIME"]["fileInfo"]
            self.channel_info_db = self.client["ONGOINGANIME"]["animeChannelInfo"]
            self.opts_db = self.client["ONGOINGANIME"]["opts"]
            self.file_store_db = self.client["ONGOINGANIME"]["fileStore"]
            self.broadcast_db = self.client["ONGOINGANIME"]["broadcastInfo"]
            LOGS.info("Successfully Connected With MongoDB")
            # Create indexes in background
            self._create_indexes()
        except Exception as exc:  # pylint: disable=broad-except
            LOGS.exception(exc)
            LOGS.critical(str(exc))
            sys.exit(1)

    def _create_indexes(self):
        """Create database indexes for better query performance."""
        try:
            # Unique index on _id is automatic, but we can add others
            self.opts_db.create_index("_id", unique=True)
            self.file_store_db.create_index("_id", unique=True)
            self.broadcast_db.create_index("_id", unique=True)
            self.channel_info_db.create_index("_id", unique=True)
            self.file_info_db.create_index("_id", unique=True)
        except Exception as exc:  # pylint: disable=broad-except
            LOGS.error(exc)

    async def add_anime(self, uid):
        """Add anime to the uploaded list if not already present.

        Args:
            uid: Unique identifier for the anime.
        """
        data = await self.file_info_db.find_one({"_id": uid})
        if not data:
            await self.file_info_db.insert_one({"_id": uid})

    async def toggle_separate_channel_upload(self):
        """Toggle the separate channel upload setting.

        Returns:
            The new state of the setting.
        """
        data = await self.opts_db.find_one({"_id": "SEPARATE_CHANNEL_UPLOAD"})
        _data = not (data or {}).get("switch", False)
        await self.opts_db.update_one({"_id": "SEPARATE_CHANNEL_UPLOAD"}, {"$set": {"switch": _data}}, upsert=True)

    async def is_separate_channel_upload(self):
        """Check if separate channel upload is enabled.

        Returns:
            True if enabled, False otherwise.
        """
        data = await self.opts_db.find_one({"_id": "SEPARATE_CHANNEL_UPLOAD"})
        return (data or {}).get("switch", False)

    async def toggle_original_upload(self):
        """Toggle the original upload setting.

        Returns:
            The new state of the setting.
        """
        data = await self.opts_db.find_one({"_id": "OG_UPLOAD"})
        _data = not (data or {}).get("switch", False)
        await self.opts_db.update_one({"_id": "OG_UPLOAD"}, {"$set": {"switch": _data}}, upsert=True)

    async def is_original_upload(self):
        """Check if original upload is enabled.

        Returns:
            True if enabled, False otherwise.
        """
        data = await self.opts_db.find_one({"_id": "OG_UPLOAD"})
        return (data or {}).get("switch", False)

    async def toggle_button_upload(self):
        """Toggle the button upload setting.

        Returns:
            The new state of the setting.
        """
        data = await self.opts_db.find_one({"_id": "BUTTON_UPLOAD"})
        _data = not (data or {}).get("switch", False)
        await self.opts_db.update_one({"_id": "BUTTON_UPLOAD"}, {"$set": {"switch": _data}}, upsert=True)

    async def is_button_upload(self):
        """Check if button upload is enabled.

        Returns:
            True if enabled, False otherwise.
        """
        data = await self.opts_db.find_one({"_id": "BUTTON_UPLOAD"})
        return (data or {}).get("switch", False)

    async def is_anime_uploaded(self, uid):
        """Check if an anime has already been uploaded.

        Args:
            uid: Unique identifier for the anime.

        Returns:
            True if uploaded, False otherwise.
        """
        data = await self.file_info_db.find_one({"_id": uid})
        if data:
            return True
        return False

    async def add_anime_channel_info(self, title, _data):
        """Add or update anime channel information.

        Args:
            title: The anime title.
            _data: The channel information to store.
        """
        await self.channel_info_db.update_one({"_id": title}, {"$set": {"data": _data}}, upsert=True)

    async def get_anime_channel_info(self, title):
        """Get anime channel information.

        Args:
            title: The anime title.

        Returns:
            The stored channel data or empty dict.
        """
        data = await self.channel_info_db.find_one({"_id": title})
        if data and (data or {}).get("data"):
            return data["data"]
        return {}

    async def store_items(self, _hash, _list):
        """Store file items for later retrieval.

        Args:
            _hash: The hash key.
            _list: The list of items to store.
        """
        # in case
        await self.file_store_db.update_one({"_id": _hash}, {"$set": {"data": _list}}, upsert=True)

    async def get_store_items(self, _hash):
        """Retrieve stored file items.

        Args:
            _hash: The hash key.

        Returns:
            The stored list or empty list.
        """
        data = await self.file_store_db.find_one({"_id": _hash})
        if (data or {}).get("data"):
            return data["data"]
        return []

    async def add_broadcast_user(self, user_id):
        """Add a user to the broadcast list.

        Args:
            user_id: The user ID to add.
        """
        data = await self.broadcast_db.find_one({"_id": user_id})
        if not data:
            await self.broadcast_db.insert_one({"_id": user_id})

    async def get_broadcast_user(self):
        """Get all broadcast users.

        Returns:
            List of user IDs.
        """
        data = self.broadcast_db.find()
        return [i["_id"] for i in (await data.to_list(length=None))]

    async def toggle_ss_upload(self):
        """Toggle the screenshots/sample upload setting.

        Returns:
            The new state of the setting.
        """
        data = await self.opts_db.find_one({"_id": "SS_UPLOAD"})
        _new = not (data or {}).get("switch", False)
        await self.opts_db.update_one(
            {"_id": "SS_UPLOAD"},
            {"$set": {"switch": _new}},
            upsert=True,
        )

    async def is_ss_upload(self):
        """Check if screenshots/sample upload is enabled.

        Returns:
            True if enabled, False otherwise.
        """
        data = await self.opts_db.find_one({"_id": "SS_UPLOAD"})
        return (data or {}).get("switch", False)
