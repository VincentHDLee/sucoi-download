# Sucoidownload - TikTok 批量下载器

一个基于 Python 和 yt-dlp 的简单图形界面工具，用于批量下载 TikTok 视频。

## 功能

*   通过图形界面输入多个 TikTok 视频 URL（每行一个）。
*   选择本地文件夹保存下载的视频。
*   自动使用 yt-dlp 下载视频，并尝试获取最佳质量（需要 FFmpeg 支持合并）。
*   默认将视频保存在程序目录下的 `download` 文件夹中。
*   提供简单的下载状态反馈。

## 依赖

*   Python 3.x
*   Tkinter (通常随 Python 自带)
*   yt-dlp: `pip install yt-dlp`
*   **FFmpeg**: **必须安装** 并且其路径已添加到系统环境变量 `PATH` 中。yt-dlp 需要 FFmpeg 来合并分离的视频和音频流，以获得最佳质量。请从 [FFmpeg 官网](https://ffmpeg.org/download.html) 下载并配置。

## 如何使用

1.  **安装依赖**:
    ```bash
    pip install yt-dlp
    # 确保已安装并配置好 FFmpeg
    ```
2.  **运行程序**:
    *   **Windows**: 直接运行 `python sucoidownload.py`。
    *   **Linux/macOS/Git Bash/WSL**: 运行 `./start.sh` (首次运行可能需要 `chmod +x start.sh`)。
3.  **界面操作**:
    *   在 "请输入 TikTok 视频 URL" 文本框中粘贴 URL，每行一个。
    *   点击 "选择路径" 按钮选择或确认保存位置 (默认为 `download` 文件夹)。
    *   点击 "开始下载" 按钮。
    *   观察左上角的状态提示。

## 注意事项

*   下载成功与否依赖于 yt-dlp 对 TikTok 的支持情况以及网络连接。
*   **FFmpeg 是必需的**，否则可能只能下载到音频或低画质视频。请务必正确安装并配置。
*   视频标题中的特殊字符可能会影响最终保存的文件名。

## 版权

本项目为内部工具，版权所有。