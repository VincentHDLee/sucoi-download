# core/download_service.py - Encapsulates yt-dlp download logic
import os
import yt_dlp
import threading
import time # 需要 time 模块来实现延时
import logging

class UserCancelledError(Exception):
    """Exception raised when user requests download cancellation."""
    pass

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

class DownloadService:
    """提供通用的视频下载服务，封装 yt-dlp 调用，并包含重试机制。"""

    def __init__(self, default_options=None):
        """初始化下载服务。"""
        self.default_ydl_opts = {
            'quiet': True,
            'noprogress': True,
            'noplaylist': True,
            'encoding': 'utf-8',
            'nocheckcertificate': True,
            'ignoreerrors': False, # 修改为 False，让 yt-dlp 在出错时抛出异常
            'postprocessors': [
                 {'key': 'FFmpegVideoConvertor', 'preferedformat': 'mp4'},
            ],
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        }
        if default_options:
            self.default_ydl_opts.update(default_options)

        self._callback_context = {}
        self._context_lock = threading.Lock()

    def _progress_hook(self, d):
        """内部 yt-dlp 进度回调钩子。"""
        thread_id = threading.get_ident()
        context_key = thread_id
        with self._context_lock:
            context = self._callback_context.get(context_key)

        if not context:
             logger.warning("进度钩子无法找到上下文信息 (线程: %s)", thread_id)
             return

        callback = context.get('callback')
        item_id = context.get('item_id')
        cancel_func = context.get('is_cancel_requested_func')
        error_reported_key = f"{context_key}_error_reported"
        error_reported = context.get(error_reported_key, False)

        if not callback or not item_id or not cancel_func:
            logger.warning("进度钩子上下文信息不完整 (item_id: %s, callback: %s, cancel_func: %s)", item_id, callback, cancel_func)
            return

        try:
            if cancel_func():
                 logger.info("检测到用户取消请求 for [%s]", item_id)
                 raise UserCancelledError(f"用户取消了任务 {item_id}")
        except Exception as cancel_check_e:
             logger.error("检查取消状态时出错 for [%s]: %s", item_id, cancel_check_e)

        status = d['status']
        progress_data = {'id': item_id, 'status': status}

        try:
            if status == 'downloading':
                progress_data['percent'] = d.get('_percent_str', '0%').strip()
                progress_data['size'] = d.get('_total_bytes_str') or d.get('_downloaded_bytes_str', '未知')
                progress_data['speed'] = d.get('_speed_str', 'N/A')
                progress_data['eta'] = d.get('_eta_str', 'N/A')
            elif status == 'finished':
                progress_data['filename'] = os.path.basename(d.get('filename', ''))
                progress_data['size'] = d.get('_total_bytes_str', '未知')
                progress_data['description'] = '完成'
                if d.get('postprocessor'): progress_data['description'] = '后处理中...'
            elif status == 'error':
                if not error_reported:
                     progress_data['description'] = str(d.get('error', '下载错误'))[:100]
                     with self._context_lock:
                         if context_key in self._callback_context:
                             self._callback_context[context_key][error_reported_key] = True
                else:
                     return # 忽略后续错误报告
        except Exception as e:
            logger.error("解析进度数据时出错: %s", e, exc_info=True)
            progress_data['status'] = 'error'
            progress_data['description'] = f"内部错误: {e}"
            with self._context_lock:
                if context_key in self._callback_context:
                     self._callback_context[context_key][error_reported_key] = True

        try:
            callback(progress_data)
        except Exception as cb_e:
            logger.error("调用外部进度回调时出错 (item_id: %s): %s", item_id, cb_e, exc_info=True)

    def _was_error_reported_by_hook(self, context_key):
        with self._context_lock:
            context = self._callback_context.get(context_key)
            if context:
                return context.get(f"{context_key}_error_reported", False)
        return False

    def _mark_error_reported(self, context_key, reported=True): # 添加设置状态的参数
        with self._context_lock:
            context = self._callback_context.get(context_key)
            if context:
                context[f"{context_key}_error_reported"] = reported

    def _extract_friendly_error(self, download_error):
        # TODO: 未来根据 download_error 的类型和内容，解析更具体的错误原因，
        # 例如区分视频不存在、权限问题、网络问题等。
        # msg = str(download_error) # 保留原始消息用于日志记录可能更好
        # logger.debug(f"原始下载错误: {msg}") # 可以添加调试日志记录原始错误
        return "下载失败" # 暂时统一返回通用错误信息

    def download_item(self, item_info, progress_callback, is_cancel_requested_func):
        item_id = item_info.get('id')
        url = item_info.get('url')
        output_path = item_info.get('output_path')

        if not all([item_id, url, output_path, callable(progress_callback), callable(is_cancel_requested_func)]):
            error_msg = "下载信息或回调函数不完整"
            logger.error("%s: id=%s, url=%s, output_path=%s, cb=%s, cancel_func=%s",
                         error_msg, item_id, url, output_path, progress_callback, is_cancel_requested_func)
            return {'id': item_id, 'status': 'error', 'error_message': error_msg}

        final_status = 'pending'
        final_filepath = None
        error_message = None
        max_retries = 2
        retry_delays = [3, 5]

        task_opts = self.default_ydl_opts.copy()
        try:
             os.makedirs(output_path, exist_ok=True)
             task_opts['outtmpl'] = os.path.join(output_path, '%(title)s [%(id)s].%(ext)s')
        except Exception as e:
             logger.error("无法创建或访问输出目录 '%s': %s", output_path, e)
             return {'id': item_id, 'status': 'error', 'error_message': f"输出目录错误: {e}"}

        if 'ydl_opts' in item_info and isinstance(item_info['ydl_opts'], dict):
            task_opts.update(item_info['ydl_opts'])

        # --- 限速逻辑已移除 ---
        task_opts['progress_hooks'] = [self._progress_hook]

        thread_id = threading.get_ident()
        context_key = thread_id
        context = {
            'item_id': item_id,
            'callback': progress_callback,
            'is_cancel_requested_func': is_cancel_requested_func,
            f"{context_key}_error_reported": False
        }
        with self._context_lock:
            self._callback_context[context_key] = context

        try: # 外层 try，确保 finally 会执行
            # --- 重试循环 ---
            for attempt in range(max_retries + 1):
                # 重置错误报告标志，以便重试时钩子可以再次报告错误
                self._mark_error_reported(context_key, False)
                attempt_error_message = None # 记录本次尝试的错误信息

                try: # 内层 try，处理单次尝试的异常
                    logger.info(f"开始下载尝试 {attempt + 1}/{max_retries + 1} [{item_id}]: {url}")
                    if attempt == 0:
                        progress_callback({'id': item_id, 'status': 'preparing'})

                    with yt_dlp.YoutubeDL(task_opts) as ydl:
                        result_code = ydl.download([url])

                        if result_code == 0:
                            final_status = 'finished'
                            logger.info(f"下载完成 [{item_id}] (尝试 {attempt + 1})")
                            try:
                               info_dict = ydl.extract_info(url, download=False)
                               if info_dict: final_filepath = ydl.prepare_filename(info_dict)
                            except Exception as path_e: logger.warning("获取文件路径失败: %s", path_e)
                            break # 成功，跳出 for 循环
                        else:
                            # result_code 非 0
                            # 如果 ignoreerrors=False, 理论上错误会通过异常抛出，
                            # result_code != 0 的情况会减少。但以防万一保留处理。
                            attempt_error_message = f"yt-dlp 返回非零状态码: {result_code}"
                            logger.error(f"下载失败 [{item_id}] (尝试 {attempt + 1}): {attempt_error_message}")
                            # 标记错误，继续重试或结束循环
                            self._mark_error_reported(context_key)
                            # 不再需要检查 _was_error_reported_by_hook，因为异常处理会捕获更详细信息

                except UserCancelledError as uce:
                    final_status = 'cancelled'
                    error_message = str(uce) # 使用取消的错误消息
                    logger.info("任务已取消 [%s]: %s", item_id, error_message)
                    progress_callback({'id': item_id, 'status': 'cancelled', 'description': "用户已取消"})
                    break # 取消后跳出 for 循环

                except yt_dlp.utils.DownloadError as de:
                    # 异常处理：捕获 DownloadError 并提取信息
                    # if not self._was_error_reported_by_hook(context_key): # 移除检查，总是尝试报告新捕获的错误
                    error_message_short = self._extract_friendly_error(de) # 提取友好错误信息
                    attempt_error_message = f"{error_message_short}" # 直接使用提取后的信息
                    logger.error(f"下载失败 [{item_id}] (尝试 {attempt + 1}): {attempt_error_message}\nOriginal Error: %s", de, exc_info=False)
                    self._mark_error_reported(context_key) # 标记错误发生
                    # 删除了原有的 else 块

                except Exception as e:
                    # 未知异常处理
                    # if not self._was_error_reported_by_hook(context_key): # 移除检查
                    attempt_error_message = f"发生未知错误: {e}" # 包含异常类型
                    logger.error(f"下载失败 [{item_id}] (尝试 {attempt + 1}): {attempt_error_message}", exc_info=True)
                    self._mark_error_reported(context_key) # 标记错误发生
                    # 删除了原有的 else 块

                # --- 循环结束判断与重试延时 ---
                if final_status == 'finished' or final_status == 'cancelled':
                    break # 如果已成功或取消，直接跳出

                if attempt < max_retries: # 如果还有重试机会
                    delay = retry_delays[attempt]
                    logger.info(f"任务 [{item_id}] 第 {attempt + 2} 次重试将在 {delay} 秒后开始...")
                    progress_callback({'id': item_id, 'status': 'retrying', 'description': f'等待 {delay}s 后重试 ({attempt + 2}/{max_retries + 1})'})
                    wait_start = time.time()
                    while time.time() - wait_start < delay:
                        if is_cancel_requested_func():
                             logger.info("在重试等待期间检测到取消请求 for [%s]", item_id)
                             # 直接在这里设置最终状态并跳出，避免进入下一次循环
                             final_status = 'cancelled'
                             error_message = f"用户在重试等待期间取消了任务 {item_id}"
                             progress_callback({'id': item_id, 'status': 'cancelled', 'description': "用户已取消"})
                             break # 跳出 while 等待循环
                        time.sleep(0.2)
                    if final_status == 'cancelled': # 如果在等待时取消了，也跳出 for 循环
                        break
                else: # 已达到最大重试次数
                    logger.error(f"任务 [{item_id}] 所有 {max_retries + 1} 次尝试均失败。")
                    final_status = 'error' # 最终状态设为错误
                    error_message = attempt_error_message or "所有重试尝试均失败" # 使用最后一次捕获的错误或通用消息
                    # 确保发送最终错误状态回调
                    # if not self._was_error_reported_by_hook(context_key): # 注释掉此检查，确保最终错误状态总是被发送以覆盖 'retrying'
                    progress_callback({'id': item_id, 'status': 'error', 'description': error_message[:100]}) # 发送清理后的错误信息
                    break # 跳出 for 循环

            # --- for 循环结束 ---
            # 修正：如果循环结束状态仍是 pending，说明是未处理的错误
            if final_status == 'pending':
                final_status = 'error'
                if not error_message: error_message = "下载因未知原因失败"
                # 确保发送最终错误状态回调
                if not self._was_error_reported_by_hook(context_key):
                     progress_callback({'id': item_id, 'status': 'error', 'description': error_message[:100]})

        finally: # 外层 finally，确保上下文被清理
            with self._context_lock:
                if context_key in self._callback_context:
                    del self._callback_context[context_key]

        # --- 准备最终返回结果 ---
        result = {'id': item_id, 'status': final_status}
        if final_status == 'finished' and final_filepath and os.path.exists(final_filepath):
             result['filepath'] = final_filepath
        # 只记录最后一次尝试的或特定的错误信息
        if final_status != 'finished' and error_message and "已由钩子报告" not in error_message:
             result['error_message'] = error_message
        logger.debug("DownloadService: 即将返回最终结果 for %s: %s (类型: %s)", item_id, result, type(result))
        return result

# --- Test Code ---
if __name__ == '__main__':
    print("Testing DownloadService...")
    def my_progress_callback(data): print(f"  Callback: {data}")
    cancel_flag = False
    def mock_is_cancel_requested(): return cancel_flag
    service = DownloadService()
    output_dir = 'test_download_service_retry'
    os.makedirs(output_dir, exist_ok=True) # 确保测试目录存在

    # --- Test 1: 正常下载 ---
    print("\n[Test 1] 正常下载")
    item1 = {'id': 'Test_OK', 'url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ', 'output_path': output_dir}
    cancel_flag = False
    res1 = service.download_item(item1, my_progress_callback, mock_is_cancel_requested)
    print(f"[Test 1] Result: {res1}")

    # --- Test 2: 模拟下载失败一次后成功 ---
    print("\n[Test 2] 模拟第一次失败，第二次成功")
    class MockYoutubeDLFailOnce:
        def __init__(self, opts): self.attempt = 0; self.opts=opts # 保存选项以备后用
        def __enter__(self): return self
        def __exit__(self, exc_type, exc_val, exc_tb): pass
        def download(self, urls):
            self.attempt += 1
            context_key = threading.get_ident()
            item_id = service._callback_context.get(context_key, {}).get('item_id', 'Unknown') # 获取 item_id 用于日志
            if self.attempt == 1:
                print(f"  MockYoutubeDL: 模拟第一次下载失败 for [{item_id}] (返回码 1)")
                # 注意：不再需要模拟钩子报告错误，让 download_item 处理
                # service._mark_error_reported(context_key)
                # hook_data = {'status': 'error', 'error': '模拟的下载错误'}
                # service._progress_hook(hook_data)
                return 1 # 返回错误码
            else:
                print(f"  MockYoutubeDL: 模拟第二次下载成功 for [{item_id}]")
                file_path = os.path.join(output_dir, 'MockVideo [MockID].mp4')
                # 模拟钩子发送完成状态
                hook_data = {'status': 'finished', 'filename': file_path, '_total_bytes_str': '10.0MiB'}
                # 调用真实的钩子处理函数
                if 'progress_hooks' in self.opts:
                    for hook in self.opts['progress_hooks']: hook(hook_data)
                return 0
        def extract_info(self, url, download): return {'id': 'MockID', 'title': 'MockVideo'}
        def prepare_filename(self, info): return os.path.join(output_dir, 'MockVideo [MockID].mp4')

    original_ydl = yt_dlp.YoutubeDL
    yt_dlp.YoutubeDL = MockYoutubeDLFailOnce
    item2 = {'id': 'Test_Retry_OK', 'url': 'mock://fail_once', 'output_path': output_dir}
    cancel_flag = False
    res2 = service.download_item(item2, my_progress_callback, mock_is_cancel_requested)
    print(f"[Test 2] Result: {res2}")
    yt_dlp.YoutubeDL = original_ydl

    # --- Test 3: 模拟一直失败 ---
    print("\n[Test 3] 模拟一直失败")
    class MockYoutubeDLFailAlways:
        def __init__(self, opts): self.attempt = 0
        def __enter__(self): return self
        def __exit__(self, exc_type, exc_val, exc_tb): pass
        def download(self, urls):
            self.attempt += 1
            item_id = service._callback_context.get(threading.get_ident(), {}).get('item_id', 'Unknown')
            print(f"  MockYoutubeDL: 模拟第 {self.attempt} 次下载失败 for [{item_id}] (抛出异常)")
            raise yt_dlp.utils.DownloadError("模拟持续下载错误")
        def extract_info(self, url, download): return None

    yt_dlp.YoutubeDL = MockYoutubeDLFailAlways
    item3 = {'id': 'Test_Retry_Fail', 'url': 'mock://fail_always', 'output_path': output_dir}
    cancel_flag = False
    res3 = service.download_item(item3, my_progress_callback, mock_is_cancel_requested)
    print(f"[Test 3] Result: {res3}")
    yt_dlp.YoutubeDL = original_ydl

    # --- Test 4: 测试重试期间取消 ---
    print("\n[Test 4] 测试重试期间取消")
    yt_dlp.YoutubeDL = MockYoutubeDLFailAlways # 使用持续失败的模拟类
    item4 = {'id': 'Test_Retry_Cancel', 'url': 'mock://fail_cancel', 'output_path': output_dir}
    cancel_flag = False
    download_thread = threading.Thread(target=service.download_item,
                                       args=(item4, my_progress_callback, mock_is_cancel_requested),
                                       daemon=True)
    download_thread.start()
    print("  [Test 4] 等待 4 秒（第一次重试等待期间）后请求取消...")
    time.sleep(4)
    print("  [Test 4] 设置取消标志")
    cancel_flag = True
    download_thread.join(10)
    if download_thread.is_alive(): print("  [Test 4] 线程未按预期结束!")
    else: print("  [Test 4] 线程已结束 (检查回调中的 cancelled 状态)")
    yt_dlp.YoutubeDL = original_ydl

    print("\nDownloadService retry tests finished.")