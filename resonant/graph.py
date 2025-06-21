from random import sample
from typing import Tuple, List, Dict

from songaffect import AffectAnalyzer
from songmodel import KnownSong
from songrepository import SongRepository


# it's not ideal that this just queries every single song every time it needs to do something
#  it's a fundamental problem, though. if this were to be optimized it would have to be integrated with the db
#  i.e. the db would need to be aware of affect scores and such, or at least similar-affect cliques
#  this would be reasonable for a larger project but it's out of scope here - the performance impact is not significant


class MusicGraph:
    """
    Uses the SongRepository and AffectAnalyzer to explore the space of songs with the metric induced by similarity.
    Produces playlists, playtrees, samples songs by similarity, etc.
    """
    def __init__(self, song_repository: SongRepository, affect_analyzer: AffectAnalyzer):
        self.song_repository = song_repository
        self.affect_analyzer = affect_analyzer

    def get_sampled_songs_for(self, song: KnownSong, num_songs: int) -> List[KnownSong]:
        """
        Return a random selection of songs, ordered by similarity to the passed song.
        """
        all_songs = self.song_repository.get_all_songs()
        all_songs.remove(song)
        selected_songs = sample(all_songs, num_songs)
        return sorted(selected_songs, key=lambda s: -self.affect_analyzer.similarity(s, song))

    def get_playlist_from_song(self, song: KnownSong, num_songs: int) -> List[KnownSong]:
        """
        Return a playlist of the passed length starting from the passed song.
        """
        return self.get_playlist_from_head([song], num_songs)

    def get_playlist_from_head(self, head: List[KnownSong], num_songs: int) -> List[KnownSong]:
        """
        Return a playlist of the passed length, starting with the passed head (sequence of songs).
        """
        num_missing = num_songs - len(head)
        assert num_missing >= 0

        playlist = head[:]
        if not num_missing: return playlist

        current_song = playlist[-1]
        selectable_songs = [song for song in self.song_repository.get_all_songs() if song not in playlist]
        for _ in range(num_missing):
            next_song = max(selectable_songs, key=lambda s: self.affect_analyzer.similarity(s, current_song))

            current_song = next_song
            playlist.append(current_song)
            selectable_songs.remove(current_song)

        return playlist

    def get_tree_from_playlist(self, playlist: List[KnownSong], max_depth: int, max_children_per_depth: List[int]) -> \
            Tuple[List[KnownSong], Dict[KnownSong, List[KnownSong]]]:
        """
        Takes a playlist and, interpreting as a (directed) path graph, expands it into a tree of alternative options
         note that max depth is reduced towards the end of the tree, s.t. no path along the tree can be longer than the
         starting playlist itself.
        :param playlist: playlist to expand into a tree
        :param max_depth: max length of an alternative path going out from the playlist
        :param max_children_per_depth: list - max amount of children a node can have at each depth
        :return: a tuple of all the new songs added, a dict specifying the child nodes of each song
        """

        if max_depth == 0:
            return [], dict()

        to_expand_depth = {song: 0 for song in playlist[:-max_depth]}
        for i in range(1, max_depth):
            to_expand_depth[playlist[-i - 1]] = max_depth - i

        children = {song: [] for song in to_expand_depth}

        to_expand_children = {song: max_children_per_depth[depth] for song, depth in to_expand_depth.items()}

        other_songs = [song for song in self.song_repository.get_all_songs() if song not in playlist]
        similarities = {song: {other_song: self.affect_analyzer.similarity(song, other_song)
                               for other_song in other_songs}
                        for song in to_expand_depth}

        closest_other_song = {song: max(other_songs, key=similarities[song].__getitem__) for song in to_expand_depth}
        similarity_to_closest = {song: similarities[song][closest_other_song[song]] for song in to_expand_depth}

        while to_expand_depth:

            current_node = max(to_expand_depth, key=similarity_to_closest.__getitem__)

            new_node = closest_other_song[current_node]

            children[current_node].append(new_node)

            # a reminder of all the exploration state - ensure that all of these are updated correctly
            # children, to_expand_depth, to_expand_children, other_songs,
            # similarities, closest_other_song, similarity_to_closest

            # remove child from other songs, update closest_ and similarity_ accordingly
            other_songs.remove(new_node)
            if not other_songs:
                # break early, so at this point we only have to care that children has the correct state
                break
            for song in to_expand_depth:
                # this covers current_node, too
                if closest_other_song[song] == new_node:
                    closest_other_song[song] = max(other_songs, key=similarities[song].__getitem__)
                    similarity_to_closest[song] = similarities[song][closest_other_song[song]]

            # if not hitting max depth, include child in the exploration queue, init expl values for child
            current_depth = to_expand_depth[current_node]
            new_depth = current_depth + 1
            if new_depth < max_depth:
                children[new_node] = []
                to_expand_depth[new_node] = new_depth
                to_expand_children[new_node] = max_children_per_depth[new_depth]
                similarities[new_node] = {other_song: self.affect_analyzer.similarity(new_node, other_song) for
                                          other_song in other_songs}
                closest_other_song[new_node] = max(other_songs, key=similarities[new_node].__getitem__)
                similarity_to_closest[new_node] = similarities[new_node][closest_other_song[new_node]]

            # if had enough children, remove self from exploration queue, ensure data integrity w the rest
            to_expand_children[current_node] -= 1
            if to_expand_children[current_node] == 0:
                to_expand_depth.pop(current_node)
                to_expand_children.pop(current_node)
                similarities.pop(current_node)
                closest_other_song.pop(current_node)
                similarity_to_closest.pop(current_node)

        added_nodes = sum(children.values(), [])
        return added_nodes, children
