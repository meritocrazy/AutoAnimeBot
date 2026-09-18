#    This file is part of the AutoAnime distribution.
#    Copyright (c) 2025 Kaif_00z
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

import asyncio
import shlex


class Torrent:
    def __init__(self) -> None:
        # Use list format for create_subprocess_exec to avoid shell injection
        self.cmd_template = ["aria2c", "-x", "10", "-j", "10", "--seed-time=0"]

    async def bash(self, cmd):
        if isinstance(cmd, str):
            args = shlex.split(cmd)
        else:
            args = cmd
        process = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        err = stderr.decode().strip() or None
        out = stdout.decode().strip()
        return out, err

    async def download_magnet(self, link: str, path: str):
        cmd = self.cmd_template + ["-d", path, link]
        await self.bash(cmd)
