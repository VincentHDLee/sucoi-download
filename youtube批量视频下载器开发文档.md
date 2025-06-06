# Sucoidownload 增强版 - 开发文档与计划 (更新于 2025-04-07)

## 当前情况与调整背景
由于所有尝试的 YouTube 下载方案均失败，且 YouTube 的下载逻辑实现较为复杂，开发团队决定暂时搁置 YouTube 功能。现在的目标是调整 Sucoidownload 的架构，使其支持模块化设计和多平台扩展，采用类似浏览器的标签菜单形式，让用户可以切换不同平台的下载页面。新的开发重点包括：
- **添加标签样式菜单**：为主程序引入标签界面，解耦业务逻辑。
- **实现 TikTok 模块**：作为模块化设计的验证，优先支持 TikTok 视频下载。
- **完善下载流程与体验**: 包括并行下载、错误处理、**内置重试机制**、UI 布局和状态显示优化。

以下是调整后的文档和开发计划。

---

## 项目概览 (调整后)
Sucoidownload 增强版旨在打造一个模块化的视频批量下载工具，通过标签式界面支持多个平台（如 TikTok、YouTube 等）。当前阶段目标是：
- 实现主程序的标签菜单界面。
- 开发 TikTok 模块，支持输入 URL 并下载视频。
- 建立可扩展的架构，为未来添加其他平台（如 YouTube）奠定基础。
- 提供稳定可靠的下载体验，包括并行处理、**错误自动重试 (最多2次)** 和清晰的状态反馈。

### 核心目标
- 主程序 (`core/main_app.py`) 通过标签菜单动态加载平台模块和 UI，实现解耦。
- 提供类似浏览器的用户体验，用户可在不同平台下载页面间切换。
- 初期支持 TikTok 视频下载，验证模块化设计的可行性。
- 实现并行下载以提高效率，并通过内置重试机制处理临时性错误。

---

## 架构设计 (已部分实现)
### 模块化扩展

为了支持更多视频平台，Sucoidownload 采用了模块化设计。这种设计将特定平台的逻辑（URL 解析、任务生成等）与核心下载服务和 UI 分离。

**详细的扩展方法、新平台（如 Instagram、Bilibili、Vimeo）的技术分析与集成步骤，请务必参考：[模块扩展开发指南](模块扩展开发指南.md)**。

---

- **`core/main_app.py` (核心控制器):**
  - 初始化 Tkinter GUI (`ui/main_window.py`)。
  - 管理通用功能：下载队列展示、配置加载、用户交互（按钮事件处理）、状态栏更新、消息弹窗。
  - 动态加载平台模块 (`modules/`) 和平台 UI (`ui/`) 并创建对应标签页。
  - 使用 `concurrent.futures.ThreadPoolExecutor` 管理下载线程池，实现并行下载。
  - 协调下载任务的提交、监控和结果汇总。
  - 处理下载进度回调，更新 UI 状态（包括清理 ANSI 码）。
- **`core/download_service.py` (下载服务):**
  - 封装对 `yt-dlp` 的调用逻辑。
  - 提供统一的 `download_item` 接口，接受任务信息和回调函数。
  - **内置下载重试机制** (默认最多 2 次重试，延迟 3s/5s)，对调用者透明。
  - 通过回调函数 (`progress_callback`) 向调用者报告下载进度、状态（包括 `retrying`）和最终结果。
  - 处理通用的下载错误。
- **`config/config_manager.py` (配置模块):**
  - 管理 `config.json`，存储 API 密钥（若需要）、默认下载路径、最大并发数等。
- **`modules/` (平台业务逻辑模块):**
  - **核心职责**: 封装特定平台的业务逻辑，如 URL 解析、API 调用（如果需要）、为 `yt-dlp` 生成任务参数等。**严格禁止包含任何 UI 代码**。每个模块应独立工作，不依赖其他平台模块。
  - **扩展方式**: 在此目录下为新平台创建子目录（例如 `instagram/`），并在其中创建 `logic.py` 文件，实现平台特定的逻辑。详细接口规范和实现步骤参见 [模块扩展开发指南](模块扩展开发指南.md)。
  - `tiktok/logic.py`: (已实现) 封装 TikTok 相关逻辑。
  - `instagram/logic.py`, `bilibili/logic.py`, `vimeo/logic.py`: (推荐下一步扩展) 未来添加这些平台的逻辑模块。
  - `youtube/logic.py`: (已搁置) 原计划封装 YouTube 搜索、下载逻辑。
- **`ui/` (用户界面模块):**
  - **核心职责**: 包含主窗口框架 (`main_window.py`) 和各个平台对应的标签页 UI。平台标签页负责接收用户输入（如 URL），并调用 `main_app.py` 提供的接口来触发相应的平台逻辑模块，最终将任务添加到下载队列。
  - **扩展方式**: 为新平台创建对应的标签页 Python 文件（例如 `instagram_tab.py`），实现其特定的 UI 布局和控件。`main_app.py` 会动态扫描并加载这些标签页。详细实现步骤参见 [模块扩展开发指南](模块扩展开发指南.md)。
  - `main_window.py`: 主窗口框架和通用 UI 元素（如菜单、状态栏、下载列表 Treeview）。
  - `tiktok_tab.py`: (已实现) TikTok 标签页 UI。
  - `instagram_tab.py`, `bilibili_tab.py`, `vimeo_tab.py`: (推荐下一步扩展) 未来添加这些平台的 UI 标签页。
  - `youtube_tab.py`: (已搁置) 原计划的 YouTube 标签页 UI。

---

## GUI 设计 (已部分实现)
- **主窗口：**
  - 顶部：状态栏、设置按钮、下载路径选择。
  - 中部：使用 `ttk.Notebook` 实现标签式布局，每个标签代表一个平台。
  - 下部：
      - 下载列表 (`ttk.Treeview`): 显示任务的选择框、文件名、大小、**状态 (使用 `[...]`, `%`, `[OK]`, `[ERR]`, `[重试中...]` 等文本指示)**、剩余时间(清理后)、速度(清理后)、平台、描述。
      - **主进度条**: 位于下载列表下方，显示所有活动任务的**平均进度**。
      - **控制按钮栏**: 包含 "移除选中项"、"下载选中项" 按钮。
- **TikTok 标签页：**
  - 输入框：用于输入 TikTok 视频 URL (每行一个)。
  - 按钮：“添加到下载队列”、“立即下载”。
- **通用控件：**
  - 设置窗口：用于配置 API Key、默认下载路径、最大并发数。

---

## 技术选型
| 技术/工具                   | 用途                         | 原因                              |
|---------------------------|------------------------------|-----------------------------------|
| Python                    | 开发语言                    | 生态丰富，适合快速开发            |
| Tkinter (`ttk`)           | GUI 框架                    | 轻量、跨平台，`ttk` 外观现代      |
| `ttk.Notebook`            | 标签菜单实现                | 内置支持多标签切换                |
| `ttk.Treeview`            | 下载列表显示                | 表格形式展示数据清晰              |
| `ttk.Progressbar`         | 总体进度显示                | 直观反馈下载进展                  |
| yt-dlp                    | 视频下载核心                | 通用性强，支持多平台              |
| `concurrent.futures`      | 并行下载管理                | Python 标准库，方便管理线程池     |
| `config_manager.py`       | 配置管理                   | 统一管理设置，提高灵活性          |
| `re`                      | 正则表达式 (清理 ANSI 码)    | 处理 `yt-dlp` 输出             |
| `json`                    | 数据持久化 (未来计划)        | 标准库，方便读写结构化数据        |
| `time`                    | 重试延时                    | 标准库，实现等待功能              |

---

## 注意事项
- **模块化设计：** 每个平台模块 (`modules/`) 只包含业务逻辑，不依赖 Tkinter。对应的 UI 在 `ui/` 目录下实现。
- **接口统一：** 主程序 (`main_app.py`) 通过标准接口与平台模块交互。
- **错误处理:** `DownloadService` 处理下载层面的错误和重试，`main_app.py` 处理任务调度和 UI 更新中的错误。
- **线程安全**: 访问共享数据（如 `_callback_context`, `active_task_progress`）时需注意线程安全（已使用 `_context_lock`）。

## 预期成果 (已达成)
- 一个支持标签菜单的 Sucoidownload 主程序框架。
- 可用的 TikTok 下载模块，用户可输入 URL 下载视频，支持并行和自动重试。
- 清晰定义的可扩展架构，便于未来添加 YouTube 等平台。
- 相对稳定和用户友好的下载体验，具有基本的错误处理和状态反馈。

---

## 已知问题与未来计划 (更新于 2025-04-09)

### 已知问题
*   (已解决) 主进度条相关问题已通过移除进度条并改用状态栏计数解决。

### 短期计划 (参考三日计划)
*   **下载队列持久化**: **(已完成)** 实现程序关闭后保存和恢复未完成/出错的任务。
*   **美化 TikTok 标签页界面**: 调整控件布局，优化视觉效果。（**低优先级 - TODO**）
*   **更新文档 (README)**: **(已完成)** 补充队列持久化等新功能的使用说明。
*   **处理持久化边界情况/错误**: **(已完成)** 增强健壮性。

### 中长期计划 / 优化方向 (来自 Grok 建议筛选)
*   **改进错误反馈**: 在下载列表的“描述”列显示更具体的错误信息。
*   **处理私有/受限内容**: (来自扩展指南) 研究并实现一种安全的方式，允许用户提供必要的凭据（如 Cookies 文件、账户登录 - 需谨慎处理安全性）来下载需要授权的内容（例如 Instagram Stories/私有帖子, Vimeo 私有视频等）。
*   **暴露高级下载选项**: (来自扩展指南) 在平台标签页或设置中，提供更多 `yt-dlp` 的常用选项，例如选择视频/音频格式、下载字幕、使用代理等。
*   **下载质量预设**: (来自扩展指南) 允许用户为特定平台或全局设置首选的下载质量和格式（例如，总是下载最佳质量的 MP4）。
*   **后台下载与系统通知**: (来自扩展指南) 探索将下载任务作为后台进程运行，并在完成后通过系统通知告知用户（可能需要额外的库）。
*   **探索插件系统架构**: (来自扩展指南) 从长远来看，可以考虑设计一个更灵活的插件系统，允许开发者更容易地添加对新平台的支持，甚至自定义下载流程，而无需修改核心代码。
*   **优化状态栏进度**: **(已完成)** 移除了主进度条，改为在状态栏显示任务计数进度。
*   **暂停/恢复功能**: 添加暂停和恢复下载的功能（依赖技术可行性）。
*   **改进重试机制**: **(UI部分完成)** UI 简化了重试状态显示为 `[重试中...]`，未来可考虑根据错误类型动态调整重试策略。
*   **性能优化**: 动态调整线程池大小，添加下载限速选项。
*   **代码健壮性**: 实现全局异常处理机制。
*   **扩展性**: 定义更严格的平台模块接口规范，添加下载列表批量选择（全选/反选）。
*   **实现可靠的下载取消功能**: 允许用户在下载过程中停止任务（当前已移除）。
*   **其他**: 添加日志查看功能、多语言支持、增加测试覆盖率。