#!/usr/bin/env python3

"""
curl https://api.openai.com/v1/audio/speech \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o-mini-tts",
    "input": "The quick brown fox jumped over the lazy dog.",
    "voice": "alloy"
  }' \
  --output speech.mp3
"""

import argparse
import os
import re
import requests
import logging
import time
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from multiprocessing import Process

def split_text(text, max_chars=2000):
    paras = re.split(r'\n\s*\n+', text)
    chunks = []
    for p in paras:
        p = p.strip()
        if not p:
            continue
        if len(p) <= max_chars:
            chunks.append(p)
        else:
            for i in range(0, len(p), max_chars):
                chunks.append(p[i:i+max_chars])
    return chunks

def fetch_and_save(idx, chunk, base, out_dir):
    out_file = os.path.join(out_dir, f"{base}_part{idx}.mp3")
    if os.path.exists(out_file):
        logging.debug(f"Skipping chunk {idx}, exists at {out_file}")
        return
    logging.debug(f"Requesting chunk {idx} ({len(chunk)} chars)")
    data = {"model": "gpt-4o-mini-tts", "input": chunk, "voice": "alloy"}
    try:
        resp = requests.post(
            "https://api.openai.com/v1/audio/speech",
            headers={
                "Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}",
                "Content-Type": "application/json"
            },
            json=data
        )
        logging.debug(f"Status {resp.status_code} for chunk {idx}")
        if resp.ok:
            with open(out_file, "wb") as f:
                f.write(resp.content)
            logging.debug(f"Saved {out_file}")
        else:
            logging.error(f"Error {resp.status_code} on chunk {idx}: {resp.text}")
    except Exception as e:
        logging.error(f"Exception on chunk {idx}: {e}")

def player(base, out_dir, total):
    idx = 1
    while idx <= total:
        path = os.path.join(out_dir, f"{base}_part{idx}.mp3")
        if os.path.exists(path):
            logging.debug(f"Playing part {idx}")
            subprocess.run([
                "ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet",
                "-af", "atempo=2.0", path
            ])
            idx += 1
        else:
            time.sleep(0.5)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True)
    parser.add_argument("--workers", type=int, default=5)
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(message)s")

    base = os.path.splitext(os.path.basename(args.file))[0]
    out_dir = f"{base}_speech"
    os.makedirs(out_dir, exist_ok=True)

    with open(args.file, "r", encoding="utf-8") as f:
        text = f.read()

    chunks = split_text(text, 2000)
    logging.debug(f"Total sections: {len(chunks)}")
    for i, c in enumerate(chunks, 1):
        logging.debug(f"Section {i} text: {c}")

    p = Process(target=player, args=(base, out_dir, len(chunks)))
    p.daemon = True
    p.start()

    tasks = [(idx, chunk, base, out_dir) for idx, chunk in enumerate(chunks, 1)]
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = [executor.submit(fetch_and_save, idx, chunk, base, out_dir) for idx, chunk, base, out_dir in tasks]
        for future in as_completed(futures):
            future.result()

    p.join()

if __name__ == "__main__":
    main()
