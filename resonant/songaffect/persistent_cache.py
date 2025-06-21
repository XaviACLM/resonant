import os

import h5py
import numpy as np
from urllib.parse import quote, unquote

import config


class AffectVectorCache:
    """
    Maintains a HDF5 cache of all computed affect vectors, keyed by the song's raw name.
    """
    def __init__(self):
        self.path = os.path.join(config.data_dir, 'affect_vector_cache.h5py')
        with h5py.File(self.path, 'a') as f:
            f.require_group("affect")

    def _key(self, raw_name: str) -> str:
        return quote(raw_name, safe='')

    def insert_vector(self, raw_name: str, vec: np.ndarray):
        assert vec.shape == (1280,) and vec.dtype != np.float32

        with h5py.File(self.path, 'a') as f:
            group = f.require_group("affect")
            group.create_dataset(self._key(raw_name), data=vec, dtype='float32')

    def get_vector(self, raw_name: str) -> np.ndarray | None:
        with h5py.File(self.path, 'r') as f:
            group = f.get("affect")
            if group is None:
                return None
            key = self._key(raw_name)
            if key not in group:
                return None
            return group[key][()]

    def vector_exists(self, raw_name: str) -> bool:
        with h5py.File(self.path, 'r') as f:
            return self._key(raw_name) in f.get("affect", {})
