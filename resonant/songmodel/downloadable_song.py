from songmodel.song import Song


class DownloadableSong(Song):

    def download(self, file_path: str):
        """
        Download the song represented by the instance into the passed filepath.
        """
        raise NotImplementedError()
