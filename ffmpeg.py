import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Callable


def build_ffmpeg_command(video_url: str, index: int) -> str:
    return (
        f'ffmpeg -i "{video_url}" '
        f'-c copy -bsf:a aac_adtstoasc {index}.mp4;'
    )


def download_videos(
    video_urls: list[str],
    output_directory: str,
    progress_callback: Callable[[float | None, str], None] | None = None,
    start_index: int = 1,
    output_indices: list[int] | None = None,
) -> list[str]:
    if start_index < 1:
        raise ValueError("start_index must be greater than zero.")
    if output_indices is not None and len(output_indices) != len(video_urls):
        raise ValueError("output_indices must match the number of video URLs.")
    if output_indices is not None and any(index < 1 for index in output_indices):
        raise ValueError("output_indices must contain positive integers.")
    if output_indices is not None and len(set(output_indices)) != len(output_indices):
        raise ValueError("output_indices must be unique.")

    executable_name = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
    ffmpeg_path = shutil.which(executable_name)
    if ffmpeg_path is None:
        raise FileNotFoundError(
            "FFmpeg was not found. Install FFmpeg and add it to PATH."
        )
    ffprobe_name = "ffprobe.exe" if os.name == "nt" else "ffprobe"
    ffprobe_path = shutil.which(ffprobe_name)

    output_path = Path(output_directory)
    output_path.mkdir(parents=True, exist_ok=True)
    downloaded_files: list[str] = []
    total = len(video_urls)

    for offset, video_url in enumerate(video_urls):
        index = (
            output_indices[offset]
            if output_indices is not None
            else start_index + offset
        )
        destination = output_path / f"{index}.mp4"
        if destination.exists():
            raise FileExistsError(
                f"Download destination already exists: {destination}"
            )

        duration = _probe_duration(ffprobe_path, video_url)
        if progress_callback:
            progress_callback(
                offset / total if duration else None,
                f"Downloading video {index} ({offset + 1} of {total})…",
            )

        process = subprocess.Popen(
            [
                ffmpeg_path,
                "-n",
                "-nostdin",
                "-v",
                "error",
                "-i",
                video_url,
                "-c",
                "copy",
                "-progress",
                "pipe:1",
                "-nostats",
                str(destination),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
        error_lines: list[str] = []
        if process.stdout is None:
            process.kill()
            raise RuntimeError("Unable to read FFmpeg progress output.")

        with process.stdout:
            for line in process.stdout:
                line = line.strip()
                if not line:
                    continue
                if "=" not in line:
                    error_lines.append(line)
                    continue

                key, value = line.split("=", 1)
                if key not in ("out_time_us", "out_time_ms") or not duration:
                    continue
                try:
                    elapsed = int(value) / 1_000_000
                except ValueError:
                    continue
                if progress_callback:
                    progress_callback(
                        (offset + min(elapsed / duration, 1)) / total,
                        f"Downloading video {index} ({offset + 1} of {total})…",
                    )

        return_code = process.wait()
        if return_code:
            details = "\n".join(error_lines).strip() or "FFmpeg returned an error."
            raise RuntimeError(
                f"Failed to download video {index}: {details}"
            )

        downloaded_files.append(str(destination))
        if progress_callback:
            progress_callback(
                (offset + 1) / total,
                f"Downloaded video {index}.",
            )

    return downloaded_files


def _probe_duration(ffprobe_path: str | None, video_url: str) -> float | None:
    if ffprobe_path is None:
        return None

    try:
        result = subprocess.run(
            [
                ffprobe_path,
                "-v",
                "error",
                "-show_entries",
                "format=duration:stream=duration",
                "-of",
                "json",
                video_url,
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=15,
        )
    except subprocess.TimeoutExpired:
        return None
    if result.returncode:
        return None

    try:
        metadata = json.loads(result.stdout)
        durations = [
            float(value)
            for value in [
                metadata.get("format", {}).get("duration"),
                *(
                    stream.get("duration")
                    for stream in metadata.get("streams", [])
                ),
            ]
            if value is not None and float(value) > 0
        ]
    except (TypeError, ValueError, json.JSONDecodeError):
        return None

    return max(durations, default=None)