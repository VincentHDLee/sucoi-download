# Sucoidownload - 模块化视频下载器

一个基于 Python、yt-dlp 和 Tkinter 的模块化视频下载工具，提供图形界面，支持从多个平台搜索和下载视频。

## 主要功能

*   **模块化平台支持**: 通过标签页切换不同视频平台的操作界面 (当前支持 YouTube, TikTok)。
*   **YouTube 平台**:
    *   **视频搜索**: 使用 YouTube Data API v3，通过关键词搜索视频。
    *   **结果展示**: 在表格中清晰展示搜索结果，包含视频标题、播放量、点赞数、发布时间等信息。
    *   **添加到队列**: 可选择一个或多个搜索结果，将其添加到全局下载列表。
*   **TikTok 平台**: (基础支持)
    *   提供 URL 输入框，可添加 TikTok 视频到下载列表或直接下载 (具体实现依赖 `tiktok.py` 模块)。
*   **全局下载列表**:
    *   以表格形式集中管理来自不同平台的待下载、下载中、已完成或出错的任务。
    *   实时显示下载状态、文件大小、下载速度、预计剩余时间等。
*   **配置管理与设置**:
    *   **下载队列持久化**: 程序关闭时会自动保存未完成或出错的任务状态（如 URL、文件名、平台等），并在下次启动时自动加载，避免任务丢失。

    *   通过 `config.json` 文件管理配置项。
    *   提供图形化的设置界面，方便配置 YouTube API Key 和默认视频下载路径。
    *   下载路径修改后自动保存。
*   **用户友好的界面**:
    *   统一的顶部工具栏，包含状态显示、下载路径选择和设置入口。
    *   使用 `ttk` 主题，界面风格更现代。
*   **核心下载引擎**: 基于强大的 `yt-dlp`，理论上支持其所支持的所有网站 (需要相应模块实现对接)。

## 依赖

*   Python 3.x
*   Tkinter (通常随 Python 自带)
*   yt-dlp: `pip install yt-dlp`
*   Google API Python Client: `pip install google-api-python-client` (用于 YouTube 搜索)
*   **FFmpeg**: **强烈推荐安装** 并且其路径已添加到系统环境变量 `PATH` 中。yt-dlp 需要 FFmpeg 来合并分离的视频和音频流（常见于 YouTube 等网站），以获得最佳质量。请从 [FFmpeg 官网](https://ffmpeg.org/download.html) 下载并配置。

## 如何使用

1.  **获取 YouTube API Key (如果需要使用 YouTube 搜索功能)**:
    *   访问 [Google Cloud Console](https://console.cloud.google.com/)。
    *   创建一个新项目。
    *   在项目中启用 "YouTube Data API v3"。
    *   创建 API 密钥凭据。
    *   将获取到的 API Key 复制下来。

2.  **安装依赖**:
    ```bash
    pip install yt-dlp google-api-python-client
    # 推荐安装并配置好 FFmpeg
    ```

3.  **配置程序**:
    *   首次运行程序前 (或运行后通过设置界面)，编辑项目根目录下的 `config.json` 文件 (如果不存在，可以复制 `config.example.json` 并重命名)。
    *   将你的 YouTube API Key 填入 `api_key` 字段。
    *   (可选) 修改 `default_download_path` 为你希望的默认下载路径。
    *   或者，在程序启动后，点击右上角的 "设置" 按钮进行配置。

4.  **运行程序** (在 `sucoi-download` 目录下):
    *   **Windows**: 双击 `start.bat` 文件，或在命令行运行 `python sucoidownload.py`。

5.  **界面操作**:
    *   **选择平台**: 点击顶部的 "YouTube" 或 "TikTok" 标签页。
    *   **YouTube**:
        *   在 "搜索关键词" 输入框中输入你想搜索的内容。
        *   (可选) 选择时长和排序方式 (如果相关功能已实现)。
        *   点击 "搜索视频" 按钮。
        *   在 "搜索结果" 表格中查看结果。
        *   勾选或按住 Ctrl/Shift 点击选择想要下载的视频。
        *   点击 "添加到下载列表" 按钮。
    *   **TikTok**:
        *   (根据 `tiktok.py` 的实现) 可能需要输入 URL 并点击相应按钮。
    *   **下载列表**:
        *   切换到底部的 "下载列表" 查看已添加的任务。
        *   (如果需要选择下载项) 勾选要下载的任务。
        *   点击主界面上的 "开始下载" 按钮 (如果下载按钮在全局区域)。*注意：当前版本下载按钮可能位于 YouTube 标签页内，请根据实际界面操作。*
    *   **通用操作**:
        *   点击顶部 "选择下载路径" 按钮可以临时更改本次运行的下载目录。
        *   通过顶部的状态栏查看程序当前状态。
        *   点击顶部 "设置" 按钮修改配置。

## 注意事项

*   **YouTube API 配额**: YouTube Data API 有每日使用配额限制，请合理使用搜索功能。频繁或大量的搜索请求可能会耗尽配额。
*   下载成功与否依赖于 `yt-dlp` 对目标网站的支持情况以及网络连接。部分网站可能需要登录 Cookie 或代理才能正常下载 (当前版本暂未提供 Cookie/代理配置界面)。
*   **FFmpeg 对于下载高质量视频至关重要**，否则可能只能下载到音频或低画质文件。
*   `yt-dlp` 支持的网站列表可参考其官方文档：[https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md)
*   **持久化文件**: 未完成的下载任务信息保存在项目根目录下的 `download_queue.json` 文件中。请勿手动编辑此文件，否则可能导致加载失败或程序异常。


## 版权

本项目为内部工具，版权所有。