import os
import re

import httpx


def _sanitize_filename(name: str) -> str:
    name = re.sub(r'[<>:"/\\|?*]', "", name)
    name = name.strip(". ")
    return name[:200]


async def download(episode: dict, dest_dir: str) -> str:
    os.makedirs(dest_dir, exist_ok=True)

    filename = _sanitize_filename(f"{episode['id']} - {episode['title']}") + ".mp3"
    file_path = os.path.join(dest_dir, filename)

    headers = {"Referer": "https://www.rtve.es/"}

    async with httpx.AsyncClient(
        headers=headers,
        follow_redirects=True,
        timeout=30,
    ) as client:
        async with client.stream("GET", episode["audio_url"]) as response:
            response.raise_for_status()
            with open(file_path, "wb") as f:
                async for chunk in response.aiter_bytes(chunk_size=65536):
                    f.write(chunk)

    return file_path
