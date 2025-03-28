# tiktok.py - TikTok Platform Specific Logic
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import yt_dlp # 需要导入 yt_dlp
import os
from threading import Thread

def create_tab(notebook, main_app_instance):
    """创建并返回 TikTok 标签页的 Frame。"""
    tiktok_frame = ttk.Frame(notebook, padding="10")

    # --- TikTok 控件定义 ---
    url_label = tk.Label(tiktok_frame, text="输入 TikTok 视频 URL (每行一个):")
    url_text = tk.Text(tiktok_frame, height=10, width=50) # 允许多个 URL

    # 使用 Frame 来容纳按钮
    button_frame = tk.Frame(tiktok_frame)
    # TODO: 按钮功能需要连接到主程序的通用下载队列或模块内部逻辑
    add_button = tk.Button(button_frame, text="添加到下载队列", command=lambda: add_tiktok_urls(url_text, main_app_instance))
    download_now_button = tk.Button(button_frame, text="立即下载选中项", command=lambda: download_tiktok_urls(url_text, main_app_instance))

    # --- TikTok 布局 ---
    url_label.grid(row=0, column=0, sticky=tk.W, padx=(0, 10), pady=5)
    url_text.grid(row=1, column=0, sticky="nsew", padx=(0, 10), pady=5)

    button_frame.grid(row=2, column=0, pady=10, sticky="ew")
    # 让按钮在 Frame 内分布
    button_frame.columnconfigure(0, weight=1)
    button_frame.columnconfigure(1, weight=1)
    add_button.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
    download_now_button.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

    # 配置 TikTok Frame 的网格权重
    tiktok_frame.rowconfigure(1, weight=1) # 让 Text 控件可垂直扩展
    tiktok_frame.columnconfigure(0, weight=1) # 让 Text 控件可水平扩展

    return tiktok_frame

def add_tiktok_urls(url_text_widget, app):
    """将 TikTok URL 添加到主程序的下载队列 (占位)。"""
    urls = url_text_widget.get("1.0", tk.END).strip().splitlines()
    urls = [url for url in urls if url.strip()] # 过滤空行

    if not urls:
        messagebox.showwarning("提示", "请输入 TikTok 视频 URL。")
        return

    print(f"准备添加 {len(urls)} 个 TikTok URL 到下载队列 (功能待实现)")
    # TODO: 调用 app (主程序实例) 的方法将 urls 添加到通用下载队列 (download_tree)
    # 例如: app.add_urls_to_download_queue(urls, platform='TikTok')
    messagebox.showinfo("提示", f"已获取 {len(urls)} 个 URL，添加到队列功能待实现。")

def download_tiktok_urls(url_text_widget, app):
    """直接下载输入的 TikTok URLs (简化版，不经过队列)。"""
    urls = url_text_widget.get("1.0", tk.END).strip().splitlines()
    urls = [url for url in urls if url.strip()] # 过滤空行

    if not urls:
        messagebox.showwarning("提示", "请输入 TikTok 视频 URL。")
        return

    output_path = app.path_var.get() # 从主程序获取保存路径
    if not output_path:
        messagebox.showwarning("警告", "请先在主界面底部选择保存路径！")
        return

    # 在新线程中执行下载
    download_thread = Thread(target=_perform_tiktok_download, args=(urls, output_path, app))
    download_thread.daemon = True
    download_thread.start()

def _perform_tiktok_download(urls, output_path, app):
    """执行 TikTok 视频下载的后台函数。"""
    # 更新主程序状态 (示例)
    app.status_label.config(text=f"状态: 开始下载 {len(urls)} 个 TikTok 视频...")

    # yt-dlp 配置 (可根据 TikTok 特点调整)
    ydl_opts = {
        # 使用标题作为文件名 (参考旧代码)
        'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
        'quiet': False,
        'noplaylist': True, # 确保只下载单个视频
        'encoding': 'utf-8',
        'nocheckcertificate': True,
        # TikTok 可能不需要特定格式
        # 'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'ignoreerrors': True,
        # 可选: 添加 progress_hooks 并通过回调更新 GUI (如果需要显示进度)
        # 'progress_hooks': [lambda d: app.update_download_progress(d)],
    }

    success_count = 0
    error_count = 0

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # 尝试下载所有 URL
            ydl.download(urls)
            # 注意：由于 ignoreerrors=True，即使部分失败，这里也可能不抛异常
            # 更可靠的方法是分析 ydl.extract_info 的返回值或使用 progress hook
            # 简化处理：假设没有异常就是全部成功（可能不准确）
            success_count = len(urls) # 暂定全部成功
            # TODO: 需要更精确的成功/失败计数

    except Exception as e:
        print(f"下载 TikTok 视频时出错: {e}")
        error_count = len(urls) # 暂定全部失败

    # 更新主程序状态和提示 (在主线程中)
    def final_update():
        final_message = f"TikTok 下载完成！尝试: {len(urls)}, 成功: {success_count} (预估), 失败: {error_count} (预估)"
        app.status_label.config(text=f"状态: {final_message}")
        if error_count > 0:
             messagebox.showwarning("TikTok 下载", final_message + "\n部分下载可能失败，请检查输出文件夹。")
        else:
             messagebox.showinfo("TikTok 下载", final_message)

    app.root.after(0, final_update)

# 可选的测试代码
if __name__ == '__main__':
    # 模拟一个 app 对象用于测试
    class MockApp:
        def __init__(self):
            self.path_var = tk.StringVar(value='test_tiktok_download')
            self.root = tk.Tk() # 需要一个 root 来使用 after
            self.status_label = tk.Label(self.root, text="")
            os.makedirs(self.path_var.get(), exist_ok=True)
        def run(self):
            # 模拟下载
            test_urls = ["https://www.tiktok.com/@scout2015/video/6718335390787505413"] # 示例 URL
            _perform_tiktok_download(test_urls, self.path_var.get(), self)
            self.root.mainloop() # 保持运行以查看消息框

    mock_app = MockApp()
    mock_app.run()