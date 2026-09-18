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

"""Shared subprocess utilities for async command execution."""

import asyncio
import shlex
from typing import Optional


async def run_subprocess(
    cmd: list[str] | str,
    capture_stderr: bool = True,
) -> tuple[str, Optional[str]]:
    """Run a subprocess asynchronously with proper argument handling.

    Args:
        cmd: Command as list of args or string (will be split with shlex).
        capture_stderr: Whether to capture stderr separately (True) or merge with stdout (False).

    Returns:
        Tuple of (stdout, stderr). stderr is None if capture_stderr=False or no error.
    """
    if isinstance(cmd, str):
        args = shlex.split(cmd)
    else:
        args = cmd

    if not capture_stderr:
        process = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        stdout, _ = await process.communicate()
        return stdout.decode().strip(), None

    process = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()
    err = stderr.decode().strip() or None
    out = stdout.decode().strip()
    return out, err


async def run_subprocess_stream(
    cmd: list[str] | str,
    callback=None,
) -> tuple[str, Optional[str]]:
    """Run a subprocess and stream output line by line.

    Args:
        cmd: Command as list of args or string (will be split with shlex).
        callback: Optional async function(line: str) -> None called for each output line.

    Returns:
        Tuple of (stdout, stderr).
    """
    if isinstance(cmd, str):
        args = shlex.split(cmd)
    else:
        args = cmd

    process = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )

    output_lines = []
    while True:
        line_bytes = await process.stdout.readline()
        if not line_bytes:
            break
        line = line_bytes.decode(errors="ignore").strip()
        output_lines.append(line)
        if callback:
            await callback(line)

    await process.wait()
    return "\n".join(output_lines), None
