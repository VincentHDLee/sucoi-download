# 更新日志 (Changelog)

本项目的所有重要更改都将记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
版本遵循[语义化版本](https://semver.org/lang/zh-CN/)规范。

## [0.2.4] - 2025-04-09 (修订)

### 新增 (Added)

*   **下载队列持久化**:
    *   实现程序关闭时自动保存未完成/出错的任务状态到 `download_queue.json`。
    *   实现程序启动时自动从 `download_queue.json` 加载未完成的任务到下载列表。
    *   为加载持久化队列添加了错误处理（如文件损坏时的备份）和用户提示。

### 更改 (Changed)

*   **UI 风格统一与美化**:
    *   将 TikTok 标签页 (`ui/tiktok_tab.py`) 中的 `tk` 控件替换为 `ttk` 版本，优化布局并添加滚动条。
    *   将主窗口 (`ui/main_window.py`) 中的 `tk` 按钮、标签、框架、输入框等替换为 `ttk` 版本。
    *   将 YouTube 标签页 (`ui/youtube_tab.py`) 中的 `tk` 按钮、标签、输入框等替换为 `ttk` 版本。
    *   移除了“停止下载”按钮的自定义样式（按钮已移除）。
    *   **状态显示**: 移除了主进度条，改为在状态栏显示任务计数进度（例如 “正在下载: 3/10”），并优化了最终完成状态的提示文本。
    *   **重试状态**: 简化了下载列表中重试状态的显示为 `[重试中...]`。
*   **错误信息改进**:
    *   修改 `DownloadService`，将 `yt-dlp` 的 `ignoreerrors` 设为 `False` 以捕获更详细错误。
    *   修改 `DownloadService` 中的错误提取逻辑，暂时统一返回“下载失败”给用户，并添加 TODO 注释。
    *   在主程序更新错误状态的描述时，添加了对 ANSI 转义码的清理。
*   **健壮性改进**:
    *   重构了 `start_immediate_downloads` 方法，简化逻辑，减少对异步 UI 状态的依赖，以解决竞争条件和重复提交问题。
    *   在 `start_selected_downloads` 和 `start_immediate_downloads` 中增加了对任务状态和存在性的检查，防止无效提交。

### 修复 (Fixed)

*   修复了 `modules/tiktok/logic.py` 中调用 `app.show_message` 时传递无效 `parent` 参数导致的 `TypeError`。
*   修复了下载任务在所有重试失败后，UI 状态仍显示为 `[重试中...]` 而不是 `[ERR]` 的问题。
*   修复了 `_on_closing` 方法未能正确将 `'[...] '` (准备中) 状态重置为 '待下载' 再保存到持久化文件的问题。
*   修复了因 `apply_diff` 操作引入的 Pylance 报告的缩进和语法错误。
*   修复了重启应用加载持久化任务后，点击“下载选中项”因状态检查逻辑错误而无法启动下载的问题。
*   修复了“移除选中项”后，下次启动程序时被移除的任务仍然从持久化文件加载的问题（通过在关闭时正确忽略已移除项并清空文件实现）。
*   修复了在设置窗口修改并发数时，因方法参数不匹配导致无法保存设置的问题 (`save_settings` `TypeError`)。
*   修复了移除取消功能时遗漏的代码调用导致的运行时错误 (`AttributeError`, `NameError`)。
*   修复了移除取消功能时引入的 `SyntaxError` (`core/download_service.py` 中的 `try...except` 结构错误)。

*   **移除 (Removed)**:
    *   移除了主窗口下方的“停止下载”按钮及相关的下载取消功能。


---


## [0.2.3] - 2025-04-07

### 新增 (Added)

*   **下载重试机制**: `DownloadService` 现在会在下载失败时自动进行最多两次重试 (分别延迟 3 秒和 5 秒)，以提高对临时网络问题的容错性。
*   **重试状态显示**: 下载列表中的任务在重试等待期间会显示 `[重试中...]` 状态。

### 更改 (Changed)

*   优化了下载列表“状态”列的显示，使用更通用的 ASCII 符号 (`[...]`, `%`, `[OK]`, `[ERR]`, `[CAN]`) 替代 Unicode 图标，以解决潜在的字体渲染问题。
*   优化了“剩余时间”和“传输速度”列的显示，移除了可能导致渲染错误的 ANSI 转义码。

### 修复 (Fixed)

*   修复了 `DownloadService.download_item` 方法在下载完成后，由于返回值处理逻辑错误可能返回 `None` 的问题。此问题导致后续调用者 (如 `_run_single_download_task`) 出现 `AttributeError: 'NoneType' object has no attribute 'get'` 错误。
*   改进了 `DownloadService` 中处理下载错误和取消状态的逻辑，确保在各种情况下都能返回包含正确状态 (`finished`, `error`, `cancelled`) 的字典。

---


## [0.2.2] - 2025-04-07

### 新增 (Added)

*   **并行下载框架**:
    *   引入 `concurrent.futures.ThreadPoolExecutor` 管理下载线程。
    *   添加 `max_concurrent_downloads` 配置项到 `config.example.json` (默认值为 3)。
    *   在设置窗口添加了最大并发下载数 (1-10) 的下拉选择框。
*   **下载取消改进**:
    *   `DownloadService` 现在会检查取消请求标志，并尝试在下载过程中断任务（通过进度钩子）。
    *   任务被用户取消时，状态会更新为“已取消”。
*   **错误处理增强**:
    *   `DownloadService` 尝试解析常见的 `yt-dlp` 下载错误，并提供更友好的错误描述。
    *   保存设置失败时，错误提示框会显示更详细的原因（如果可用）。
*   **设置窗口提示**: 当保存设置且 YouTube API Key 为空时，会额外弹出警告提示。

### 更改 (Changed)

*   修改了 `save_settings` 逻辑，以保存并发数配置，并在配置变化时重新创建线程池。
*   修改了 `_on_closing` 逻辑，以正确关闭 `ThreadPoolExecutor`。
*   修改了 `start_immediate_downloads` 和 `start_selected_downloads`，使用 `ThreadPoolExecutor` 提交任务。
*   创建了 `_monitor_download_futures` 方法替换旧的 `_monitor_download_threads` 来监控 `Future` 对象。
*   修改了 `ConfigManager`，使其能在保存失败时返回错误信息。
*   调整了设置窗口中底部按钮的布局，统一使用 `grid` 并将“选择路径”按钮移至左侧。

### 修复 (Fixed)

*   修复了设置窗口中布局管理器 (`pack` 和 `grid`) 混用导致的 `TclError`。

---


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
*   **代码整理 (TikTok 模块)**:
    *   重构 `modules/tiktok/logic.py`，使其不再直接依赖 UI 控件，改为接收处理后的 URL 列表。
    *   统一 `modules/tiktok/logic.py` 中的消息提示，改为调用主程序的 `show_message` 方法。
    *   移除 `modules/tiktok/logic.py` 中未使用的导入、冗余函数 (`_perform_single_tiktok_download`) 和测试代码块。
    *   更新 `ui/tiktok_tab.py` 以适配 `logic` 函数签名变化，在调用前提取 URL 列表。
    *   改进了 `modules/tiktok/logic.py` 的函数文档字符串。

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