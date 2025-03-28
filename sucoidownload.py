# sucoidownload.py
import yt_dlp
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog, messagebox
import os
from threading import Thread
from config_manager import ConfigManager
from googleapiclient.discovery import build

class Sucoidownload:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Sucoidownload - 视频批量下载器")
        self.root.geometry("600x450") # 稍微增加高度以容纳搜索结果

        # --- 配置管理器 ---
        self.config_manager = ConfigManager()
        self.api_key = self.config_manager.get_config('api_key')
        # API Key 警告移到后面，避免 config.json 不存在时就弹窗

        # --- 组件定义 ---
        # 状态显示
        self.status_label = tk.Label(self.root, text="状态: 就绪")

        # 搜索关键词输入
        self.keyword_label = tk.Label(self.root, text="搜索关键词:")
        self.keyword_entry = tk.Entry(self.root)
        self.search_button = tk.Button(self.root, text="搜索视频", command=self.handle_search)

        # --- 表格区域 --- 
        # 搜索结果框架
        self.search_frame = ttk.LabelFrame(self.root, text="搜索结果")
        # 下载列表框架
        self.download_frame = ttk.LabelFrame(self.root, text="下载列表")


        # 搜索结果 Treeview
        search_cols = ('name', 'views', 'likes', 'favorites', 'comments', 'published', 'duration')
        self.search_tree = ttk.Treeview(self.search_frame, columns=search_cols, show='headings', height=5)

        # 定义列标题
        self.search_tree.heading('name', text='视频名称')
        self.search_tree.heading('views', text='播放量')
        self.search_tree.heading('likes', text='点赞量')
        self.search_tree.heading('favorites', text='收藏量') # 注意：API可能不直接提供收藏量
        self.search_tree.heading('comments', text='评论数')
        self.search_tree.heading('published', text='更新时间')
        self.search_tree.heading('duration', text='时长')

        # 设置列宽 (可根据需要调整)
        self.search_tree.column('name', width=200, stretch=True)
        self.search_tree.column('views', width=80, anchor=tk.E, stretch=False)
        self.search_tree.column('likes', width=80, anchor=tk.E, stretch=False)
        self.search_tree.column('favorites', width=80, anchor=tk.E, stretch=False)
        self.search_tree.column('comments', width=80, anchor=tk.E, stretch=False)
        self.search_tree.column('published', width=100, stretch=False)
        self.search_tree.column('duration', width=60, anchor=tk.E, stretch=False)

        # 添加滚动条
        search_scrollbar = ttk.Scrollbar(self.search_frame, orient=tk.VERTICAL, command=self.search_tree.yview)
        self.search_tree.configure(yscrollcommand=search_scrollbar.set)

        # 布局 Treeview 和滚动条
        self.search_tree.grid(row=0, column=0, sticky='nsew')
        search_scrollbar.grid(row=0, column=1, sticky='ns')

        # 配置框架内的网格权重，使 Treeview 可以缩放
        self.search_frame.grid_rowconfigure(0, weight=1)
        self.search_frame.grid_columnconfigure(0, weight=1)



        # 下载列表 Treeview
        download_cols = ('select', 'filename', 'size', 'status', 'eta', 'speed', 'last_connected', 'description')
        self.download_tree = ttk.Treeview(self.download_frame, columns=download_cols, show='headings', height=7)

        # 定义列标题
        self.download_tree.heading('select', text='选择')
        self.download_tree.heading('filename', text='文件名')
        self.download_tree.heading('size', text='大小')
        self.download_tree.heading('status', text='状态')
        self.download_tree.heading('eta', text='剩余时间')
        self.download_tree.heading('speed', text='传输速度')
        self.download_tree.heading('last_connected', text='最后连接')
        self.download_tree.heading('description', text='描述')

        # 设置列宽和最小宽度 (minwidth) 以解决表头显示问题
        self.download_tree.column('select', width=40, minwidth=40, anchor=tk.CENTER, stretch=False)
        self.download_tree.column('filename', width=250, minwidth=150, stretch=True)
        self.download_tree.column('size', width=80, minwidth=60, anchor=tk.E, stretch=False)
        self.download_tree.column('status', width=100, minwidth=80, stretch=False)
        self.download_tree.column('eta', width=80, minwidth=60, anchor=tk.E, stretch=False)
        self.download_tree.column('speed', width=100, minwidth=80, anchor=tk.E, stretch=False)
        self.download_tree.column('last_connected', width=100, minwidth=80, stretch=False)
        self.download_tree.column('description', width=150, minwidth=100, stretch=False)

        # 添加滚动条
        download_scrollbar = ttk.Scrollbar(self.download_frame, orient=tk.VERTICAL, command=self.download_tree.yview)
        self.download_tree.configure(yscrollcommand=download_scrollbar.set)

        # 布局 Treeview 和滚动条
        self.download_tree.grid(row=0, column=0, sticky='nsew')
        download_scrollbar.grid(row=0, column=1, sticky='ns')

        # 配置框架内的网格权重
        self.download_frame.grid_rowconfigure(0, weight=1)
        self.download_frame.grid_columnconfigure(0, weight=1)

        # 下载列表框架
        self.download_frame = ttk.LabelFrame(self.root, text="下载列表")


        # 保存路径选择
        # self.url_label 和 self.url_text 已移除
        # self.path_label 已移除
        # 优先从配置加载默认下载路径
        configured_path = self.config_manager.get_config('default_download_path')
        default_download_path = "" # 初始化
        script_dir = os.path.dirname(os.path.abspath(__file__))
        fallback_path = os.path.join(script_dir, "download")

        if configured_path and os.path.isdir(os.path.dirname(os.path.abspath(configured_path))):
             default_download_path = os.path.abspath(configured_path)
        else:
            # 如果配置无效或为空，则回退到脚本目录下的 download 文件夹
            default_download_path = fallback_path
            if configured_path: # 如果配置了但无效，给个提示
                print(f"警告: config.json 中的 default_download_path '{configured_path}' 无效或其父目录不存在，将使用默认路径: {default_download_path}")

        os.makedirs(default_download_path, exist_ok=True) # 确保最终路径存在
        self.path_var = tk.StringVar(value=default_download_path)
        self.path_var.trace_add("write", self.save_download_path_to_config) # 路径变化时保存到配置
        self.path_entry = tk.Entry(self.root, textvariable=self.path_var)
        self.path_button = tk.Button(self.root, text="选择下载路径", command=self.select_path)

        # 下载按钮
        # 下载列表 Treeview
        download_cols = ('select', 'filename', 'size', 'status', 'eta', 'speed', 'last_connected', 'description')
        self.download_tree = ttk.Treeview(self.download_frame, columns=download_cols, show='headings', height=7)

        # 定义列标题
        self.download_tree.heading('select', text='选择') # 用于复选框
        self.download_tree.heading('filename', text='文件名')
        self.download_tree.heading('size', text='大小')
        self.download_tree.heading('status', text='状态')
        self.download_tree.heading('eta', text='剩余时间')
        self.download_tree.heading('speed', text='传输速度')
        self.download_tree.heading('last_connected', text='最后连接') # yt-dlp可能不提供此信息
        self.download_tree.heading('description', text='描述') # 用于显示错误信息等

        # 设置列宽
        self.download_tree.column('select', width=40, anchor=tk.CENTER)
        self.download_tree.column('filename', width=250)
        self.download_tree.column('size', width=80, anchor=tk.E)
        self.download_tree.column('status', width=100)
        self.download_tree.column('eta', width=80, anchor=tk.E)
        self.download_tree.column('speed', width=100, anchor=tk.E)
        self.download_tree.column('last_connected', width=100)
        self.download_tree.column('description', width=150)

        # 添加滚动条
        download_scrollbar = ttk.Scrollbar(self.download_frame, orient=tk.VERTICAL, command=self.download_tree.yview)
        self.download_tree.configure(yscrollcommand=download_scrollbar.set)

        # 布局 Treeview 和滚动条
        self.download_tree.grid(row=0, column=0, sticky='nsew')
        download_scrollbar.grid(row=0, column=1, sticky='ns')

        # 配置框架内的网格权重
        self.download_frame.grid_rowconfigure(0, weight=1)
        self.download_frame.grid_columnconfigure(0, weight=1)

        # 添加到下载按钮 (放在 search_frame 内部或外部均可，这里暂放外部)
        self.add_to_download_button = tk.Button(self.root, text="添加到下载列表", command=self.add_selected_to_download)

        self.download_button = tk.Button(self.root, text="开始下载", command=self.start_download)

        # 设置按钮
        self.settings_button = tk.Button(self.root, text="设置", command=self.open_settings_window)

        # --- 布局 ---
        # 配置根窗口的网格布局
        self.root.columnconfigure(0, weight=1) # 列权重调整为均等或按需调整
        self.root.columnconfigure(1, weight=0) # 第二列（按钮）不扩展
        # 配置行的权重，让表格区域获得垂直扩展空间
        self.root.rowconfigure(3, weight=1) # 搜索结果表格行 (新)
        self.root.rowconfigure(4, weight=1) # 下载列表表格行 (新)

        # 第 0 行: 状态标签 (移除设置按钮布局)
        self.status_label.grid(row=0, column=0, columnspan=2, sticky=tk.W, padx=10, pady=(10, 5)) # 恢复 columnspan

        # 第 1 行: 搜索关键词标签
        self.keyword_label.grid(row=1, column=0, columnspan=2, sticky=tk.W, padx=10, pady=(5, 0))

        # 第 2 行: 搜索关键词输入框, 搜索按钮, 添加按钮, 下载按钮, 设置按钮
        self.keyword_entry.grid(row=2, column=0, sticky=tk.EW, padx=(10, 5), pady=5)
        self.search_button.grid(row=2, column=1, sticky=tk.W, padx=(0, 5), pady=5)
        self.add_to_download_button.grid(row=2, column=2, sticky=tk.W, padx=(0, 5), pady=5) # 插入添加按钮
        self.download_button.grid(row=2, column=3, sticky=tk.W, padx=(0, 5), pady=5) # 下载按钮移到 col 3
        self.settings_button.grid(row=2, column=4, sticky=tk.W, padx=(0, 10), pady=5) # 设置按钮移到 col 4

        # --- 主窗口列配置调整 ---
        # --- 主窗口列配置调整 (增加一列) ---
        self.root.columnconfigure(0, weight=1) # keyword_entry
        self.root.columnconfigure(1, weight=0) # search_button
        self.root.columnconfigure(2, weight=0) # add_to_download_button
        self.root.columnconfigure(3, weight=0) # download_button
        self.root.columnconfigure(4, weight=0) # settings_button

        # 第 3 行: 搜索结果框架
        self.search_frame.grid(row=3, column=0, columnspan=5, sticky='nsew', padx=10, pady=5) # columnspan 调整为 5

        # 第 4 行: 下载列表框架
        self.download_frame.grid(row=4, column=0, columnspan=5, sticky='nsew', padx=10, pady=5) # columnspan 调整为 5

        # 第 5 行: (空置)

        # 第 6 行: (空置，稍后放置选择路径按钮)

        # 第 7 行: 保存路径输入框 (标签已移除)
        self.path_entry.grid(row=7, column=0, columnspan=5, sticky=tk.EW, padx=10, pady=5) # columnspan 调整为 5


        # 第 6 行: 选择下载路径按钮
        self.path_button.grid(row=6, column=0, sticky=tk.W, padx=(10, 5), pady=(5, 5))


        # 第 6 行: 选择下载路径按钮
        self.path_button.grid(row=6, column=0, sticky=tk.W, padx=(10, 5), pady=(5, 5))

        # --- 其他旧布局代码已移除或调整 ---

        # 检查 API Key 并提示 (移到这里，确保 config_manager 已初始化)
        if not self.api_key or self.api_key == 'YOUR_YOUTUBE_DATA_API_KEY_HERE':
             messagebox.showwarning("配置警告", "未在 config.json 中配置有效的 YouTube API Key！\n请在 config.json 文件中填入您的 API Key 以启用搜索功能。")

        self.root.mainloop()

    def save_download_path_to_config(self, *args):
        """回调函数：当下载路径变量变化时，将其保存到配置文件。"""
        new_path = self.path_var.get()
        if new_path:
            parent_dir_exists = os.path.isdir(os.path.dirname(os.path.abspath(new_path)))
            path_is_dir = os.path.isdir(os.path.abspath(new_path))
            if parent_dir_exists or path_is_dir:
                 abs_path = os.path.abspath(new_path)
                 print(f"路径有效，尝试保存到配置: {abs_path}")
                 self.config_manager.update_config('default_download_path', abs_path)
            else:
                 print(f"尝试保存的路径 '{new_path}' 的父目录不存在，未更新配置。")

    def select_path(self):
        """打开文件夹选择对话框"""
        folder = filedialog.askdirectory()
        if folder:
            self.path_var.set(folder)

    def progress_hook(self, d):
        """下载进度回调函数，用于更新 download_tree 中的状态。"""
        video_id = d.get('info_dict', {}).get('id')
        if not video_id:
             # 回退逻辑: 更新主状态栏
             status_text = "状态: 未知视频下载中..."
             if d['status'] == 'downloading':
                 status_text = f"状态: 下载中... {d.get('_percent_str', '0%')}"
             elif d['status'] == 'finished':
                 status_text = "状态: 一个文件下载完成，处理中..."
             elif d['status'] == 'error':
                 status_text = "状态: 下载出错 (未知视频)"
             self.root.after(0, lambda: self.status_label.config(text=status_text))
             self.root.after(0, lambda: self.root.update_idletasks())
             return

        # --- 在主线程中更新 Treeview ---
        def update_treeview_progress():
            try:
                if not self.download_tree.exists(video_id):
                    return # 项可能已被移除

                status = d['status']
                if status == 'downloading':
                    total_bytes_str = d.get('_total_bytes_str') # 使用格式化好的字符串
                    downloaded_bytes = d.get('downloaded_bytes')
                    speed_str = d.get('_speed_str', 'N/A')
                    eta_str = d.get('_eta_str', 'N/A')
                    percent_str = d.get('_percent_str', '0%')
                    filename = d.get('filename', '未知文件')
                    base_filename = os.path.basename(filename)

                    size_str = total_bytes_str if total_bytes_str else d.get('_downloaded_bytes_str', '未知')

                    self.download_tree.set(video_id, column='filename', value=base_filename)
                    self.download_tree.set(video_id, column='size', value=size_str)
                    self.download_tree.set(video_id, column='status', value=f"下载中 {percent_str.strip()}")
                    self.download_tree.set(video_id, column='eta', value=eta_str)
                    self.download_tree.set(video_id, column='speed', value=speed_str)
                    self.download_tree.set(video_id, column='description', value='') # 清除旧信息

                elif status == 'finished':
                    filename = d.get('filename', '未知文件')
                    base_filename = os.path.basename(filename)
                    total_bytes_str = d.get('_total_bytes_str', '未知') # 获取最终大小

                    self.download_tree.set(video_id, column='filename', value=base_filename)
                    self.download_tree.set(video_id, column='size', value=total_bytes_str)
                    self.download_tree.set(video_id, column='status', value="下载完成")
                    self.download_tree.set(video_id, column='eta', value='0s')
                    self.download_tree.set(video_id, column='speed', value='')
                    # 检查是否需要后处理 (例如合并音视频)
                    postprocessor = d.get('postprocessor')
                    description = '合并/转换中...' if postprocessor else '完成'
                    self.download_tree.set(video_id, column='description', value=description)

                elif status == 'error':
                    error_msg = d.get('error', '下载过程中发生错误') # yt-dlp hook 可能不提供 error 字段
                    # 尝试从日志或 yt-dlp 的输出中获取更详细信息可能更好，但这里简化
                    self.download_tree.set(video_id, column='status', value="下载出错")
                    self.download_tree.set(video_id, column='description', value=str(error_msg)[:100]) # 显示错误摘要

            except Exception as e:
                print(f"更新 Treeview 进度时出错 (vid={video_id}, status={d.get('status')}): {e}")

        self.root.after(0, update_treeview_progress)

    def download_videos_from_tree(self, video_ids, output_path):
        """从下载列表 (Treeview) 下载指定的视频。"""
        ydl_opts = {
            'outtmpl': os.path.join(output_path, '%(title)s [%(id)s].%(ext)s'),
            'progress_hooks': [self.progress_hook], # progress_hook 稍后修改
            'quiet': False,
            'noplaylist': True,
            'encoding': 'utf-8',
            'nocheckcertificate': True,
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            # 'ffmpeg_location': '/path/to/ffmpeg',
            'ignoreerrors': True, # 忽略单个视频错误，继续下载
        }

        download_success_count = 0
        download_error_count = 0
        total_videos = len(video_ids)

        for i, video_id in enumerate(video_ids):
            # --- 在主线程更新 Treeview 状态 ---
            def update_treeview_status(vid, status_text, description=""):
                 # 使用 try-except 包装 Treeview 操作，增加健壮性
                 try:
                     if self.download_tree.exists(vid):
                         self.download_tree.set(vid, column='status', value=status_text)
                         self.download_tree.set(vid, column='description', value=description)
                     else:
                         print(f"警告: 尝试更新不存在的项: {vid}")
                 except Exception as tk_e:
                     print(f"更新 Treeview 时出错 (vid={vid}): {tk_e}")

            self.root.after(0, update_treeview_status, video_id, "准备下载")
            self.root.after(0, lambda: self.status_label.config(text=f"状态: 准备下载 {i+1}/{total_videos}"))
            self.root.after(0, lambda: self.root.update_idletasks())

            url = f"https://www.youtube.com/watch?v={video_id}"
            download_successful = False # 标记当前视频是否成功

            try:
                # 清除旧的进度信息
                self.current_download_info = {'id': video_id} # 传递 video_id 给 progress_hook

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    # download 调用本身可能会被 ignoreerrors 捕获错误，我们需要通过 hook 判断
                    result = ydl.download([url])
                    # result 为 0 表示成功, 非 0 表示失败 (但 ignoreerrors 可能使其总是返回 0)
                    # 所以主要依赖 progress_hook 更新状态
            except Exception as e: # 捕捉 yt-dlp 初始化等错误
                download_error_count += 1
                error_msg = str(e)
                print(f"下载视频 {url} 时发生严重错误: {error_msg}")
                self.root.after(0, update_treeview_status, video_id, "下载出错", error_msg[:100])
                continue # 继续下一个视频

            # 检查 progress_hook 设置的最终状态
            final_status = ""
            try:
                if self.download_tree.exists(video_id):
                    final_status = self.download_tree.set(video_id, column='status')
            except Exception as tk_e:
                print(f"获取最终状态时出错 (vid={video_id}): {tk_e}")

            if final_status == "下载完成":
                download_success_count += 1
            elif final_status != "下载出错": # 如果不是明确的出错，但也不是完成，则标记可能出错
                download_error_count += 1
                self.root.after(0, update_treeview_status, video_id, "完成(可能出错)", "检查文件")
            else: # 如果状态已经是 "下载出错"
                 download_error_count += 1


        # 所有视频尝试下载完成后更新状态和弹窗
        def show_final_status():
            final_message = f"全部任务完成！成功: {download_success_count}, 失败/出错: {download_error_count}"
            self.status_label.config(text=f"状态: {final_message}")
            if download_error_count > 0:
                 messagebox.showwarning("下载完成", final_message + "\n部分视频下载失败或可能出错，请检查。")
            else:
                 messagebox.showinfo("成功", final_message)
            # 重新启用按钮
            self.download_button.config(state=tk.NORMAL)
            self.search_button.config(state=tk.NORMAL)
            self.add_to_download_button.config(state=tk.NORMAL)
        self.root.after(0, show_final_status)

    def start_download(self):
        """从下载列表获取任务，并在新线程中启动下载过程"""
        output_path = self.path_var.get()
        if not output_path:
            messagebox.showwarning("警告", "请选择保存路径！")
            return

        # 获取下载列表中所有项的 iid (视频 ID)
        all_item_iids = self.download_tree.get_children()
        if not all_item_iids:
             messagebox.showinfo("提示", "下载列表为空。")
             return

        # 筛选出状态为“待下载”或“下载出错”的项准备下载
        video_ids_to_download = []
        for item_iid in all_item_iids:
             item_values = self.download_tree.item(item_iid, 'values')
             # 检查状态列 (假设是第 4 列，索引为 3)
             if item_values and len(item_values) > 3 and item_values[3] in ('待下载', '下载出错'):
                 video_ids_to_download.append(item_iid)

        if not video_ids_to_download:
             messagebox.showinfo("提示", "没有待下载或下载失败的任务。")
             return

        # 禁用按钮
        self.download_button.config(state=tk.DISABLED)
        self.search_button.config(state=tk.DISABLED)
        self.add_to_download_button.config(state=tk.DISABLED) # 禁用添加按钮
        self.status_label.config(text="状态: 开始准备下载...")
        self.root.update_idletasks()

        # 将视频 ID 列表传递给下载线程
        download_thread = Thread(target=self.download_videos_from_tree, args=(video_ids_to_download, output_path))
        download_thread.daemon = True
        download_thread.start()

    def handle_search(self):
         """处理搜索按钮点击事件"""
         query = self.keyword_entry.get().strip()
         if not query:
             messagebox.showwarning("搜索", "请输入搜索关键词！")
             return
         if not self.api_key or self.api_key == 'YOUR_YOUTUBE_DATA_API_KEY_HERE':
             messagebox.showerror("API Key 错误", "无效或未配置 YouTube API Key。\n请在 config.json 中配置后重试。")
             return
         self.status_label.config(text="状态: 正在搜索...")
         self.search_button.config(state=tk.DISABLED)
         self.download_button.config(state=tk.DISABLED)
         self.root.update_idletasks()

         def search_task():
             video_ids = self.search_videos(query)
             self.root.after(0, update_search_results, video_ids)

         def update_search_results(videos_info): # 参数改为接收详细信息列表
             # 清空旧的搜索结果
             for i in self.search_tree.get_children():
                 self.search_tree.delete(i)

             # 重新启用按钮
             self.search_button.config(state=tk.NORMAL)
             self.download_button.config(state=tk.NORMAL)

             if videos_info is None: # 检查是否出错
                 self.status_label.config(text="状态: 搜索出错")
                 # 错误弹窗已在 search_videos 中处理
                 return

             if videos_info:
                 # 填充搜索结果表格
                 for video in videos_info:
                     # 按照 search_tree 定义的列顺序插入值
                     self.search_tree.insert('', tk.END, values=(
                         video.get('name', ''),
                         video.get('views', '0'),
                         video.get('likes', '0'),
                         video.get('favorites', 'N/A'),
                         video.get('comments', '0'),
                         video.get('published', ''),
                         video.get('duration', '')
                     ), iid=video.get('id')) # 使用视频 ID 作为 item ID (iid)

                 self.status_label.config(text=f"状态: 找到 {len(videos_info)} 个视频")
             else: # API调用成功但未找到视频
                 self.status_label.config(text="状态: 未找到相关视频")
                 messagebox.showinfo("搜索结果", "未找到与关键词匹配的视频。")

         search_thread = Thread(target=search_task) # search_task 内部调用 search_videos
         search_thread.daemon = True
         search_thread.start()

    def search_videos(self, query):
        """
        使用 YouTube Data API 搜索视频并获取详细信息。

        参数:
            query (str): 搜索关键词。

        返回:
            list: 包含视频详细信息字典的列表，每个字典包含表格所需的字段。
                  出错则返回 None。
        """
        import isodate # 导入 isodate 用于解析时长
        from datetime import timedelta

        def format_duration(duration_str):
            """将 ISO 8601 时长字符串转换为 HH:MM:SS 或 MM:SS 格式。"""
            try:
                duration = isodate.parse_duration(duration_str)
                total_seconds = int(duration.total_seconds())
                hours, remainder = divmod(total_seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                if hours > 0:
                    return f"{hours:02}:{minutes:02}:{seconds:02}"
                else:
                    return f"{minutes:02}:{seconds:02}"
            except Exception:
                return "未知"

        def format_large_number(num_str):
             """格式化数字，如果太大则显示 K, M, B"""
             try:
                 num = int(num_str)
                 if num >= 1_000_000_000:
                     return f"{num / 1_000_000_000:.1f}B"
                 if num >= 1_000_000:
                     return f"{num / 1_000_000:.1f}M"
                 if num >= 1000:
                     return f"{num / 1000:.1f}K"
                 return str(num)
             except (ValueError, TypeError):
                 return num_str if num_str else "0"

        try:
            youtube = build('youtube', 'v3', developerKey=self.api_key)

            search_request = youtube.search().list(
                part='snippet',
                q=query,
                type='video',
                maxResults=50
            )
            search_response = search_request.execute()
            search_items = search_response.get('items', [])

            video_details = {}
            video_ids = []
            for item in search_items:
                 if isinstance(item, dict) and 'id' in item and isinstance(item['id'], dict) and 'videoId' in item['id']:
                     video_id = item['id']['videoId']
                     video_ids.append(video_id)
                     video_details[video_id] = item.get('snippet', {})
                 else:
                     print(f"警告: 发现无效的搜索结果项: {item}")

            if not video_ids:
                 return []

            detailed_videos_info = []
            batch_size = 50
            for i in range(0, len(video_ids), batch_size):
                 batch_ids = video_ids[i:i + batch_size]
                 ids_str = ','.join(batch_ids)

                 video_request = youtube.videos().list(
                     part='snippet,statistics,contentDetails',
                     id=ids_str
                 )
                 video_response = video_request.execute()
                 video_items = video_response.get('items', [])

                 for video_item in video_items:
                     vid = video_item.get('id')
                     if not vid: continue

                     snippet = video_item.get('snippet', {})
                     stats = video_item.get('statistics', {})
                     content = video_item.get('contentDetails', {})
                     search_snippet = video_details.get(vid, {})

                     title = snippet.get('title', '无标题')
                     published_at_search = search_snippet.get('publishedAt', '')
                     published_at_video = snippet.get('publishedAt', '')
                     published_display = published_at_search[:10] if published_at_search else (published_at_video[:10] if published_at_video else '未知')

                     view_count = format_large_number(stats.get('viewCount'))
                     like_count = format_large_number(stats.get('likeCount'))
                     favorite_count = 'N/A' # API 不直接提供
                     comment_count = format_large_number(stats.get('commentCount', '0')) # 评论可能被禁用，默认为0
                     duration = format_duration(content.get('duration'))

                     detailed_videos_info.append({
                         'id': vid,
                         'name': title,
                         'views': view_count,
                         'likes': like_count,
                         'favorites': favorite_count,
                         'comments': comment_count,
                         'published': published_display,
                         'duration': duration
                     })

            return detailed_videos_info

        except Exception as e:
            print(f"调用 YouTube API 时出错: {e}")
            error_message = f"搜索视频时发生错误: {e}"
            if "quotaExceeded" in str(e):
                 error_message = "YouTube API 配额已用尽。请稍后重试或检查您的配额限制。"
            elif "invalidKey" in str(e):
                 error_message = "无效的 YouTube API Key。请检查 config.json 中的配置。"
            elif "accessNotConfigured" in str(e) or "forbidden" in str(e).lower():
                 error_message = "YouTube API 未启用或无权访问。请检查 Google Cloud 项目设置。"
            self.root.after(0, lambda: messagebox.showerror("API 错误", error_message))
            return None

    # 正确缩进 open_settings_window 方法定义
    def open_settings_window(self):
        """打开设置窗口。"""
        settings_window = tk.Toplevel(self.root)
        settings_window.title("设置")
        settings_window.geometry("450x200")
        settings_window.transient(self.root)
        settings_window.grab_set()

        placeholder_api_key = "你的API key"
        placeholder_path = "软件根目录download文件夹"
        placeholder_color = 'grey'
        try:
            default_fg_color = settings_window.cget('fg')
        except tk.TclError: # 处理可能的 TclError (例如在某些系统上默认值无法获取)
            default_fg_color = 'black' # 使用标准黑色作为回退

        api_key_var = tk.StringVar()
        download_path_var = tk.StringVar()

        tk.Label(settings_window, text="YouTube API Key:").grid(row=0, column=0, padx=10, pady=10, sticky=tk.W)
        api_key_entry = tk.Entry(settings_window, textvariable=api_key_var, width=40)
        api_key_entry.grid(row=0, column=1, padx=10, pady=10, sticky=tk.EW)

        tk.Label(settings_window, text="默认下载地址:").grid(row=1, column=0, padx=10, pady=5, sticky=tk.W)
        download_path_entry = tk.Entry(settings_window, textvariable=download_path_var, width=40)
        download_path_entry.grid(row=1, column=1, padx=(10, 5), pady=5, sticky=tk.EW)
        select_path_button = tk.Button(settings_window, text="...", command=lambda: self.select_default_download_path(download_path_var, settings_window))
        select_path_button.grid(row=1, column=2, padx=(0, 10), pady=5, sticky=tk.W)

        button_frame_settings = tk.Frame(settings_window)
        button_frame_settings.grid(row=2, column=0, columnspan=3, pady=15)

        save_button = tk.Button(button_frame_settings, text="保存", command=lambda: self.save_settings(api_key_var.get(), download_path_var.get(), settings_window, placeholder_api_key, placeholder_path))
        save_button.pack(side=tk.LEFT, padx=10)
        cancel_button = tk.Button(button_frame_settings, text="取消", command=settings_window.destroy)
        cancel_button.pack(side=tk.LEFT, padx=10)

        def setup_placeholder_logic(entry, var, placeholder_text):
            def on_focus_in(event):
                if var.get() == placeholder_text:
                    var.set('')
                    entry.config(fg=default_fg_color)
            def on_focus_out(event):
                if not var.get():
                    var.set(placeholder_text)
                    entry.config(fg=placeholder_color)
            # --- 这两行 bind 调用属于 setup_placeholder_logic 函数 ---
            entry.bind("<FocusIn>", on_focus_in)
            entry.bind("<FocusOut>", on_focus_out)

        # --- 窗口居中逻辑 ---
        settings_window.update_idletasks() # 更新窗口信息以获取尺寸
        width = 450 # 设置窗口宽度
        height = 200 # 设置窗口高度
        # 获取主窗口位置和尺寸
        main_x = self.root.winfo_x()
        main_y = self.root.winfo_y()
        main_width = self.root.winfo_width()
        main_height = self.root.winfo_height()
        # 计算设置窗口居中后的左上角坐标
        x = main_x + (main_width // 2) - (width // 2)
        y = main_y + (main_height // 2) - (height // 2)
        # 设置窗口几何尺寸和位置
        settings_window.geometry(f'{width}x{height}+{x}+{y}')

        # --- 错误放置的代码已移除 ---

        current_api_key = self.config_manager.get_config('api_key')
        current_path = self.config_manager.get_config('default_download_path')

        if current_api_key and current_api_key != 'YOUR_YOUTUBE_DATA_API_KEY_HERE':
            api_key_var.set(current_api_key)
            api_key_entry.config(fg=default_fg_color)
        else:
            api_key_var.set(placeholder_api_key)
            api_key_entry.config(fg=placeholder_color)

        if current_path:
            download_path_var.set(current_path)
            download_path_entry.config(fg=default_fg_color)
        else:
            download_path_var.set(placeholder_path)
            download_path_entry.config(fg=placeholder_color)

        setup_placeholder_logic(api_key_entry, api_key_var, placeholder_api_key)
        setup_placeholder_logic(download_path_entry, download_path_var, placeholder_path)

        settings_window.columnconfigure(1, weight=1)

    def save_settings(self, api_key, download_path, window, placeholder_api, placeholder_pth):
        """保存设置到配置文件。"""
        updates = {}
        final_api_key = api_key if api_key != placeholder_api else ''
        final_download_path = os.path.abspath(download_path) if download_path and download_path != placeholder_pth else ''
        updates['api_key'] = final_api_key
        updates['default_download_path'] = final_download_path
        self.config_manager.update_multiple_configs(updates)
        messagebox.showinfo("设置", "设置已保存。", parent=window)
        self.api_key = final_api_key
        current_main_path = self.path_var.get()
        new_default_path = final_download_path if final_download_path else self.get_fallback_download_path()
        temp_config = self.config_manager.config.copy()
        # 需要获取保存 *前* 的配置值来判断是否是旧默认路径
        # 由于 config_manager 在 update_multiple_configs 中已经保存, 这里需要模拟获取旧值
        # 一个简单的模拟: 如果 updates 中有 'default_download_path', 则旧值可能是空的或者某个路径
        # 这里简化逻辑: 如果主路径是 fallback_path 并且新默认路径不是 fallback_path, 则更新
        # 或者如果主路径不是 fallback_path, 但它等于旧的配置值(这个难以精确获取), 也更新
        # 简化: 仅当新默认路径非空时,才考虑更新主路径
        if final_download_path:
            # 如果主窗口路径是fallback路径，直接更新
            if current_main_path == self.get_fallback_download_path():
                 self.path_var.set(new_default_path)
                 print(f"主界面下载路径已更新为新的默认值: {new_default_path}")
            # else: # 如果主窗口不是fallback, 不主动改变用户可能已手动选择的路径
            #    pass
        else: # 如果新默认路径为空
             # 如果主窗口路径不是fallback路径（说明之前可能设置过默认或手动选过），则设置回fallback
             if current_main_path != self.get_fallback_download_path():
                 self.path_var.set(self.get_fallback_download_path())
                 print(f"默认下载路径已清空，主界面下载路径已更新为回退值: {self.get_fallback_download_path()}")

        window.destroy()

    def select_default_download_path(self, path_var, parent_window):
        """为设置窗口中的下载路径选择文件夹。"""
        folder = filedialog.askdirectory(parent=parent_window)
        if folder:
            abs_path = os.path.abspath(folder)
            path_var.set(abs_path)
            # 手动触发 focus out 以移除占位符颜色（如果存在）
            parent_window.focus() # 让输入框失去焦点, 使 on_focus_out 生效

    def add_selected_to_download(self):
        """将搜索结果中选中的项添加到下载列表。"""
        selected_item_iids = self.search_tree.selection() # 获取选中项的 iid 列表 (也就是视频 ID)
        if not selected_item_iids:
             messagebox.showinfo("提示", "请先在搜索结果中选择要添加的视频。")
             return

        added_count = 0
        skipped_count = 0
        # 获取当前下载列表已有的视频 ID，避免重复添加
        existing_download_iids = set(self.download_tree.get_children())

        for video_id in selected_item_iids:
            if video_id in existing_download_iids:
                 print(f"视频 {video_id} 已在下载列表中，跳过。")
                 skipped_count += 1
                 continue

            # 从 search_tree 获取选中行的数据
            search_values = self.search_tree.item(video_id, 'values')
            if not search_values or len(search_values) < 7: # 检查数据是否有效
                print(f"警告: 无法获取视频 {video_id} 的完整数据，跳过。")
                skipped_count += 1
                continue

            # 从搜索结果数据构造下载列表所需的数据
            # ('select', 'filename', 'size', 'status', 'eta', 'speed', 'last_connected', 'description')
            video_title = search_values[0] # 获取标题
            download_values = (
                '☐',          # 选择框占位符 (后续实现)
                video_title,  # 文件名用视频标题代替
                '未知',       # 大小未知
                '待下载',     # 初始状态
                '',           # ETA
                '',           # Speed
                '',           # Last Connected
                ''            # Description
            )

            # 将数据插入到 download_tree，使用 video_id 作为 iid
            try:
                 self.download_tree.insert('', tk.END, iid=video_id, values=download_values)
                 added_count += 1
            except tk.TclError as e: # 处理可能的 iid 重复错误 (理论上不应发生，因为前面检查了)
                 print(f"添加到下载列表时出错 (视频ID: {video_id}): {e}")
                 skipped_count += 1

        status_message = f"添加完成：{added_count} 个视频已添加到下载列表。"
        if skipped_count > 0:
            status_message += f" {skipped_count} 个已存在或无效，已跳过。"
        self.status_label.config(text=f"状态: {status_message}")
        # 可以选择性地取消搜索结果的选择
        # self.search_tree.selection_remove(selected_item_iids)


    def get_fallback_download_path(self):
         """获取回退的默认下载路径（脚本目录下的 download）。"""
         script_dir = os.path.dirname(os.path.abspath(__file__))
         return os.path.join(script_dir, "download")

if __name__ == "__main__":
    Sucoidownload()

# --- 已移除错误位置的代码 ---