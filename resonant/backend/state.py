from graph import MusicGraph
from songrepository import SongRepository
from songaffect import AffectAnalyzer

song_repository = SongRepository()
affect_analyzer = AffectAnalyzer()
music_graph = MusicGraph(song_repository, affect_analyzer)
song_sources = []
