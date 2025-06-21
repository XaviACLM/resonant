from typing import Iterable

from .downloadable_song import DownloadableSong


class DownloadableSongSource:

    def get_newest_songs(self) -> Iterable[DownloadableSong]:
        """
        Returns an iterable of DownloadableSongs from the source represented by this instance, ordered from most recent.
        """
        raise NotImplementedError()

    def get_name(self) -> str:
        """
        Returns a string used by the user to identify which source this is (e.g. youtube likes)
        """
        raise NotImplementedError()