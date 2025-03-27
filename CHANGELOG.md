# 更新日志 (Changelog)

本项目的所有重要更改都将记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
版本遵循[语义化版本](https://semver.org/lang/zh-CN/)规范。

## [0.1.0] - 2025-03-27

### 新增 (Added)

*   基于 `yt-dlp` 和 `Tkinter` 创建初始的视频批量下载工具 (`sucoidownload.py`)。
*   在程序启动时自动创建 `download` 文件夹作为默认保存路径。
*   添加 `start.sh` 启动脚本，方便在类 Unix 环境下运行。
*   添加 `.gitignore` 文件，忽略 Python 缓存、虚拟环境、下载内容等。
*   添加 `README.md` 文件，包含项目说明、依赖和使用方法。
*   添加 `youtube批量视频下载器开发文档.md`，规划 YouTube 搜索与下载功能。
*   添加本 `CHANGELOG.md` 文件。

### 更改 (Changed)

*   修复了下载视频只有音频或无法播放的问题，调整 `yt-dlp` 的 `format` 和 `postprocessors` 参数（最终移除以使用默认设置）。
*   优化了 Tkinter GUI 布局，使用 `grid` 替换 `pack`，调整组件位置。
*   将 GUI 文本和 `README.md` 中的描述通用化，不再仅限于 TikTok，反映工具支持多种网站。

### 修复 (Fixed)

*   修复了 Tkinter 布局中 `grid` 和 `pack` 混用导致的 `TclError`。