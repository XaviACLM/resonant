import os
from typing import Optional

import config
from songmodel import DownloadableSong
from songmodel.song import Song


class KnownSong(Song):
    """
    A song that has been downloaded, and thus we know a filepath for its mp3 + its name and artist (nullable)
    """

    def __init__(self, raw_name: Optional[str], name: Optional[str], artist: Optional[str], filename: str):
        super().__init__(raw_name, name, artist)
        self.filename = filename

    @property
    def filepath(self):
        return os.path.join(config.music_dir, self.filename)

    @property
    def repr_name(self) -> str:
        """
        Return a user-identifiable name for this song in a standard format.
        """
        if self.name is not None and self.artist is not None:
            return f"{self.artist} - {self.name}"
        else:
            return self.raw_name

    @classmethod
    def from_downloadable_song(cls, downloadable_song: DownloadableSong, filepath: str):
        """
        Create an instance from a (recently downloaded) DownloadableSong object.
        """
        return cls(downloadable_song.raw_name,
                   downloadable_song.name,
                   downloadable_song.artist,
                   filepath)

    def __hash__(self):
        return hash(self.raw_name)

    def __eq__(self, other):
        return self.raw_name == other.raw_name
