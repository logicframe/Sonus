# Sonus

> A lightweight desktop YouTube audio player for Windows.

Sonus is a simple desktop application for listening to audio from YouTube without displaying the video itself. It supports direct videos, playlists, text search, queue management, background caching, playback controls and volume adjustment.

## Features

- Search YouTube for music and choose a result from the search list.
- Open a direct YouTube video link.
- Add a YouTube playlist to the queue.
- Combine playlists and individual videos in one queue.
- Play, pause, skip forward, go back and seek through a track.
- Adjust playback volume.
- Background audio caching with selectable download modes.
- Sequential, repeat-queue and random playback modes.
- Configurable search result count from 1 to 50.
- Dark Sonus interface with rounded panels.
- English and Russian interface languages.

## Requirements

- Windows 10 or Windows 11.
- Internet connection for search and first-time audio downloads.
- WinGet for automatic setup of missing components(It's installed by default on Windows 10/11 as part of "App Installer").

The Global Windows launcher installs Python 3.13 and the Python dependencies automatically when needed. It also checks for FFmpeg and attempts to install it through WinGet when it is not available.

## Quick start

1. Download the latest release from the **Releases** page.
2. Extract the archive to a folder.
3. Run `run_windows.bat`.
4. Wait for the first-time environment setup to finish.
5. Sonus starts automatically without leaving a console window open.

On subsequent launches, the launcher reuses the existing Python environment and only installs missing/outdated Python packages when necessary.

## Using Sonus

Paste a YouTube video or playlist URL into the search bar and press **Process**.

For a text query, enter a track title, artist or another search phrase and start the search. Select a result and add it to the queue.

The queue can contain tracks from multiple sources. Adding a new video or playlist does not replace the existing queue.

## Background caching

Sonus can download tracks to a local cache in the background. The mode can be changed in the application settings:

- **Streaming** - downloads tracks in queue order, from the first item to the last.
- **Smart** - downloads the selected track first, then continues through the queue in order.
- **Mixed** - downloads the selected track first, then two previous and two next tracks, then continues through the queue in order.

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

---

# Sonus - Русский

> Лёгкий десктопный аудиоплеер YouTube для Windows.

Sonus — простое настольное приложение для прослушивания аудио с YouTube без отображения самого видео. Поддерживаются отдельные видео, плейлисты, текстовый поиск, управление очередью, фоновое кэширование, управление воспроизведением и громкостью.

## Возможности

- Поиск музыки на YouTube и выбор результата из списка.
- Открытие прямой ссылки на видео YouTube.
- Добавление плейлистов YouTube в очередь.
- Объединение плейлистов и отдельных видео в одной очереди.
- Воспроизведение, пауза, переход вперёд/назад и перемотка.
- Изменение громкости.
- Фоновое кэширование аудио с выбором режима загрузки.
- Последовательное, повторное и случайное воспроизведение очереди.
- Настраиваемое количество результатов поиска от 1 до 50.
- Тёмный интерфейс Sonus со скруглёнными панелями.
- Английский и русский языки интерфейсы.

## Требования

- Windows 10 или Windows 11.
- Подключение к интернету для поиска и первой загрузки аудио.
- WinGet для автоматической установки отсутствующих компонентов(установлен в windows 10/11 по умолчанию).

Глобальный Windows-лаунчер автоматически устанавливает Python 3.13 и Python-зависимости при необходимости. Он также проверяет наличие FFmpeg и пытается установить его через WinGet, если FFmpeg отсутствует.

## Быстрый запуск

1. Скачайте последнюю версию со страницы **Releases**.
2. Распакуйте архив в любую папку.
3. Запустите `run_windows.bat`.
4. Дождитесь завершения первоначальной настройки окружения.
5. Sonus запустится автоматически без постоянно открытого окна консоли.

При последующих запусках лаунчер использует существующее окружение и устанавливает только отсутствующие или обновлённые Python-пакеты.

## Использование Sonus

Вставьте ссылку на видео или плейлист YouTube в поисковую строку и нажмите **Обработать**.

Для текстового поиска введите название трека, исполнителя или другой поисковый запрос и запустите поиск. Выберите результат и добавьте его в очередь.

Очередь может содержать треки из разных источников. Добавление нового видео или плейлиста не заменяет существующую очередь.

## Фоновое кэширование

Sonus может загружать треки в локальный кэш в фоновом режиме. Режим можно изменить в настройках приложения:

- **Потоковая** - треки загружаются по порядку очереди, от первого до последнего.
- **Умная** - сначала загружается выбранный трек, затем остальные по порядку очереди.
- **Смешанная** - сначала загружается выбранный трек, затем два предыдущих и два следующих, после чего загрузка продолжается по порядку очереди.

Фоновая загрузка выполняется последовательно, чтобы не создавать лишнюю нагрузку на сеть и процессор.

Рабочий кэш очищается при запуске Sonus, поэтому файлы предыдущих сеансов не накапливаются бесконечно.

## Результаты поиска

Текстовый поиск сначала использует музыкально-ориентированный поиск YouTube, а при необходимости переходит к обычному поиску YouTube. Поэтому результаты должны лучше соответствовать музыкальным запросам, однако Sonus не может гарантировать, что каждый результат будет исключительно аудиорелизом.

## Структура проекта

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

## Разработка

Приложение реализовано на Python: Tkinter используется для графического интерфейса, pygame - для воспроизведения аудио. Метаданные YouTube и загрузка обрабатываются через yt-dlp, а FFmpeg используется для подготовки аудио.

Для запуска исходников в уже настроенном совместимом окружении:

```powershell
python -m pip install -r requirements.txt
python app.py
```

Для Windows рекомендуется использовать `run_windows.bat`.

## Стороннее программное обеспечение

Sonus использует сторонние программы и библиотеки, включая:

- [yt-dlp](https://github.com/yt-dlp/yt-dlp)
- [pygame](https://www.pygame.org/)
- [Pillow](https://python-pillow.org/)
- [FFmpeg](https://ffmpeg.org/)

Для этих компонентов действуют их собственные лицензии. Лицензия Sonus не распространяется на стороннее программное обеспечение.

## YouTube и ответственность за содержимое

Sonus является независимым приложением и не связан с YouTube или Google, не одобрен и не спонсируется ими.

Пользователь самостоятельно отвечает за соблюдение применимого законодательства, авторских прав и условий используемых сервисов. Используйте только тот контент, к которому у вас есть право доступа или загрузки.

## Лицензия

Sonus распространяется по лицензии [MIT License](LICENSE).
