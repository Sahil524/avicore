# Avicore: Universal Media CLI

![Version](https://img.shields.io/badge/version-1.1.0-blue.svg) ![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux-lightgrey) ![License](https://img.shields.io/badge/license-MIT-green)

**Avicore** is a hardened, production-grade command-line tool for processing media. It wraps the complexity of FFmpeg into simple, human-readable commands. It handles video, audio, and image processing with defensive safety checks, smart file naming, and detailed progress reporting.

---

## ⚡ Quick Install (Windows)

You do not need Python or FFmpeg installed. Avicore is standalone.

### Step 1: Download
Download the latest `avicore.exe` from the [Releases Page](https://github.com/Sahil524/avicore/releases).

### Step 2: Install (Add to Path)
1.  Place `avicore.exe` in a permanent folder (e.g., inside `Documents` or `C:\Tools`).
2.  Open **PowerShell** in that folder (Shift + Right Click > "Open PowerShell window here").
3.  Copy and run this command to make Avicore available everywhere:

```powershell
[Environment]::SetEnvironmentVariable("Path", $env:Path + ";" + (Get-Location), "User")
```
That's it! Close PowerShell and open a new terminal. You can now type avicore from anywhere.

📖 Command Reference
🎬 Video Commands
Commands for processing video files (.mp4, .mkv, .mov, .avi, etc.).

1. Convert Single Video
Intelligently converts a video to a new format. By default, it re-encodes to H.264/AAC to ensure compatibility.

Usage: avicore video convert [INPUT] [FORMAT]

Example: avicore video convert movie.mkv mp4

Options:

--fast: Uses "Stream Copy" mode. Instant conversion but only works if codecs are compatible.

--force: Overwrite if file exists.

2. Bulk Convert
Converts all videos matching a pattern. Includes a progress bar and summary report.

Usage: avicore video bulk [PATTERN] [FORMAT]

Example: avicore video bulk "*.mov" mp4

3. Mute Video
Removes the audio track while keeping the video stream and subtitles intact. Does not re-encode video (Instant).

Usage: avicore video mute [INPUT]

Example: avicore video mute clip.mp4

🎵 Audio Commands
Commands for processing audio files (.mp3, .wav, .flac, .aac, etc.).

1. Extract Audio
Rips the audio stream from a video file and saves it as a high-quality MP3 (192kbps).

Usage: avicore audio extract [VIDEO_FILE]

Example: avicore audio extract lecture.mp4

2. Bulk Audio Convert
Batch processes audio files with progress tracking.

Usage: avicore audio bulk [PATTERN] [FORMAT]

Example: avicore audio bulk "*.wav" mp3

🖼️ Image Commands
Commands for processing images (.jpg, .png, .webp, etc.).

1. Smart Compress
Reduces file size intelligently based on input type.

JPG: Reduces Quality Factor (default 60%).

PNG: Increases Compression Level (Lossless).

Usage: avicore image compress [PATTERN] --quality [0-100]

Example: avicore image compress "*.jpg" --quality 50

2. Convert Image
Changes image format (e.g., PNG to JPG, WebP to PNG).

Usage: avicore image convert [INPUT] [FORMAT]

Example: avicore image convert logo.png webp

⚙️ Advanced Features
🛡️ Safety Systems
Smart Overwrite Protection: Avicore never overwrites files unless you force it. It will auto-suggest a new name (e.g., video_1.mp4).

Crash Cleanup: If you interrupt a conversion (Ctrl+C), Avicore deletes the corrupt partial file automatically.

Self-Diagnostic: On every run, Avicore checks its internal engine integrity.

🐛 Debugging
If a file fails to convert, use the verbose flag to generate a detailed log file:

Bash
avicore --verbose video convert broken.mp4 mp4
This creates avicore.log in your temp folder with full FFmpeg error data.

🛠️ Build from Source (Developers Only)
If you want to modify the code yourself:

Clone Repo: git clone https://github.com/Sahil524/avicore

Install Requirements: pip install click pyinstaller

Download Engine:

Download FFmpeg Static Binary from gyan.dev.

Extract ffmpeg.exe and place it in a bin/ folder inside the project.

Build:

PowerShell
python -m PyInstaller --onefile --add-binary "bin/ffmpeg.exe;." --name avicore --clean app.py
Output: The binary will be in dist/.