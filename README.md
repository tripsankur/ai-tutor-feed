# AI Tutor — Audio Course

Generated artifacts (audio, podcast feed, course site) for a personal learning pipeline.
Source lives in a private repo; this repo only hosts published output via GitHub Pages.

- **Course site:** https://tripsankur.github.io/ai-tutor-feed/
- **Podcast feed (subscribe in any podcast app):** https://tripsankur.github.io/ai-tutor-feed/feed/feed.xml

Tracks: Databricks Platform & Data Engineering · Databricks AI · GenAI System Design · RAG · Agentic AI + MCP · LangChain/LangGraph · Transformers · LLMOps.

## Morning Brief podcast

A separate weekday feed: https://tripsankur.github.io/ai-tutor-feed/brief/feed.xml

- The 7:33 AM Sydney brief pushes a spoken script to `brief/scripts/YYYY-MM-DD.md`.
- `.github/workflows/morning-brief.yml` runs `brief/build.py`, which voices new scripts with ElevenLabs, saves `brief/audio/YYYY-MM-DD.mp3` and rebuilds `brief/feed.xml`.
- Needs the repo secret `ELEVENLABS_API_KEY`. Episodes older than 30 days are removed.
