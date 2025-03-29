# modules/tiktok/logic.py - TikTok Platform Specific Business Logic
import tkinter as tk # 仅用于 messagebox
from tkinter import messagebox
# import yt_dlp #不再直接使用
import os
from threading import Thread # 可能不再需要，取决于主程序如何管理
import hashlib # 用于生成 ID

# 注意：这个文件不应该直接依赖 Tkinter 的控件 (除了 messagebox)
# 它应该通过 app 实例来交互

PLATFORM_NAME = "TikTok" # 定义平台名称常量

def add_tiktok_urls(url_text_widget, app):
    """
    从 UI 获取 TikTok URL 并请求添加到主程序的下载队列。
    """
    # TODO: 后续优化：此函数应接收文本内容，而不是 Text 控件本身
    urls_text = url_text_widget.get("1.0", tk.END).strip()
    if not urls_text:
        messagebox.showwarning("提示", "请输入 TikTok 视频 URL。", parent=app.view.root if hasattr(app, 'view') else None)
        return

    urls = urls_text.splitlines()
    urls = [url.strip() for url in urls if url.strip()] # 过滤空行和前后空格

    if not urls:
        messagebox.showwarning("提示", "未发现有效的 TikTok 视频 URL。", parent=app.view.root if hasattr(app, 'view') else None)
        return

    print(f"准备添加 {len(urls)} 个 TikTok URL 到下载队列")
    # 调用 app (主程序实例) 的方法将 urls 添加到通用下载队列 (download_tree)
    if hasattr(app, 'add_urls_to_download_queue'):
        # 传递 platform 参数很重要
        app.add_urls_to_download_queue(urls, platform=PLATFORM_NAME)
        # 由 add_urls_to_download_queue 负责显示最终状态或消息
        # messagebox.showinfo("提示", f"已将 {len(urls)} 个 URL 请求添加到下载队列。", parent=app.view.root if hasattr(app, 'view') else None)
    else:
        messagebox.showerror("错误", "主程序缺少 'add_urls_to_download_queue' 方法。", parent=app.view.root if hasattr(app, 'view') else None)


def download_tiktok_urls(url_text_widget, app):
    """
    准备并请求立即下载输入的 TikTok URLs（不通过UI队列）。
    """
    # TODO: 后续优化：此函数应接收文本内容，而不是 Text 控件本身
    urls_text = url_text_widget.get("1.0", tk.END).strip()
    if not urls_text:
        messagebox.showwarning("提示", "请输入 TikTok 视频 URL。", parent=app.view.root if hasattr(app, 'view') else None)
        return

    urls = urls_text.splitlines()
    urls = [url.strip() for url in urls if url.strip()] # 过滤空行和前后空格

    if not urls:
        messagebox.showwarning("提示", "未发现有效的 TikTok 视频 URL。", parent=app.view.root if hasattr(app, 'view') else None)
        return

    # 从主程序获取保存路径 (应该通过 app 实例的方法获取)
    output_path = app.get_download_path() # 假设 app 有此方法

    if not output_path:
        # get_download_path 内部应处理路径无效的情况并可能提示用户
        # 此处无需再次提示
        return

    # 检查 app 实例是否提供了启动下载的方法
    if not hasattr(app, 'start_immediate_downloads'):
         messagebox.showerror("错误", "主程序实例缺少 'start_immediate_downloads' 方法。", parent=app.view.root if hasattr(app, 'view') else None)
         return

    # --- 构造 item_info 列表 ---
    items_to_download = []
    for url in urls:
         # 生成唯一 ID
         url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
         item_id = f"{PLATFORM_NAME}_{url_hash}"
         item_info = {
             'id': item_id,
             'url': url,
             'output_path': output_path,
             # 可以添加特定于 TikTok 的 ydl_opts (如果需要)
             'ydl_opts': {
                  # 例如: 'format': 'best' # TikTok 可能不需要复杂格式选择
             }
         }
         items_to_download.append(item_info)
    # --------------------------

    if items_to_download:
         print(f"请求立即下载 {len(items_to_download)} 个 TikTok 任务...")
         # 调用主程序的方法来处理这些任务的异步执行
         app.start_immediate_downloads(items_to_download)
         app.update_status(f"已提交 {len(items_to_download)} 个 TikTok 任务进行立即下载。")
         # 可以考虑清空输入框？ url_text_widget.delete("1.0", tk.END)
    else:
         app.show_message("提示", "没有有效的任务可供下载。")


# 这个函数现在不直接由本模块调用，而是可能由 app controller 在启动单个下载线程时调用
# 或者，如果 DownloadService 完全封装，这个函数可能不再需要
# 保留结构以备将来可能需要平台特定预处理或后处理
def _perform_single_tiktok_download(item_id, url, output_path, app):
    """
    (重构后，此函数可能不再直接使用，由 DownloadService 处理)
    执行单个 TikTok 视频的下载逻辑（旧版实现参考）。
    """
    # 检查 app 是否有 download_service 实例
    if not hasattr(app, 'download_service'):
        app.update_download_progress({'id': item_id, 'status': 'error', 'description': 'DownloadService未初始化'})
        return

    item_info = {
        'id': item_id,
        'url': url,
        'output_path': output_path,
        # 可以添加特定于 TikTok 的 ydl_opts (如果需要)
        'ydl_opts': {
            # 'format': 'best'
        }
    }

    # 调用 DownloadService 处理下载和回调
    # 回调函数直接使用 app 上的方法
    result = app.download_service.download_item(item_info, app.update_download_progress)

    # download_item 返回最终状态，但主要更新通过回调完成
    print(f"DownloadService result for {item_id}: {result}")


# 可选的测试代码 (用于测试逻辑，不依赖真实 UI)
if __name__ == '__main__':

    # --- 模拟 App Controller ---
    # 需要模拟 DownloadService 和相关方法
    import time
    from core.download_service import DownloadService # 需要能找到 core

    class MockAppForLogic:
        def __init__(self):
            self._download_path = 'test_tiktok_logic_refactored'
            self._status = "Idle"
            self._cancel_requested = False
            # 实例化 DownloadService
            self.download_service = DownloadService()
            # 模拟 UI 更新方法
            self.view = lambda: None # Placeholder
            self.view.root = tk.Tk() # Need a root for messagebox parent
            self.view.root.withdraw() # Hide the dummy root window

            os.makedirs(self._download_path, exist_ok=True)
            print(f"MockAppForLogic initialized. Download path: {self._download_path}")
            self.active_threads = []

        def get_download_path(self):
            return self._download_path

        def update_status(self, message):
            self._status = message
            print(f"MockApp Status Update: {message}")

        def request_cancel(self):
            print("MockApp: Cancel requested by user.")
            self._cancel_requested = True
            # 在实际应用中，需要一种机制通知 DownloadService 或正在运行的线程

        def is_cancel_requested(self):
            # 简单的标志，DownloadService 内部目前不直接使用这个
            # 需要修改 DownloadService 或增加取消机制
            return self._cancel_requested

        def reset_cancel_request(self):
             self._cancel_requested = False

        def show_message(self, title, message, msg_type='info', parent=None):
             # 使用 print 代替 messagebox 在测试时
             print(f"MockApp Message [{msg_type.upper()}] ({title}): {message}")
             # messagebox.showinfo(title, message, parent=parent or self.view.root)


        def add_urls_to_download_queue(self, urls, platform):
             print(f"MockApp: Adding {len(urls)} URLs for {platform} to queue: {urls}")

        def update_download_progress(self, data):
             # 模拟主线程更新下载列表
             print(f"  Progress Update (Thread: {threading.get_ident()}): {data}")

        # --- 新增：模拟启动立即下载任务 ---
        def start_immediate_downloads(self, items_info):
            print(f"MockApp: Received request for immediate download of {len(items_info)} items.")
            self.reset_cancel_request() # 重置取消标志
            self.active_threads = []

            # 为每个任务启动一个线程来调用 DownloadService
            for item in items_info:
                 thread = Thread(target=self._run_download_task, args=(item,))
                 thread.daemon = True
                 self.active_threads.append(thread)
                 thread.start()

            # 启动监控线程 (可选，用于等待所有任务完成)
            monitor = Thread(target=self._monitor_tasks)
            monitor.daemon = True
            monitor.start()

        def _run_download_task(self, item_info):
             print(f"  Starting download thread for: {item_info['id']}")
             result = self.download_service.download_item(item_info, self.update_download_progress)
             print(f"  Download thread finished for {item_info['id']}. Result: {result['status']}")

        def _monitor_tasks(self):
             print("  Monitor: Waiting for download threads...")
             for t in self.active_threads:
                  t.join()
             print("  Monitor: All download threads finished.")
             self.update_status("所有立即下载任务已结束。")


    mock_app = MockAppForLogic()

    # --- 测试添加 URL (不变) ---
    class MockText:
         _content = ""
         def get(self, start, end): return self._content
         def set_content(self, text): self._content = text
    mock_text_widget = MockText()
    mock_text_widget.set_content("https://www.tiktok.com/@scout2015/video/6718335390787505413\n \n invalid url \n")
    print("\n--- Testing add_tiktok_urls ---")
    add_tiktok_urls(mock_text_widget, mock_app)

    # --- 测试立即下载 ---
    mock_text_widget.set_content("https://www.tiktok.com/@scout2015/video/6718335390787505413 \n https://vt.tiktok.com/ZSYX5WXdP/") # 两个有效 URL
    print("\n--- Testing download_tiktok_urls (immediate download) ---")
    download_tiktok_urls(mock_text_widget, mock_app)

    # --- 等待后台线程 ---
    print("\nWaiting for background threads (up to 60s)... Press Ctrl+C to potentially interrupt.")
    start_wait = time.time()
    while any(t.is_alive() for t in mock_app.active_threads) and time.time() - start_wait < 60:
         try:
              time.sleep(1)
         except KeyboardInterrupt:
              print("\nCtrl+C detected during wait. Requesting cancel...")
              mock_app.request_cancel() # 请求取消
              # DownloadService 目前没有好的取消机制，线程会继续运行直到完成或出错
              break

    print("\n--- Test Finished ---")
    # 退出可能需要强制，因为 Tkinter root 可能仍在后台
    try: mock_app.view.root.destroy()
    except: pass
    os._exit(0) # Force exit if threads are stuck (e.g., waiting on network)