"""Video assembly using FFmpeg – combines video clips with TTS audio."""

import os
import subprocess
from pathlib import Path


def assemble_video(script: dict, audio_files: list, video_files: list, output_path: Path) -> Path:
    """Merge video + audio per scene, then concatenate all scenes into final video."""
    scenes = script['scenes']
    final_output = output_path / "final_video.mp4"
    merged_clips = []

    for i, scene in enumerate(scenes):
        audio_path = audio_files[i] if i < len(audio_files) else None
        video_path = video_files[i] if i < len(video_files) else None

        if not video_path or not Path(video_path).exists():
            continue

        clip_output = output_path / f"scene_{scene['id']}_merged.mp4"
        duration = scene.get('duration', 8)

        if audio_path and Path(audio_path).exists() and Path(audio_path).stat().st_size > 0:
            _merge_video_audio(video_path, audio_path, clip_output, duration)
        else:
            _trim_video(video_path, clip_output, duration)

        if clip_output.exists():
            merged_clips.append(str(clip_output))

    if not merged_clips:
        raise RuntimeError("Keine Video-Clips zum Zusammensetzen verfügbar")

    if len(merged_clips) == 1:
        # Single scene – just copy
        import shutil
        shutil.copy(merged_clips[0], str(final_output))
    else:
        _concatenate_clips(merged_clips, final_output)

    return final_output


def _merge_video_audio(video_path: str, audio_path: str, output: Path, duration: int):
    cmd = [
        'ffmpeg', '-y',
        '-i', video_path,
        '-i', audio_path,
        '-c:v', 'libx264', '-c:a', 'aac',
        '-pix_fmt', 'yuv420p',
        '-shortest',
        '-t', str(duration),
        str(output)
    ]
    subprocess.run(cmd, check=True, capture_output=True)


def _trim_video(video_path: str, output: Path, duration: int):
    cmd = [
        'ffmpeg', '-y',
        '-i', video_path,
        '-c:v', 'libx264', '-an',
        '-pix_fmt', 'yuv420p',
        '-t', str(duration),
        str(output)
    ]
    subprocess.run(cmd, check=True, capture_output=True)


def _concatenate_clips(clips: list, output: Path):
    concat_file = output.parent / "concat.txt"
    with open(concat_file, 'w') as f:
        for clip in clips:
            f.write(f"file '{clip}'\n")

    cmd = [
        'ffmpeg', '-y',
        '-f', 'concat',
        '-safe', '0',
        '-i', str(concat_file),
        '-c:v', 'libx264',
        '-c:a', 'aac',
        '-pix_fmt', 'yuv420p',
        '-movflags', '+faststart',
        str(output)
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    concat_file.unlink(missing_ok=True)
