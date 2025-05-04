#!/usr/bin/env python3
import sys, os, tiktoken, requests, subprocess
from collections import deque
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED

def split_text(text, enc, max_tokens):
    tokens = enc.encode(text)
    for i in range(0, len(tokens), max_tokens):
        yield enc.decode(tokens[i:i+max_tokens])

def fetch_speech(idx, text, out_dir, api_key):
    url = "https://api.openai.com/v1/audio/speech"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"model": "gpt-4o-mini-tts", "voice": "alloy", "input": text}
    r = requests.post(url, headers=headers, json=payload, stream=True)
    r.raise_for_status()
    path = os.path.join(out_dir, f"segment_{idx}.mp3")
    with open(path, "wb") as f:
        for chunk in r.iter_content(8192):
            f.write(chunk)
    return idx, path

def main():
    if len(sys.argv) < 2:
        sys.exit("Usage: python tts_play.py <input.txt>")
    inp = sys.argv[1]
    name = os.path.splitext(os.path.basename(inp))[0]
    out_dir = f"{name}_tts"
    os.makedirs(out_dir, exist_ok=True)
    text = open(inp).read()
    enc = tiktoken.encoding_for_model("gpt-4o-mini-tts")
    segments = list(split_text(text, enc, 1000))
    api_key = os.getenv("OPENAI_API_KEY")

    queue = deque(range(len(segments)))
    completed = {}
    next_idx = 0
    max_workers = 5

    with ThreadPoolExecutor(max_workers=max_workers) as exe:
        futures = {}
        while next_idx < len(segments):
            while len(futures) < max_workers and queue:
                i = queue.popleft()
                futures[exe.submit(fetch_speech, i, segments[i], out_dir, api_key)] = i
            done, _ = wait(futures.keys(), return_when=FIRST_COMPLETED)
            for fut in done:
                idx, path = fut.result()
                completed[idx] = path
                futures.pop(fut)
            while next_idx in completed:
                subprocess.run(["mpv", "--no-video", "--speed=2.5", completed.pop(next_idx)])
                next_idx += 1

if __name__ == "__main__":
    main()
