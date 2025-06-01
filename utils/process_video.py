import subprocess
import os
import tempfile

FFMPEG_PATH = os.path.abspath("./ffmpeg-bin/ffmpeg")
FFPROBE_PATH = os.path.abspath("./ffmpeg-bin/ffprobe")


def process_video_ffmpeg(input_file_path: str) -> str:
    output_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name

    command = [
        FFMPEG_PATH,
        "-i", input_file_path,
        "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
        output_file
    ]

    subprocess.run(command, check=True)
    return output_file


def get_video_metadata(file_path: str) -> tuple[int, int, int]:
    command = [
        FFPROBE_PATH,
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height,duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        file_path,
    ]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    width, height, duration = result.stdout.strip().split("\n")
    return int(float(duration)), int(width), int(height)
