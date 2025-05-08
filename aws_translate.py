#!/usr/bin/env python3
import boto3
import argparse
import difflib
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed


class Sample:
    @staticmethod
    def translate_client():
        return boto3.client("translate", region_name="us-west-2")

    @staticmethod
    def translate(text: str, src: str, tgt: str):
        client = Sample.translate_client()
        try:
            return client.translate_text(
                Text=text,
                SourceLanguageCode=src,
                TargetLanguageCode=tgt,
            )
        except Exception as e:
            print(f"error: {e}")
            return {}

    @staticmethod
    def diff(a: str, b: str) -> str:
        return "\n".join(
            difflib.unified_diff(
                a.splitlines(),
                b.splitlines(),
                fromfile="prev",
                tofile="curr",
                lineterm="",
            )
        )

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
        l = lang.strip().lower()
        if not l:
            return l
        if not hasattr(Sample, "_lang_map"):
            client = Sample.translate_client()
            Sample._lang_map = {}
            token = None
            while True:
                params = {"DisplayLanguageCode": "en"}
                if token:
                    params["NextToken"] = token
                resp = client.list_languages(**params)
                for item in resp.get("Languages", []):
                    code = item["LanguageCode"].lower()
                    name = item["LanguageName"].lower()
                    Sample._lang_map[code] = code
                    Sample._lang_map[name] = code
                    if "(" in name:
                        Sample._lang_map[name.split("(")[0].strip()] = code
                    if "," in name:
                        for part in name.split(","):
                            Sample._lang_map[part.strip()] = code
                token = resp.get("NextToken")
                if not token:
                    break
        return Sample._lang_map.get(l, l)

    @staticmethod
    def get_supported_languages(display_language_code: str = "en"):
        client = Sample.translate_client()
        langs, token = [], None
        while True:
            kwargs = {"DisplayLanguageCode": display_language_code}
            if token:
                kwargs["NextToken"] = token
            resp = client.list_languages(**kwargs)
            langs.extend([l["LanguageCode"] for l in resp.get("Languages", [])])
            token = resp.get("NextToken")
            if not token:
                break
        return langs

    @staticmethod
    def process_file(path: Path, overwrite: bool = False):
        try:
            original = path.read_text(encoding="utf-8")
        except Exception:
            return
        pieces = Sample._split(original)
        supported = Sample.get_supported_languages()
        src = None
        for tgt in supported:
            if src is not None and tgt.lower() == src.lower():
                continue
            translated_pieces = []
            for chunk in pieces:
                resp = Sample.translate(chunk, "auto" if src is None else src, tgt)
                if not resp:
                    return
                if src is None:
                    src = resp["SourceLanguageCode"]
                translated_pieces.append(resp["TranslatedText"])
            translated = "".join(translated_pieces)
            out_path = path.with_name(f"{path.stem}_{src}-{tgt}{path.suffix}")
            if out_path.exists() and not overwrite:
                print(f"Skipping existing file: {out_path}")
                continue
            out_path.write_text(translated, encoding="utf-8")
            print(f"Detected: {src} -> {tgt}")
            print(f"Wrote {out_path}")

    @staticmethod
    def main():
        p = argparse.ArgumentParser()
        p.add_argument(
            "--file",
            dest="file",
            help="text file or directory (required unless --walk)",
        )
        p.add_argument(
            "--walk",
            nargs="?",
            const=".",
            metavar="DIR",
            help="translate all UTF-8 files under DIR (default current dir)",
        )
        p.add_argument(
            "--toall",
            action="store_true",
            help="translate to all supported target languages (requires --file)",
        )
        p.add_argument(
            "--overwrite",
            action="store_true",
            help="overwrite existing translated files",
        )
        args = p.parse_args()

        if args.toall and not args.file:
            p.error("--toall requires --file")

        if args.walk is not None:
            inp_dir = Path(args.file or args.walk)
            if not inp_dir.is_dir():
                p.error(f"--walk requires a directory path, but '{inp_dir}' is not a directory")
            with ThreadPoolExecutor(max_workers=100) as executor:
                futures = []
                for root, _, files in os.walk(inp_dir):
                    for name in files:
                        futures.append(
                            executor.submit(
                                Sample.process_file, Path(root) / name, args.overwrite
                            )
                        )
                for f in as_completed(futures):
                    f.result()
        else:
            if not args.file:
                p.error("--file is required when --walk is not specified")
            inp = Path(args.file)
            if not inp.exists():
                p.error(f"File '{inp}' does not exist")
            Sample.process_file(inp, overwrite=args.overwrite)


if __name__ == "__main__":
    Sample.main()