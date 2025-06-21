import os
from random import randint
from typing import Optional, List
from sqlalchemy import create_engine, Column, String
from sqlalchemy.orm import declarative_base, Session

import config
from songmodel import KnownSong


Base = declarative_base()


class KnownSongModel(Base):
    __tablename__ = 'known_songs'

    raw_name = Column(String, primary_key=True)
    name = Column(String, nullable=True)
    artist = Column(String, nullable=True)
    filepath = Column(String, nullable=False)


class SongDBInterface:
    """
    Maintains a sql db of KnownSong objects with SQLAlchemy.
    Not meant to be used directly but rather through SongRepository.
    """
    def __init__(self):
        db_path = os.path.join(config.data_dir, "known_songs.db")
        db_url = f'sqlite:///{db_path}'
        self.engine = create_engine(db_url, echo=False, future=True)
        Base.metadata.create_all(self.engine)

    def _to_model(self, song: KnownSong) -> KnownSongModel:
        if song.raw_name is None:
            raise ValueError("raw_name cannot be None (it's the primary key)")
        return KnownSongModel(
            raw_name=song.raw_name,
            name=song.name,
            artist=song.artist,
            filepath=song.filename
        )

    def add_song(self, song: KnownSong):
        model = self._to_model(song)
        with Session(self.engine) as session:
            session.add(model)
            session.commit()

    def add_songs(self, songs: List[KnownSong]):
        models = [self._to_model(s) for s in songs]
        with Session(self.engine) as session:
            session.add_all(models)
            session.commit()

    def get_random_song(self) -> Optional[KnownSong]:
        with Session(self.engine) as session:
            count = session.query(KnownSongModel).count()
            if count == 0: return None
            offset = randint(0, count - 1)
            row = session.query(KnownSongModel).offset(offset).limit(1).one()
            return KnownSong(row.raw_name, row.name, row.artist, row.filepath)

    def get_song_by_raw_name(self, raw_name: str) -> Optional[KnownSong]:
        with Session(self.engine) as session:
            row = session.get(KnownSongModel, raw_name)
            if row:
                return KnownSong(row.raw_name, row.name, row.artist, row.filepath)
            raw_names = session.query(KnownSongModel.raw_name).all()
            return None


    def get_all_songs(self) -> List[KnownSong]:
        with Session(self.engine) as session:
            results = session.query(KnownSongModel).all()
            return [KnownSong(r.raw_name, r.name, r.artist, r.filepath) for r in results]

    def remove_song_by_raw_name(self, raw_name: str):
        with Session(self.engine) as session:
            song = session.get(KnownSongModel, raw_name)
            if song:
                session.delete(song)
                session.commit()

    def is_in_db(self, raw_name: str) -> bool:
        with Session(self.engine) as session:
            return session.get(KnownSongModel, raw_name) is not None
