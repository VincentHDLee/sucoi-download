# sucoidownload.py
import yt_dlp
import tkinter as tk
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

        # URL 输入框
        self.url_label = tk.Label(self.root, text="视频 URL（每行一个）或搜索结果:") # 修改标签
        self.url_text = tk.Text(self.root, height=10, width=50)

        # 保存路径选择
        self.path_label = tk.Label(self.root, text="保存路径:")
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
        self.path_button = tk.Button(self.root, text="选择路径", command=self.select_path)

        # 下载按钮
        self.download_button = tk.Button(self.root, text="开始下载", command=self.start_download)

        # 设置按钮
        self.settings_button = tk.Button(self.root, text="设置", command=self.open_settings_window)

        # --- 布局 ---
        # 配置根窗口的网格布局
        self.root.columnconfigure(0, weight=3) # 输入框占更多空间
        self.root.columnconfigure(1, weight=1) # 按钮占较少空间
        self.root.rowconfigure(4, weight=1) # 让 URL 输入框可以垂直扩展 (重要)

        # 第 0 行: 状态标签 和 设置按钮
        self.status_label.grid(row=0, column=0, sticky=tk.W, padx=10, pady=(10, 5))
        self.settings_button.grid(row=0, column=1, sticky=tk.E, padx=10, pady=(10, 5))

        # 第 1 行: 搜索关键词标签
        self.keyword_label.grid(row=1, column=0, columnspan=2, sticky=tk.W, padx=10, pady=(5, 0))

        # 第 2 行: 搜索关键词输入框 和 搜索按钮
        self.keyword_entry.grid(row=2, column=0, sticky=tk.EW, padx=(10, 5), pady=5)
        self.search_button.grid(row=2, column=1, sticky=tk.W, padx=(0, 10), pady=5)

        # 第 3 行: URL 标签
        self.url_label.grid(row=3, column=0, columnspan=2, sticky=tk.W, padx=10, pady=(5, 0))

        # 第 4 行: URL 输入框
        self.url_text.grid(row=4, column=0, columnspan=2, sticky=tk.NSEW, padx=10, pady=5) # NSEW 填充

        # 第 5 行: 保存路径标签
        self.path_label.grid(row=5, column=0, columnspan=2, sticky=tk.W, padx=10, pady=(5, 0))

        # 第 6 行: 保存路径输入框
        self.path_entry.grid(row=6, column=0, columnspan=2, sticky=tk.EW, padx=10, pady=5)

        # 第 7 行: 按钮 Frame (用于水平排列按钮)
        button_frame = tk.Frame(self.root)
        button_frame.grid(row=7, column=0, columnspan=2, pady=10)

        # 配置 button_frame 内部的网格布局 (让两列权重相等，按钮会居中排列)
        button_frame.columnconfigure(0, weight=1)
        button_frame.columnconfigure(1, weight=1)

        # 在 Frame 内使用 grid 排列按钮
        self.path_button.grid(row=0, column=0, padx=5, sticky=tk.E)
        self.download_button.grid(row=0, column=1, padx=5, sticky=tk.W)

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
        """下载进度回调函数，用于更新状态标签"""
        if d['status'] == 'downloading':
            percent = d.get('_percent_str', '0%')
            filename = d.get('filename', '未知文件')
            base_filename = os.path.basename(filename)
            max_len = 40
            display_name = base_filename if len(base_filename) <= max_len else base_filename[:max_len-3] + '...'
            self.status_label.config(text=f"状态: 下载中 {display_name}... {percent}")
            self.root.update_idletasks()
        elif d['status'] == 'finished':
            filename = d.get('filename', '未知文件')
            base_filename = os.path.basename(filename)
            max_len = 50
            display_name = base_filename if len(base_filename) <= max_len else base_filename[:max_len-3] + '...'
            self.status_label.config(text=f"状态: {display_name} 下载完成，处理中...")
            self.root.update_idletasks()
        elif d['status'] == 'error':
            self.status_label.config(text="状态: 下载出错")
            self.root.update_idletasks()

    def download_videos(self, urls, output_path):
        """使用 yt-dlp 下载指定 URL 列表中的视频。"""
        ydl_opts = {
            'outtmpl': os.path.join(output_path, '%(title)s [%(id)s].%(ext)s'),
            'progress_hooks': [self.progress_hook],
            'quiet': False,
            'noplaylist': True,
            'encoding': 'utf-8',
            'nocheckcertificate': True,
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            # 'ffmpeg_location': '/path/to/ffmpeg',
        }
        download_success_count = 0
        download_error_count = 0
        total_urls = len(urls)

        for i, url in enumerate(urls):
            def update_status_sync(status_text):
                self.status_label.config(text=status_text)
                self.root.update_idletasks()
            self.root.after(0, update_status_sync, f"状态: 准备下载第 {i+1}/{total_urls} 个视频: {url}")

            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
                download_success_count += 1
            except Exception as e:
                download_error_count += 1
                print(f"下载视频 {url} 时出错: {e}")
                self.root.after(0, update_status_sync, f"状态: 第 {i+1}/{total_urls} 个视频下载出错")

        def show_final_status():
            final_message = f"全部任务完成！成功: {download_success_count}, 失败: {download_error_count}"
            self.status_label.config(text=f"状态: {final_message}")
            if download_error_count > 0:
                 messagebox.showwarning("下载完成", final_message + "\n部分视频下载失败，请检查控制台输出。")
            else:
                 messagebox.showinfo("成功", final_message)
            self.download_button.config(state=tk.NORMAL)
            self.search_button.config(state=tk.NORMAL)
        self.root.after(0, show_final_status)

    def start_download(self):
        """从 GUI 获取输入，并在新线程中启动下载过程"""
        urls = self.url_text.get("1.0", tk.END).strip().splitlines()
        output_path = self.path_var.get()
        urls = [url for url in urls if url.strip()]
        if not urls:
            messagebox.showwarning("警告", "请至少输入一个有效的视频 URL！")
            return
        if not output_path:
            messagebox.showwarning("警告", "请选择保存路径！")
            return
        self.download_button.config(state=tk.DISABLED)
        self.search_button.config(state=tk.DISABLED)
        self.status_label.config(text="状态: 开始下载...")
        self.root.update_idletasks()
        download_thread = Thread(target=self.download_videos, args=(urls, output_path))
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

         def update_search_results(video_ids):
             self.search_button.config(state=tk.NORMAL)
             self.download_button.config(state=tk.NORMAL)
             if video_ids is None:
                 self.status_label.config(text="状态: 搜索出错")
                 return
             if video_ids:
                 video_urls = [f"https://www.youtube.com/watch?v={vid}" for vid in video_ids]
                 self.url_text.delete("1.0", tk.END)
                 self.url_text.insert("1.0", "\n".join(video_urls))
                 self.status_label.config(text=f"状态: 找到 {len(video_ids)} 个视频")
             else:
                 self.status_label.config(text="状态: 未找到相关视频")
                 messagebox.showinfo("搜索结果", "未找到与关键词匹配的视频。")

         search_thread = Thread(target=search_task)
         search_thread.daemon = True
         search_thread.start()

    def search_videos(self, query):
        """使用 YouTube Data API 搜索视频。"""
        try:
            youtube = build('youtube', 'v3', developerKey=self.api_key)
            request = youtube.search().list(
                part='snippet',
                q=query,
                type='video',
                maxResults=50
            )
            response = request.execute()
            items = response.get('items', [])
            if not isinstance(items, list):
                 print(f"警告: API 响应中的 'items' 不是列表: {items}")
                 return None
            video_ids = []
            for item in items:
                 if isinstance(item, dict) and 'id' in item and isinstance(item['id'], dict) and 'videoId' in item['id']:
                     video_ids.append(item['id']['videoId'])
                 else:
                     print(f"警告: 发现无效的搜索结果项: {item}")
            return video_ids
        except Exception as e:
            # 正确缩进 except 块内容
            print(f"调用 YouTube API 时出错: {e}")
            error_message = f"搜索视频时发生错误: {e}"
            if "quotaExceeded" in str(e):
                 error_message = "YouTube API 配额已用尽。请稍后重试或检查您的配额限制。"
            elif "invalidKey" in str(e):
                 error_message = "无效的 YouTube API Key。请检查 config.json 中的配置。"
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
            entry.bind("<FocusIn>", on_focus_in)
            entry.bind("<FocusOut>", on_focus_out)

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

    def get_fallback_download_path(self):
         """获取回退的默认下载路径（脚本目录下的 download）。"""
         script_dir = os.path.dirname(os.path.abspath(__file__))
         return os.path.join(script_dir, "download")

if __name__ == "__main__":
    Sucoidownload()

# --- 已移除错误位置的代码 ---