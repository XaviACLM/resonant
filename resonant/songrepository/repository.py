import os
from itertools import takewhile
from typing import Iterable, List, Optional

import config
from .db import SongDBInterface
from songmodel import KnownSong, DownloadableSong


class SongRepository:
    def __init__(self):
        self.db = SongDBInterface()

    def get_all_songs(self) -> List[KnownSong]:
        return self.db.get_all_songs()

    def get_random_song(self) -> Optional[KnownSong]:
        return self.db.get_random_song()

    def download_new_songs(self, songs: Iterable[DownloadableSong]):
        """
        Given an iterable of DownloadableSongs, downloads and ingests them into the database until it finds one that
        is already present, at which point it stops.
        """
        to_download = takewhile(lambda s: not self.db.is_in_db(s.raw_name), songs)
        new_songs = []
        for song in to_download:
            filename = song.id_ + ".mp3"
            filepath = os.path.join(config.music_dir, filename)
            song.download(filepath)
            new_songs.append(KnownSong.from_downloadable_song(song, filename))
        self.db.add_songs(new_songs)

    def get_by_raw_name(self, raw_name: str) -> KnownSong:
        return self.db.get_song_by_raw_name(raw_name)