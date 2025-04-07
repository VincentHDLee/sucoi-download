# 更新日志 (Changelog)

本项目的所有重要更改都将记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
版本遵循[语义化版本](https://semver.org/lang/zh-CN/)规范。

## [0.2.1] - 2025-04-07

### 新增 (Added)

*   **下载选中项**: 在下载列表下方添加 "下载选中项" 按钮，用于下载列表中勾选的任务。
*   **下载总结**: 下载批次结束后，弹出包含成功和失败数量的总结对话框。

### 更改 (Changed)

*   **"添加到队列"默认选中**: 通过 "添加到下载队列" 按钮添加的任务现在默认处于选中状态 ('☑')。
*   **优化状态提示**:
    *   "添加到下载队列" 的状态栏提示现在包含尝试总数、成功添加数、跳过数和失败数。
    *   "开始下载" (包括选中和立即) 的状态栏提示现在显示实际启动的任务数量。
    *   下载开始时，进度条会立即显示一个小的初始值 (安慰性进度)。
*   **"停止下载"按钮样式**: 将 "停止下载" 按钮背景色改为淡红色 (`#f8d7da`) 以示醒目。
*   **"移除选中项"按钮锁定逻辑**: 该按钮现在只在下载过程中被禁用，下载前和结束后均可使用。

### 修复 (Fixed)

*   修复了 "立即下载" 功能因参数类型错误 (`item_info` 列表 vs `url` 列表) 而无法启动下载任务的问题。
*   修复了 "立即下载" 功能调用时缺少 `platform` 参数导致的 `TypeError`。
*   修复了 "下载选中项" 流程结束后，监控线程未启动导致界面卡死和不显示总结弹窗的问题。

---


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

*   添加 `start.bat` 批处理文件，为 Windows 用户提供双击启动快捷方式。
*   **下载列表交互**:
    *   实现点击第一列选择框切换选中/未选中状态 ('☐'/'☑')。
    *   在下载列表下方添加 "移除选中项" 按钮，用于删除选中的下载任务。

*   **取消下载 (基础)**:
    *   添加 "停止下载" 按钮到主界面。
    *   实现通过标志位 (`cancel_requested`) 中断后续下载任务的逻辑。
    *   修改 YouTube 和 TikTok 模块的下载函数以支持检查取消标志（在文件之间中断）。

*   **下载进度条**: 使用 `ttk.Progressbar` 替代纯文本状态，更直观地显示下载进度。
### 更改 (Changed)

*   **架构重构 (Refactoring)**:
    *   创建 `youtube.py` 模块，将 YouTube 平台的搜索 (`search_videos`) 和下载 (`download_videos`) 逻辑从主程序 `sucoidownload.py` 中分离出来。
    *   修改 `youtube.download_videos` 以使用回调函数 (`progress_callback`) 报告下载进度，实现与 GUI 的解耦。
    *   修改 `sucoidownload.py` 以调用 `youtube.py` 中的函数，并实现 `update_download_progress` 回调来更新下载列表。

*   **前端重构 (GUI Rework)**:
    *   将原 URL 输入/结果文本框替换为两个 `ttk.Treeview` 表格，分别用于显示“搜索结果”和“下载列表”。
    *   实现 `add_selected_to_download` 方法，允许将搜索结果添加到下载列表。
    *   修改下载逻辑 (`start_download`, `download_videos_from_tree`, `progress_hook`) 以适配新的下载列表表格，实现状态更新。
*   **布局调整 (Layout Adjustments)**:
    *   多次调整按钮（搜索、添加、下载、设置、选择路径）和路径输入框的位置，以优化操作流程和视觉效果。
    *   为下载列表表格的列添加 `minwidth` 属性，改善小窗口下的表头显示。
*   重构 `sucoidownload.py` 代码结构，将 `search_videos` 移入 `Sucoidownload` 类。
*   优化 `download_videos` 方法，改为逐个下载 URL，并增加成功/失败计数和总结。
*   优化 `progress_hook`，在状态栏显示更详细的下载信息（文件名和百分比）。
*   优化下载和搜索过程中的按钮状态管理（禁用/启用），防止重复操作。
*   改进 API 错误处理，提供更具体的错误信息（如配额超限、无效 Key）。
*   调整主窗口大小和布局以适应新组件。
*   文件名模板加入视频 ID (`%(title)s [%(id)s].%(ext)s`) 避免潜在重名。

*   调整 TikTok 标签页，将 "立即下载选中项" 按钮文本改为 "立即下载"。
*   调整 YouTube 标签页布局，使 "时长" 和 "排序" 筛选条件的标签和下拉框在同一行左对齐显示。
### 修复 (Fixed)

*   修复了多次因代码操作（`apply_diff`, `insert_content`）导致的缩进错误。

*   修复了主界面顶部控件（状态、设置、路径选择）与中间标签页 (`Notebook`) 控件发生视觉重叠的问题，将所有顶部/底部控件统一水平排列到顶部框架中。

### 移除 (Removed)

*   移除旧的 `start.sh` 启动脚本，由 `start.bat` 替代 Windows 下的启动方式。


### 已知问题 (Known Issues)

*   (暂无)

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