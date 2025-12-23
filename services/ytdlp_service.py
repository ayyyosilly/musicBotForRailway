import yt_dlp

YTDL_OPTS = {
    "format": "bestaudio/best",
    "quiet": True,
    "noplaylist": True,
}

def get_audio(query: str):
    with yt_dlp.YoutubeDL(YTDL_OPTS) as ydl:
        try:
            info = ydl.extract_info(query, download=False)
        except Exception:
            return None

    return {
        "title": info.get("title"),
        "url": info.get("webpage_url"),
        "source": info.get("url"),
        "thumbnail": info.get("thumbnail")
    }
