"""Morning Brief podcast builder.

For every script in brief/scripts/YYYY-MM-DD.md that has no MP3 yet, ask
ElevenLabs to voice it, save brief/audio/YYYY-MM-DD.mp3, then rebuild
brief/feed.xml. Old episodes beyond KEEP_DAYS are removed to keep the repo small.
"""
import datetime as dt
import email.utils
import html
import json
import os
import pathlib
import re
import sys
import urllib.error
import urllib.request

from mutagen.mp3 import MP3

ROOT = pathlib.Path(__file__).resolve().parent
SCRIPTS = ROOT / "scripts"
AUDIO = ROOT / "audio"
FEED = ROOT / "feed.xml"
BASE_URL = "https://tripsankur.github.io/ai-tutor-feed/brief"

API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID", "vDchjyOZZytffNeZXfZK")  # "Mike", American podcast host
MODELS = [m for m in os.environ.get("ELEVENLABS_MODELS", "eleven_v4,eleven_v3,eleven_multilingual_v2").split(",") if m]
TAG_MODELS = {"eleven_v3", "eleven_v4"}
MAX_CHARS = 4800  # ElevenLabs request limit is 5,000 characters
KEEP_DAYS = int(os.environ.get("KEEP_DAYS", "30"))


def chunks(text):
    """Split on paragraph breaks so each request stays under MAX_CHARS."""
    parts, cur = [], ""
    for para in text.split("\n\n"):
        if cur and len(cur) + len(para) + 2 > MAX_CHARS:
            parts.append(cur)
            cur = para
        else:
            cur = f"{cur}\n\n{para}" if cur else para
    if cur:
        parts.append(cur)
    return parts


def tts(text):
    last_err = None
    for model in MODELS:
        # Audio tags like [upbeat] or [pause] only work on v3 and v4; older models read them aloud.
        body = text if model in TAG_MODELS else re.sub(r"\[[^\]\n]+\]\s*", "", text)
        req = urllib.request.Request(
            f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}?output_format=mp3_44100_128",
            data=json.dumps({"text": body, "model_id": model}).encode(),
            headers={"xi-api-key": API_KEY, "Content-Type": "application/json", "Accept": "audio/mpeg"},
        )
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            last_err = f"{model}: HTTP {e.code} {e.read()[:300]!r}"
            print("TTS failed, trying next model:", last_err, file=sys.stderr)
            if e.code in (401, 402, 429):  # bad key, no credits, rate limit: other models won't help
                break
    raise SystemExit(f"ElevenLabs failed: {last_err}")


def title_of(text, day):
    m = re.search(r"^#\s+(.+)$", text, re.M)
    return m.group(1).strip() if m else f"Morning Brief · {day:%a %d %b %Y}"


def spoken(text):
    """Drop the markdown title line; everything else is read aloud."""
    return re.sub(r"^#\s+.+\n+", "", text, count=1).strip()


def summary(text):
    body = re.sub(r"\[[^\]]+\]", "", spoken(text))
    return " ".join(body.split())[:300]


def main():
    AUDIO.mkdir(exist_ok=True)
    today = dt.date.today()
    for script in sorted(SCRIPTS.glob("*.md")):
        day = dt.date.fromisoformat(script.stem)
        mp3 = AUDIO / f"{script.stem}.mp3"
        if (today - day).days > KEEP_DAYS:
            script.unlink()
            mp3.unlink(missing_ok=True)
            continue
        if not mp3.exists():
            if not API_KEY:
                raise SystemExit("ELEVENLABS_API_KEY secret is not set")
            audio = b"".join(tts(part) for part in chunks(spoken(script.read_text())))
            mp3.write_bytes(audio)
            print(f"Voiced {script.name}: {len(audio)} bytes")

    items = []
    for script in sorted(SCRIPTS.glob("*.md"), reverse=True):
        mp3 = AUDIO / f"{script.stem}.mp3"
        if not mp3.exists():
            continue
        text = script.read_text()
        day = dt.date.fromisoformat(script.stem)
        secs = int(MP3(mp3).info.length)
        pub = email.utils.format_datetime(dt.datetime(day.year, day.month, day.day, 20, 45, tzinfo=dt.timezone.utc) - dt.timedelta(days=1))
        items.append(f"""    <item>
      <title>{html.escape(title_of(text, day))}</title>
      <description>{html.escape(summary(text))}</description>
      <enclosure url="{BASE_URL}/audio/{mp3.name}" length="{mp3.stat().st_size}" type="audio/mpeg"/>
      <guid isPermaLink="false">morning-brief-{script.stem}</guid>
      <pubDate>{pub}</pubDate>
      <itunes:duration>{secs // 3600:02d}:{secs % 3600 // 60:02d}:{secs % 60:02d}</itunes:duration>
      <itunes:episodeType>full</itunes:episodeType>
      <itunes:explicit>false</itunes:explicit>
    </item>""")

    now = email.utils.format_datetime(dt.datetime.now(dt.timezone.utc))
    FEED.write_text(f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>Morning Brief with Ankur</title>
    <link>{BASE_URL}/feed.xml</link>
    <description>A fast weekday briefing on markets, AI, Databricks and Aays, with one deep dive and a talking point to practise. General information, not financial advice.</description>
    <language>en-au</language>
    <lastBuildDate>{now}</lastBuildDate>
    <atom:link href="{BASE_URL}/feed.xml" rel="self" type="application/rss+xml"/>
    <itunes:author>Ankur Tripathi</itunes:author>
    <itunes:image href="{BASE_URL}/cover.png"/>
    <itunes:category text="Business"/>
    <itunes:type>episodic</itunes:type>
    <itunes:explicit>false</itunes:explicit>
{chr(10).join(items)}
  </channel>
</rss>
""")
    print(f"Feed has {len(items)} episodes")


if __name__ == "__main__":
    main()
