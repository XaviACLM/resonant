import os

from resonant import config

config.set_program_dirs(os.path.abspath("data"),
                        os.path.abspath("temp"),
                        os.path.abspath("program_files"))
config.set_user_files_dir(os.path.abspath("user_files"))
config.set_ffmpeg_path(r"C:\Program Files\ffmpeg\bin\ffmpeg.exe")

from resonant.sources import YoutubeDownloadableSongSource
from resonant.songrepository import SongRepository
from songaffect import AffectAnalyzer
from resonant.graph import MusicGraph

song_repository = SongRepository()
affect_analyzer = AffectAnalyzer()
music_graph = MusicGraph(song_repository, affect_analyzer)

song_sources = [
    YoutubeDownloadableSongSource.liked_videos_playlist(
        "me",
        'client_secret_8281972041-5fkf1r8jnstpe5h3na4fc9ka6g529vhg.apps.googleusercontent.com.json'
    ),
    # YoutubeDownloadableSongSource.watch_history_playlist(
    #     "me",
    #     'client_secret_8281972041-5fkf1r8jnstpe5h3na4fc9ka6g529vhg.apps.googleusercontent.com.json'
    # ),
]


for song_source in song_sources:
    print(f"Updating with new songs from [{song_source.get_name()}]")
    song_repository.download_new_songs(song_source.get_newest_songs())

all_songs = song_repository.get_all_songs()
for i, song_1 in enumerate(all_songs):
    for song_2 in all_songs[:i]:
        similarity = affect_analyzer.similarity(song_1, song_2)
        print(similarity, song_1.repr_name, song_2.repr_name)
        mirror_similarity = affect_analyzer.similarity(song_2, song_1)
        assert abs(similarity - mirror_similarity) < 1e-10


s = song_repository.get_random_song()
print(s.repr_name)


print("")
for ss in music_graph.get_sampled_songs_for(s, 5):
    print(ss.repr_name)
    print(ss.raw_name)

print("")
for opts in music_graph.get_playlist_for_song(s, 3, 1):
    print(opts[0].repr_name)
    for opt in opts[1:]:
        print("\t",opt.repr_name)

print("")
print(music_graph.get_song_tree_from(s, 2, 2))


print("")
p = music_graph.get_playlist_from_song(s,6)
for ss in p:
    print(ss.repr_name)

print("")
t = music_graph.get_tree_from_playlist(p,2,[1,2])