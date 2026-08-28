# Sonus v1.1.0

Second Global release of Sonus for Windows.

## Highlights

This release focuses on a substantial internal refactor and quality-of-life keyboard shortcuts while preserving the working application behavior from the previous release.

### Refactor

- The application is no longer maintained as one large Python source file.
- Core responsibilities are split into dedicated modules for playback, queue management, caching, YouTube services, UI, settings, configuration and Windows platform integration.
- `app.py` is now a minimal entry point.
- The refactor is intended to make future maintenance and feature work safer without changing the application's established behavior.

### Keyboard shortcuts

When the Sonus main window is active:

- `↑` — volume +5%
- `↓` — volume -5%
- `→` — next track
- `←` — previous track
- `Enter` — play/pause

The shortcuts are disabled while Sonus is minimized or while another Sonus window/dialog has focus. Arrow keys also no longer move the queue selection as ordinary list navigation.

## Other

The release keeps the existing Sonus functionality, including YouTube videos and playlists, combined queue management, playback controls, seeking, volume control, background caching modes, repeat/random playback, English and Russian UI, startup cache cleanup, the first-run legal acknowledgement and automatic Windows setup.

## Windows setup

Download the source archive below, extract it and run `run_windows.bat`.

The launcher checks the required environment and installs missing Python dependencies automatically. Python 3.13 is used for compatibility with the current pygame dependency. FFmpeg is also checked during setup.

## Notes

This is a Global source release. The repository does not publish bundled executable releases or archives containing third-party binaries.

Sonus is not affiliated with YouTube or Google. Users are responsible for complying with applicable laws, copyright restrictions, creators' rights and service terms when accessing content.

---

# Sonus v1.1.0 - Русский

Второй Global-релиз Sonus для Windows.

## Основное

Этот релиз посвящён значительному внутреннему рефакторингу и новым горячим клавишам без намеренного изменения уже работающей функциональности приложения.

### Рефакторинг

- Приложение больше не хранится в одном большом Python-файле.
- Основные части разделены на отдельные модули: воспроизведение, очередь, кэширование, работа с YouTube, интерфейс, настройки, конфигурация и интеграция с Windows.
- `app.py` теперь является минимальной точкой входа.
- Рефакторинг сделан для упрощения дальнейшей поддержки и разработки без изменения устоявшегося поведения приложения.

### Горячие клавиши

Когда главное окно Sonus активно:

- `↑` — громкость +5%
- `↓` — громкость -5%
- `→` — следующий трек
- `←` — предыдущий трек
- `Enter` — воспроизведение / пауза

Горячие клавиши не работают, когда Sonus свёрнут или когда фокус находится на другом окне/диалоге Sonus. Стрелки также больше не перемещают выделение в очереди как обычная навигация по списку.

## Остальное

В релизе сохранена существующая функциональность Sonus: работа с видео и плейлистами YouTube, объединённая очередь, управление воспроизведением, перемотка, регулировка громкости, режимы фонового кэширования, повтор/случайное воспроизведение, русский и английский языки интерфейса, очистка кэша при запуске, одноразовое юридическое уведомление и автоматическая настройка Windows.

## Установка в Windows

Скачайте расположенный ниже архив с исходным кодом, распакуйте его и запустите `run_windows.bat`.

Лаунчер проверит необходимое окружение и автоматически установит отсутствующие Python-зависимости. Python 3.13 используется для совместимости с текущей зависимостью pygame. Наличие FFmpeg также проверяется во время настройки.

## Примечания

Это Global-релиз исходного кода. В репозитории не публикуются готовые исполняемые сборки или архивы со встроенными сторонними бинарными файлами.

Sonus не связан с YouTube или Google. Пользователь самостоятельно отвечает за соблюдение применимого законодательства, авторских прав, прав создателей контента и условий используемых сервисов.
