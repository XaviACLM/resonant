import subprocess
import os
from typing import Tuple, Optional

import requests
import re
from io import BytesIO
from urllib.parse import urlparse, parse_qs

import imageio.v2 as imageio
from yt_dlp import YoutubeDL

import config


def download_from_youtube(url: str, file_path: str):
    with YoutubeDL({"outtmpl": file_path, "format":"mp4"}) as ydl:
        ydl.download(url)


def convert_mp4_to_mp3(origin_file_path: str, destination_file_path: str, remove_original=True):
    # ffmpeg conversion
    subprocess.Popen(
        [config.ffmpeg_path, "-i", origin_file_path, destination_file_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    ).communicate()

    if remove_original:
        os.remove(origin_file_path)


def convert_mp4_to_mp3_with_cover(origin_file_path: str, destination_file_path: str, image_path: str,
                                  remove_original=True,
                                  remove_thumb=True):
    """
    Extracts audio from an mp4 file into an mp3 file. Takes in a path to an image file to insert into the mp3's
    metadata as cover. Optionally deletes the original mp4 and image file upon completion.
    """
    subprocess.Popen([
        config.ffmpeg_path,
        "-i", origin_file_path,
        "-i", image_path,
        "-map", "0:a",
        "-map", "1:v",
        "-c:a", "libmp3lame",
        "-c:v", "mjpeg",
        "-id3v2_version", "3",
        "-metadata:s:v", "title=Album cover",
        "-metadata:s:v", "comment=Cover (front)",
        destination_file_path,
        "-y"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    ).communicate()

    if remove_original:
        os.remove(origin_file_path)
    if remove_thumb:
        os.remove(image_path)


def download_cropped_youtube_thumbnail(video_id: str, output_file_path: str):
    """
    Given the id of a youtube video, extracts its thumbnail, crops it into a square, and saves it into the passed path.
    """
    for quality in ['maxresdefault', 'hqdefault']:
        url = f"https://i.ytimg.com/vi/{video_id}/{quality}.jpg"
        response = requests.get(url)
        if response.status_code != 200: continue
        img = imageio.imread(BytesIO(response.content))
        h, w, _ = img.shape
        side = min(h, w)
        top = (h - side) // 2
        left = (w - side) // 2
        cropped = img[top:top+side, left:left+side]
        imageio.imwrite(output_file_path, cropped)
        return
    raise Exception("failed to get thumbnail")


def extract_youtube_id(url):
    """
    Extracts youtube video id from a(ny) youtube url.
    """
    parsed = urlparse(url)
    if parsed.hostname in ['youtu.be']:
        return parsed.path.lstrip('/')
    elif parsed.hostname in ['www.youtube.com', 'youtube.com']:
        return parse_qs(parsed.query).get('v', [None])[0]
    return None


def extract_artist_and_name_from_youtube_title(video_title: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Given the YouTube title of a song, attempts to perform some processing on it to extract an artist and song name.
    Returns artist, name. Both are nullable.
    """
    match = re.fullmatch(".*?『(.+?)』.*?", video_title)
    if match is not None:
        video_title = match.group(1)

    matchers = ["(.+?)\((.+?)\)","(.+?)\[(.+?)\]","(.+?)\|(.+?)","(.+?)(f(?:ea)?t\..+?)"]
    bad_words = ["official", "music", "video", "audio", "lyrics", "album", "visualizer", "prod.", "ft.", "feat.", "warning flashing lights"]

    finished = False
    while not finished:
        video_title = video_title.strip()
        for matcher in matchers:
            match = re.fullmatch(matcher, video_title)
            if match is not None:
                parenthetical = match.group(2).lower()
                if any((word in parenthetical for word in bad_words)):
                    video_title = match.group(1)
                    break
        else:
            finished = True

    items = re.split(" - ", video_title)
    if len(items) == 2:
        return items

    match = re.fullmatch("(.+?) ?\"(.+?)\"", video_title)
    if match is not None:
        return match.groups()

    return None, None
