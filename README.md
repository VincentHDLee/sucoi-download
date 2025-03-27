# Sucoidownload - 视频批量下载器

一个基于 Python 和 yt-dlp 的简单图形界面工具，用于批量下载来自各种网站的视频。

## 功能

*   通过图形界面输入多个视频 URL（每行一个），支持 yt-dlp 所支持的大部分网站。
*   选择本地文件夹保存下载的视频。
*   自动使用 yt-dlp 下载视频，并尝试获取最佳质量（需要 FFmpeg 支持合并）。
*   默认将视频保存在程序目录下的 `download` 文件夹中。
*   提供简单的下载状态反馈。

## 依赖

*   Python 3.x
*   Tkinter (通常随 Python 自带)
*   yt-dlp: `pip install yt-dlp`
*   **FFmpeg**: **强烈推荐安装** 并且其路径已添加到系统环境变量 `PATH` 中。yt-dlp 需要 FFmpeg 来合并分离的视频和音频流（常见于 YouTube, Bilibili 等网站），以获得最佳质量。请从 [FFmpeg 官网](https://ffmpeg.org/download.html) 下载并配置。

## 如何使用

1.  **安装依赖**:
    ```bash
    pip install yt-dlp
    # 推荐安装并配置好 FFmpeg
    ```
2.  **运行程序**:
    *   **Windows**: 直接运行 `python sucoidownload.py`。
    *   **Linux/macOS/Git Bash/WSL**: 运行 `./start.sh` (首次运行可能需要 `chmod +x start.sh`)。
3.  **界面操作**:
    *   在 "请输入视频 URL" 文本框中粘贴 URL，每行一个。支持 YouTube, Bilibili, TikTok 等众多网站。
    *   点击 "选择路径" 按钮选择或确认保存位置 (默认为 `download` 文件夹)。
    *   点击 "开始下载" 按钮。
    *   观察左上角的状态提示。

## 注意事项

*   下载成功与否依赖于 yt-dlp 对目标网站的支持情况以及网络连接。部分网站可能需要登录 Cookie 或代理才能正常下载。
*   **FFmpeg 对于下载高质量视频至关重要**，否则可能只能下载到音频或低画质文件。请务必正确安装并配置。
*   视频标题中的特殊字符可能会影响最终保存的文件名。
*   `yt-dlp` 支持的网站列表可参考其官方文档：[https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md)

## 版权

本项目为内部工具，版权所有。