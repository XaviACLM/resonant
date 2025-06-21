from typing import List, Tuple

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response, FileResponse
from mutagen.id3 import ID3, APIC
from mutagen.mp3 import MP3

from .state import song_repository, music_graph, song_sources

router = APIRouter()


# sources

@router.get("/sources")
def list_sources() -> List[str]:
    return [s.get_name() for s in song_sources]


@router.post("/sources/{source_name}/update")
def update_from_source(source_name: str):
    source = next(filter(lambda s: s.get_name() == source_name, song_sources), None)
    assert source is not None # can only have been from list_sources()
    song_repository.download_new_songs(source.get_newest_songs())


# songs

@router.get("/songs")
def get_all_songs() -> List[str]:
    return [s.raw_name for s in song_repository.get_all_songs()]


@router.get("/songs/random")
def get_random_song() -> str:
    song = song_repository.get_random_song()
    if not song:
        raise HTTPException(status_code=404, detail="No songs available")
    return song.raw_name


@router.get("/songs/sampled_for/{raw_name}")
def get_sampled_songs(raw_name: str, qt_songs: int) -> List[str]:
    """
    Return a list of randomly sampled songs, ordered by similarity to the given song.

    :param raw_name: Name of the reference song.
    :param qt_songs: Number of similar songs to return.
    :return: A list of similar songs, sorted by similarity.
    """
    song = song_repository.get_by_raw_name(raw_name)
    sampled = music_graph.get_sampled_songs_for(song, qt_songs)
    return [s.raw_name for s in sampled]


# song data

@router.get("/song_data/display_name/{raw_name}")
def get_display_name(raw_name: str) -> str:
    """
    Return a readable standard name for a song.
    :param raw_name: Name of the reference song.
    :return: A string representation of the song, {artist} - {name}.
    """
    song = song_repository.get_by_raw_name(raw_name)
    return song.repr_name


@router.get("/song_data/display_artist_and_name/{raw_name}")
def get_display_artist_and_name(raw_name: str) -> Tuple[str, str]:
    """
    Return a tuple containing the artist and name of a song.
    :param raw_name: Name of the reference song.
    :return: A tuple of strings (artist, name).
    """
    song = song_repository.get_by_raw_name(raw_name)
    if song.artist is not None and song.name is not None:
        return song.artist, song.name
    else:
        return "", song.raw_name


@router.get("/audio/{raw_name}")
def serve_audio(raw_name: str):
    song = song_repository.get_by_raw_name(raw_name)
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")
    return FileResponse(song.filepath, media_type="audio/mpeg")


@router.get("/album-art/{raw_name}")
def get_album_art(raw_name: str):
    song = song_repository.get_by_raw_name(raw_name)
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")

    audio = MP3(song.filepath, ID3=ID3)
    if not audio.tags:
        raise HTTPException(status_code=404, detail="No ID3 tag found")

    for tag in audio.tags.values():
        if isinstance(tag, APIC):
            return Response(content=tag.data, media_type=tag.mime)

    raise HTTPException(status_code=404, detail="No album art found")


# playlist business

@router.get("/playlists/playlist_from/{root_raw_name}")
def get_playlist_from(root_raw_name: str, num_songs: int = 8, with_playtree=False):
    """
    Return a playlist or playtree starting at the requested song.
    :param root_raw_name: Name of the song at which to start the playlist.
    :param num_songs: Desired length of the playlist
    :param with_playtree: bool, determining whether to return a sole playlist or accompany it with a playtree.
    :return:
        - If `with_playtree` is False: a list of songs.
        - If `with_playtree` is True: a tuple (playlist, vertices, edges), representing the playlist and playtree.
    """
    playlist = music_graph.get_playlist_from_song(song_repository.get_by_raw_name(root_raw_name), num_songs)
    if with_playtree:
        added_songs, children = music_graph.get_tree_from_playlist(playlist, 2, [2,2])
        return (
            [song.raw_name for song in playlist],
            [song.raw_name for song in added_songs],
            {song.raw_name: [s.raw_name for s in c] for song, c in children.items()}
        )
    else:
        return [song.raw_name for song in playlist]


@router.get("/playlists/playlist_from_head")
def get_playlist_from_head(head_raw_names: List[str] = Query(...), num_songs: int = 8, with_playtree=False):
    """
    Return a playlist or playtree starting with the requested sequence of songs.
    :param head_raw_names: List of the songs to start the playlist with, in this order.
    :param num_songs: Desired length of the playlist
    :param with_playtree: bool, determining whether to return a sole playlist or accompany it with a playtree.
    :return:
        - If `with_playtree` is False: a list of songs.
        - If `with_playtree` is True: a tuple (playlist, vertices, edges), representing the playlist and playtree.
    """
    head = [song_repository.get_by_raw_name(raw_name) for raw_name in head_raw_names]
    playlist = music_graph.get_playlist_from_head(head, num_songs)
    if with_playtree:
        added_songs, children = music_graph.get_tree_from_playlist(playlist, 2, [2,2])
        return (
            [song.raw_name for song in playlist],
            [song.raw_name for song in added_songs],
            {song.raw_name: [s.raw_name for s in c] for song, c in children.items()}
        )
    else:
        return [song.raw_name for song in playlist]
