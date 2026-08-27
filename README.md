# Sonus

> A lightweight desktop YouTube audio player for Windows.

Sonus is a simple desktop application for listening to audio from YouTube without displaying the video itself. It supports direct videos, playlists, text search, queue management, background caching, playback controls and volume adjustment.

## Features

- Search YouTube for music and choose a result from the search list.
- Open a direct YouTube video link.
- Add a YouTube playlist to the queue.
- Combine playlists and individual videos in one queue.
- Play, pause, skip forward, go back and seek through a track.
- Adjust playback volume without restarting the track.
- Background audio caching with selectable download modes.
- Sequential, repeat-queue and random playback modes.
- Configurable search result count from 1 to 50.
- Dark Sonus interface with rounded panels.
- Windows GUI mode without a persistent console window.

## Requirements

- Windows 10 or Windows 11.
- Internet connection for search and first-time audio downloads.
- WinGet for automatic setup of missing components.

The Global Windows launcher installs Python 3.13 and the Python dependencies automatically when needed. It also checks for FFmpeg and attempts to install it through WinGet when it is not available.

## Quick start

1. Download the latest release from the **Releases** page.
2. Extract the archive to a folder.
3. Run `run_windows.bat`.
4. Wait for the first-time environment setup to finish.
5. Sonus starts automatically without leaving a console window open.

On subsequent launches, the launcher reuses the existing Python environment and only installs missing/outdated Python packages when necessary.

## Using Sonus

Paste a YouTube video or playlist URL into the search bar and press **Обработать**.

For a text query, enter a track title, artist or another search phrase and start the search. Select a result and add it to the queue.

The queue can contain tracks from multiple sources. Adding a new video or playlist does not replace the existing queue.

## Background caching

Sonus can download tracks to a local cache in the background. The mode can be changed in the application settings:

- **Потоковая** — downloads tracks in queue order, from the first item to the last.
- **Умная** — downloads the selected track first, then continues through the queue in order.
- **Смешанная** — downloads the selected track first, then two previous and two next tracks, then continues through the queue in order.

Background downloads are sequential to keep network and CPU usage reasonable.

The runtime cache is cleared when Sonus starts, so previous sessions do not accumulate audio files indefinitely.

## Search results

The text search uses a music-oriented YouTube search first and falls back to the regular YouTube search if needed. Search results are therefore intended to favor music content, but Sonus cannot guarantee that every YouTube result is an audio-only release.

## Project structure

```text
Sonus/
├── app.py
├── requirements.txt
├── run_windows.bat
├── sonus.ico
├── CHANGELOG.md
├── LICENSE
└── .gitignore
```

## Development

The application is currently implemented in Python using Tkinter for the desktop interface and pygame for audio playback. YouTube metadata and downloads are handled through yt-dlp, while FFmpeg is used for audio preparation.

To run the source directly in an existing compatible Python environment:

```powershell
python -m pip install -r requirements.txt
python app.py
```

For Windows users, `run_windows.bat` is the recommended entry point.

## Third-party software

Sonus relies on third-party software and libraries, including:

- [yt-dlp](https://github.com/yt-dlp/yt-dlp)
- [pygame](https://www.pygame.org/)
- [Pillow](https://python-pillow.org/)
- [FFmpeg](https://ffmpeg.org/)

Their respective licenses apply to those components. The project does not relicense third-party software under the Sonus license.

## YouTube and content responsibility

Sonus is an independent desktop application and is not affiliated with, endorsed by, or sponsored by YouTube or Google.

Users are responsible for complying with applicable laws, copyright restrictions, and the terms of the services they access. Only use content that you are permitted to access or download.

## License

Sonus is licensed under the [MIT License](LICENSE).
