#!/usr/bin/env python3
"""
curl https://api.openai.com/v1/audio/speech \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o-mini-tts",
    "input": "The quick brown fox jumped over the lazy dog.",
    "voice": "coral"
  }' \
  --output speech.mp3
"""
import argparse, concurrent.futures, logging, os, sys, time
from pathlib import Path

import requests

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)

API_URL = "https://api.openai.com/v1/audio/speech"
HEADERS = {
    "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}",
    "Content-Type": "application/json",
}
MODEL = "gpt-4o-mini-tts"
VOICE = "coral"
MAX_WORKERS = 5
RETRIES = 2
TIMEOUT = 60
TOKENS_PER_CHUNK = 1000


def chunk_tokens(text: str, max_tokens: int = TOKENS_PER_CHUNK) -> list[str]:
    try:
        import tiktoken

        enc = tiktoken.get_encoding("cl100k_base")
        ids = enc.encode(text)
        return [enc.decode(ids[i : i + max_tokens]) for i in range(0, len(ids), max_tokens)]
    except Exception:
        words = text.split()
        return [" ".join(words[i : i + max_tokens]) for i in range(0, len(words), max_tokens)]


def fetch_tts(text: str, idx: int, out_dir: Path) -> None:
    for attempt in range(RETRIES + 1):
        try:
            logging.debug("Requesting idx=%s attempt=%s", idx, attempt)
            r = requests.post(
                API_URL,
                headers=HEADERS,
                json={"model": MODEL, "input": text, "voice": VOICE},
                stream=True,
                timeout=TIMEOUT,
            )
            r.raise_for_status()
            out_file = out_dir / f"{idx:04d}.mp3"
            with out_file.open("wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            logging.info("Saved %s", out_file)
            return
        except Exception:
            logging.exception("Download failed idx=%s attempt=%s", idx, attempt)
            time.sleep(2 ** attempt)
    logging.error("Giving up idx=%s", idx)


def main():
    p = argparse.ArgumentParser(description="Parallel TTS downloader (max 5).")
    p.add_argument("--file", required=True, help="Text file to TTS, split every 1000 tokens")
    args = p.parse_args()

    src = Path(args.file).expanduser().resolve()
    if not src.is_file():
        logging.error("Input file not found: %s", src)
        sys.exit(1)

    out_dir = src.parent / (src.with_suffix("").name + "_tts")
    out_dir.mkdir(exist_ok=True)

    chunks = chunk_tokens(src.read_text(encoding="utf-8"))
    if not chunks:
        logging.error("No tokens found in %s", src)
        sys.exit(1)

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        ex.map(lambda args: fetch_tts(*args), [(chunk, idx, out_dir) for idx, chunk in enumerate(chunks, 1)])


if __name__ == "__main__":
    main()