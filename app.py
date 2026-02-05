#!/usr/bin/env python3
"""
avicore — hardened, single-file media CLI.
Senior-architect revision: defensive, codec-aware, progress-driven, diagnosable.
"""

from __future__ import annotations

import sys
import os
import signal
import subprocess
import logging
from pathlib import Path
from typing import List, Iterable, Optional, Tuple
import click
import glob

IMAGE_FORMATS = {"jpg","jpeg","png","webp","bmp"}
VIDEO_FORMATS = {"mp4","mkv","mov","avi","webm"}
AUDIO_FORMATS = {"mp3","wav","aac","flac","ogg"}

# ============================================================
# Version
# ============================================================

APP_VERSION: str = "1.1.0"

# ============================================================
# Globals / State
# ============================================================

CREATED_FILES: List[Path] = []
LOG_FILE: Path = Path("avicore.log")

# ============================================================
# Logging
# ============================================================

def setup_logging(verbose: bool) -> None:
    logging.basicConfig(
        filename=str(LOG_FILE),
        level=logging.DEBUG if verbose else logging.WARNING,
        format="%(asctime)s | %(levelname)s | %(message)s",
        filemode="a",
    )

# ============================================================
# FFmpeg Resolution & Verification
# ============================================================

def resolve_ffmpeg() -> Path:
    # Add the .exe extension if we are on Windows
    ext = ".exe" if os.name == "nt" else ""
    
    if hasattr(sys, "_MEIPASS"):
        # Look for ffmpeg.exe inside the temp bundle
        candidate = Path(sys._MEIPASS) / f"ffmpeg{ext}"
    else:
        # Look for ffmpeg.exe in your local bin folder
        candidate = Path(__file__).parent / "bin" / f"ffmpeg{ext}"

    return candidate


def verify_ffmpeg(ffmpeg: Path) -> None:
    if not ffmpeg.exists():
        raise click.ClickException(
            f"FFmpeg not found.\nExpected location: {ffmpeg.resolve()}"
        )

    try:
        result = subprocess.run(
            [str(ffmpeg), "-version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip())
    except Exception as exc:
        raise click.ClickException(
            "FFmpeg self-diagnostic failed.\n"
            f"Binary path: {ffmpeg.resolve()}\n"
            f"Reason: {exc}"
        )

# ============================================================
# Safety & Cleanup
# ============================================================

def register_cleanup() -> None:
    def _handler(sig, frame=None):
        click.secho("\nInterrupted. Cleaning up partial outputs…", fg="yellow")
        for f in CREATED_FILES:
            try:
                if f.exists():
                    f.unlink()
            except Exception:
                logging.exception("Cleanup failed")
        sys.exit(130)

    signal.signal(signal.SIGINT, _handler)
    signal.signal(signal.SIGTERM, _handler)



def suggest_path(path: Path) -> Path:
    base = path.stem
    suffix = path.suffix
    parent = path.parent
    idx = 1
    while True:
        candidate = parent / f"{base}_{idx}{suffix}"
        if not candidate.exists():
            return candidate
        idx += 1

def backup_original(src: Path) -> Path:
    backup_dir = src.parent / "backup"
    backup_dir.mkdir(exist_ok=True)

    target = backup_dir / src.name

    counter = 1
    while target.exists():
        target = backup_dir / f"{src.stem}_{counter}{src.suffix}"
        counter += 1

    src.rename(target)
    return target



# ============================================================
# Subprocess Wrapper
# ============================================================

def run_ffmpeg(cmd: List[str], dry_run: bool = False) -> bool:
    logging.debug("FFmpeg cmd: %s", " ".join(cmd))

    if dry_run:
        click.secho("[DRY-RUN] " + " ".join(cmd), fg="cyan")
        return True

    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        if result.returncode != 0:
            logging.error(result.stderr)
            click.secho("FFmpeg failed. See avicore.log for details.", fg="red")
            return False

        return True

    except Exception as exc:
        logging.exception("Execution failure")
        click.secho(f"Execution error: {exc}", fg="red")
        return False

# ============================================================
# Input Expansion (Windows-safe)
# ============================================================

def expand_inputs(inputs) -> List[Path]:
    results = []

    for item in inputs:
        matches = glob.glob(item)
        if matches:
            results.extend(matches)
        else:
            p = Path(item)
            if p.exists():
                results.append(str(p))

    return list(dict.fromkeys(Path(p) for p in results))


# ============================================================
# CLI Root
# ============================================================

@click.group(context_settings=dict(help_option_names=[]))
@click.option("--verbose", is_flag=True, help="Enable detailed logging to avicore.log")
@click.option("--dry-run", is_flag=True, help="Preview commands without executing")
@click.pass_context
def cli(ctx: click.Context, verbose: bool, dry_run: bool) -> None:
    setup_logging(verbose)
    register_cleanup()

    ffmpeg = resolve_ffmpeg()
    verify_ffmpeg(ffmpeg)

    ctx.obj = {
        "ffmpeg": ffmpeg,
        "verbose": verbose,
        "dry_run": dry_run,
    }

# ============================================================
# VERSION
# ============================================================

@cli.command(help="Display avicore version.")
def version() -> None:
    click.secho(f"avicore v{APP_VERSION}", fg="green")

@cli.command()
def help():
    click.echo("""
AVI CORE — Simple Media Toolkit

USAGE:

  avicore image convert <files> <format>
  avicore image compress <files>

  avicore video convert <files> <format>
  avicore video mute <files>

  avicore audio convert <files> <format>
  avicore audio extract <video>

EXAMPLES:

 Convert all PNG to WEBP:
   avicore image convert "*.png" webp

 Compress all JPG images:
   avicore image compress "*.jpg"

 Convert all MKV videos:
   avicore video convert "*.mkv" mp4

 Remove audio from videos:
   avicore video mute "*.mp4"

 Extract MP3 from video:
   avicore audio extract movie.mp4

GLOBAL OPTIONS:

 --dry-run     Preview operations
 --verbose     Debug logging

IMPORTANT:

 • Original files are always moved to ./backup
 • Output files keep original names
 • Wildcards must be quoted on Windows

""")


# ============================================================
# VIDEO
# ============================================================

@cli.group()
def video(): pass

@video.command(help="Convert video container.\nSafe default: libx264 + aac.\nUse --fast to stream-copy.")
@click.argument("input", nargs=-1)
@click.argument("format")
@click.option("--fast", is_flag=True, help="Use codec copy when compatible.")
@click.option("--force", is_flag=True)
@click.pass_context
def convert(ctx: click.Context, input: str, format: str, fast: bool, force: bool) -> None:

    if format.lower() not in VIDEO_FORMATS:
        raise click.ClickException("Unsupported video format")

    files = expand_inputs(input)
    if not files:
        raise click.ClickException("No input files resolved")

    ffmpeg: Path = ctx.obj["ffmpeg"]
    dry_run = ctx.obj["dry_run"]

    ok = fail = 0

    with click.progressbar(files, label="Converting videos") as bar:
        for src in bar:

            dst = src.with_name(src.stem + "." + format)

            if dst.exists() and not force:
                click.secho(f"Skipping existing file: {dst.name}", fg="yellow")
                fail += 1
                continue

            if fast:
                cmd = [str(ffmpeg), "-i", str(src), "-map", "0", "-c", "copy", str(dst)]
            else:
                cmd = [
                    str(ffmpeg), "-i", str(src),
                    "-map", "0",
                    "-c:v", "libx264",
                    "-c:a", "aac",
                    "-movflags", "+faststart",
                    str(dst),
                ]

            if run_ffmpeg(cmd, dry_run):
                backup_original(src)
                CREATED_FILES.append(dst)
                ok += 1
            else:
                fail += 1

    click.secho(f"Completed → Success: {ok} | Failed: {fail}", fg="green")


@video.command(help="Mute video (remove audio only, keep metadata).")
@click.argument("input", nargs=-1)
@click.option("--force", is_flag=True)
@click.pass_context
def mute(ctx: click.Context, input: str, force: bool) -> None:

    files = expand_inputs(input)
    if not files:
        raise click.ClickException("No input files resolved")

    ffmpeg: Path = ctx.obj["ffmpeg"]
    dry_run = ctx.obj["dry_run"]

    ok = fail = 0

    with click.progressbar(files, label="Muting videos") as bar:
        for src in bar:

            dst = src  # overwrite same filename

            if dst.exists() and not force:
                click.secho(f"Skipping existing file: {dst.name}", fg="yellow")
                fail += 1
                continue

            cmd = [
                str(ffmpeg), "-i", str(src),
                "-map", "0",
                "-an",
                "-c:v", "copy",
                "-c:s", "copy",
                str(dst),
            ]

            if run_ffmpeg(cmd, dry_run):
                backup_original(src)
                CREATED_FILES.append(dst)
                ok += 1
            else:
                fail += 1

    click.secho(f"Completed → Success: {ok} | Failed: {fail}", fg="green")

# ============================================================
# IMAGE
# ============================================================


@cli.group()
def image(): pass


@image.command(help="Convert image(s).\nExample:\n avicore image convert *.png webp")
@click.argument("pattern", nargs=-1)
@click.argument("format")
@click.option("--force", is_flag=True)
@click.pass_context
def convert(ctx, pattern, format, force):
    if format.lower() not in IMAGE_FORMATS:
        raise click.ClickException("Unsupported image format")

    files = expand_inputs(pattern)
    if not files:
        raise click.ClickException("No input files resolved")

    ffmpeg = ctx.obj["ffmpeg"]
    dry_run = ctx.obj["dry_run"]

    ok = fail = 0

    with click.progressbar(files, label="Converting images") as bar:
        for src in bar:
            original = src
            dst = src.with_name(src.stem + "." + format)

            if dst.exists() and not force:
                dst = suggest_path(dst)

            cmd = [str(ffmpeg), "-i", str(src), str(dst)]

            if run_ffmpeg(cmd, dry_run):
                backup_original(src)
                CREATED_FILES.append(dst)
                ok += 1
            else:
                fail += 1

    click.secho(f"Completed → Success: {ok} | Failed: {fail}", fg="green")


@image.command(help="Compress images intelligently.\nExample:\n avicore image compress *.jpg --quality 70")
@click.argument("pattern", nargs=-1)
@click.option("--quality", default=60, show_default=True)
@click.option("--force", is_flag=True)
@click.pass_context
def compress(ctx: click.Context, pattern: str, quality: int, force: bool) -> None:
    files = expand_inputs(pattern)
    if not files:
        raise click.ClickException("No input files resolved.")

    ffmpeg: Path = ctx.obj["ffmpeg"]
    ok = 0
    fail = 0

    with click.progressbar(files, label="Compressing images") as bar:
        for src in bar:
            try:
                ext = src.suffix.lower()
                dst = src
                if dst.exists() and not force:
                    dst = suggest_path(dst)

                if ext == ".png":
                    cmd = [
                        str(ffmpeg), "-i", str(src),
                        "-compression_level", "9",
                        str(dst),
                    ]
                else:
                    q = max(2, min(31, int((100 - quality) / 3)))
                    cmd = [
                        str(ffmpeg), "-i", str(src),
                        "-q:v", str(q),
                        str(dst),
                    ]

                if run_ffmpeg(cmd, ctx.obj["dry_run"]):
                    backup_original(src)
                    CREATED_FILES.append(dst)
                    ok += 1
                else:
                    fail += 1
            except Exception:
                logging.exception("Image compress failure")
                fail += 1

    click.secho(f"Batch Report → Success: {ok}, Failed: {fail}", fg="yellow")


# ============================================================
# AUDIO COMMANDS
# ============================================================

@cli.group()
def audio(): pass

@audio.command(help="Extract audio from video as MP3 (192kbps).\n\nExample:\n  avicore audio extract input.mp4")
@click.argument("input")
@click.option("--force", is_flag=True, help="Overwrite existing files.")
@click.pass_context
def extract(ctx: click.Context, input: str, force: bool) -> None:
    src = Path(input)
    if not src.exists():
        raise click.ClickException(f"Input not found: {src}")

    dst = src.with_suffix(".mp3")
    if dst.exists() and not force:
        dst = suggest_path(dst)

    ffmpeg: Path = ctx.obj["ffmpeg"]

    # -vn = no video, -ab 192k = audio bitrate
    cmd = [
        str(ffmpeg), "-i", str(src),
        "-vn", "-ab", "192k", "-map", "a",
        str(dst)
    ]

    if run_ffmpeg(cmd, ctx.obj["dry_run"]):
        backup_original(src)
        CREATED_FILES.append(dst)
        click.secho(f"Extracted → {dst}", fg="green")

@audio.command(help="Convert audio format.\n\nExample:\n  avicore audio convert input.wav mp3")
@click.argument("input")
@click.argument("format")
@click.option("--force", is_flag=True, help="Overwrite existing files.")
@click.pass_context
def convert(ctx: click.Context, input: str, format: str, force: bool) -> None:
    if format.lower() not in AUDIO_FORMATS:
        raise click.ClickException("Unsupported audio format")

    src = Path(input)
    if not src.exists():
        raise click.ClickException(f"Input not found: {src}")

    dst = src.with_name(src.stem + "." + format)
    if dst.exists() and not force:
        dst = suggest_path(dst)

    ffmpeg: Path = ctx.obj["ffmpeg"]
    cmd = [str(ffmpeg), "-i", str(src), str(dst)]

    if run_ffmpeg(cmd, ctx.obj["dry_run"]):
        backup_original(src)
        CREATED_FILES.append(dst)
        click.secho(f"Converted → {dst}", fg="green")

# ============================================================
# ENTRY
# ============================================================

if __name__ == "__main__":
    cli()