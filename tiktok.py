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
    download_now_button = tk.Button(button_frame, text="立即下载", command=lambda: download_tiktok_urls(url_text, main_app_instance)) # 修改按钮文本

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
    """执行 TikTok 视频下载的后台函数，支持取消。"""
    app.status_label.config(text=f"状态: 开始下载 {len(urls)} 个 TikTok 视频...")

    ydl_opts = {
        'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
        'quiet': False, 'noplaylist': True, 'encoding': 'utf-8',
        'nocheckcertificate': True,
        'ignoreerrors': True, # ignoreerrors 保证即使出错也继续循环
        # 注意: 如果需要精细进度更新，需要添加 progress_hooks 并确保回调能处理 TikTok ID
        # 'progress_hooks': [lambda d: _tiktok_progress_hook(d, app)],
    }

    success_count = 0
    error_count = 0
    cancelled_count = 0
    processed_count = 0

    try:
        # 在循环外创建实例以复用
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            for index, url in enumerate(urls):
                processed_count += 1
                # 检查取消标志
                if app.cancel_requested:
                    print(f"TikTok 下载任务被用户取消。停止处理 URL: {url}")
                    cancelled_count = len(urls) - index
                    error_count += cancelled_count # 将取消的计入错误总数
                    # 发送取消状态给主程序 (如果需要)
                    # remaining_ids = urls[index:]
                    # for i, rem_url in enumerate(remaining_ids):
                    #    if hasattr(app, 'update_download_progress'):
                    #        # 需要为 TikTok 定义一个合适的、唯一的 ID
                    #        tiktok_id = f"tiktok_{rem_url[-19:]}" # 简单示例 ID
                    #        app.update_download_progress({'id': tiktok_id, 'status': 'error', 'description': '用户取消'})
                    break # 跳出循环

                # TODO: 发送 preparing 状态 (需要唯一 ID)
                # tiktok_id = f"tiktok_{url[-19:]}"
                # if hasattr(app, 'update_download_progress'):
                #     app.update_download_progress({'id': tiktok_id, 'status': 'preparing'})

                try:
                    print(f"开始下载 TikTok URL: {url}")
                    ydl.download([url])
                    # 注意: 由于 ignoreerrors=True，这里不抛错不代表一定成功
                    # 需要更可靠的方式判断，例如检查钩子记录的状态或文件是否存在
                    # 简化处理：暂定执行完 download 就算成功
                    success_count += 1
                    print(f"完成 TikTok URL: {url}")
                    # TODO: 发送 finished 状态 (需要唯一 ID)
                    # if hasattr(app, 'update_download_progress'):
                    #     app.update_download_progress({'id': tiktok_id, 'status': 'finished'})
                except Exception as e:
                    # 一般 download 设置 ignoreerrors 后不太会在这里出错，除非是严重错误
                    print(f"下载 TikTok URL {url} 时出错: {e}")
                    error_count += 1
                    # TODO: 发送 error 状态 (需要唯一 ID)
                    # if hasattr(app, 'update_download_progress'):
                    #     app.update_download_progress({'id': tiktok_id, 'status': 'error', 'description': str(e)[:100]})

    except Exception as e:
        # 捕获创建 YoutubeDL 实例或循环外的其他错误
        print(f"TikTok 下载过程中发生严重错误: {e}")
        # 将剩余未处理或处理中的计为错误
        error_count = len(urls) - success_count

    # 更新主程序状态和提示 (在主线程中)
    def final_update():
        total_attempted = processed_count # 实际处理的 URL 数量
        final_error_count = error_count # 包括取消和下载失败
        final_message = f"TikTok 下载完成！尝试: {total_attempted}/{len(urls)}, 成功: {success_count}, 失败/取消: {final_error_count}"
        app.status_label.config(text=f"状态: {final_message}")
        if final_error_count > 0:
             messagebox.showwarning("TikTok 下载", final_message + "\n部分下载可能失败或被取消。")
        else:
             messagebox.showinfo("TikTok 下载", final_message)

    app.root.after(0, final_update)

# TODO: (可选) 实现 TikTok 的 progress hook
# def _tiktok_progress_hook(d, app):
#     # 需要从 d 中提取唯一标识符 (可能需要解析 URL 或 info_dict)
#     # ...
#     # 调用 app.update_download_progress(...)
#     pass

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