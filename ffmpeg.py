def build_ffmpeg_command(video_url: str, index: int) -> str:
    return (
        f'ffmpeg -i "{video_url}" '
        f'-c copy -bsf:a aac_adtstoasc {index}.mp4;'
    )