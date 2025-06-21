import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from resonant import config

config.set_program_dirs(os.path.abspath("data"),
                        os.path.abspath("temp"),
                        os.path.abspath("program_files"))
config.set_user_files_dir(os.path.abspath("user_files"))
config.set_ffmpeg_path(r"C:\Program Files\ffmpeg\bin\ffmpeg.exe")

from resonant.sources import YoutubeDownloadableSongSource
from resonant.backend import song_sources

song_sources.extend([
    YoutubeDownloadableSongSource.liked_videos_playlist(
        "me",
        'client_secret_8281972041-5fkf1r8jnstpe5h3na4fc9ka6g529vhg.apps.googleusercontent.com.json'
    ),
    # YoutubeDownloadableSongSource.watch_history_playlist(
    #     "me",
    #     'client_secret_8281972041-5fkf1r8jnstpe5h3na4fc9ka6g529vhg.apps.googleusercontent.com.json'
    # ),
])

from resonant.backend import router as api_router

app = FastAPI()
app.include_router(api_router)

# mount frontend
app.mount("/", StaticFiles(directory="static", html=True), name="static")
