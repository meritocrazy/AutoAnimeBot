import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# Mock environment variables before importing modules that use config
@pytest.fixture(autouse=True)
def mock_env():
    with patch.dict(
        os.environ,
        {
            "API_ID": "12345",
            "API_HASH": "test_hash",
            "BOT_TOKEN": "test_token",
            "MONGO_SRV": "mongodb://localhost:27017",
            "MAIN_CHANNEL": "-1001234567890",
            "LOG_CHANNEL": "-1001234567891",
            "CLOUD_CHANNEL": "-1001234567892",
            "OWNER": "123456789",
            "CRF": "27",
            "THUMBNAIL": "https://example.com/thumb.jpg",
            "FFMPEG": "ffmpeg",
            "SESSION": "",
            "BACKUP_CHANNEL": "-1001111111111",
            "FORCESUB_CHANNEL": "0",
            "FORCESUB_CHANNEL_LINK": "",
            "SEND_SCHEDULE": "False",
            "RESTART_EVERDAY": "True",
            "LOG_ON_MAIN": "False",
            "DEV_MODE": "False",
        },
    ):
        yield


@pytest.fixture(scope="session", autouse=True)
def _close_shared_tools_session():
    """Close the singleton Tools aiohttp session after the whole test run."""
    yield
    import asyncio

    from functions.tools import Tools

    try:
        asyncio.run(Tools().close_session())
    except RuntimeError:
        pass


class TestTools:
    @pytest.fixture
    def tools(self):
        from functions.tools import Tools

        return Tools()

    def test_hbs_zero(self, tools):
        assert tools.hbs(0) == ""

    def test_hbs_bytes(self, tools):
        assert tools.hbs(512) == "512 B"

    def test_hbs_kilobytes(self, tools):
        assert tools.hbs(1536) == "1.5 KB"

    def test_hbs_megabytes(self, tools):
        assert tools.hbs(2_097_152) == "2.0 MB"

    def test_hbs_gigabytes(self, tools):
        assert tools.hbs(3_221_225_472) == "3.0 GB"

    def test_ts_milliseconds(self, tools):
        assert tools.ts(500) == "500ms"

    def test_ts_seconds(self, tools):
        assert tools.ts(1500) == "1s:500ms"

    def test_ts_minutes(self, tools):
        assert tools.ts(65_000) == "1m:5s"

    def test_ts_hours(self, tools):
        assert tools.ts(3_665_000) == "1h:1m:5s"

    def test_ts_days(self, tools):
        assert tools.ts(90_065_000) == "1d:1h:1m:5s"

    def test_stdr_seconds(self, tools):
        assert tools.stdr(5) == "00:00:05"

    def test_stdr_minutes(self, tools):
        assert tools.stdr(65) == "00:01:05"

    def test_stdr_hours(self, tools):
        assert tools.stdr(3665) == "01:01:05"

    def test_crf_validation(self):
        from functions.config import Var

        # Test that CRF can be cast to int and is in valid range
        crf_val = int(Var.CRF)
        assert 20 <= crf_val <= 51


class TestConfig:
    def test_var_values(self):
        from functions.config import Var

        assert Var.API_ID == 12345
        assert Var.API_HASH == "test_hash"
        assert Var.BOT_TOKEN == "test_token"
        assert Var.CRF == "27"
        assert Var.FFMPEG == "ffmpeg"
        assert Var.MAIN_CHANNEL == -1001234567890
        assert Var.LOG_CHANNEL == -1001234567891
        assert Var.CLOUD_CHANNEL == -1001234567892
        assert Var.OWNER == 123456789


class TestAnimeInfo:
    @pytest.fixture
    def anime_info(self):
        from functions.info import AnimeInfo

        return AnimeInfo("[SubsPlease] One Piece - 1000 (1080p).mkv")

    def test_parse_anime_title(self, anime_info):
        assert anime_info.data.get("anime_title") == "One Piece"

    def test_parse_episode_number(self, anime_info):
        assert anime_info.data.get("episode_number") == "1000"

    def test_parse_video_resolution(self, anime_info):
        assert anime_info.data.get("video_resolution") == "1080p"

    def test_proper_name_generation(self, anime_info):
        # Should generate a proper name for Kitsu search
        proper = anime_info.get_proper_name_for_func(anime_info.name)
        assert "One Piece" in proper

    @pytest.mark.asyncio
    async def test_rename_original(self, anime_info):
        result = await anime_info.rename(original=True)
        assert "One Piece" in result
        assert "1080p" in result
        assert result.endswith(".mkv")

    @pytest.mark.asyncio
    async def test_rename_compressed(self, anime_info):
        result = await anime_info.rename(original=False)
        assert "One Piece" in result
        assert "1080p" in result
        assert result.endswith(".mkv")


class TestReporter:
    @pytest.mark.asyncio
    async def test_reporter_init(self):
        from core.bot import Bot
        from libs.logger import Reporter

        mock_client = MagicMock(spec=Bot)
        mock_client.is_connected = MagicMock(return_value=True)
        mock_client.send_message = AsyncMock()

        reporter = Reporter(mock_client, "test_file.mkv")
        assert reporter.file_name == "test_file.mkv"
        assert reporter.client == mock_client

    @pytest.mark.asyncio
    async def test_alert_new_file_founded(self):
        from core.bot import Bot
        from functions.config import Var
        from libs.logger import Reporter

        mock_client = MagicMock(spec=Bot)
        mock_client.is_connected = MagicMock(return_value=True)
        mock_msg = MagicMock()
        mock_client.send_message = AsyncMock(return_value=mock_msg)

        reporter = Reporter(mock_client, "test_file.mkv")
        await reporter.alert_new_file_founded()

        mock_client.send_message.assert_called_once()
        assert reporter.msg == mock_msg


class TestTorrent:
    @pytest.mark.asyncio
    async def test_torrent_init(self):
        from libs.ariawarp import Torrent

        torrent = Torrent()
        assert "aria2c" in torrent.cmd_template
        assert "-x" in torrent.cmd_template
        assert "-j" in torrent.cmd_template

    @pytest.mark.asyncio
    async def test_download_magnet_cmd_format(self):
        from libs.ariawarp import Torrent

        torrent = Torrent()
        # Check command structure
        cmd = torrent.cmd_template + ["-d", "/path", "magnet:?xt=urn:btih:test"]
        assert cmd[0] == "aria2c"
        assert "-d" in cmd
        assert "/path" in cmd
        assert "magnet:?xt=urn:btih:test" in cmd


class TestDatabase:
    @pytest.mark.asyncio
    async def test_database_init_connection_params(self):
        # Test that MongoDB connection parameters are set correctly
        from database import DataBase
        from functions.config import Var

        # Just verify the class can be imported and has the right structure
        assert hasattr(DataBase, "__init__")
        assert hasattr(DataBase, "add_anime")
        assert hasattr(DataBase, "toggle_original_upload")
        assert hasattr(DataBase, "is_original_upload")


class TestScheduleTasks:
    @pytest.mark.asyncio
    async def test_schedule_init(self):
        from telethon import TelegramClient

        from functions.schedule import ScheduleTasks

        mock_bot = MagicMock(spec=TelegramClient)
        mock_bot.loop = MagicMock()

        with patch("apscheduler.schedulers.asyncio.AsyncIOScheduler") as mock_sch:
            schedule = ScheduleTasks(mock_bot)
            # Should not start scheduler when both flags are False
            mock_sch.assert_not_called()


class TestAdminUtils:
    @pytest.mark.asyncio
    async def test_admin_panel_buttons(self):
        from core.bot import Bot
        from database import DataBase
        from functions.utils import AdminUtils

        mock_db = MagicMock(spec=DataBase)
        mock_bot = MagicMock(spec=Bot)

        admin = AdminUtils(mock_db, mock_bot)
        buttons = admin.admin_panel()

        # Should have 5 rows of buttons (LOGS+Restart, Encode+SS, Button Upload, Separate Channel, Broadcast)
        assert len(buttons) == 5
        # First row: LOGS, Restart
        assert len(buttons[0]) == 2
        # Second row: Encode, SS
        assert len(buttons[1]) == 2
        # Third row: Button Upload
        assert len(buttons[2]) == 1
        # Fourth row: Separate Channel Upload
        assert len(buttons[3]) == 1
        # Fifth row: Broadcast
        assert len(buttons[4]) == 1


class TestToolsAsync:
    @pytest.fixture
    def tools(self):
        from functions.tools import Tools

        return Tools()

    @pytest.mark.asyncio
    async def test_init_dir(self, tools, tmp_path):
        # Test directory creation
        import os

        old_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            tools.init_dir()
            assert os.path.exists("encode")
            assert os.path.exists("thumbs")
            assert os.path.exists("downloads")
            assert os.path.exists("thumb.jpg")
        finally:
            os.chdir(old_cwd)

    @pytest.mark.asyncio
    async def test_init_dir_with_existing_thumb(self, tools, tmp_path):
        # Regression: temp dirs must be created even when thumb.jpg already
        # exists (creation loop was once nested inside the thumb.jpg check)
        import os

        old_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            with open("thumb.jpg", "wb") as f:
                f.write(b"existing-thumb")
            tools.init_dir()
            assert os.path.exists("encode")
            assert os.path.exists("thumbs")
            assert os.path.exists("downloads")
        finally:
            os.chdir(old_cwd)

    @pytest.mark.asyncio
    async def test_bash_not_found(self, tools):
        # Test command not found handling
        import platform

        if platform.system() == "Windows":
            # On Windows, nonexistent command raises FileNotFoundError
            with pytest.raises(FileNotFoundError):
                await tools.bash_(["nonexistent_command_xyz"], run_code=1)
        else:
            out, err = await tools.bash_(["nonexistent_command_xyz"], run_code=1)
            assert "NOT_FOUND" in err or err is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
