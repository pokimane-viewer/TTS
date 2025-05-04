#!/usr/bin/env python3
import sys, re, os, subprocess
from concurrent.futures import ThreadPoolExecutor
import simpleaudio as sa
try:
    from TTS.api import TTS
    use_coqui = True
except ModuleNotFoundError:
    from gtts import gTTS
    from playsound import playsound
    use_coqui = False

def synthesize(tts, text, idx, out_dir):
    if use_coqui:
        path = os.path.join(out_dir, f"segment_{idx}.wav")
        tts.tts_to_file(text=text, file_path=path)
        tmp = path + ".tmp.wav"
        subprocess.run(["ffmpeg", "-y", "-i", path, "-filter:a", "atempo=2.0", tmp],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        os.replace(tmp, path)
    else:
        path = os.path.join(out_dir, f"segment_{idx}.mp3")
        gTTS(text=text, lang='en').save(path)
        tmp = path + ".tmp.mp3"
        subprocess.run(["ffmpeg", "-y", "-i", path, "-filter:a", "atempo=2.0", tmp],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        os.replace(tmp, path)
    return idx, path

def play_file(path):
    if use_coqui:
        wave = sa.WaveObject.from_wave_file(path)
        play_obj = wave.play()
        play_obj.wait_done()
    else:
        playsound(path)

def main():
    if len(sys.argv) < 2:
        sys.exit("Usage: python tts_play.py <input.txt>")
    with open(sys.argv[1], 'r') as f:
        content = f.read()
    segments = re.split(r'(?<=[.?!])\s+', content)
    output_dir = 'tts_output'
    os.makedirs(output_dir, exist_ok=True)
    if use_coqui:
        tts = TTS(model_name="tts_models/en/ljspeech/tacotron2-DDC", progress_bar=False)
    with ThreadPoolExecutor() as executor:
        futures = [executor.submit(synthesize, tts if use_coqui else None, seg, idx, output_dir)
                   for idx, seg in enumerate(segments)]
    results = [future.result() for future in futures]
    for _, filename in sorted(results, key=lambda x: x[0]):
        play_file(filename)

if __name__ == "__main__":
    main()