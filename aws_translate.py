#!/usr/bin/env python3
import boto3
import argparse
import difflib
from pathlib import Path

class Sample:
    @staticmethod
    def translate_client():
        return boto3.client("translate", region_name="us-west-2")

    @staticmethod
    def translate(text: str, src: str, tgt: str):
        client = Sample.translate_client()
        try:
            return client.translate_text(Text=text,
                                         SourceLanguageCode=src,
                                         TargetLanguageCode=tgt)
        except Exception as e:
            print(f"error: {e}")
            return {}

    @staticmethod
    def diff(a: str, b: str) -> str:
        return "\n".join(
            difflib.unified_diff(a.splitlines(), b.splitlines(),
                                 fromfile="prev", tofile="curr", lineterm=""))

    @staticmethod
    def _split(text: str, max_bytes: int = 10000):
        out, buf = [], ""
        for line in text.splitlines(keepends=True):
            if len((buf + line).encode()) > max_bytes:
                if buf:
                    out.append(buf)
                    buf = ""
                while len(line.encode()) > max_bytes:
                    cut_bytes = line.encode()[:max_bytes]
                    cut_str = cut_bytes.decode(errors="ignore")
                    out.append(cut_str)
                    line = line[len(cut_str):]
            buf += line
        if buf:
            out.append(buf)
        return out

    @staticmethod
    def _normalize_lang(lang: str) -> str:
        m = {
            "english": "en", "en": "en", "en-us": "en",
            "spanish": "es", "es": "es", "es-es": "es",
            "french": "fr", "fr": "fr",
            "german": "de", "de": "de",
            "italian": "it", "it": "it",
            "japanese": "ja", "ja": "ja",
            "korean": "ko", "ko": "ko",
            "russian": "ru", "ru": "ru",
            "chinese": "zh", "simplified chinese": "zh",
            "zh": "zh", "zh-cn": "zh",
            "traditional chinese": "zh-TW", "zh-tw": "zh-TW"
        }
        return m.get(lang.strip().lower(), lang)

    @staticmethod
    def main():
        p = argparse.ArgumentParser()
        p.add_argument("--file", "--input", dest="input", required=True, help="text file")
        p.add_argument("--language", required=True, help="target language code or name")
        args = p.parse_args()

        tgt = Sample._normalize_lang(args.language)
        with open(args.input, "r", encoding="utf-8") as f:
            original = f.read()

        pieces = Sample._split(original)
        translated_pieces, src = [], None
        for chunk in pieces:
            resp = Sample.translate(chunk, "auto" if src is None else src, tgt)
            if not resp:
                return
            if src is None:
                src = resp["SourceLanguageCode"]
            translated_pieces.append(resp["TranslatedText"])

        translated = "".join(translated_pieces)
        out_path = Path(args.input).with_name(f"{Path(args.input).stem}_{src}-{tgt}{Path(args.input).suffix}")
        with open(out_path, "w", encoding="utf-8") as out:
            out.write(translated)
        print(f"Detected: {src} -> {tgt}")
        print(f"Wrote {out_path}")

if __name__ == "__main__":
    Sample.main()