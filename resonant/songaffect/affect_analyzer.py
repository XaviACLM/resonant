from typing import Dict

import numpy as np

from songmodel import KnownSong
from .affect_vector_extraction import extract_affect_vector
from .persistent_cache import AffectVectorCache


class AffectAnalyzer:
    def __init__(self):
        self.persistent_cache = AffectVectorCache()
        self.cache: Dict[str, np.ndarray] = dict()

    def _affect_vector(self, song: KnownSong) -> np.ndarray:
        """
        Return an affect vector for the passed song. Get it from either of the caches of possible. Otherwise, compute
        and insert into caches.
        """
        key = song.raw_name
        affect_vector = self.cache.get(key, None)
        if affect_vector is not None:
            return affect_vector

        affect_vector = self.persistent_cache.get_vector(key)
        if affect_vector is not None:
            self.cache[key] = affect_vector
            return affect_vector

        affect_vector = self._compute_affect_vector(song)
        self.cache[key] = affect_vector
        self.persistent_cache.insert_vector(key, affect_vector)
        return affect_vector

    @staticmethod
    def _compute_affect_vector(song: KnownSong) -> np.ndarray:
        # the tf code may work w arbitrary resolution but in application we avoid using doubles
        return extract_affect_vector(song.filepath).astype(np.float32)

    def similarity(self, song1: KnownSong, song2: KnownSong) -> float:
        """
        Return a similarity score ranging from 0 to 1 for the passed songs.
        """
        return np.dot(self._affect_vector(song1), self._affect_vector(song2))
