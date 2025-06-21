"""
Runtime editable config for the program. Note that the last line here makes this module into a(n instance of a) class
object, st. we can do config.set_program_dirs(...) and later access config.data_dir
"""

import sys
import os


# just here for intellisense
data_dir = ""
temp_dir = ""
program_files_dir = ""
user_files_dir = ""
ffmpeg_path = ""


class ConfigObject(sys.__class__):

    @property
    def music_dir(self):
        return os.path.join(self.data_dir, "music")

    def set_program_dirs(self, data_dir: str, temp_dir: str, program_files_dir: str):
        self.data_dir = data_dir
        self.temp_dir = temp_dir
        self.program_files_dir = program_files_dir

    def set_user_files_dir(self, user_files_dir: str):
        self.user_files_dir = user_files_dir

    def set_ffmpeg_path(self, ffmpeg_path: str):
        self.ffmpeg_path = ffmpeg_path


# endows the module object with a class, st. import config; config.music_dir works
sys.modules[__name__].__class__ = ConfigObject
