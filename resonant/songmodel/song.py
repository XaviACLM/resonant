from functools import cached_property
from typing import Optional

from util import deterministic_hash


class Song:

    def __init__(self, raw_name: str, name: Optional[str], artist: Optional[str]):
        self.raw_name = raw_name
        self.name = name
        self.artist = artist

    @classmethod
    def from_raw_name(cls, raw_name: str):
        return cls(raw_name, None, None)

    @classmethod
    def from_name_and_artist(cls, name: str, artist: str):
        raw_name = f"{artist}- {name}"
        return cls(raw_name, name, artist)

    @cached_property
    def id_(self) -> str:
        """
        Return a string identifier of fixed (32-char) length, unique if raw_name is unique.
        """
        return deterministic_hash(self.raw_name)[:32]