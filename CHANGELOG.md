# 更新日志 (Changelog)

本项目的所有重要更改都将记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
版本遵循[语义化版本](https://semver.org/lang/zh-CN/)规范。

## [0.2.0] - 2025-03-28

### 新增 (Added)

*   **YouTube 搜索功能**:
    *   集成 Google API Python Client (`google-api-python-client`)。
    *   在 GUI 添加关键词输入框和“搜索视频”按钮。
    *   实现 `search_videos` 方法，调用 YouTube Data API v3 `search.list`。
    *   实现 `handle_search` 方法，在后台线程处理搜索逻辑，并将结果（视频 URL）填充到 URL 输入框。
*   **配置管理**:
    *   创建 `config_manager.py` 模块 (`ConfigManager` 类) 用于加载/保存 `config.json`。
    *   创建 `config.example.json` 作为配置模板。
    *   移除代码中的硬编码 API Key，改为从配置加载。
    *   默认下载路径现在也从配置加载，并支持在修改后自动保存。
*   **设置界面**:
    *   在主窗口添加“设置”按钮。
    *   创建 `open_settings_window` 方法，弹出 Toplevel 窗口。
    *   设置窗口包含 YouTube API Key 和默认下载地址的输入框。
    *   实现输入框占位符效果（灰色提示文本）。
    *   实现 `save_settings` 方法，将修改后的配置保存到 `config.json` 并更新主程序状态。
    *   添加路径选择按钮 (`...`) 以方便选择默认下载路径。

### 更改 (Changed)

*   重构 `sucoidownload.py` 代码结构，将 `search_videos` 移入 `Sucoidownload` 类。
*   优化 `download_videos` 方法，改为逐个下载 URL，并增加成功/失败计数和总结。
*   优化 `progress_hook`，在状态栏显示更详细的下载信息（文件名和百分比）。
*   优化下载和搜索过程中的按钮状态管理（禁用/启用），防止重复操作。
*   改进 API 错误处理，提供更具体的错误信息（如配额超限、无效 Key）。
*   调整主窗口大小和布局以适应新组件。
*   文件名模板加入视频 ID (`%(title)s [%(id)s].%(ext)s`) 避免潜在重名。

### 修复 (Fixed)

*   修复了多次因代码操作（`apply_diff`, `insert_content`）导致的缩进错误。

---


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