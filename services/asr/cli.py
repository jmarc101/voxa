import argparse
from services.asr.engine import AsrEngine


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("audio_path")
    p.add_argument("--model", default="tiny")
    args = p.parse_args()

    eng = AsrEngine(model=args.model)

    # handle both list/generator of segments or a single string
    out = eng.recognize(args.audio_path)
    if isinstance(out, str):
        print(out)
    else:
        for seg in out:
            # if seg has .text (typical faster-whisper)
            txt = getattr(seg, "text", seg)
            print(txt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
