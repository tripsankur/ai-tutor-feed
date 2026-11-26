"""Morning Brief podcast builder.

For every script in brief/scripts/YYYY-MM-DD.md that has no MP3 yet, voice it
locally with Kokoro, save brief/audio/YYYY-MM-DD.mp3, then rebuild
brief/feed.xml. Old episodes beyond KEEP_DAYS are removed to keep the repo small.
"""
import datetime as dt
import email.utils
import html
import os
import pathlib
import re
import subprocess

from mutagen.mp3 import MP3

ROOT = pathlib.Path(__file__).resolve().parent
SCRIPTS = ROOT / "scripts"
AUDIO = ROOT / "audio"
FEED = ROOT / "feed.xml"
BASE_URL = "https://tripsankur.github.io/ai-tutor-feed/brief"

# Same engine as the Interview Ready feed: Kokoro, an open-source model that runs
# on the build machine. No API key, no per-episode cost.
KOKORO_DIR = pathlib.Path(os.environ.get("KOKORO_DIR", ROOT / "models"))
VOICE = os.environ.get("KOKORO_VOICE", "af_heart")  # American; Ankur's rule: never a British voice
SPEED = float(os.environ.get("KOKORO_SPEED", "1.1"))  # a touch faster than default
SAMPLE_RATE = 24000
BITRATE = "64k"
GAP_SECONDS = 0.45  # breath between paragraphs
KEEP_DAYS = int(os.environ.get("KEEP_DAYS", "30"))

_kokoro = None


def kokoro():
    global _kokoro
    if _kokoro is None:
        from kokoro_onnx import Kokoro
        _kokoro = Kokoro(str(KOKORO_DIR / "kokoro-v1.0.onnx"), str(KOKORO_DIR / "voices-v1.0.bin"))
    return _kokoro


def paragraphs(text):
    # Delivery tags like [upbeat] or [pause] are ElevenLabs-only; Kokoro would read them aloud.
    text = re.sub(r"\[[^\]\n]+\]\s*", "", text)
    text = re.sub(r"[*_`>#]", "", text)
    return [" ".join(p.split()) for p in text.split("\n\n") if p.strip()]


def tts(text, out):
    import numpy as np
    import soundfile as sf
    gap = None
    pieces = []
    for para in paragraphs(text):
        samples, sr = kokoro().create(para, voice=VOICE, speed=SPEED, lang="en-us")
        if gap is None:
            gap = np.zeros(int(sr * GAP_SECONDS), dtype=samples.dtype)
        pieces += [samples, gap]
    if not pieces:
        raise SystemExit(f"No speakable text for {out.name}")
    wav = out.with_suffix(".wav")
    sf.write(str(wav), np.concatenate(pieces), sr)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav), "-ar", str(SAMPLE_RATE),
                    "-ac", "1", "-b:a", BITRATE, "-metadata", "artist=Morning Brief with Ankur",
                    "-metadata", f"title={out.stem}", str(out)], check=True)
    wav.unlink()


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
            tts(spoken(script.read_text()), mp3)
            print(f"Voiced {script.name}: {mp3.stat().st_size} bytes")

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
    <itunes:image href="{BASE_URL}/cover-sunrise.png"/>
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
