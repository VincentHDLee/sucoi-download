# core/main_app.py - Main Application Logic Controller
import tkinter as tk
from tkinter import messagebox # Keep for internal logic potentially
import os
import importlib # For dynamic module loading
from threading import Thread
import time # For monitor thread sleep
import concurrent.futures
import re # 用于清除 ANSI 转义码
import json # 用于队列持久化

# Import necessary components from the new structure
# Adjust imports based on running from project root or core directory
try:
    # Assuming running from project root (e.g., python -m core.main_app)
    from config.config_manager import ConfigManager
    from ui.main_window import MainWindow
    from core.download_service import DownloadService # <-- 已取消注释
except ImportError:
    # Fallback if running directly from core directory (adjust paths)
    import sys
    # Add project root (one level up) to sys.path
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    from config.config_manager import ConfigManager
    from ui.main_window import MainWindow
    from core.download_service import DownloadService # <-- 已取消注释 (Fallback)

class SucoiAppController:
    """主应用程序逻辑控制器。"""

    def __init__(self):
        self.root = tk.Tk()
        self.cancel_requested = False
        # 移除 self.active_download_threads = []

        # --- Initialize Core Components ---
        # Determine base path for config relative to this script's location
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir) # Assumes core is one level down
        config_path = os.path.join(project_root, 'config', 'config.json')
        example_config_path = os.path.join(project_root, 'config', 'config.example.json')

        self.config_manager = ConfigManager(config_file=config_path,
                                             example_config_file=example_config_path)
        # Initialize DownloadService
        self.download_service = DownloadService() # <-- 恢复原状

        # --- Initialize ThreadPoolExecutor ---
        try:
            max_workers_config = self.config_manager.get_config('max_concurrent_downloads', 3)
            # Ensure it's a valid integer between 1 and, say, 10 (or a reasonable upper limit)
            self.max_workers = max(1, min(10, int(max_workers_config)))
        except (ValueError, TypeError):
            print(f"警告: 配置中的 'max_concurrent_downloads' 值无效，将使用默认值 3。")
            self.max_workers = 3
        print(f"信息: 初始化下载线程池，最大并发数: {self.max_workers}")
        self.download_executor = concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers)
        self.active_futures = {} # 用于存储 Future 对象，键为 item_id
        self.active_task_progress = {} # 用于存储活动任务进度 {item_id: percentage} - 将被移除
        self.removed_item_ids = set() # 存储用户已移除的任务ID
        # --- 新增：用于基于计数的批次进度条 ---
        self.total_batch_tasks = 0      # 当前批次的总任务数
        self.completed_batch_tasks = 0  # 当前批次已完成的任务数


        # --- Initialize UI ---
        # Pass self (the controller) to the MainWindow
        self.view = MainWindow(self.root, self)

        # --- Load Platform Modules and Tabs ---
        self.platform_modules = {} # Store loaded platform logic modules
        self.platform_ui_modules = {} # Store loaded platform UI modules
        self._load_platforms()

        # Bind close window event
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

        # --- Load Persistent Queue ---
        # --- Start the Application ---
        self._load_persistent_queue() # 加载上次未完成的任务
        self.root.mainloop()

    def _load_platforms(self):
        """Dynamically load platform modules and add their UI tabs."""
        # Define platforms to load { 'PlatformName': ('logic_module_path', 'ui_module_path') }
        platforms_to_load = {
            # Platform Name: (logic module path relative to project root, ui module path relative to project root)
            'TikTok': ('modules.tiktok.logic', 'ui.tiktok_tab'),
            'YouTube': ('modules.youtube.logic', 'ui.youtube_tab'), # Keep placeholder
        }

        for name, (logic_path, ui_path) in platforms_to_load.items():
            logic_module = None
            ui_create_tab_func = None

            # Load logic module
            try:
                logic_module = importlib.import_module(logic_path)
                self.platform_modules[name] = logic_module
                print(f"成功加载 '{name}' 逻辑模块。")
            except ImportError as e:
                print(f"警告: 无法加载 {name} 逻辑模块 ({logic_path}): {e}")
                # If logic fails, we might still want to load the UI (to show an error tab)

            # Load UI module and get create_tab function
            try:
                ui_module = importlib.import_module(ui_path)
                if hasattr(ui_module, 'create_tab'):
                    ui_create_tab_func = ui_module.create_tab
                    self.platform_ui_modules[name] = ui_module
                    print(f"成功加载 '{name}' UI 模块。")
                else:
                     print(f"警告: UI 模块 {ui_path} 未实现 create_tab 函数。")
                     self.view._add_error_tab(name, f"UI模块 {ui_path} 接口不完整") # Use view's method
                     continue # Cannot add tab without create_tab

            except ImportError as e:
                print(f"警告: 无法加载 {name} UI 模块 ({ui_path}): {e}")
                self.view._add_error_tab(name, f"无法加载UI模块:\n{e}") # Use view's method
                continue # Cannot add tab if UI module fails

            # Add the tab using the UI function
            if ui_create_tab_func:
                 # Pass self (controller) to create_tab so UI elements can call controller methods
                 tab_frame = self.view.add_platform_tab(name, ui_create_tab_func)
                 # TODO: Store reference to tab_frame if needed for later control

    # --- Methods called by MainWindow (UI Events) ---

    def request_cancel(self):
        """Sets the cancel flag and updates status. Called by Stop button."""
        if not self.cancel_requested:
            self.cancel_requested = True
            self.view.update_status_bar("正在请求停止下载...")
            # TODO: Implement a more robust way to signal threads if needed
        else:
            self.view.update_status_bar("已请求停止下载")

    # 修改：接收 limit_kb_str，参数名使用 kwargs 风格以提高可读性
    def save_settings(self, *, api_key, download_path, concurrency_str, window, placeholder_api, placeholder_pth): # 恢复 download_path, placeholder_pth
        """Saves settings from the settings dialog. Called by Save button in settings."""
        updates = {}
        final_api_key = api_key if api_key != placeholder_api else ''
        final_download_path = ''
        is_path_valid = False

        if download_path and download_path != placeholder_pth:
            try:
                abs_path = os.path.abspath(download_path)
                # Check if the directory exists or if its parent exists
                if os.path.isdir(abs_path) or os.path.isdir(os.path.dirname(abs_path)):
                     final_download_path = abs_path
                     is_path_valid = True
                else:
                     print(f"警告: 设定的默认下载路径 '{abs_path}' 似乎无效，将不保存此路径。")
                     self.view.show_message("警告", f"路径 '{download_path}' 无效，请选择一个有效的目录。", msg_type='warning', parent=window)
                     # Keep the old path or clear it? Let's keep the old one.
                     final_download_path = self.config_manager.get_config('default_download_path', '')
            except Exception as e:
                 print(f"校验下载路径时出错: {e}")
                 self.view.show_message("错误", f"校验下载路径时出错:\n{e}", msg_type='error', parent=window)
                 return # Don't proceed if severe error validating path

        else: # Path was empty or placeholder
             final_download_path = '' # Clear the path setting
        # --- 处理并发数 (添加空字符串检查) ---
        final_concurrency = self.config_manager.get_config('max_concurrent_downloads', 3) # 默认值
        if concurrency_str: # 仅在非空时尝试转换
            try:
                concurrency_int = int(concurrency_str)
                # 限制范围
                final_concurrency = max(1, min(10, concurrency_int))
            except (ValueError, TypeError):
                print(f"警告: 无效的并发数值 '{concurrency_str}'，将使用旧值或默认值 {final_concurrency}。")
                self.view.show_message("警告", f"并发数值 '{concurrency_str}' 无效，未更新此项。", msg_type='warning', parent=window)
        else:
            # 如果为空字符串，也使用默认值
            print(f"警告: 并发数值为空，将使用旧值或默认值 {final_concurrency}。")
            self.view.show_message("警告", "并发数值未设置，将使用默认值。", msg_type='warning', parent=window)

        # --- 下载限速逻辑已移除 ---

        updates['api_key'] = final_api_key
        # 恢复下载路径更新
        updates['default_download_path'] = final_download_path
        updates['max_concurrent_downloads'] = final_concurrency
        # updates['download_limit_kb'] = final_limit_kb # 限速值更新已移除

        # Perform the save
        save_successful, error_msg = self.config_manager.update_multiple_configs(updates) # 修改：接收返回元组

        if save_successful:
            # 添加：更新当前的 ThreadPoolExecutor (如果并发数改变)
            if self.max_workers != final_concurrency:
                 print(f"信息: 并发数已从 {self.max_workers} 更改为 {final_concurrency}。重新创建线程池...")
                 # 关闭旧的 executor - 非阻塞，允许现有任务完成
                 # 注意：这可能导致短时间内超过新的 max_workers 限制
                 self.download_executor.shutdown(wait=False)
                 # 创建新的 executor
                 self.max_workers = final_concurrency
                 try:
                     self.download_executor = concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers)
                     print("信息: 新的下载线程池已创建。")
                 except Exception as e:
                     # 如果创建失败，记录错误并通知用户，可能需要重启应用
                     print(f"错误：创建新的 ThreadPoolExecutor 失败: {e}")
                     self.view.show_message("错误", f"无法应用新的并发设置 ({final_concurrency}): {e}\n请重启应用。", msg_type='error', parent=window)
                     # Revert max_workers or keep? Let's keep the config value but warn.
                     # Executor might be unusable now.

            self.view.show_message("设置", "设置已保存。", parent=window)

            # 添加：检查 API Key 是否为空，并给出提示
            if not final_api_key:
                warning_msg = "YouTube API Key 未设置，YouTube 相关功能（如搜索）将无法使用。"
                print(f"警告: {warning_msg}") # 在控制台也打印日志
                # 在保存成功提示后，再弹出一个警告框
                self.view.show_message("提示", warning_msg, msg_type='warning', parent=window)

            # 主窗口路径现在独立于设置窗口管理，此处无需更新
            window.destroy()
        else:
            # 修改：显示更详细的错误信息
            error_detail = f"保存设置失败！\n\n原因: {error_msg}" if error_msg else "保存设置失败！请检查日志。"
            self.view.show_message("错误", error_detail, msg_type='error', parent=window)


    # --- Methods called by Platform Logic Modules ---

    def get_download_path(self):
        """Returns the currently configured download path from the UI."""
        path = self.view.get_path_variable().get()
        # Basic validation before returning
        if not path or not os.path.isdir(path):
             fallback = self.get_fallback_download_path()
             try: os.makedirs(fallback, exist_ok=True); return fallback
             except: return "" # Return empty if fallback fails too
        return path

    def update_status(self, message):
         """Safely updates the status bar in the main window."""
         if self.root.winfo_exists(): # Check if root window still exists
             self.root.after(0, self.view.update_status_bar, message)

    def show_message(self, title, message, msg_type='info'):
         """Safely shows a message box."""
         if self.root.winfo_exists():
             self.root.after(0, self.view.show_message, title, message, msg_type)

    def is_cancel_requested(self):
        """Checks if a download cancellation has been requested."""
        return self.cancel_requested

    def reset_cancel_request(self):
         """Resets the cancellation flag."""
         self.cancel_requested = False

    def add_urls_to_download_queue(self, urls, platform):
        """Adds URLs to the main download queue (Treeview)."""
        if not self.root.winfo_exists(): return # Don't update if window closed

        # 修改：记录总尝试次数
        total_attempted = len(urls)

        def do_add():
            download_tree = self.view.get_download_treeview()
            if not download_tree: return

            added_count = 0
            skipped_count = 0
            error_count = 0 # 新增错误计数
            existing_download_iids = set(download_tree.get_children())

            for url in urls:
                if not url or not isinstance(url, str) or not (url.startswith("http://") or url.startswith("https://")):
                    print(f"警告: 跳过格式无效的 URL: {url}")
                    skipped_count += 1 # 无效格式也算跳过
                    continue

                # Generate unique ID
                import hashlib
                try:
                    url_hash = hashlib.md5(url.encode()).hexdigest()[:8] # Short hash
                    download_iid = f"{platform}_{url_hash}"
                except Exception as hash_e:
                    print(f"为 URL '{url}' 生成哈希时出错: {hash_e}")
                    error_count += 1
                    continue

                if download_iid in existing_download_iids:
                    skipped_count += 1
                    continue

                try:
                    # Use URL part as title fallback
                    video_title = url.split('/')[-1].split('?')[0] if '/' in url else url
                    if not video_title: video_title = url # Final fallback
                    # Store full URL in description column
                    download_values = ('☑', video_title[:50], '未知', '待下载', '', '', platform, url)
                    download_tree.insert('', tk.END, iid=download_iid, values=download_values)
                    added_count += 1
                except Exception as e:
                    print(f"添加 URL '{url}' 到下载列表时出错: {e}")
                    error_count += 1 # 插入失败算作错误

            # 修改：更新状态提示，包含总数、成功数、跳过数和错误数
            status_parts = []
            if added_count > 0: status_parts.append(f"成功添加 {added_count}")
            if skipped_count > 0: status_parts.append(f"跳过 {skipped_count} (无效/重复)")
            if error_count > 0: status_parts.append(f"失败 {error_count}")

            if not status_parts:
                 status_message = f"尝试添加 {total_attempted} 个任务，无有效操作。"
            else:
                 status_message = f"添加任务 (尝试 {total_attempted} 个): {', '.join(status_parts)}。"

            self.update_status(status_message)

        self.root.after(0, do_add)


    def update_download_progress(self, progress_data):
        """
        Safely updates the download list and progress bar.
        Called by download threads (via self.root.after).
        """
        if not self.root.winfo_exists(): return # Don't update if window closed

        item_id = progress_data.get('id') # Expected format: platform_hash
        if not item_id:
            print("警告: 收到缺少 id 的进度回调数据:", progress_data)
            return

        # 编译一次正则表达式以提高效率
        ansi_escape_pattern = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

        def do_update():
            if not self.root.winfo_exists(): return
            download_tree = self.view.get_download_treeview()
            progress_bar = self.view.get_progress_bar()
            if not download_tree or not progress_bar: return

            try:
                if not download_tree.exists(item_id): return # Item might have been removed

                status = progress_data.get('status')
                values_to_set = {}
                percent_value = None
                status_text = "" # 用于组合符号和文本

                if status == 'preparing':
                    status_text = "[...]" # 使用 ASCII 符号
                    values_to_set = {'status': status_text, 'description': ''} # 清空旧描述
                    percent_value = 0.0
                elif status == 'downloading':
                    p_str = progress_data.get('percent', '0%')
                    try:
                        # 清除 ANSI 转义码
                        cleaned_p_str = ansi_escape_pattern.sub('', p_str)
                        percent_value = float(cleaned_p_str.strip('%'))
                        status_text = f"{cleaned_p_str}" # 只显示清理后的百分比
                    except ValueError:
                         percent_value = 0.0
                         status_text = "0%" # 如果转换失败，显示0%
                    # 清理 ETA 和 Speed 字符串中的 ANSI 码
                    eta_str = progress_data.get('eta', 'N/A')
                    speed_str = progress_data.get('speed', 'N/A')
                    cleaned_eta_str = ansi_escape_pattern.sub('', eta_str)
                    cleaned_speed_str = ansi_escape_pattern.sub('', speed_str)
                    values_to_set = {
                        'filename': progress_data.get('filename', download_tree.set(item_id, 'filename'))[:50], # Limit length
                        'size': progress_data.get('size', '未知'),
                        'status': status_text,
                        'eta': cleaned_eta_str, # 使用清理后的 ETA
                        'speed': cleaned_speed_str, # 使用清理后的 Speed
                        'description': '' # 清空描述，避免干扰
                    }
                elif status == 'finished':
                    status_text = "[OK]" # 使用 ASCII 符号
                    values_to_set = {
                        'filename': progress_data.get('filename', download_tree.set(item_id, 'filename'))[:50],
                        'size': progress_data.get('size', '未知'),
                        'status': status_text, 'eta': '0s', 'speed': '',
                        'description': progress_data.get('description', '') # 保留可能的文件路径等
                    }
                    percent_value = 100.0
                elif status == 'error':
                    status_text = "[ERR]" # 使用 ASCII 符号
                    # 获取原始错误描述
                    error_desc_raw = str(progress_data.get('description', '未知错误'))
                    # 清理 ANSI 码
                    cleaned_error_desc = ansi_escape_pattern.sub('', error_desc_raw)
                    # 设置清理后的描述，并限制长度
                    values_to_set = {'status': status_text, 'description': cleaned_error_desc[:100]} # Limit desc length
                    percent_value = 0.0 # Reset progress on error
                elif status == 'cancelled': # 处理新增的取消状态
                     status_text = "[CAN]" # 使用 ASCII 符号
                     values_to_set = {'status': status_text, 'description': progress_data.get('description', "用户取消")}
                     percent_value = 0.0 # Reset progress on cancel
                elif status == 'retrying': # 新增处理重试状态，并显示次数
                    retry_count = progress_data.get('retry_count', '?') # 从回调数据获取当前重试次数
                    max_retries = progress_data.get('max_retries', '?') # 从回调数据获取最大重试次数
                    status_text = f"[重试中... {retry_count}/{max_retries}]" # 格式化状态文本
                    # description 可能包含重试的具体原因，保留它
                    values_to_set = {'status': status_text, 'description': progress_data.get('description', '')}
                    # 重试时不改变进度百分比，percent_value 设为 None
                    percent_value = None

                # Update Treeview
                for col, value in values_to_set.items():
                     if download_tree.exists(item_id):
                          download_tree.set(item_id, column=col, value=value)

                # --- 更新基于任务计数的总体进度条 (此处代码已正确) ---
                # (保持现有代码不变，因为上次 apply_diff 已成功更新此部分)
                if status == 'finished':
                    # 检查是否已对此任务计数，防止重复增加
                    if not hasattr(self, '_finished_in_current_batch'):
                        self._finished_in_current_batch = set()

                    if item_id not in self._finished_in_current_batch:
                        self._finished_in_current_batch.add(item_id)
                        self.completed_batch_tasks += 1

                        if self.total_batch_tasks > 0:
                            # 计算进度：基础 5% + 完成比例 * 95%
                            progress_percentage = 5 + (self.completed_batch_tasks / self.total_batch_tasks) * 95
                            progress_bar['value'] = progress_percentage
                            # print(f"Debug: 任务完成 {item_id}, 已完成 {self.completed_batch_tasks}/{self.total_batch_tasks}, 进度: {progress_percentage:.2f}%") # 调试日志
                        else:
                            # 如果总任务数为0（理论上不应发生在此处），保持初始值或设为 100？
                            # 保持 5% 可能更合理，_final_ui_update 会处理最终状态
                            progress_bar['value'] = 5
                # 注意：其他状态 (downloading, error, cancelled, retrying) 不再直接更新主进度条
                # 主进度条仅在任务完成时递增，或在批次结束时设置最终状态 (_final_ui_update)

            except Exception as e:
                # Avoid crashing the app due to UI update errors
                print(f"更新 Treeview 或进度时出错 (iid={item_id}, data={progress_data}): {e}")

        self.root.after(0, do_update)


    # --- Core Application Logic ---

    def _initialize_download_path(self, path_var):
        """Initializes the download path variable based on config or fallback."""
        configured_path = self.config_manager.get_config('default_download_path')
        fallback_path = self.get_fallback_download_path()
        default_download_path = fallback_path # Start with fallback

        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir) # Assumes core is one level down

        try:
            if configured_path:
                 potential_path = os.path.abspath(configured_path) # Assume it's absolute or resolve based on cwd
                 # Let's try resolving relative to project root as a fallback if not absolute
                 if not os.path.isabs(configured_path):
                     potential_path_rel = os.path.abspath(os.path.join(project_root, configured_path))
                     if os.path.isdir(os.path.dirname(potential_path_rel)): # Check parent dir validity
                          potential_path = potential_path_rel
                          print(f"将相对路径 '{configured_path}' 解析为项目根目录相对路径: {potential_path}")

                 # Check if the final path's parent directory is valid
                 if os.path.isdir(os.path.dirname(potential_path)):
                      default_download_path = potential_path
                 else:
                      print(f"警告: 配置文件中的路径 '{configured_path}' (解析为 '{potential_path}') 无效，使用默认路径。")
            # Ensure the chosen path exists
            os.makedirs(default_download_path, exist_ok=True)
        except Exception as e:
            print(f"初始化下载路径时出错: {e}. 使用默认路径 {fallback_path}")
            default_download_path = fallback_path
            try: os.makedirs(default_download_path, exist_ok=True)
            except Exception as e2: print(f"创建默认下载目录失败: {e2}")

        path_var.set(default_download_path)


    def save_download_path_to_config(self, *args):
        """Callback when download path changes in UI; saves to config."""
        new_path = self.view.get_path_variable().get()
        if new_path:
             try:
                 abs_path = os.path.abspath(new_path)
                 # Check if parent directory exists, indicating a plausible path
                 if os.path.isdir(os.path.dirname(abs_path)) or os.path.isdir(abs_path):
                     self.config_manager.update_config('default_download_path', abs_path)
                 else:
                     print(f"尝试保存的路径 '{new_path}' 父目录无效，未更新配置。")
             except Exception as e:
                 print(f"保存下载路径时出错: {e}")

    def get_fallback_download_path(self):
         """Gets the fallback download directory path (project_root/download)."""
         script_dir = os.path.dirname(os.path.abspath(__file__))
         project_root = os.path.dirname(script_dir)
         return os.path.join(project_root, "download")

    def get_config(self, key, default=None):
         """Provides access to configuration values."""
         return self.config_manager.get_config(key, default)


    # 修改：方法接受 items_info 列表，而不是 urls 列表
    def start_immediate_downloads(self, items_info_list, platform):
        """
        最终重构：准备、异步添加UI、直接提交有效任务。
        """
        if not self.root.winfo_exists(): return
        output_path = self.get_download_path()
        if not output_path:
            self.show_message("警告", "无法确定有效的下载路径！")
            return

        if not items_info_list:
            self.show_message("提示", "没有提供有效的下载任务信息。")
            return

        download_tree = self.view.get_download_treeview()
        if not download_tree:
             self.show_message("错误", "无法访问下载列表界面。")
             return

        # --- 1. 准备阶段: 筛选有效任务信息 & 识别新URL ---
        valid_items_to_submit = []
        new_urls_to_add_to_ui = []
        initial_existing_iids = set(download_tree.get_children()) if download_tree else set()
        processed_ids_in_batch = set() # 防止同一批次重复处理相同ID

        for item_info in items_info_list:
            item_id = item_info.get('id')
            url = item_info.get('url')

            # 基本验证 + 批次内去重
            if not item_id or not url or not isinstance(url, str) or not (url.startswith("http://") or url.startswith("https://")) or item_id in processed_ids_in_batch:
                if item_id in processed_ids_in_batch:
                     print(f"信息: 批次内已包含任务 {item_id}，跳过重复项。")
                else:
                     print(f"警告: 跳过无效的任务信息: {item_info}")
                continue

            item_info['output_path'] = output_path
            valid_items_to_submit.append(item_info) # 加入待提交列表
            processed_ids_in_batch.add(item_id)

            if item_id not in initial_existing_iids:
                new_urls_to_add_to_ui.append(url)
        # ------------------------------------

        # --- 2. UI 添加阶段 (异步) ---
        if new_urls_to_add_to_ui:
            print(f"信息: 尝试添加 {len(new_urls_to_add_to_ui)} 个新 URL 到 UI...")
            self.add_urls_to_download_queue(new_urls_to_add_to_ui, platform)
        # --------------------------

        # --- 3. 提交阶段 ---
        if not valid_items_to_submit:
            self.show_message("提示", "没有有效的任务可供下载。")
            return

        self.reset_cancel_request()
        self.view.disable_controls(True)
        try:
            if hasattr(self.view, 'remove_button'): self.view.remove_button.config(state=tk.DISABLED)
        except Exception as e: print(f"禁用移除按钮时出错: {e}")

        actual_task_count = len(valid_items_to_submit)
        self.update_status(f"开始提交 {actual_task_count} 个下载任务...") # 更新状态文本
        self.active_task_progress = {}
        try:
            progress_bar = self.view.get_progress_bar()
            if progress_bar: progress_bar['value'] = 0
        except Exception as e: print(f"设置初始进度条时出错: {e}")

        self.active_futures = {}
        submitted_count = 0
        # 直接提交所有有效任务 (valid_items_to_submit)
        for item_info in valid_items_to_submit:
            item_id = item_info['id']

            # 检查是否已在运行 (防止外部快速连续点击导致重复提交)
            if item_id in self.active_futures and not self.active_futures[item_id].done():
                 print(f"信息: 任务 {item_id} 已在运行或等待中，跳过本次提交。")
                 continue

            try:
                future = self.download_executor.submit(self._run_single_download_task, item_info)
                self.active_futures[item_id] = future
                future.add_done_callback(
                    lambda f, captured_id=item_id: print(f"信息: Future 完成回调 (立即下载) for {captured_id}. 结果: {f.result() if not f.exception() else f.exception()}")
                )
                submitted_count += 1
                # 不再在此处更新UI状态为 '[...]', 交给 _run_single_download_task 处理
            except Exception as submit_e:
                print(f"提交下载任务 {item_id} 到线程池时出错: {submit_e}")
                # 提交失败，尝试更新 UI（如果任务存在）
                try:
                    # 检查是否存在再更新
                    if download_tree.exists(item_id):
                         self.update_download_progress({'id': item_id, 'status': 'error', 'description': f'提交错误: {submit_e}'})
                    # else: # 如果任务还不在UI上，也无法更新，忽略即可，后续 _run_single_download_task 也无法执行
                except Exception as update_e:
                     print(f"在报告提交错误时更新 UI 失败 ({item_id}): {update_e}")

        if submitted_count == 0:
            self.view.disable_controls(False)
            try:
                if hasattr(self.view, 'remove_button'): self.view.remove_button.config(state=tk.NORMAL)
            except Exception as e: print(f"恢复移除按钮时出错: {e}")
            self.update_status("没有任务成功提交。") # 更新状态
            return

        # 只有在成功提交了任务后才启动监控
        self.update_status(f"已提交 {submitted_count} 个任务，开始下载...") # 更新最终提交状态
        monitor_thread = Thread(target=self._monitor_download_futures)
        monitor_thread.daemon = True
        monitor_thread.start()


    def start_selected_downloads(self):
        """Starts downloading selected ('☑') items from the list."""
        if not self.root.winfo_exists(): return
        download_tree = self.view.get_download_treeview()
        output_path = self.get_download_path() # Ensures path is valid or fallback
        if not output_path:
            self.show_message("警告", "无法确定有效的下载路径！")
            return # Correctly indented return

        selected_iids = []
        items_to_reset = []

        for item_iid in download_tree.get_children(''):
            try:
                 values = download_tree.item(item_iid, 'values')
                 # Checkbox (col 0), Status (col 3)
                 # 允许重试 '[ERR]' 和 '[CAN]' 状态的任务
                 if values and len(values) > 3 and values[0] == '☑' and values[3] in ('待下载', '下载出错', '准备下载', '[ERR]', '[CAN]'):
                      selected_iids.append(item_iid)
                      items_to_reset.append(item_iid)
            except Exception as e:
                 print(f"检查下载项 {item_iid} 时出错: {e}")

        if not selected_iids:
            self.show_message("提示", "没有选中待下载或可重试的任务。")
            return # Correctly indented return

        # --- Reset status in UI immediately ---
        for iid in items_to_reset:
            try:
                 if download_tree.exists(iid):
                      download_tree.set(iid, column='status', value="[...] ") # 使用准备中符号
                      # Clear description only if it's not the URL
                      # Assuming URL is now in col 7
                      current_desc = "" # Default to empty
                      try: # Getting value might fail if col doesn't exist yet
                          current_desc = download_tree.set(iid, column=7)
                      except Exception: pass
                      # Check type before calling startswith
                      if not (isinstance(current_desc, str) and (current_desc.startswith("http://") or current_desc.startswith("https://"))):
                           download_tree.set(iid, column='description', value="") # Clear non-URL description
            except Exception as e: print(f"重置下载状态时出错 (iid={iid}): {e}")
        # ------------------------------------

        self.reset_cancel_request()
        self.view.disable_controls(True) # Disable general controls
        # Explicitly disable remove button during download start (Part 1 of Fix #2)
        try:
            if hasattr(self.view, 'remove_button'): self.view.remove_button.config(state=tk.DISABLED)
        except Exception as e: print(f"禁用移除按钮时出错: {e}")
        # 修改：改进状态提示，并设置进度条初始值
        actual_task_count = len(selected_iids) # 实际将要启动的任务数
        self.update_status(f"开始准备下载 {actual_task_count} 个选中任务...")

        # --- 初始化基于计数的进度条 ---
        self.total_batch_tasks = actual_task_count
        self.completed_batch_tasks = 0
        if hasattr(self, '_finished_in_current_batch'): # 清除上一批次的完成记录
            del self._finished_in_current_batch
        try:
            progress_bar = self.view.get_progress_bar()
            if progress_bar:
                progress_bar['value'] = 5 if actual_task_count > 0 else 0 # 设置初始进度为 5% (如果任务数>0)
            else:
                print("警告: 无法获取进度条控件。")
        except Exception as e:
            print(f"设置初始进度条时出错: {e}")
        # -----------------------------

        # 修改：使用 ThreadPoolExecutor 提交任务
        self.active_futures = {} # 清空之前的 Future 记录

        # --- Submit tasks to the executor for each selected item ---
        submitted_count = 0
        for item_iid in selected_iids:
            try:
                 # === 新增检查: 确认任务存在且状态仍可下载 ===
                 if not download_tree.exists(item_iid):
                     print(f"警告: 任务 {item_iid} 在提交前已从列表移除，跳过。")
                     continue

                 current_status = download_tree.set(item_iid, 'status')
                 # 允许 '待下载', '[...]', '下载出错', '[ERR]', '[CAN]' 状态的任务提交
                 # '[...]' 是我们刚刚在 UI 上设置的准备状态
                 allowed_statuses_for_submit = ['待下载', '[...]', '下载出错', '[ERR]', '[CAN]', '[...] '] # 添加 '[...] ' 状态
                 if current_status not in allowed_statuses_for_submit:
                     print(f"警告: 任务 {item_iid} 状态为 '{current_status}'，不适合提交下载，跳过。")
                     continue
                 # ========================================

                 # Get URL from the 8th column ('description', index 7)
                 values = download_tree.item(item_iid, 'values')
                 if len(values) > 7:
                      url = values[7]
                      if url and isinstance(url, str) and (url.startswith("http://") or url.startswith("https://")):
                           item_info = {
                               'id': item_iid,
                               'url': url,
                               'output_path': output_path,
                               # TODO: Add platform-specific ydl_opts if needed here based on iid prefix?
                           }
                           future = self.download_executor.submit(self._run_single_download_task, item_info)
                           self.active_futures[item_iid] = future # 使用 item_id 作为键存储 Future
                           # 添加回调以立即检查 Future 结果
                           item_id_for_callback = item_iid # 捕获当前 item_id
                           future.add_done_callback(
                               lambda f, captured_id=item_id_for_callback: print(f"信息: Future 完成回调 (选中下载) for {captured_id}. 结果: {f.result() if not f.exception() else f.exception()}")
                           )
                           submitted_count += 1
                      else:
                           print(f"警告: 无法从列表获取有效的URL for iid {item_iid} (value: {url})")
                           self.update_download_progress({'id': item_iid, 'status': 'error', 'description': '列表中的URL无效'})
                 else:
                      print(f"警告: 无法获取 {item_iid} 的完整值 (列数不足)")
                      self.update_download_progress({'id': item_iid, 'status': 'error', 'description': '内部列表数据错误'})
            except Exception as e:
                 print(f"提交下载任务 {item_iid} 到线程池时出错: {e}")
                 self.update_download_progress({'id': item_iid, 'status': 'error', 'description': f'提交错误: {e}'})
        # -------------------------------------------

        if submitted_count == 0:
            self.view.disable_controls(False) # Re-enable controls if nothing started
            # 恢复移除按钮状态
            try:
                if hasattr(self.view, 'remove_button'): self.view.remove_button.config(state=tk.NORMAL)
            except Exception as e: print(f"恢复移除按钮时出错: {e}")
            self.update_status("没有有效的任务启动。")
            return # Correctly indented return

        # Start monitoring thread (now monitors futures) ONLY if tasks were submitted
        monitor_thread = Thread(target=self._monitor_download_futures) # 修改：调用新的监控方法
        monitor_thread.daemon = True # Ensure monitor thread doesn't block exit
        monitor_thread.start()


    def _run_single_download_task(self, item_info):
        """在后台线程中调用 DownloadService 下载单个项目，并确保返回字典。"""
        item_id = item_info.get('id')
        # 默认错误结果，防止意外情况导致返回 None
        result = {'id': item_id, 'status': 'error', 'error_message': '未知任务执行错误'}

        if not self.download_service:
            print(f"错误: DownloadService 未初始化，无法下载 {item_id}")
            result = {'id': item_id, 'status': 'error', 'error_message': '核心下载服务未初始化'}
            self.update_download_progress(result) # 更新UI状态
            print(f"信息: _run_single_download_task 即将返回错误结果 for {item_id}: {result}")
            return result

        print(f"信息: 下载线程启动 for: {item_id}")
        try:
            # 调用 DownloadService 进行下载
            download_result = self.download_service.download_item(item_info, self.update_download_progress, self.is_cancel_requested)
            # 关键日志：记录 download_item 的实际返回值
            print(f"信息: download_item 直接返回结果 for {item_id}: {download_result} (类型: {type(download_result)})")

            # 健壮性检查：如果 download_item 返回 None 或非字典，记录警告并使用错误字典
            if download_result is None:
                print(f"警告: download_item for {item_id} 返回了 None！")
                result = {'id': item_id, 'status': 'error', 'error_message': '下载服务未按预期返回结果 (None)'}
            elif not isinstance(download_result, dict):
                 print(f"警告: download_item for {item_id} 返回了非字典类型: {type(download_result)}！")
                 result = {'id': item_id, 'status': 'error', 'error_message': f'下载服务返回类型错误 ({type(download_result)})'}
            else:
                 result = download_result # 使用 download_item 的有效返回结果

        except Exception as e:
            print(f"错误: _run_single_download_task 捕获到异常 for {item_id}: {e}")
            # 记录详细 traceback (可选，根据需要取消注释)
            # import traceback
            # print(traceback.format_exc())
            error_desc = f'任务执行异常: {e}'
            result = {'id': item_id, 'status': 'error', 'error_message': error_desc}
            # 尝试更新UI状态
            try:
                self.update_download_progress({'id': item_id, 'status': 'error', 'description': error_desc})
            except Exception as ui_update_err:
                 print(f"错误: 在处理下载异常时更新UI失败 for {item_id}: {ui_update_err}")

        # 最终日志：记录此函数最终将返回的值
        print(f"信息: _run_single_download_task 即将返回最终结果 for {item_id}: {result}")
        return result

    def _monitor_download_futures(self):
        """Waits for active download futures to complete and updates UI."""
        if not self.active_futures:
            print("监控：没有活动的 Future 对象需要监控。") # 添加调试信息
            return

        print(f"监控：开始监控 {len(self.active_futures)} 个 Future 对象...") # 添加调试信息
        processed_ids = set(self.active_futures.keys()) # 修正：在循环开始前获取 ID 集合
        all_futures = list(self.active_futures.values()) # 获取 Future 列表

        # 使用 concurrent.futures.wait 等待所有 Future 完成
        # done, not_done = concurrent.futures.wait(all_futures, return_when=concurrent.futures.ALL_COMPLETED)
        # 或者，更简单地循环检查直到所有 future 都 done (处理取消时可能更好)
        active_count = len(all_futures)
        while active_count > 0:
            completed_count = sum(1 for f in all_futures if f.done())
            active_count = len(all_futures) - completed_count
            time.sleep(0.5)
            if self.is_cancel_requested():
                print("监控：检测到取消请求，等待任务自行结束或出错...")
                # 不再强制中断，让 Service 内部处理
                pass

        print("监控：所有 Future 对象已完成。") # 添加调试信息
        was_cancelled = self.is_cancel_requested() # 检查最终状态

        # --- 准备最终 UI 更新的回调参数 ---
        # 修正：将统计逻辑移到 final_ui_update
        # final_update_args = { ... }

        # --- 在主线程中执行收尾 UI 更新 ---
        if self.root.winfo_exists():
            print("监控：调度 final_ui_update 到主线程。") # 添加调试信息
            # 修正：传递 processed_ids 给 final_ui_update
            self.root.after(0, lambda p_ids=processed_ids, cancelled=was_cancelled: self._final_ui_update(p_ids, cancelled))
        else:
            print("监控：窗口已关闭，无法调度 final_ui_update。") # 添加调试信息

        # 修正：清空操作移到 _final_ui_update 的末尾
        # print("监控：清空 active_futures。")
        # self.active_futures = {}

    # 修正：修改 final_ui_update 签名并调整逻辑
    def _final_ui_update(self, processed_ids, was_cancelled):
        """在主线程中执行下载结束后的 UI 更新和总结。"""
        if not self.root.winfo_exists():
             print("监控：UI 更新时窗口已不存在。") # 添加调试信息
             return
        print("监控：开始执行最终 UI 更新。") # 添加调试信息

        # --- Calculate Summary ---
        success_count = 0
        error_count = 0
        cancelled_count = 0
        download_tree = self.view.get_download_treeview()
        total_tasks_in_batch = len(processed_ids) # 使用传递过来的 ID 数量
        print(f"监控：统计 {total_tasks_in_batch} 个任务的结果...") # 添加调试信息

        if download_tree:
            for item_iid in processed_ids:
                try:
                    if download_tree.exists(item_iid):
                         status = download_tree.set(item_iid, 'status')
                         if status == "[OK]": # 使用新的状态文本
                             success_count += 1
                         elif status == "[ERR]": # 使用新的状态文本
                             error_count += 1
                         elif status == "[CAN]": # 使用新的状态文本
                             cancelled_count += 1
                         # 其他状态（如准备中[...]或百分比%）视为未完成
                    else:
                         # 如果任务从列表移除了，也算一种结果（或计入失败？）
                         print(f"监控：任务 {item_iid} 在列表中不存在，计为错误。")
                         error_count += 1
                except Exception as read_status_e:
                     print(f"监控：读取任务 {item_iid} 状态时出错: {read_status_e}")
                     error_count += 1 # 读取状态失败也算错误
        else:
            print("监控：无法访问下载列表 Treeview，所有任务计为错误。")
            error_count = total_tasks_in_batch # 无法读取列表，全算失败

        # --- Re-enable Controls ---
        print("监控：恢复 UI 控件状态。")
        self.reset_cancel_request() # 重置取消标志
        self.view.disable_controls(False)
        try:
            if hasattr(self.view, 'remove_button'): self.view.remove_button.config(state=tk.NORMAL)
        except Exception as e: print(f"恢复移除按钮时出错: {e}")

        # --- Update Status Bar and Show Summary Dialog ---
        final_status_msg = "下载任务结束。"
        if was_cancelled: final_status_msg = "下载任务已取消。"
        self.update_status(final_status_msg)

        # --- Update Progress Bar to Final State ---
        try:
            progress_bar = self.view.get_progress_bar()
            if progress_bar:
                # 检查条件：未被取消 且 总任务数 > 0 且 (使用 self.completed_batch_tasks 比较更准确) 完成数等于总数
                all_succeeded_and_not_cancelled = (not was_cancelled and
                                                   self.total_batch_tasks > 0 and
                                                   self.completed_batch_tasks == self.total_batch_tasks)

                if all_succeeded_and_not_cancelled:
                    progress_bar['value'] = 100
                    final_progress_status = "100%"
                else:
                    # 其他情况（被取消、有失败/错误、0任务）都归零
                    progress_bar['value'] = 0
                    final_progress_status = "重置 (0%)"
                print(f"Debug: 批次结束，最终进度条状态: {final_progress_status}")
        except Exception as e: print(f"设置最终进度条时出错: {e}")

        summary_title = "下载完成" if not was_cancelled else "下载取消"
        summary_message = f"下载批次处理完毕。\n\n" \
                          f"总计任务: {total_tasks_in_batch} 个\n" \
                          f"成功: {success_count} 个\n" \
                          f"失败: {error_count} 个\n"
        if cancelled_count > 0:
             summary_message += f"取消: {cancelled_count} 个\n"
        # if was_cancelled and (success_count + error_count + cancelled_count < total_tasks_in_batch):
        #      summary_message += f"\n注意：部分任务可能因取消而未完成或状态未知。"
        # --- 重置批次计数器和临时状态 ---
        print(f"Debug: 重置批次计数器，之前状态: {self.completed_batch_tasks}/{self.total_batch_tasks}")
        self.total_batch_tasks = 0
        self.completed_batch_tasks = 0
        if hasattr(self, '_finished_in_current_batch'):
            del self._finished_in_current_batch
        # ------------------------------------

        print(f"监控：显示总结弹窗: Title='{summary_title}', Message='{summary_message.replace('\\n', ' ')}'") # 添加调试信息
        self.show_message(summary_title, summary_message)

        # 修正：在 final_ui_update 的最后清空 futures 和 progress
        print("监控：清空 active_futures 和 active_task_progress。") # 添加调试信息
        self.active_futures = {} # 清空 Future 记录
        self.active_task_progress = {} # 清空进度记录

        # --- 重置批次计数器和临时状态 ---
        print(f"Debug: 重置批次计数器，之前状态: {self.completed_batch_tasks}/{self.total_batch_tasks}")
        self.total_batch_tasks = 0
        self.completed_batch_tasks = 0
        if hasattr(self, '_finished_in_current_batch'):
            del self._finished_in_current_batch
        # ------------------------------------


    def _on_closing(self):
        """Handles the window closing event, saving the queue."""
        print("检测到窗口关闭事件...")

        # --- 保存队列逻辑 ---
        print("信息: 开始处理队列保存逻辑...") # 添加日志
        queue_to_save = []
        download_tree = self.view.get_download_treeview()
        if download_tree:
            all_item_ids = download_tree.get_children()
            for item_id in all_item_ids:
                try:
                    values = download_tree.item(item_id, 'values')
                    # ('☑', filename, size, status, eta, speed, platform, description/url)
                    status = values[3]
                    # 只有未完成、出错、取消的状态需要保存
                    savable_statuses = ['待下载', '下载出错', '已取消', '[...]','[重试中...]', '[ERR]', '[CAN]', '0%', '10%', '...'] # 包含可能的中间状态和旧格式
                    # 更准确的判断：只要不是 '[OK]' 都应该尝试保存其原始信息
                    # 增加检查：跳过用户已移除的任务
                    if status != '[OK]' and item_id not in self.removed_item_ids:
                        # 从 description 或 item_id 恢复 URL
                        url = values[7] # 假设第8列是 Description/URL
                        if not (url.startswith('http://') or url.startswith('https://')):
                           # 如果 Description 不是 URL，尝试从 item_id 解析 (需要约定格式)
                           # 或者需要额外存储 URL 信息，目前先假设 description 是 URL
                           print(f"警告: 无法从任务 {item_id} 的描述 '{url}' 中明确恢复 URL，跳过保存。")
                           continue

                        task_data = {
                            "item_id": item_id,
                            "url": url,
                            "platform": values[6],
                            "filename": values[1], # 保存文件名
                            "size": values[2],     # 保存大小
                            "status": status,      # 保存当前状态
                            "description": values[7] # 保存描述（可能是错误信息或原始 URL）
                        }
                        # 对于正在下载的状态，统一保存为“待下载”，以便下次启动时重新开始
                        if '%' in status or status == '[...] ' or status == '[重试中...]': # 修正：匹配带空格的状态
                            task_data['status'] = '待下载'
                            task_data['description'] = url # 重新下载时清空旧描述

                        queue_to_save.append(task_data)
                except Exception as e:
                    print(f"处理任务 {item_id} 以进行保存时出错: {e}")

        print(f"信息: 准备保存的任务数量: {len(queue_to_save)}") # 添加日志
        if queue_to_save:
            # 修正：确保使用正确的项目根目录来拼接路径
            script_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(script_dir)
            queue_file_path = os.path.join(project_root, 'download_queue.json')
            try:
                print(f"信息: 正在保存 {len(queue_to_save)} 个未完成的任务到 {queue_file_path}...")
                # 确保以 'w' 模式打开，覆盖旧内容
                with open(queue_file_path, 'w', encoding='utf-8') as f:
                    json.dump(queue_to_save, f, indent=4, ensure_ascii=False)
                print("信息: 持久化队列保存成功。")
            except Exception as e:
                print(f"错误: 保存持久化队列到 {queue_file_path} 时失败: {e}")
                # 可以考虑弹窗提示用户保存失败
                try: # 尝试使用 messagebox
                     if self.root.winfo_exists():
                          messagebox.showerror("保存错误", f"无法保存未完成的下载任务到文件:\n{e}", parent=self.root)
                except Exception as mb_e:
                     print(f"显示保存错误弹窗时也发生错误: {mb_e}")
        else: # 如果 queue_to_save 为空（所有项完成或被移除）
            script_dir = os.path.dirname(os.path.abspath(__file__)) # 重新获取路径
            project_root = os.path.dirname(script_dir)
            queue_file_path = os.path.join(project_root, 'download_queue.json')
            try:
                print(f"信息: 没有未完成且未移除的任务需要保存，尝试清空 {queue_file_path}...")
                with open(queue_file_path, 'w', encoding='utf-8') as f:
                    json.dump([], f, indent=4, ensure_ascii=False) # 写入空列表
                print("信息: 持久化队列文件已成功清空。")
            except Exception as e:
                print(f"错误: 清空持久化队列文件 {queue_file_path} 时失败: {e}")
                try:
                     if self.root.winfo_exists():
                          messagebox.showerror("保存错误", f"无法清空下载队列记录文件:\n{e}", parent=self.root)
                except Exception as mb_e:
                     print(f"显示清空错误弹窗时也发生错误: {mb_e}")

        # --- 检查是否有活动任务，并提示用户 ---
        if self.active_futures:
             # 弹出确认对话框
             if messagebox.askyesno("退出确认", "下载仍在进行中，确定要退出吗？\n未完成的任务状态将保存。", parent=self.root):
                  print("用户确认退出，正在请求取消下载...")
                  self.request_cancel() # Signal cancellation to running tasks
                  # 关闭 Executor，非阻塞
                  self.download_executor.shutdown(wait=False, cancel_futures=False)
                  print("下载线程池关闭指令已发送。")
                  if self.root.winfo_exists(): self.root.destroy()
                  print("应用程序退出。")
             else:
                  print("用户取消退出。")
                  return # 用户取消，不关闭窗口
        else:
             # 没有活动任务，正常关闭
             print("关闭下载线程池...")
             self.download_executor.shutdown(wait=True) # 等待线程池完全关闭
             print("下载线程池已关闭。")
             if self.root.winfo_exists(): self.root.destroy()
             print("应用程序退出。")

    def _load_persistent_queue(self):
        """加载持久化的下载队列，增强错误处理。"""
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)
        queue_file_path = os.path.join(project_root, 'download_queue.json')
        backup_file_path = os.path.join(project_root, 'download_queue.json.bak') # 定义备份文件名

        print(f"信息: 尝试从 {queue_file_path} 加载持久化队列...")

        if not os.path.exists(queue_file_path):
            print("信息: 持久化队列文件不存在，跳过加载。")
            return

        loaded_tasks = []
        try:
            with open(queue_file_path, 'r', encoding='utf-8') as f:
                loaded_tasks = json.load(f)
        except json.JSONDecodeError as json_err:
            error_msg = f"解析持久化队列文件失败，文件可能已损坏。\n错误: {json_err}\n文件路径: {queue_file_path}"
            print(f"错误: {error_msg}")
            # 尝试备份损坏的文件
            try:
                if os.path.exists(backup_file_path):
                     # 如果备份文件已存在，可以加上时间戳或序号避免覆盖
                     import datetime
                     timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
                     backup_file_path += f".{timestamp}"
                os.rename(queue_file_path, backup_file_path)
                error_msg += f"\n\n已将损坏的文件备份为: {os.path.basename(backup_file_path)}"
                print(f"信息: 已将损坏的文件备份为 {backup_file_path}")
            except Exception as backup_err:
                backup_fail_msg = f"尝试备份损坏的队列文件失败: {backup_err}"
                print(f"错误: {backup_fail_msg}")
                error_msg += f"\n\n{backup_fail_msg}"

            # 弹窗提示用户 (确保在主线程执行)
            self.show_message("加载错误", error_msg, msg_type='error')
            return # 遇到 JSON 解析错误则不加载
        except Exception as e:
            error_msg = f"读取持久化队列文件时发生错误。\n错误: {e}\n文件路径: {queue_file_path}"
            print(f"错误: {error_msg}")
            # 弹窗提示用户
            self.show_message("加载错误", error_msg, msg_type='error')
            return # 遇到其他读取错误也不加载

        if not loaded_tasks:
            print("信息: 持久化队列为空或加载失败后为空。")
            return

        # --- 接下来的加载逻辑与之前相同 ---
        download_tree = self.view.get_download_treeview()
        if not download_tree:
            print("错误: 无法获取下载列表 Treeview 组件，无法加载队列。")
            # 也许也应该给用户一个提示？
            self.show_message("内部错误", "无法访问下载列表界面组件，队列加载失败。", msg_type='error')
            return

        added_count = 0
        skipped_count = 0
        error_count = 0
        existing_iids = set(download_tree.get_children())

        for task_data in loaded_tasks:
            try:
                item_id = task_data.get('item_id')
                url = task_data.get('url')
                platform = task_data.get('platform')
                status = task_data.get('status', '待下载')

                if not all([item_id, url, platform]):
                    print(f"警告: 持久化任务数据不完整，跳过: {task_data}")
                    skipped_count += 1
                    continue

                if item_id in existing_iids:
                    skipped_count += 1
                    continue

                filename = task_data.get('filename', url.split('/')[-1].split('?')[0] or url)[:50]
                size = task_data.get('size', '未知')
                description = task_data.get('description', url)

                normalized_status = status
                if status == '[ERR]': normalized_status = '下载出错'
                if status == '[CAN]': normalized_status = '已取消'

                # 对于加载时状态不是 '待下载'/'下载出错'/'已取消' 的任务，也将其状态重置为 '待下载'
                # 这样即使用户手动改了json，启动后也能尝试重新下载
                if normalized_status not in ['待下载', '下载出错', '已取消']:
                    print(f"警告: 持久化任务状态 '{status}' 无效或不可恢复，重置为 '待下载' 以尝试重新下载任务 {item_id}")
                    normalized_status = '待下载'
                    description = url # 重置描述为URL

                values = ('☑', filename, size, normalized_status, '', '', platform, description)
                download_tree.insert('', tk.END, iid=item_id, values=values)
                existing_iids.add(item_id)
                added_count += 1

            except Exception as load_item_e:
                print(f"从持久化数据加载任务 {task_data.get('item_id', '未知ID')} 时出错: {load_item_e}")
                error_count += 1
                # 这里可以考虑是否给用户一个总的加载失败条目提示

        status_parts = []
        if added_count > 0: status_parts.append(f"成功加载 {added_count}")
        if skipped_count > 0: status_parts.append(f"跳过 {skipped_count} (无效/重复)")
        if error_count > 0: status_parts.append(f"失败 {error_count}")

        if status_parts:
             load_message = f"加载持久化队列: {', '.join(status_parts)}。"
             print(f"信息: {load_message}")
             # 可以在状态栏显示加载结果
             # self.update_status(load_message) # 暂时注释掉，避免覆盖启动时的"就绪"状态太快
        elif not os.path.exists(queue_file_path): # 如果文件不存在，不显示 "没有加载"
             pass # 之前已经打印过文件不存在的信息
        else: # 文件存在但加载了0条（可能文件为空或全部跳过/失败）
             print("信息: 没有从持久化文件加载任何有效任务。")




    # --- UI Action Handlers ---

    def handle_search(self):
        """处理当前激活标签页的搜索事件。"""
        try:
            notebook = self.view.notebook
            current_tab_index = notebook.index(notebook.select())
            current_tab_text = notebook.tab(current_tab_index, "text")
            platform_name = current_tab_text # Assume tab text is platform name
        except (tk.TclError, AttributeError):
            self.show_message("提示", "请先选择一个平台标签页。")
            return

        logic_module = self.platform_modules.get(platform_name)

        if not logic_module or not hasattr(logic_module, 'search_videos'):
            self.show_message("提示", f"平台 '{platform_name}' 暂不支持搜索功能。")
            return

        # --- 特定于 YouTube 的搜索参数获取 ---
        if platform_name == 'YouTube':
            try:
                query = self.view.youtube_keyword_entry.get().strip()
                duration_selection = self.view.youtube_duration_var.get()
                order_selection = self.view.youtube_order_var.get()
                if not query:
                    self.show_message("搜索", "请输入搜索关键词！", parent=self.view.root) # Use main window as parent
                    return
            except AttributeError as e:
                self.show_message("错误", f"YouTube 搜索控件未正确初始化！\n{e}")
                return

            # --- 将 GUI 选择映射到 API 参数 ---
            duration_map = {
                "任意": "any", "短片 (<4分钟)": "short", "中等 (4-20分钟)": "medium", "长片 (>20分钟)": "long"
            }
            order_map = {
                "相关性": "relevance", "上传日期": "date", "观看次数": "viewCount", "评分": "rating"
            }
            duration_api_value = duration_map.get(duration_selection, 'any')
            order_api_value = order_map.get(order_selection, 'relevance')
            # --- 映射结束 ---

            self.update_status("正在搜索 YouTube 视频...")
            self.view.disable_controls(True) # 禁用主控件

            # 启动后台搜索线程
            search_thread = Thread(target=self._run_search_task,
                                   args=(logic_module.search_videos, query, duration_api_value, order_api_value))
            search_thread.daemon = True
            search_thread.start()
        else:
            # 其他平台搜索逻辑（如果支持）
            self.show_message("提示", f"平台 '{platform_name}' 的搜索功能待实现。")

    def _run_search_task(self, search_function, query, duration, order):
        """在后台线程中执行搜索并安排 UI 更新。"""
        try:
            # 注意：search_videos 需要 app 实例作为第一个参数
            videos_info, error_msg = search_function(self, query, video_duration=duration, order=order)
        except Exception as e:
            print(f"执行搜索任务时出错: {e}")
            videos_info, error_msg = None, f"执行搜索时发生内部错误: {e}"

        # 在主线程中更新 UI
        if self.root.winfo_exists():
             self.root.after(0, self._update_search_results_ui, videos_info, error_msg)

    def _update_search_results_ui(self, videos_info, error_msg):
        """在主线程中更新搜索结果 UI。"""
        self.view.disable_controls(False) # 恢复控件

        try:
            # 假设结果应该更新到 YouTube 搜索树
            # TODO: 使其更通用，例如通过平台名称查找目标 Treeview
            tree = self.view.youtube_search_tree
            # 清空旧结果
            for i in tree.get_children(): tree.delete(i)
        except AttributeError:
            print("错误：无法访问 YouTube 搜索结果 Treeview。")
            self.update_status("状态: 更新搜索结果时发生内部错误")
            return

        if error_msg:
            self.update_status("状态: 搜索出错")
            self.show_message("搜索错误", error_msg)
            return
        elif videos_info is None: # API 调用成功但逻辑出错
            self.update_status("状态: 搜索出错")
            self.show_message("搜索错误", "处理搜索结果时发生未知错误。")
            return

        if videos_info:
            for video in videos_info:
                try:
                    # Treeview iid 使用视频 ID
                    tree.insert('', tk.END, values=(
                        video.get('name', ''), video.get('views', '0'), video.get('likes', '0'),
                        video.get('favorites', 'N/A'), video.get('comments', '0'),
                        video.get('published', ''), video.get('duration', '')), iid=video.get('id'))
                except Exception as e:
                    print(f"插入 YouTube 搜索结果时出错 (vid={video.get('id')}): {e}")
            self.update_status(f"状态: 找到 {len(videos_info)} 个视频")

    def mark_items_as_removed(self, item_ids):
        """记录用户已从UI移除的任务ID，以便在保存时忽略它们。"""
        if isinstance(item_ids, list):
            self.removed_item_ids.update(item_ids)
            print(f"信息: 标记了 {len(item_ids)} 个任务为已移除: {item_ids}")
        elif isinstance(item_ids, str):
            self.removed_item_ids.add(item_ids)
            print(f"信息: 标记了任务 {item_ids} 为已移除")

        else:
            self.update_status("状态: 未找到相关视频")
            self.show_message("搜索结果", "未找到与关键词匹配的视频。") # parent=self.view.root?

    def add_selected_to_download(self):
        """将活动标签页搜索结果中选中的项添加到全局下载列表。"""
        try:
            notebook = self.view.notebook
            current_tab_index = notebook.index(notebook.select())
            current_tab_text = notebook.tab(current_tab_index, "text")
            platform_name = current_tab_text
        except (tk.TclError, AttributeError):
            self.show_message("提示", "请先选择一个平台标签页。")
            return

        source_tree = None
        if platform_name == 'YouTube':
            try: source_tree = self.view.youtube_search_tree
            except AttributeError: self.show_message("错误", "YouTube 搜索结果控件未初始化！"); return
        elif platform_name == 'TikTok':
             # TikTok 标签页目前没有可选列表，此操作无效
             self.show_message("提示", "请直接在 TikTok 标签页输入 URL 进行添加或下载。")
             return
        else:
             self.show_message("错误", f"未知的平台标签: {platform_name}")
             return

        if source_tree is None:
             self.show_message("错误", f"平台 '{platform_name}' 缺少结果表格！")
             return

        selected_item_iids = source_tree.selection()
        if not selected_item_iids:
             self.show_message("提示", f"请先在 {platform_name} 结果中选择要添加的项。")
             return

        urls_to_add = []
        if platform_name == 'YouTube':
             # 对于 YouTube, iid 就是 video ID
             for video_id in selected_item_iids:
                  urls_to_add.append(f"https://www.youtube.com/watch?v={video_id}")
        # Add logic for other platforms if they have selectable lists

        if urls_to_add:
             # 调用已有的方法将 URLs 添加到主下载队列
             self.add_urls_to_download_queue(urls_to_add, platform=platform_name)
             # add_urls_to_download_queue 会更新状态栏
        else:
             self.show_message("提示", f"未能从选中的 {platform_name} 项中提取有效的下载信息。")


# --- Main Execution ---
if __name__ == '__main__':
    # Ensure paths work when running directly from core/
    # (Path setup moved inside try/except block in class imports)

    # Create necessary dummy files/dirs if they don't exist for direct execution
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.makedirs(os.path.join(project_root, 'config'), exist_ok=True)
    if not os.path.exists(os.path.join(project_root, 'config', '__init__.py')):
        with open(os.path.join(project_root, 'config', '__init__.py'), 'w') as f: pass
    if not os.path.exists(os.path.join(project_root, 'config', 'config.json')):
        with open(os.path.join(project_root, 'config', 'config.json'), 'w') as f: f.write('{}')
    if not os.path.exists(os.path.join(project_root, 'config', 'config.example.json')):
        with open(os.path.join(project_root, 'config', 'config.example.json'), 'w') as f: f.write('{"api_key": "", "default_download_path": "", "max_concurrent_downloads": 3}') # Add default concurrency
    os.makedirs(os.path.join(project_root, 'ui'), exist_ok=True)
    if not os.path.exists(os.path.join(project_root, 'ui', '__init__.py')):
        with open(os.path.join(project_root, 'ui', '__init__.py'), 'w') as f: pass
    os.makedirs(os.path.join(project_root, 'modules'), exist_ok=True)
    if not os.path.exists(os.path.join(project_root, 'modules', '__init__.py')):
        with open(os.path.join(project_root, 'modules', '__init__.py'), 'w') as f: pass
    # Dummy TikTok
    os.makedirs(os.path.join(project_root, 'modules', 'tiktok'), exist_ok=True)
    if not os.path.exists(os.path.join(project_root, 'modules', 'tiktok', '__init__.py')):
        with open(os.path.join(project_root, 'modules', 'tiktok', '__init__.py'), 'w') as f: pass
    if not os.path.exists(os.path.join(project_root, 'modules', 'tiktok', 'logic.py')):
        with open(os.path.join(project_root, 'modules', 'tiktok', 'logic.py'), 'w') as f: f.write("import time\ndef add_tiktok_urls(urls, app):\n print(f'Dummy TikTok add: {urls}')\ndef download_tiktok_urls(urls, app):\n print(f'Dummy TikTok download: {urls}')\n app.start_immediate_downloads([{'id':f'dummy_{i}', 'url':u} for i,u in enumerate(urls)], 'TikTok')")
    if not os.path.exists(os.path.join(project_root, 'ui', 'tiktok_tab.py')):
        with open(os.path.join(project_root, 'ui', 'tiktok_tab.py'), 'w') as f: f.write("import tkinter as tk; from tkinter import ttk; def create_tab(n, app): f=ttk.Frame(n); ttk.Label(f, text='Dummy TikTok UI').pack(); ttk.Button(f, text='Dummy Start DL', command=lambda: app.start_selected_downloads()).pack(); return f") # Fixed lambda
    # Dummy YouTube
    os.makedirs(os.path.join(project_root, 'modules', 'youtube'), exist_ok=True)
    if not os.path.exists(os.path.join(project_root, 'modules', 'youtube', '__init__.py')):
        with open(os.path.join(project_root, 'modules', 'youtube', '__init__.py'), 'w') as f: pass
    if not os.path.exists(os.path.join(project_root, 'modules', 'youtube', 'logic.py')):
        with open(os.path.join(project_root, 'modules', 'youtube', 'logic.py'), 'w') as f: f.write("# Dummy youtube logic")
    if not os.path.exists(os.path.join(project_root, 'ui', 'youtube_tab.py')):
        with open(os.path.join(project_root, 'ui', 'youtube_tab.py'), 'w') as f: f.write("import tkinter as tk; from tkinter import ttk; def create_tab(n, app): f=ttk.Frame(n); ttk.Label(f, text='Dummy YouTube UI').pack(); return f")

    print("Starting SucoiAppController...")
    app = SucoiAppController()
    print("SucoiAppController exited.")