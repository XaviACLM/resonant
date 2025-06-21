import os
import pickle
from typing import Iterable, Dict, List
import re

from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

import config
from songmodel import DownloadableSongSource, DownloadableSong
from util import deterministic_hash
from .dl_util import download_cropped_youtube_thumbnail, download_from_youtube, convert_mp4_to_mp3_with_cover, \
    extract_youtube_id, extract_artist_and_name_from_youtube_title


class YoutubeDownloadableSong(DownloadableSong):
    def __init__(self, video_name, video_url):
        artist, name = extract_artist_and_name_from_youtube_title(video_name)
        raw_name = video_name.replace("/","")
        super().__init__(raw_name, name, artist)
        self.video_url = video_url

    def download(self, file_path: str):

        # useful for testing when clearing out the db
        # if os.path.exists(file_path): return

        temp_filepath = os.path.join(config.temp_dir, self.id_) + ".mp4"
        temp_cover_filepath = os.path.join(config.temp_dir, self.id_) + "_thumb.jpg"

        download_cropped_youtube_thumbnail(extract_youtube_id(self.video_url),temp_cover_filepath)

        download_from_youtube(self.video_url, temp_filepath)
        convert_mp4_to_mp3_with_cover(temp_filepath, file_path, temp_cover_filepath,
                                      remove_original=True, remove_thumb=True)

        if not os.path.exists(file_path):
            # todo
            raise Exception("Youtube download failed. Probably some kind of rate limiting, fixable with aria2c?")


class YoutubeDownloadableSongSource(DownloadableSongSource):
    """
    Song source which pulls DownloadableSong objects from playlists associated to youtube accounts, particularly
    liked videos and watch history. Requires Google OAuth2 credentials on init.
    """

    def __init__(self, user_ui_name: str, credentials_file: str, playlist_name: str):
        self.user_ui_name = user_ui_name
        self.credentials_file = credentials_file
        self.playlist_name = playlist_name

    @classmethod
    def liked_videos_playlist(cls, user_ui_name: str, credentials_file: str):
        return cls(user_ui_name, credentials_file, "likes")

    @classmethod
    def watch_history_playlist(cls, user_ui_name: str, credentials_file: str):
        # todo this endpoint might've gotten moved elsewhere. worth exploring
        raise Exception("Watch history no longer available from the youtube API")
        return cls(user_ui_name, credentials_file, "history")

    def get_name(self):
        return f"Youtube {self.playlist_name} ({self.user_ui_name})"

    def get_credentials(self) -> Dict:
        """
        Attempts to retrieve token file from cache. Otherwise, prompts the user to go through an OAuth2 flow to produce
        and cache a new token.
        """
        scopes = ['https://www.googleapis.com/auth/youtube.readonly']
        credentials_cache_file = os.path.join(config.data_dir, f'{deterministic_hash(self.user_ui_name)[:32]}_token.pickle')
        client_secret_file = os.path.join(
            config.user_files_dir,
            self.credentials_file
        )

        if os.path.exists(credentials_cache_file):
            with open(credentials_cache_file, 'rb') as token:
                return pickle.load(token)
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                client_secret_file, scopes)
            credentials = flow.run_local_server(port=8080)
            with open(credentials_cache_file, 'wb') as token:
                pickle.dump(credentials, token)
            return credentials

    def get_newest_songs(self) -> Iterable[DownloadableSong]:
        credentials = self.get_credentials()
        youtube = build('youtube', 'v3', credentials=credentials)

        # get channel data
        channel_response = youtube.channels().list(
            part="contentDetails",
            mine=True
        ).execute()

        # fish out playlist id for liked videos
        liked_videos_playlist_id = channel_response['items'][0]['contentDetails']['relatedPlaylists'][self.playlist_name]

        # everything up to here could be cached as long as we used lazy loading, but it's unlikely we'll ever be running
        #  this twice in a single runtime anyway.

        # get items in liked videos list
        playlist_items = []
        nextPageToken = None

        while True:
            response = youtube.playlistItems().list(
                part='snippet,contentDetails',
                playlistId=liked_videos_playlist_id,
                maxResults=50,
                pageToken=nextPageToken
            ).execute()

            playlist_items.extend(response['items'])
            nextPageToken = response.get('nextPageToken')

            if not nextPageToken:
                break

        # extract id of each video
        video_ids = []
        for item in playlist_items:
            video_id = item['contentDetails']['videoId']
            video_ids.append(video_id)

        # chunks of 50 (api max i think?)
        def chunked(iterable, size=50):
            for i in range(0, len(iterable), size):
                yield iterable[i:i + size]

        # get video data
        for chunk in chunked(video_ids, 50):
            details_response = youtube.videos().list(
                part='snippet',
                id=','.join(chunk)
            ).execute()

            for item in details_response['items']:
                video_id = item['id']
                title = item['snippet']['title']
                category_id = item['snippet'].get('categoryId')
                is_music = category_id == '10'
                url = f"https://www.youtube.com/watch?v={video_id}"

                if not is_music: continue

                yield YoutubeDownloadableSong(title, url)
