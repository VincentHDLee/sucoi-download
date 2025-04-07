# core/download_service.py - Encapsulates yt-dlp download logic
import os
import yt_dlp
import threading # Only if service manages threads, otherwise remove

class UserCancelledError(Exception):
    """Exception raised when user requests download cancellation."""
    pass


# TODO: Integrate with a proper logging setup
import logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO) # Basic config for now

class DownloadService:
    """提供通用的视频下载服务，封装 yt-dlp 调用。"""

    def __init__(self, default_options=None):
        """
        初始化下载服务。

        参数:
            default_options (dict, optional): 可选的 yt-dlp 默认参数。
        """
        self.default_ydl_opts = {
            'quiet': True,         # 减少控制台输出, 依赖 GUI/日志
            'noprogress': True,    # 依赖 progress_hooks
            'noplaylist': True,    # 通常下载单个视频
            'encoding': 'utf-8',
            'nocheckcertificate': True, # 避免某些网络环境下的证书问题
            'ignoreerrors': True,    # 让 yt-dlp 在单个文件错误时继续处理列表（如果适用）
            'postprocessors': [
                 {'key': 'FFmpegVideoConvertor', 'preferedformat': 'mp4'}, # 尝试转为 mp4
                 # {'key': 'FFmpegMetadata'}, # 可选：写入元数据
                 # {'key': 'EmbedThumbnail'},  # 可选：嵌入封面
            ],
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best', # 优先 mp4
            # 'logger': logger, # 将 yt-dlp 日志集成到 Python logging
            # 'concurrent_fragment_downloads': 4, # 示例：并发片段下载
        }
        if default_options:
            self.default_ydl_opts.update(default_options)

        # 用于在回调中传递信息的上下文
        self._callback_context = {}
        self._context_lock = threading.Lock() # 保护上下文访问

    def _progress_hook(self, d):
        """内部 yt-dlp 进度回调钩子。"""
        # 从上下文中获取当前任务的回调和唯一 ID
        thread_id = threading.get_ident()
        context_key = thread_id # 使用线程 ID 作为 key
        is_cancel_requested = None
        with self._context_lock:
            context = self._callback_context.get(context_key)

        if not context:
             logger.warning("进度钩子无法找到上下文信息 (线程: %s)", thread_id)
             return

        callback = context.get('callback')
        item_id = context.get('item_id')
        # 修改：获取取消检查函数
        cancel_func = context.get('is_cancel_requested_func')

        if not callback or not item_id or not cancel_func:
            logger.warning("进度钩子上下文信息不完整 (item_id: %s, callback: %s, cancel_func: %s)", item_id, callback, cancel_func)
            return

        # 修改：检查是否请求取消
        try:
            if cancel_func():
                 logger.info("检测到用户取消请求 for [%s]", item_id)
                 raise UserCancelledError(f"用户取消了任务 {item_id}")
        except Exception as cancel_check_e:
             logger.error("检查取消状态时出错 for [%s]: %s", item_id, cancel_check_e)
             # 如果检查函数本身出错，我们继续执行，避免中断下载

        # --- 提取信息 ---
        status = d['status']
        progress_data = {'id': item_id, 'status': status} # 使用原始 item_id

        try:
            if status == 'downloading':
                progress_data['percent'] = d.get('_percent_str', '0%').strip()
                progress_data['size'] = d.get('_total_bytes_str') or d.get('_downloaded_bytes_str', '未知')
                progress_data['speed'] = d.get('_speed_str', 'N/A')
                progress_data['eta'] = d.get('_eta_str', 'N/A')
                # 文件名可能在下载过程中才确定，在 finished 时再传递更可靠
                # progress_data['filename'] = os.path.basename(d.get('filename', ''))
            elif status == 'finished':
                progress_data['filename'] = os.path.basename(d.get('filename', ''))
                progress_data['size'] = d.get('_total_bytes_str', '未知')
                progress_data['description'] = '完成'
                if d.get('postprocessor'): progress_data['description'] = '后处理中...' # 更准确的状态
            elif status == 'error':
                progress_data['description'] = str(d.get('error', '下载错误'))[:100]
        except Exception as e:
            logger.error("解析进度数据时出错: %s", e, exc_info=True)
            progress_data['status'] = 'error'
            progress_data['description'] = f"内部错误: {e}"

        # --- 调用外部回调 ---
        try:
            callback(progress_data)
        except Exception as cb_e:
            logger.error("调用外部进度回调时出错 (item_id: %s): %s", item_id, cb_e, exc_info=True)


    # 修改：增加 is_cancel_requested_func 参数
    def download_item(self, item_info, progress_callback, is_cancel_requested_func):
        """
        下载单个视频项目。

        参数:
            item_info (dict): 包含下载信息的字典，应包含:
                - 'id' (str): 任务的唯一标识符。
                - 'url' (str): 要下载的视频 URL。
                - 'output_path' (str): 下载文件的目标目录。
                - 'ydl_opts' (dict, optional): 特定于此任务的额外 yt-dlp 选项。
            progress_callback (function): 用于报告进度的回调函数。
            is_cancel_requested_func (function): 一个函数，调用时返回 True 表示用户请求取消。

        返回:
            dict: 包含下载结果的字典。
        """
        item_id = item_info.get('id')
        url = item_info.get('url')
        output_path = item_info.get('output_path')

        # 验证必要信息
        if not all([item_id, url, output_path, callable(progress_callback), callable(is_cancel_requested_func)]):
            error_msg = "下载信息或回调函数不完整"
            logger.error("%s: id=%s, url=%s, output_path=%s, cb=%s, cancel_func=%s",
                         error_msg, item_id, url, output_path, progress_callback, is_cancel_requested_func)
            return {'id': item_id, 'status': 'error', 'error_message': error_msg}

        final_status = 'pending'
        final_filepath = None
        error_message = None

        # --- 准备 yt-dlp 选项 ---
        task_opts = self.default_ydl_opts.copy()
        # 设定输出模板，确保目录存在
        try:
             os.makedirs(output_path, exist_ok=True)
             # 使用更健壮的模板，包含 ID，避免潜在的文件名冲突
             task_opts['outtmpl'] = os.path.join(output_path, '%(title)s [%(id)s].%(ext)s')
        except Exception as e:
             logger.error("无法创建或访问输出目录 '%s': %s", output_path, e)
             return {'id': item_id, 'status': 'error', 'error_message': f"输出目录错误: {e}"}

        # 合并特定任务的选项
        if 'ydl_opts' in item_info and isinstance(item_info['ydl_opts'], dict):
            task_opts.update(item_info['ydl_opts'])

        # 强制添加内部进度钩子
        task_opts['progress_hooks'] = [self._progress_hook]

        # --- 设置回调上下文 ---
        thread_id = threading.get_ident()
        context_key = thread_id
        # 修改：在上下文中加入取消检查函数
        context = {
            'item_id': item_id,
            'callback': progress_callback,
            'is_cancel_requested_func': is_cancel_requested_func # 添加取消函数引用
        }
        with self._context_lock:
            self._callback_context[context_key] = context
            # logger.debug("设置回调上下文 for %s (线程: %s)", item_id, thread_id)

        # --- 执行下载 ---
        try:
            logger.info("开始下载 [%s]: %s", item_id, url)
            # 发送准备状态
            progress_callback({'id': item_id, 'status': 'preparing'})

            with yt_dlp.YoutubeDL(task_opts) as ydl:
                result_code = ydl.download([url])
                if result_code == 0:
                    final_status = 'finished'
                    logger.info("下载完成 [%s]", item_id)
                else:
                    # 如果 ignoreerrors=True，钩子可能已经报告了错误，
                    # 这里只记录一个通用错误，除非能从 ydl 实例获取更具体信息
                    final_status = 'error'
                    error_message = f"yt-dlp 返回错误码: {result_code} (可能因 ignoreerrors)"
                    logger.error("下载似乎失败 [%s]: %s", item_id, error_message)
                    # 确保回调至少收到一个错误状态
                    # 检查钩子是否已报告错误，避免重复发送
                    if not self._was_error_reported_by_hook(context_key):
                         progress_callback({'id': item_id, 'status': 'error', 'description': "下载失败 (查看日志)"})

        # 修改：优先捕获 UserCancelledError
        except UserCancelledError as uce:
            final_status = 'cancelled' # 使用新的状态
            error_message = str(uce)
            logger.info("任务已取消 [%s]: %s", item_id, error_message)
            # 发送取消状态给回调
            progress_callback({'id': item_id, 'status': 'cancelled', 'description': "用户已取消"})

        except yt_dlp.utils.DownloadError as de:
            final_status = 'error'
            # 修改：尝试细化错误信息
            error_message_short = self._extract_friendly_error(de)
            error_message = f"下载错误: {error_message_short}" # 完整的原始错误可能太长
            logger.error("下载失败 [%s]: %s\nOriginal Error: %s", item_id, error_message, de, exc_info=False) # Log full error
            progress_callback({'id': item_id, 'status': 'error', 'description': error_message_short})
            self._mark_error_reported(context_key) # 标记已报告错误

        except Exception as e:
            final_status = 'error'
            error_message = f"未知错误: {e}"
            logger.error("下载失败 [%s]: %s", item_id, error_message, exc_info=True)
            progress_callback({'id': item_id, 'status': 'error', 'description': f"未知错误: {str(e)[:50]}"}) # 截断
            self._mark_error_reported(context_key) # 标记已报告错误

        finally:
            # --- 清理回调上下文 ---
            with self._context_lock:
                if context_key in self._callback_context:
                    del self._callback_context[context_key]
                # else: # 不再警告，避免并发问题

    def _extract_friendly_error(self, download_error):
        """尝试从 yt-dlp DownloadError 中提取更友好的错误信息。"""
        original_error = download_error
        error_str = str(original_error).lower() # 转小写方便匹配

        # 尝试从原始异常链中查找更具体的信息 (如果可用)
        if hasattr(download_error, 'exc_info') and download_error.exc_info and len(download_error.exc_info) > 1:
            original_error = download_error.exc_info[1]
            error_str = str(original_error).lower()

        # 常见错误模式匹配
        if 'video unavailable' in error_str:
            return "视频不可用 (可能已删除或私有)"
        if 'private video' in error_str:
            return "私有视频，无法下载"
        if 'geo-restricted' in error_str or 'content is not available in your country' in error_str:
            return "视频地区限制，无法下载"
        if 'login required' in error_str:
            return "需要登录才能访问"
        if 'http error 404' in error_str or 'not found' in error_str:
            return "资源未找到 (404)"
        if 'http error 403' in error_str or 'forbidden' in error_str:
            return "禁止访问 (403)"
        if 'resolve host name' in error_str or 'name or service not known' in error_str:
             return "网络错误：无法解析主机名"
        if 'network is unreachable' in error_str:
             return "网络错误：网络不可达"
        if 'connection refused' in error_str:
             return "网络错误：连接被拒绝"
        if 'timed out' in error_str:
             return "网络错误：连接超时"

        # 如果没有匹配到特定模式，返回原始错误的前缀
        # 移除常见的 yt-dlp 前缀
        error_prefix = "error: "
        short_error = str(download_error)
        if short_error.lower().startswith(error_prefix):
             short_error = short_error[len(error_prefix):]

        return short_error[:100] # 返回截断后的原始错误

    def _mark_error_reported(self, context_key):
        """标记指定上下文的错误已被报告（通过回调）。"""
        with self._context_lock:
            if context_key in self._callback_context:
                self._callback_context[context_key]['error_reported'] = True

    def _was_error_reported_by_hook(self, context_key):
        """检查指定上下文的错误是否已被钩子报告过。"""
        with self._context_lock:
            context = self._callback_context.get(context_key)
            return context and context.get('error_reported', False)

                #    logger.warning("Attempting to cleanup non-existent callback context (Thread: %s)", thread_id)

            # --- 返回最终结果 ---
            result = {'id': item_id, 'status': final_status}
            if final_filepath: result['filepath'] = final_filepath
            if error_message: result['error_message'] = error_message
            return result


# --- 可选: 添加管理并发下载的方法 ---
# class DownloadManager:
#     def __init__(self, max_concurrent=3):
#         self.download_service = DownloadService()
#         self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_concurrent)
#         self.futures = {} # {item_id: future}
#
#     def submit_download(self, item_info, progress_callback, completion_callback):
#         item_id = item_info.get('id')
#         if not item_id: raise ValueError("item_info must contain an 'id'")
#
#         def task_wrapper():
#             result = self.download_service.download_item(item_info, progress_callback)
#             # Call completion callback here in the worker thread, or schedule it in main thread
#             completion_callback(result)
#             return result
#
#         future = self.executor.submit(task_wrapper)
#         self.futures[item_id] = future
#         return future
#
#     def cancel_download(self, item_id):
#         # yt-dlp 本身没有完美的取消机制，只能尝试标记
#         # 需要 DownloadService 内部或钩子配合检查取消标志
#         # self.futures[item_id].cancel() # 通常无效
#         pass
#
#     def shutdown(self, wait=True):
#         self.executor.shutdown(wait=wait)


# --- Test Code ---
if __name__ == '__main__':
    print("Testing DownloadService...")

    # 模拟进度回调
    def my_progress_callback(data):
        print(f"  Callback received: {data}")

    # 创建服务实例
    service = DownloadService()

    # --- 测试 TikTok 下载 ---
    tiktok_item = {
        'id': 'TikTok_Test1',
        'url': 'https://www.tiktok.com/@scout2015/video/6718335390787505413', # 使用有效 URL
        'output_path': 'test_download_service_output',
    }
    print(f"\n[Test 1] Downloading TikTok item: {tiktok_item['id']}")
    result1 = service.download_item(tiktok_item, my_progress_callback)
    print(f"[Test 1] Result: {result1}")

    # --- 测试 YouTube 下载 ---
    youtube_item = {
        'id': 'YouTube_Test2',
        'url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ', # Rick Astley :)
        'output_path': 'test_download_service_output',
        'ydl_opts': { # 示例：特定任务选项
            'format': 'bestaudio/best', # 只下载音频
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }
    }
    print(f"\n[Test 2] Downloading YouTube item (audio only): {youtube_item['id']}")
    result2 = service.download_item(youtube_item, my_progress_callback)
    print(f"[Test 2] Result: {result2}")

    # --- 测试无效 URL ---
    invalid_item = {
        'id': 'Invalid_Test3',
        'url': 'https://nonexistent.example.com/video.mp4',
        'output_path': 'test_download_service_output',
    }
    print(f"\n[Test 3] Downloading invalid item: {invalid_item['id']}")
    result3 = service.download_item(invalid_item, my_progress_callback)
    print(f"[Test 3] Result: {result3}")

    # --- 测试缺少信息 ---
    incomplete_item = {
        'id': 'Incomplete_Test4',
        'url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
        # Missing 'output_path'
    }
    print(f"\n[Test 4] Downloading incomplete item: {incomplete_item['id']}")
    result4 = service.download_item(incomplete_item, my_progress_callback)
    print(f"[Test 4] Result: {result4}")

    print("\nDownloadService tests finished.")