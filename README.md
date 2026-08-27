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
- English and Russian interface languages.
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

Users are responsible for complying with applicable laws, copyright restrictions, and the terms of the services they access. Only use content that you are permitted to access.

## License

Sonus is licensed under the [MIT License](LICENSE).

---

# Sonus - Русский

> Лёгкий настольный аудиоплеер YouTube для Windows.

Sonus — простое настольное приложение для прослушивания аудио с YouTube без отображения самого видео. Поддерживаются отдельные видео, плейлисты, текстовый поиск, управление очередью, фоновое кэширование, управление воспроизведением и громкостью.

## Возможности

- Поиск музыки на YouTube и выбор результата из списка.
- Открытие прямой ссылки на видео YouTube.
- Добавление плейлистов YouTube в очередь.
- Объединение плейлистов и отдельных видео в одной очереди.
- Воспроизведение, пауза, переход вперёд/назад и перемотка.
- Изменение громкости без перезапуска трека.
- Фоновое кэширование аудио с выбором режима загрузки.
- Последовательное, повторное и случайное воспроизведение очереди.
- Настраиваемое количество результатов поиска от 1 до 50.
- Тёмный интерфейс Sonus со скруглёнными панелями.
- Английский и русский языки интерфейса.
- Графический режим Windows без постоянно открытой консоли.

## Требования

- Windows 10 или Windows 11.
- Подключение к интернету для поиска и первой загрузки аудио.
- WinGet для автоматической установки отсутствующих компонентов.

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

Пользователь самостоятельно отвечает за соблюдение применимого законодательства, авторских прав и условий используемых сервисов. Используйте только тот контент, к которому у вас есть право доступа.

## Лицензия

Sonus распространяется по лицензии [MIT License](LICENSE).


## Legal notice

### First-run acknowledgement

On first launch, Sonus displays a short legal notice. The application requires the user to acknowledge it before normal use. The acknowledgement is stored locally in the application settings.

Sonus is an independent open-source desktop player and is not affiliated with, endorsed by, or sponsored by YouTube or Google. Sonus is intended for personal, non-commercial use. Sonus does not host, store, or distribute YouTube media; content is accessed at the user's request and may be temporarily cached on the user's device for playback and time-shifting. Users are responsible for complying with applicable law, copyright restrictions, creators' rights, and the terms of services they access. Only use content you are permitted to access.

### Copyright concerns (DMCA)

This repository contains source code and no hosted media. If you are a rights holder and believe specific repository content infringes your rights, please contact the repository maintainer first. GitHub also provides a DMCA takedown process for qualifying copyright complaints.

## Release policy

Official GitHub Releases are source-only. This repository does not publish bundled executable releases or archives containing third-party binaries. Release screenshots and other media are limited to content that the project has the right to use, such as original project assets or appropriately licensed / Creative Commons material.


## Юридическое уведомление

### Первоначальное уведомление

При первом запуске Sonus показывает краткое юридическое уведомление. Для начала обычной работы пользователь должен подтвердить, что ознакомился с ним. Подтверждение хранится локально в настройках приложения.

Sonus — независимый проект с открытым исходным кодом. Он не связан с YouTube или Google, не одобрен ими и не спонсируется ими. Sonus предназначен для личного некоммерческого использования. Sonus не размещает, не хранит и не распространяет медиаконтент YouTube; контент запрашивается пользователем и может временно кэшироваться на устройстве для воспроизведения и перемотки. Пользователь несёт ответственность за соблюдение применимого законодательства, ограничений авторского права, прав создателей контента и условий сервисов, к которым обращается приложение. Используйте только контент, к которому у вас есть право доступа.

### Вопросы авторского права (DMCA)

В репозитории отсутствует размещённый медиаконтент. Если правообладатель считает, что конкретный материал репозитория нарушает его права, рекомендуется сначала связаться с сопровождающим проекта. GitHub также предоставляет процедуру DMCA для соответствующих жалоб об авторских правах.

## Политика релизов

Официальные GitHub Releases распространяются только в виде исходного кода. Репозиторий не публикует готовые исполняемые файлы и архивы со сторонними бинарными файлами. Скриншоты и другие материалы для релизов ограничиваются контентом, на использование которого у проекта есть права: собственными материалами или материалами с подходящей лицензией / Creative Commons.
