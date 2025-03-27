import yt_dlp
import tkinter as tk
from tkinter import filedialog, messagebox
import os
from threading import Thread

class Sucoidownload:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Sucoidownload - 视频批量下载器") # 修改标题
        self.root.geometry("600x400")

        # 配置根窗口的网格布局
        self.root.columnconfigure(0, weight=1) # 让第一列填充可用空间
        self.root.columnconfigure(1, weight=1) # 让第二列填充可用空间 (用于按钮居中等)

        # --- 组件定义 ---

        # 状态显示 (移到最上方)
        self.status_label = tk.Label(self.root, text="状态: 就绪")

        # URL 输入框
        self.url_label = tk.Label(self.root, text="请输入视频 URL（每行一个）:") # 修改标签文本
        self.url_text = tk.Text(self.root, height=10, width=50) # width 参数在 grid 下效果有限

        # 保存路径选择
        self.path_label = tk.Label(self.root, text="保存路径:")
        script_dir = os.path.dirname(os.path.abspath(__file__))
        default_download_path = os.path.join(script_dir, "download")
        os.makedirs(default_download_path, exist_ok=True)
        self.path_var = tk.StringVar(value=default_download_path)
        self.path_entry = tk.Entry(self.root, textvariable=self.path_var) # 移除 width，让 grid 控制
        self.path_button = tk.Button(self.root, text="选择路径", command=self.select_path)

        # 下载按钮
        self.download_button = tk.Button(self.root, text="开始下载", command=self.start_download)

        # --- 使用 grid 布局 ---

        # 第 0 行: 状态标签
        self.status_label.grid(row=0, column=0, columnspan=2, sticky=tk.W, padx=10, pady=(10, 5)) # W = West (左对齐)

        # 第 1 行: URL 标签
        self.url_label.grid(row=1, column=0, columnspan=2, sticky=tk.W, padx=10, pady=(5, 0))

        # 第 2 行: URL 输入框
        self.url_text.grid(row=2, column=0, columnspan=2, sticky=tk.EW, padx=10, pady=5) # EW = East+West (水平填充)

        # 第 3 行: 保存路径标签
        self.path_label.grid(row=3, column=0, columnspan=2, sticky=tk.W, padx=10, pady=(5, 0))

        # 第 4 行: 保存路径输入框
        self.path_entry.grid(row=4, column=0, columnspan=2, sticky=tk.EW, padx=10, pady=5)

        # 第 5 行: 按钮 Frame (用于水平排列按钮)
        button_frame = tk.Frame(self.root)
        button_frame.grid(row=5, column=0, columnspan=2, pady=10) # 保持 button_frame 本身使用 grid 放置

        # 配置 button_frame 内部的网格布局 (让两列权重相等，按钮会居中排列)
        button_frame.columnconfigure(0, weight=1)
        button_frame.columnconfigure(1, weight=1)

        # 在 Frame 内使用 grid 排列按钮
        self.path_button.grid(row=0, column=0, padx=5, sticky=tk.E) # E = East (右对齐，靠近中间)
        self.download_button.grid(row=0, column=1, padx=5, sticky=tk.W) # W = West (左对齐，靠近中间)


        self.root.mainloop()

    def select_path(self):
        """打开文件夹选择对话框"""
        folder = filedialog.askdirectory()
        if folder: # 如果用户选择了文件夹
            self.path_var.set(folder)

    def progress_hook(self, d):
        """下载进度回调函数，用于更新状态标签"""
        if d['status'] == 'downloading':
            # 获取下载百分比字符串，如果不存在则默认为 '0%'
            percent = d.get('_percent_str', '0%')
            # 更新状态标签显示下载进度
            self.status_label.config(text=f"状态: 下载中... {percent}")
        elif d['status'] == 'finished':
            # 下载完成，更新状态标签
            self.status_label.config(text="状态: 下载完成，正在处理...")
        elif d['status'] == 'error':
            # 下载出错，更新状态标签
            self.status_label.config(text="状态: 下载出错")

    def download_videos(self, urls, output_path):
        """
        使用 yt-dlp 下载指定 URL 列表中的视频。

        参数:
            urls (list): 包含视频 URL 的列表。
            output_path (str): 视频保存的目录路径。
        """
        # yt-dlp 配置选项
        ydl_opts = {
            # 输出文件名模板，包含标题和扩展名
            'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
            # 让 yt-dlp 自动选择最佳格式 (移除 format 和 postprocessors)
            'progress_hooks': [self.progress_hook],  # 注册进度回调函数
            # 'proxy': 'http://your_proxy:port',  # 可选：代理设置，需要替换为你的代理服务器地址和端口
            'quiet': False,  # 不静默模式，输出日志信息
            'noplaylist': True,  # 如果 URL 是播放列表，只下载单个视频
            'encoding': 'utf-8', # 确保文件名等使用UTF-8编码
        }

        try:
            # 创建 YoutubeDL 实例并执行下载
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download(urls)
            # 所有视频下载完成后更新状态
            self.status_label.config(text="状态: 所有视频下载完成！")
            # 显示成功信息弹窗
            messagebox.showinfo("成功", "所有视频下载完成！")
        except Exception as e:
            # 下载过程中发生异常，更新状态并显示错误信息弹窗
            self.status_label.config(text=f"状态: 错误 - {str(e)}")
            messagebox.showerror("错误", f"下载失败: {str(e)}")

    def start_download(self):
        """从 GUI 获取输入，并在新线程中启动下载过程"""
        # 从文本框获取 URL 列表，去除首尾空白并按行分割
        urls = self.url_text.get("1.0", tk.END).strip().splitlines()
        # 获取用户选择的保存路径
        output_path = self.path_var.get()

        # 检查 URL 列表是否为空
        if not urls or not any(url.strip() for url in urls):
            messagebox.showwarning("警告", "请至少输入一个有效的视频 URL！")
            return
        # 检查保存路径是否已选择
        if not output_path:
            messagebox.showwarning("警告", "请选择保存路径！")
            return

        # 更新状态标签，表示下载已开始
        self.status_label.config(text="状态: 开始下载...")
        # 创建并启动一个新线程来执行下载任务，避免阻塞 GUI
        download_thread = Thread(target=self.download_videos, args=(urls, output_path))
        download_thread.daemon = True # 设置为守护线程，主程序退出时强制结束
        download_thread.start()

if __name__ == "__main__":
    # 创建 Sucoidownload 应用实例并运行
    Sucoidownload()