# sucoidownload.py
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog, messagebox
import os
from threading import Thread
import youtube # 导入 YouTube 平台模块
import tiktok  # 导入 TikTok 平台模块
from config_manager import ConfigManager

class Sucoidownload:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Sucoidownload - 模块化视频下载器")
        self.root.geometry("750x600") # 调整初始大小

        # --- 配置管理器 ---
        self.config_manager = ConfigManager()
        self.api_key = self.config_manager.get_config('api_key') # YouTube API Key (主程序需要读取以传递给模块)

        # --- 定义通用控件 ---
        self.status_label = tk.Label(self.root, text="状态: 就绪")
        self.settings_button = tk.Button(self.root, text="设置", command=self.open_settings_window)

        # --- 全局下载列表框架和 Treeview ---
        self.download_frame = ttk.LabelFrame(self.root, text="下载列表")
        download_cols = ('select', 'filename', 'size', 'status', 'eta', 'speed', 'platform', 'description')
        self.download_tree = ttk.Treeview(self.download_frame, columns=download_cols, show='headings', height=10)
        self._setup_download_tree_columns(download_cols) # 配置列
        download_scrollbar = ttk.Scrollbar(self.download_frame, orient=tk.VERTICAL, command=self.download_tree.yview)
        self.download_tree.configure(yscrollcommand=download_scrollbar.set)
        self.download_tree.grid(row=0, column=0, sticky='nsew')
        download_scrollbar.grid(row=0, column=1, sticky='ns')
        self.download_frame.grid_rowconfigure(0, weight=1)
        self.download_frame.grid_columnconfigure(0, weight=1)

        # --- 路径选择 (通用) ---
        self.path_var = tk.StringVar()
        self.path_entry = tk.Entry(self.root, textvariable=self.path_var)
        self.path_button = tk.Button(self.root, text="选择下载路径", command=self.select_path)
        self._initialize_download_path()
        self.path_var.trace_add("write", self.save_download_path_to_config)

        # --- 主窗口布局 ---
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=0) # Top frame
        self.root.rowconfigure(1, weight=1) # Notebook
        self.root.rowconfigure(2, weight=1) # Download frame
        self.root.rowconfigure(3, weight=0) # Bottom frame

        # --- 顶部区域 ---
        top_frame = tk.Frame(self.root)
        top_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 0))
        top_frame.columnconfigure(0, weight=1)
        self.status_label.grid(row=0, column=0, sticky=tk.W)
        self.settings_button.grid(row=0, column=1, sticky=tk.E)

        # --- 创建 Notebook (中部区域) ---
        self.notebook = ttk.Notebook(self.root)
        self.notebook.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)

        # --- 创建并添加平台标签页 ---
        self.platform_tabs = {}
        platforms = {'TikTok': tiktok, 'YouTube': youtube}

        for name, module in platforms.items():
            try:
                if hasattr(module, 'create_tab'):
                    tab_frame = module.create_tab(self.notebook, self)
                    self.notebook.add(tab_frame, text=name)
                    self.platform_tabs[name] = tab_frame
                    print(f"成功加载 '{name}' 标签页。")
                else:
                    print(f"警告: 模块 {module.__name__} 未实现 create_tab 函数。")
                    self._add_error_tab(name, f"模块 {module.__name__} 接口不完整")
            except Exception as e:
                print(f"加载 {name} 模块 UI 时出错: {e}")
                self._add_error_tab(name, f"加载界面失败:\n{e}")

        # --- 下载列表布局 (全局) ---
        self.download_frame.grid(row=2, column=0, sticky='nsew', padx=10, pady=5)

        # --- 底部区域 (路径选择) ---
        bottom_frame = tk.Frame(self.root)
        bottom_frame.grid(row=3, column=0, sticky="ew", padx=10, pady=(5, 10))
        bottom_frame.columnconfigure(1, weight=1)
        self.path_button.grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.path_entry.grid(row=0, column=1, sticky=tk.EW)

        # --- 启动主循环 ---
        self.root.mainloop()

    # --- Helper and Callback Methods ---
    def _setup_download_tree_columns(self, cols):
        """配置下载列表 Treeview 的列。"""
        headings = {'select': '选择', 'filename': '文件名', 'size': '大小', 'status': '状态',
                    'eta': '剩余时间', 'speed': '传输速度', 'platform': '平台', 'description': '描述'}
        widths = {'select': 40, 'filename': 250, 'size': 80, 'status': 100, 'eta': 80,
                  'speed': 100, 'platform': 60, 'description': 150}
        minwidths = {'select': 40, 'filename': 150, 'size': 60, 'status': 80, 'eta': 60,
                     'speed': 80, 'platform': 50, 'description': 100}
        stretches = {'select': False, 'filename': True, 'size': False, 'status': False, 'eta': False,
                     'speed': False, 'platform': False, 'description': False}
        anchors = {'select': tk.CENTER, 'size': tk.E, 'eta': tk.E, 'speed': tk.E}
        for col in cols:
            self.download_tree.heading(col, text=headings.get(col, col))
            self.download_tree.column(col, width=widths.get(col, 100), minwidth=minwidths.get(col, 40),
                                      stretch=stretches.get(col, False), anchor=anchors.get(col, tk.W))

    def _add_error_tab(self, name, error_message):
        """在 Notebook 中添加一个显示错误的标签页"""
        error_tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(error_tab, text=f'{name} (错误)')
        ttk.Label(error_tab, text=error_message, foreground="red").pack(padx=5, pady=5)

    def _initialize_download_path(self):
        """初始化下载路径变量"""
        configured_path = self.config_manager.get_config('default_download_path')
        default_download_path = ""
        script_dir = os.path.dirname(os.path.abspath(__file__))
        fallback_path = os.path.join(script_dir, "download")
        try:
            if configured_path and os.path.isabs(configured_path) and os.path.isdir(os.path.dirname(configured_path)):
                default_download_path = configured_path
            elif configured_path and not os.path.isabs(configured_path):
                 abs_path = os.path.abspath(os.path.join(script_dir, configured_path))
                 if os.path.isdir(os.path.dirname(abs_path)):
                      default_download_path = abs_path
                      print(f"将相对路径 '{configured_path}' 解析为绝对路径: {abs_path}")
                 else:
                      default_download_path = fallback_path
                      print(f"警告: 配置文件中的相对路径 '{configured_path}' 无效，使用默认路径。")
            else:
                default_download_path = fallback_path
                if configured_path: print(f"警告: config.json 中的 default_download_path '{configured_path}' 无效，使用默认路径。")
            os.makedirs(default_download_path, exist_ok=True)
        except Exception as e:
            print(f"初始化下载路径时出错: {e}. 使用默认路径 {fallback_path}")
            default_download_path = fallback_path
            os.makedirs(default_download_path, exist_ok=True)
        self.path_var.set(default_download_path)

    def save_download_path_to_config(self, *args):
        """回调函数：当下载路径变量变化时，将其保存到配置文件。"""
        new_path = self.path_var.get()
        if new_path:
             try:
                 abs_path = os.path.abspath(new_path)
                 if os.path.isdir(os.path.dirname(abs_path)) or os.path.isdir(abs_path):
                     self.config_manager.update_config('default_download_path', abs_path)
                 else:
                     print(f"尝试保存的路径 '{new_path}' 无效，未更新配置。")
             except Exception as e:
                 print(f"保存下载路径时出错: {e}")

    def select_path(self):
        """打开文件夹选择对话框，更新底部路径输入框"""
        folder = filedialog.askdirectory()
        if folder:
            self.path_var.set(os.path.abspath(folder))

    def update_download_progress(self, progress_data):
        """由平台模块调用的回调函数，用于在主线程更新全局下载列表。"""
        item_id = progress_data.get('id') # 使用 platform_videoid 作为 Treeview 的 iid
        if not item_id:
            print("警告: 收到缺少 id 的进度回调数据:", progress_data)
            return

        def do_update():
            try:
                if not self.download_tree.exists(item_id): return

                status = progress_data.get('status')
                if status == 'preparing':
                     self.download_tree.set(item_id, column='status', value="准备下载")
                     self.download_tree.set(item_id, column='description', value='')
                elif status == 'downloading':
                    values_to_set = {
                        'filename': progress_data.get('filename', self.download_tree.set(item_id, 'filename')),
                        'size': progress_data.get('size', '未知'),
                        'status': f"下载中 {progress_data.get('percent', '0%')}",
                        'eta': progress_data.get('eta', 'N/A'),
                        'speed': progress_data.get('speed', 'N/A'),
                        'description': ''
                    }
                    for col, value in values_to_set.items(): self.download_tree.set(item_id, column=col, value=value)
                elif status == 'finished':
                    values_to_set = {
                        'filename': progress_data.get('filename', self.download_tree.set(item_id, 'filename')),
                        'size': progress_data.get('size', '未知'),
                        'status': "下载完成", 'eta': '0s', 'speed': '',
                        'description': progress_data.get('description', '完成')
                    }
                    for col, value in values_to_set.items(): self.download_tree.set(item_id, column=col, value=value)
                elif status == 'error':
                    values_to_set = {'status': "下载出错", 'description': progress_data.get('description', '未知错误')}
                    for col, value in values_to_set.items(): self.download_tree.set(item_id, column=col, value=value)
            except Exception as e:
                print(f"在 update_download_progress 中更新 Treeview 时出错 (iid={item_id}, data={progress_data}): {e}")
        self.root.after(0, do_update)

    def start_download(self):
        """从全局下载列表获取任务，并在新线程中启动下载过程"""
        output_path = self.path_var.get()
        if not output_path:
            messagebox.showwarning("警告", "请选择保存路径！"); return

        all_item_iids = self.download_tree.get_children()
        if not all_item_iids:
             messagebox.showinfo("提示", "下载列表为空。"); return

        tasks_to_download = {}
        for item_iid in all_item_iids:
             item_values = self.download_tree.item(item_iid, 'values')
             # 检查平台和状态列
             if item_values and len(item_values) > 6 and item_values[3] in ('待下载', '下载出错', '准备下载', '完成(可能出错)'):
                 platform = item_values[6] if item_values[6] else 'unknown'
                 video_id = item_iid
                 if platform not in tasks_to_download: tasks_to_download[platform] = []
                 tasks_to_download[platform].append(video_id)
                 if item_values[3] != '待下载':
                      try:
                          if self.download_tree.exists(item_iid):
                             self.download_tree.set(item_iid, column='status', value="准备下载")
                             self.download_tree.set(item_iid, column='description', value="")
                      except Exception as e: print(f"重置下载状态时出错 (iid={item_iid}): {e}")

        if not tasks_to_download:
             messagebox.showinfo("提示", "没有待下载或可重试的任务。"); return

        self.disable_controls(True); self.status_label.config(text="状态: 开始准备下载..."); self.root.update_idletasks()

        all_threads = []; total_success = 0; total_error = 0
        def download_task_wrapper(platform_module, ids, path):
            nonlocal total_success, total_error
            if hasattr(platform_module, 'download_videos'):
                success_count, error_count = platform_module.download_videos(ids, path, self.update_download_progress)
                total_success += success_count; total_error += error_count
            else:
                 print(f"错误: 平台模块 {platform_module.__name__}缺少 download_videos 函数。"); total_error += len(ids)
                 for vid in ids: self.update_download_progress({'id': vid, 'status': 'error', 'description': '平台模块错误'})

        platform_modules = {'YouTube': youtube, 'TikTok': tiktok} # 平台名称大小写要匹配 Notebook 添加时的 text

        for platform, ids in tasks_to_download.items():
             # 使用 get 处理未找到的平台
             platform_module = platform_modules.get(platform)
             if platform_module:
                 thread = Thread(target=download_task_wrapper, args=(platform_module, ids, output_path))
                 thread.daemon = True; all_threads.append(thread); thread.start()
             else:
                 print(f"警告: 未知的平台 '{platform}'，无法下载 {len(ids)} 个任务。")
                 for vid in ids: self.update_download_progress({'id': vid, 'status': 'error', 'description': f'未知平台: {platform}'})
                 total_error += len(ids)

        def monitor_downloads():
            for t in all_threads: t.join()
            def show_final_status_wrapper():
                final_message = f"全部任务完成！成功: {total_success}, 失败/出错: {total_error}"
                self.status_label.config(text=f"状态: {final_message}")
                if total_error > 0: messagebox.showwarning("下载完成", final_message + "\n部分视频下载失败或可能出错。")
                else: messagebox.showinfo("成功", final_message)
                self.disable_controls(False)
            self.root.after(0, show_final_status_wrapper)

        monitor_thread = Thread(target=monitor_downloads); monitor_thread.daemon = True; monitor_thread.start()

    def handle_search(self):
         """处理当前激活标签页的搜索事件。"""
         try:
             current_tab_text = self.notebook.tab(self.notebook.select(), "text")
         except tk.TclError: messagebox.showwarning("提示", "请先选择一个平台标签页。"); return

         if current_tab_text == 'YouTube':
             self._handle_youtube_search()
         elif current_tab_text == 'TikTok':
             # TODO: 实现 TikTok 的搜索逻辑（如果需要）或显示不支持
             messagebox.showinfo("提示", "TikTok 平台暂不支持搜索功能。", parent=self.tiktok_tab)
         else:
             messagebox.showinfo("提示", "当前平台不支持搜索功能。", parent=self.root)

    def _handle_youtube_search(self):
         """处理 YouTube 搜索的内部逻辑。"""
         try:
             query = self.youtube_keyword_entry.get().strip()
             # TODO: 获取筛选参数
             # duration_filter = self.youtube_duration_var.get()
             # order_filter = self.youtube_order_var.get()
             if not query: messagebox.showwarning("搜索", "请输入搜索关键词！", parent=self.youtube_tab); return
         except AttributeError: messagebox.showerror("错误", "YouTube 搜索控件未正确初始化！"); return
         if not self.api_key or self.api_key == 'YOUR_YOUTUBE_DATA_API_KEY_HERE':
             messagebox.showerror("API Key 错误", "无效或未配置 YouTube API Key。\n请在设置中配置后重试。"); return

         self.status_label.config(text="状态: 正在搜索..."); self.disable_controls(True); self.root.update_idletasks()

         def search_task():
             videos_info, error_msg = youtube.search_videos(self.api_key, query) # TODO: 传入筛选参数
             self.root.after(0, update_youtube_search_results, videos_info, error_msg)

         def update_youtube_search_results(videos_info, error_msg):
             self.disable_controls(False)
             try:
                 tree = self.youtube_search_tree # 访问挂载的属性
                 for i in tree.get_children(): tree.delete(i)
             except AttributeError: print("错误：无法访问 youtube_search_tree。"); self.status_label.config(text="状态: 内部错误"); return

             if error_msg: self.status_label.config(text="状态: 搜索出错"); messagebox.showerror("搜索错误", error_msg); return
             elif videos_info is None: self.status_label.config(text="状态: 搜索出错"); messagebox.showerror("搜索错误", "发生未知错误"); return

             if videos_info:
                 for video in videos_info:
                     try:
                         tree.insert('', tk.END, values=(
                             video.get('name', ''), video.get('views', '0'), video.get('likes', '0'),
                             video.get('favorites', 'N/A'), video.get('comments', '0'),
                             video.get('published', ''), video.get('duration', '')), iid=video.get('id'))
                     except Exception as e: print(f"插入 YouTube 搜索结果时出错 (vid={video.get('id')}): {e}")
                 self.status_label.config(text=f"状态: 找到 {len(videos_info)} 个视频")
             else:
                 self.status_label.config(text="状态: 未找到相关视频")
                 messagebox.showinfo("搜索结果", "未找到与关键词匹配的视频。", parent=self.youtube_tab)

         search_thread = Thread(target=search_task); search_thread.daemon = True; search_thread.start()

    def add_selected_to_download(self):
        """将活动标签页搜索结果中选中的项添加到全局下载列表。"""
        try:
            current_tab_text = self.notebook.tab(self.notebook.select(), "text")
        except tk.TclError: messagebox.showwarning("提示", "请先选择一个平台标签页。"); return

        source_tree = None
        platform_name = current_tab_text # 直接使用标签文本作为平台名

        if platform_name == 'YouTube':
            try: source_tree = self.youtube_search_tree
            except AttributeError: messagebox.showerror("错误", "YouTube 搜索结果控件未初始化！"); return
        elif platform_name == 'TikTok':
             # TODO: 如果 TikTok 标签页有可选列表，在这里获取
             messagebox.showinfo("提示", "请直接在 TikTok 标签页输入 URL 进行下载或添加到队列（如果实现）。")
             return # TikTok 暂时没有可供选择的列表
        else: messagebox.showerror("错误", f"未知的平台标签: {platform_name}"); return

        if source_tree is None: messagebox.showerror("错误", f"{platform_name} 标签页缺少结果表格！"); return

        selected_item_iids = source_tree.selection()
        if not selected_item_iids: messagebox.showinfo("提示", f"请先在 {platform_name} 结果中选择要添加的项。"); return

        added_count, skipped_count = 0, 0
        existing_download_iids = set(self.download_tree.get_children())

        for item_id in selected_item_iids:
            # 使用平台名和 ID 组合成唯一 ID，避免冲突
            download_iid = f"{platform_name}_{item_id}"
            if download_iid in existing_download_iids: skipped_count += 1; continue
            try:
                source_values = source_tree.item(item_id, 'values')
                if not source_values or len(source_values) < 1: skipped_count += 1; continue
                video_title = source_values[0]
                download_values = ('☐', video_title, '未知', '待下载', '', '', platform_name, '')
                self.download_tree.insert('', tk.END, iid=download_iid, values=download_values) # 使用组合 ID
                added_count += 1
            except Exception as e: print(f"添加视频到下载列表时出错 (iid={download_iid}): {e}"); skipped_count += 1

        status_message = f"添加完成：{added_count} 个视频已添加到下载列表。"
        if skipped_count > 0: status_message += f" {skipped_count} 个已存在或无效，已跳过。"
        self.status_label.config(text=f"状态: {status_message}")

    def open_settings_window(self):
        """打开设置窗口。"""
        settings_window = tk.Toplevel(self.root); settings_window.title("设置"); settings_window.transient(self.root); settings_window.grab_set()
        settings_frame = ttk.Frame(settings_window, padding="10"); settings_frame.pack(expand=True, fill="both")
        placeholder_api_key = "你的API key (用于YouTube)"; placeholder_path = "软件根目录download文件夹"; placeholder_color = 'grey'
        try: default_fg_color = settings_window.cget('fg')
        except tk.TclError: default_fg_color = 'black'
        api_key_var = tk.StringVar(); download_path_var = tk.StringVar()
        tk.Label(settings_frame, text="YouTube API Key:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        api_key_entry = tk.Entry(settings_frame, textvariable=api_key_var, width=40); api_key_entry.grid(row=0, column=1, columnspan=2, padx=5, pady=5, sticky=tk.EW)
        tk.Label(settings_frame, text="默认下载地址:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        download_path_entry = tk.Entry(settings_frame, textvariable=download_path_var, width=40); download_path_entry.grid(row=1, column=1, padx=5, pady=5, sticky=tk.EW)
        select_path_button = tk.Button(settings_frame, text="...", command=lambda: self.select_default_download_path(download_path_var, settings_window)); select_path_button.grid(row=1, column=2, padx=5, pady=5, sticky=tk.W)
        button_frame_settings = tk.Frame(settings_frame); button_frame_settings.grid(row=2, column=0, columnspan=3, pady=15)
        save_button = tk.Button(button_frame_settings, text="保存", command=lambda: self.save_settings(api_key_var.get(), download_path_var.get(), settings_window, placeholder_api_key, placeholder_path)); save_button.pack(side=tk.LEFT, padx=10)
        cancel_button = tk.Button(button_frame_settings, text="取消", command=settings_window.destroy); cancel_button.pack(side=tk.LEFT, padx=10)
        def setup_placeholder_logic(entry, var, placeholder_text):
            def on_focus_in(event):
                if var.get() == placeholder_text: var.set(''); entry.config(fg=default_fg_color)
            def on_focus_out(event):
                if not var.get(): var.set(placeholder_text); entry.config(fg=placeholder_color)
            entry.bind("<FocusIn>", on_focus_in); entry.bind("<FocusOut>", on_focus_out)
        current_api_key = self.config_manager.get_config('api_key'); current_path = self.config_manager.get_config('default_download_path')
        if current_api_key and current_api_key != 'YOUR_YOUTUBE_DATA_API_KEY_HERE': api_key_var.set(current_api_key); api_key_entry.config(fg=default_fg_color)
        else: api_key_var.set(placeholder_api_key); api_key_entry.config(fg=placeholder_color)
        if current_path: download_path_var.set(current_path); download_path_entry.config(fg=default_fg_color)
        else: download_path_var.set(placeholder_path); download_path_entry.config(fg=placeholder_color)
        setup_placeholder_logic(api_key_entry, api_key_var, placeholder_api_key); setup_placeholder_logic(download_path_entry, download_path_var, placeholder_path)
        settings_frame.columnconfigure(1, weight=1); settings_window.update_idletasks()
        width = settings_window.winfo_reqwidth() + 20; height = settings_window.winfo_reqheight() + 20
        main_x, main_y = self.root.winfo_x(), self.root.winfo_y(); main_width, main_height = self.root.winfo_width(), self.root.winfo_height()
        x = main_x + (main_width // 2) - (width // 2); y = main_y + (main_height // 2) - (height // 2)
        settings_window.geometry(f'{width}x{height}+{x}+{y}'); settings_window.resizable(False, False)

    def save_settings(self, api_key, download_path, window, placeholder_api, placeholder_pth):
        """保存设置到配置文件。"""
        updates = {}; final_api_key = api_key if api_key != placeholder_api else ''; final_download_path = os.path.abspath(download_path) if download_path and download_path != placeholder_pth else ''
        updates['api_key'] = final_api_key; updates['default_download_path'] = final_download_path; self.config_manager.update_multiple_configs(updates)
        messagebox.showinfo("设置", "设置已保存。", parent=window); self.api_key = final_api_key; current_main_path = self.path_var.get(); new_default_path = final_download_path if final_download_path else self.get_fallback_download_path()
        fallback_path = self.get_fallback_download_path()
        if final_download_path and current_main_path == fallback_path: self.path_var.set(new_default_path)
        elif not final_download_path and current_main_path != fallback_path: self.path_var.set(fallback_path)
        window.destroy()

    def select_default_download_path(self, path_var, parent_window):
        """为设置窗口中的下载路径选择文件夹。"""
        folder = filedialog.askdirectory(parent=parent_window)
        if folder: abs_path = os.path.abspath(folder); path_var.set(abs_path); parent_window.focus()

    def get_fallback_download_path(self):
         """获取回退的默认下载路径（脚本目录下的 download）。"""
         script_dir = os.path.dirname(os.path.abspath(__file__))
         return os.path.join(script_dir, "download")

    def disable_controls(self, disable=True):
         """禁用或启用界面上的主要交互控件。"""
         state = tk.DISABLED if disable else tk.NORMAL
         # 通用控件
         try: self.settings_button.config(state=state)
         except AttributeError: pass
         try: self.path_button.config(state=state)
         except AttributeError: pass
         # 尝试禁用/启用 YouTube 标签页内的控件
         youtube_buttons = ['youtube_search_button', 'youtube_add_button', 'youtube_download_button']
         for btn_attr in youtube_buttons:
              try: getattr(self, btn_attr).config(state=state)
              except AttributeError: pass # 忽略按钮不存在或未挂载的情况
         # TODO: 禁用/启用 TikTok 标签页内的控件 (需要 tiktok.py 支持)
         # 需要 tiktok.py 的 create_tab 返回按钮引用或提供 enable/disable 方法


if __name__ == "__main__":
    Sucoidownload()