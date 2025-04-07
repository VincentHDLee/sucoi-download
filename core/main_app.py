# core/main_app.py - Main Application Logic Controller
import tkinter as tk
from tkinter import messagebox # Keep for internal logic potentially
import os
import importlib # For dynamic module loading
from threading import Thread
import time # For monitor thread sleep
import concurrent.futures

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
        self.download_service = DownloadService() # <-- 已取消注释

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


        # --- Initialize UI ---
        # Pass self (the controller) to the MainWindow
        self.view = MainWindow(self.root, self)

        # --- Load Platform Modules and Tabs ---
        self.platform_modules = {} # Store loaded platform logic modules
        self.platform_ui_modules = {} # Store loaded platform UI modules
        self._load_platforms()

        # Bind close window event
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

        # --- Start the Application ---
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

    # 修改：添加 concurrency_str 参数
    def save_settings(self, api_key, download_path, concurrency_str, window, placeholder_api, placeholder_pth):
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

        # 添加：处理并发数
        final_concurrency = self.max_workers # Start with current value as fallback
        try:
            concurrency_int = int(concurrency_str)
            # 限制范围
            final_concurrency = max(1, min(10, concurrency_int))
        except (ValueError, TypeError):
             print(f"警告: 无效的并发数值 '{concurrency_str}'，配置中将保留旧值或默认值。")
             # Optionally show a warning to the user, but maybe saving the rest is fine
             self.view.show_message("警告", f"并发数值 '{concurrency_str}' 无效，未更新此项。", msg_type='warning', parent=window)
             # Get the existing value to ensure it's saved correctly if other settings change
             final_concurrency = self.config_manager.get_config('max_concurrent_downloads', 3) # Reload from config if input invalid

        updates['api_key'] = final_api_key
        updates['default_download_path'] = final_download_path
        updates['max_concurrent_downloads'] = final_concurrency # 添加并发数到更新字典

        # Perform the save
        save_successful = self.config_manager.update_multiple_configs(updates)

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

            # Update main window path entry if necessary
            current_main_path = self.view.get_path_variable().get()
            fallback_path = self.get_fallback_download_path()
            new_default_path = final_download_path if final_download_path else fallback_path

            if final_download_path and current_main_path == fallback_path:
                self.view.get_path_variable().set(new_default_path)
            elif not final_download_path: # If path was cleared or invalid, reset main view to fallback
                self.view.get_path_variable().set(fallback_path)

            window.destroy()
        else:
            # 修改：显示更详细的错误信息
            error_detail = f"保存设置失败！\n\n原因: {save_successful[1]}" if isinstance(save_successful, tuple) and len(save_successful) > 1 and save_successful[1] else "保存设置失败！请检查日志。"
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

                if status == 'preparing':
                    values_to_set = {'status': "准备下载", 'description': progress_data.get('description', '')}
                    # Reset progress bar only if this is the only active non-finished/error task?
                    # For now, just set to 0 if it's preparing.
                    percent_value = 0.0
                elif status == 'downloading':
                    p_str = progress_data.get('percent', '0%')
                    try: percent_value = float(p_str.strip('%'))
                    except: percent_value = 0.0
                    values_to_set = {
                        'filename': progress_data.get('filename', download_tree.set(item_id, 'filename'))[:50], # Limit length
                        'size': progress_data.get('size', '未知'),
                        'status': f"下载中 {p_str}",
                        'eta': progress_data.get('eta', 'N/A'),
                        'speed': progress_data.get('speed', 'N/A'),
                        'description': ''
                    }
                elif status == 'finished':
                    values_to_set = {
                        'filename': progress_data.get('filename', download_tree.set(item_id, 'filename'))[:50],
                        'size': progress_data.get('size', '未知'),
                        'status': "下载完成", 'eta': '0s', 'speed': '',
                        'description': progress_data.get('description', '完成')
                    }
                    percent_value = 100.0
                elif status == 'error':
                    values_to_set = {'status': "下载出错", 'description': str(progress_data.get('description', '未知错误'))[:100]} # Limit desc length
                    percent_value = 0.0 # Reset progress on error?
                elif status == 'cancelled': # 处理新增的取消状态
                     values_to_set = {'status': "已取消", 'description': progress_data.get('description', "用户取消")}
                     # 保留之前的进度或置零？当前置零
                     percent_value = 0.0

                # Update Treeview
                for col, value in values_to_set.items():
                     if download_tree.exists(item_id):
                          download_tree.set(item_id, column=col, value=value)

                # Update Progress Bar (Simplistic: shows progress of the item being reported)
                # TODO: Implement overall progress calculation
                if percent_value is not None:
                     progress_bar['value'] = percent_value

            except Exception as e:
                # Avoid crashing the app due to UI update errors
                print(f"更新 Treeview 时出错 (iid={item_id}, data={progress_data}): {e}")

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
        """Starts downloading items passed directly as a list of item_info dictionaries."""
        if not self.root.winfo_exists(): return
        output_path = self.get_download_path() # Ensures path is valid or fallback
        if not output_path:
            self.show_message("警告", "无法确定有效的下载路径！")
            return

        if not items_info_list:
            self.show_message("提示", "没有提供有效的下载任务信息。")
            return

        # --- Filter valid items and add to download list if necessary ---
        valid_items_to_download = []
        download_tree = self.view.get_download_treeview()
        existing_iids = set(download_tree.get_children()) if download_tree else set()
        added_urls_for_queue = []

        for item_info in items_info_list:
            url = item_info.get('url')
            item_id = item_info.get('id') # ID should already be generated by logic module

            if not item_id:
                print(f"警告: 跳过缺少 ID 的任务: {item_info}")
                continue
            if not url or not isinstance(url, str) or not (url.startswith("http://") or url.startswith("https://")):
                print(f"警告: 跳过无效 URL 的任务 (ID: {item_id}): {url}")
                continue

            # Ensure output_path is correct in the item_info
            item_info['output_path'] = output_path # Overwrite if logic module didn't set it right

            # Add to UI queue only if it doesn't exist yet
            if item_id not in existing_iids:
                 added_urls_for_queue.append(url) # Collect URLs to add efficiently

            # Add to the list of tasks to actually start downloading
            # Avoid starting download for the same ID multiple times in this batch
            if not any(item['id'] == item_id for item in valid_items_to_download):
                valid_items_to_download.append(item_info)

        # Add collected new URLs to the Treeview queue
        if added_urls_for_queue:
             self.add_urls_to_download_queue(added_urls_for_queue, platform) # Let it handle status update for adding

        if not valid_items_to_download:
            self.show_message("提示", "没有有效的任务可以启动（可能已在列表中或URL无效）。")
            return

        # --- Start Download Process ---
        self.reset_cancel_request()
        self.view.disable_controls(True) # Disable general controls
        # Explicitly disable remove button
        try:
            if hasattr(self.view, 'remove_button'): self.view.remove_button.config(state=tk.DISABLED)
        except Exception as e: print(f"禁用移除按钮时出错: {e}")
        # Set initial progress and status
        actual_task_count = len(valid_items_to_download) # Use the count of valid items
        self.update_status(f"开始准备立即下载 {actual_task_count} 个任务...")
        try:
            progress_bar = self.view.get_progress_bar()
            if progress_bar: progress_bar['value'] = 5 # Comfort progress
        except Exception as e: print(f"设置初始进度条时出错: {e}")

        # 修改：使用 ThreadPoolExecutor 提交任务
        self.active_futures = {} # 清空之前的 Future 记录

        # Start submitting tasks to the executor
        submitted_count = 0
        for item_info in valid_items_to_download:
            try:
                future = self.download_executor.submit(self._run_single_download_task, item_info)
                self.active_futures[item_info['id']] = future # 使用 item_id 作为键存储 Future
                submitted_count += 1
            except Exception as e:
                 item_id_for_error = item_info.get('id', '未知ID')
                 print(f"提交下载任务 {item_id_for_error} 到线程池时出错: {e}")
                 self.update_download_progress({'id': item_id_for_error, 'status': 'error', 'description': f'提交错误: {e}'})
        # -------------------------------------------

        if submitted_count == 0:
            self.view.disable_controls(False) # Re-enable controls if nothing started
            # 恢复移除按钮状态
            try:
                if hasattr(self.view, 'remove_button'): self.view.remove_button.config(state=tk.NORMAL)
            except Exception as e: print(f"恢复移除按钮时出错: {e}")
            self.update_status("没有有效的任务启动。")
            return

        # Start monitoring thread (now monitors futures) ONLY if tasks were submitted
        monitor_thread = Thread(target=self._monitor_download_futures) # 修改：调用新的监控方法
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
                 if values and len(values) > 3 and values[0] == '☑' and values[3] in ('待下载', '下载出错', '准备下载'):
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
                      download_tree.set(iid, column='status', value="准备下载")
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
        try:
            progress_bar = self.view.get_progress_bar()
            if progress_bar: progress_bar['value'] = 5 # 安慰性进度
        except Exception as e: print(f"设置初始进度条时出错: {e}")

        # 修改：使用 ThreadPoolExecutor 提交任务
        self.active_futures = {} # 清空之前的 Future 记录

        # --- Submit tasks to the executor for each selected item ---
        submitted_count = 0
        for item_iid in selected_iids:
            try:
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
        """在后台线程中调用 DownloadService 下载单个项目。"""
        if not self.download_service:
            # logger.error("DownloadService 未初始化，无法下载 %s", item_info.get('id')) # Use print if logger not set up
            print(f"错误: DownloadService 未初始化，无法下载 {item_info.get('id')}")
            self.update_download_progress({'id': item_info.get('id'), 'status': 'error', 'description': '服务未初始化'})
            return

        item_id = item_info.get('id')
        # logger.info("下载线程启动 for: %s", item_id)
        print(f"信息: 下载线程启动 for: {item_id}")
        try:
            # 直接调用 DownloadService，它内部处理回调
            # 修改：传递 self.is_cancel_requested 作为取消检查函数
            result = self.download_service.download_item(item_info, self.update_download_progress, self.is_cancel_requested)
            # logger.info("下载线程结束 for %s. 最终状态: %s", item_id, result.get('status'))
            print(f"信息: 下载线程结束 for {item_id}. 最终状态: {result.get('status')}")
        except Exception as e:
            # logger.error("运行单任务下载时发生意外错误 for %s: %s", item_id, e, exc_info=True)
            print(f"错误: 运行单任务下载时发生意外错误 for {item_id}: {e}")
            # 尝试最后更新一次状态
            self.update_download_progress({'id': item_id, 'status': 'error', 'description': f'线程错误: {e}'})

    def _monitor_download_futures(self):
        """Waits for active download futures to complete and updates UI."""
        if not self.active_futures:
            print("监控：没有活动的 Future 对象需要监控。") # 添加调试信息
            return

        print(f"监控：开始监控 {len(self.active_futures)} 个 Future 对象...") # 添加调试信息
        # 使用 concurrent.futures.wait 等待所有 Future 完成
        # future_list = list(self.active_futures.values())
        # concurrent.futures.wait(future_list)
        # 或者，更简单地循环检查直到所有 future 都 done
        all_futures_items = list(self.active_futures.items()) # 获取 (item_id, future) 对
        active_count = len(all_futures_items)
        while active_count > 0:
            # 检查完成的 futures
            completed_count = 0
            for item_id, future in all_futures_items:
                 if future.done():
                      completed_count += 1
            active_count = len(all_futures_items) - completed_count
            # print(f"监控：剩余 {active_count} 个任务...") # 避免过多日志
            time.sleep(0.5)
            # 检查是否请求了取消
            if self.is_cancel_requested():
                print("监控：检测到取消请求，等待任务自行结束或出错...")
                # 注意：ThreadPoolExecutor 没有直接的方法强制取消正在运行的任务
                # 依赖 DownloadService 内部的检查来尽早结束
                pass # 继续等待线程结束

        # 所有 Futures 完成 (或被视为完成，例如取消后)
        print("监控：所有 Future 对象已完成。") # 添加调试信息
        was_cancelled = self.is_cancel_requested() # 检查最终状态

        # --- 执行收尾 UI 更新 ---
        def final_ui_update():
            if not self.root.winfo_exists():
                 print("监控：UI 更新时窗口已不存在。") # 添加调试信息
                 return
            print("监控：开始执行最终 UI 更新。") # 添加调试信息

            # --- Calculate Summary ---
            success_count = 0
            error_count = 0
            cancelled_count = 0 # 新增取消计数
            download_tree = self.view.get_download_treeview()
            processed_ids = set(self.active_futures.keys()) # 只统计本次提交的任务
            total_tasks_in_batch = len(processed_ids)
            print(f"监控：统计 {total_tasks_in_batch} 个任务的结果...") # 添加调试信息

            if download_tree:
                for item_iid in processed_ids:
                    try:
                        if download_tree.exists(item_iid):
                             status = download_tree.set(item_iid, 'status')
                             if status == "下载完成":
                                 success_count += 1
                             elif status == "下载出错":
                                 error_count += 1
                             elif status == "已取消" or status == "用户已取消": # 检查取消状态
                                 cancelled_count += 1
                             # 其他状态（如准备中）视为未完成
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

            summary_title = "下载完成" if not was_cancelled else "下载取消"
            # Fix: Ensure string formatting and newlines are correct
            summary_message = f"下载批次处理完毕。\n\n" \
                              f"总计任务: {total_tasks_in_batch} 个\n" \
                              f"成功: {success_count} 个\n" \
                              f"失败: {error_count} 个\n"
            if cancelled_count > 0:
                 summary_message += f"取消: {cancelled_count} 个\n"
            # if was_cancelled and (success_count + error_count + cancelled_count < total_tasks_in_batch):
            #      summary_message += f"\n注意：部分任务可能因取消而未完成或状态未知。"

            print(f"监控：显示总结弹窗: Title='{summary_title}', Message='{summary_message.replace('\\n', ' ')}'") # 添加调试信息
            self.show_message(summary_title, summary_message)

        if self.root.winfo_exists():
            print("监控：调度 final_ui_update 到主线程。") # 添加调试信息
            self.root.after(0, final_ui_update)
        else:
            print("监控：窗口已关闭，无法调度 final_ui_update。") # 添加调试信息

        print("监控：清空 active_futures。") # 添加调试信息
        self.active_futures = {} # 清空 Future 记录


    def _on_closing(self):
        """Handle window close event."""
        # 修改：检查 active_futures 是否有任务在进行
        # 注意：future.running() 或 future.done() 可能不足以判断是否真的可以安全退出
        # 最好是检查 self.active_futures 是否为空
        if self.active_futures:
             if messagebox.askyesno("退出确认", "下载仍在进行中，确定要退出吗？", parent=self.root):
                  print("请求取消所有下载并尝试关闭线程池...")
                  self.request_cancel()
                  # 尝试关闭 Executor， non-blocking，允许正在运行的任务完成
                  self.download_executor.shutdown(wait=False, cancel_futures=False) # cancel_futures=True requires Python 3.9+ and might be abrupt
                  print("线程池已发出关闭信号，主程序退出。")
                  self.root.destroy()
             else:
                  return # Don't close
        else:
             # 如果没有活动任务，也确保关闭 executor
             print("关闭下载线程池...")
             self.download_executor.shutdown(wait=True) # 等待已完成任务的线程退出
             print("线程池已关闭。")
             self.root.destroy()


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