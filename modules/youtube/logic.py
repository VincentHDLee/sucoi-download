# modules/youtube/logic.py - YouTube Platform Specific Business Logic
import isodate
from datetime import timedelta
import os
# import yt_dlp # No longer directly used here
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import logging # Use logging

logger = logging.getLogger(__name__)
PLATFORM_NAME = "YouTube" # Define platform name

# --- Helper Functions (Keep as they are used by search) ---
def _format_duration(duration_str):
    """将 ISO 8601 时长字符串转换为 HH:MM:SS 或 MM:SS 格式。"""
    try:
        duration = isodate.parse_duration(duration_str)
        total_seconds = int(duration.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours > 0: return f"{hours:02}:{minutes:02}:{seconds:02}"
        else: return f"{minutes:02}:{seconds:02}"
    except Exception: return "未知"

def _format_large_number(num_str):
    """格式化数字，如果太大则显示 K, M, B"""
    try:
        num = int(num_str)
        if num >= 1_000_000_000: return f"{num / 1_000_000_000:.1f}B"
        if num >= 1_000_000: return f"{num / 1_000_000:.1f}M"
        if num >= 1000: return f"{num / 1000:.1f}K"
        return str(num)
    except (ValueError, TypeError): return num_str if num_str else "0"

# --- Search Function (Keep implementation, logic is API specific) ---
def search_videos(app, query, max_results=50, video_duration='any', order='relevance'):
    """
    使用 YouTube Data API 搜索视频并获取详细信息。
    通过 app 实例获取 API Key。
    支持按时长和排序方式筛选。
    返回: (list | None, str | None) - (结果列表, 错误消息)
    """
    api_key = app.get_config('api_key') # 从控制器获取 API Key
    if not api_key or api_key == 'YOUR_YOUTUBE_DATA_API_KEY_HERE':
        return None, "无效或未配置 YouTube API Key。"
    try:
        youtube = build('youtube', 'v3', developerKey=api_key)
        search_params = {'part': 'snippet', 'q': query, 'type': 'video', 'maxResults': max_results, 'order': order}
        if video_duration != 'any': search_params['videoDuration'] = video_duration

        search_request = youtube.search().list(**search_params)
        search_response = search_request.execute()
        search_items = search_response.get('items', [])
        video_details = {}; video_ids = []
        for item in search_items:
             if isinstance(item, dict) and 'id' in item and isinstance(item['id'], dict) and 'videoId' in item['id']:
                 video_id = item['id']['videoId']; video_ids.append(video_id)
                 video_details[video_id] = item.get('snippet', {})
             else: logger.warning("发现无效的 YouTube 搜索结果项: %s", item)
        if not video_ids: return [], None

        detailed_videos_info = []
        batch_size = 50
        for i in range(0, len(video_ids), batch_size):
             batch_ids_str = ','.join(video_ids[i:i + batch_size])
             video_request = youtube.videos().list(part='snippet,statistics,contentDetails', id=batch_ids_str)
             video_response = video_request.execute()
             for video_item in video_response.get('items', []):
                 vid = video_item.get('id'); snippet = video_item.get('snippet', {}); stats = video_item.get('statistics', {}); content = video_item.get('contentDetails', {}); search_snippet = video_details.get(vid, {})
                 if not vid: continue
                 published_at_search = search_snippet.get('publishedAt', ''); published_at_video = snippet.get('publishedAt', '')
                 published_display = published_at_search[:10] if published_at_search else (published_at_video[:10] if published_at_video else '未知')
                 detailed_videos_info.append({
                     'id': vid,'name': snippet.get('title', '无标题'),'views': _format_large_number(stats.get('viewCount')),
                     'likes': _format_large_number(stats.get('likeCount')), 'favorites': 'N/A',
                     'comments': _format_large_number(stats.get('commentCount', '0')),
                     'published': published_display, 'duration': _format_duration(content.get('duration'))
                 })
        return detailed_videos_info, None
    except HttpError as e:
        logger.error("调用 YouTube API 时发生 HTTP 错误: %s", e, exc_info=True)
        content = e.resp.reason if hasattr(e, 'resp') else str(e)
        error_message = f"搜索视频时出错: {content}"
        if hasattr(e, 'resp') and e.resp.status == 403: # Check if resp exists before accessing status
             e_content_str = e.content.decode('utf-8', 'ignore') if isinstance(e.content, bytes) else str(e.content)
             if "quotaExceeded" in e_content_str: error_message = "YouTube API 配额已用尽。"
             elif "accessNotConfigured" in e_content_str or "forbidden" in e_content_str: error_message = "YouTube API 未启用或无权访问。"
        elif hasattr(e, 'resp') and e.resp.status == 400:
             e_content_str = e.content.decode('utf-8', 'ignore') if isinstance(e.content, bytes) else str(e.content)
             if "invalidKey" in e_content_str: error_message = "无效的 YouTube API Key。"
        return None, error_message
    except Exception as e: # Catch other potential errors
        logger.error("调用 YouTube API 时发生未知错误: %s", e, exc_info=True)
        return None, f"搜索时发生未知错误: {e}"


# --- Download Logic (Refactored Placeholder) ---

# Removed _youtube_progress_hook and _current_progress_callback
# Download logic is now handled by core.download_service.DownloadService

def download_item(app, item_iid, output_path):
    """
    (Refactored - Now handles a single item via DownloadService)
    准备并请求下载单个 YouTube 视频。

    参数:
        app: 主应用程序控制器实例。
        item_iid (str): Treeview 中的唯一项 ID (格式: YouTube_videoID)。
        output_path (str): 下载文件的目标目录。

    注意: 此函数应在单独的线程中被调用 (由主程序管理)。
    """
    if not hasattr(app, 'download_service'):
         logger.error("DownloadService 在 app 控制器中未找到!")
         # 直接更新进度可能不在主线程，最好通过 app 的方法
         app.update_download_progress({'id': item_iid, 'status': 'error', 'description': 'DownloadService不可用'})
         return # 不能继续

    video_id = item_iid.split('_', 1)[-1] # 提取实际 YouTube video ID
    if not video_id:
         logger.error("无法从 iid '%s' 提取 video_id。", item_iid)
         app.update_download_progress({'id': item_iid, 'status': 'error', 'description': '无效的内部ID'})
         return

    url = f"https://www.youtube.com/watch?v={video_id}"

    item_info = {
        'id': item_iid, # 使用 Treeview 的完整 ID 传递给服务和回调
        'url': url,
        'output_path': output_path,
        'ydl_opts': {
            # 特定于 YouTube 的选项可以放在这里
             'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
             'postprocessors': [
                  {'key': 'FFmpegVideoConvertor', 'preferedformat': 'mp4'},
             ],
             'outtmpl': os.path.join(output_path, '%(title)s [%(id)s].%(ext)s'), # 确保输出模板一致
        }
    }

    # 调用 DownloadService 处理下载，传递 app 的进度更新方法作为回调
    result = app.download_service.download_item(item_info, app.update_download_progress, app.is_cancel_requested)

    # download_item 的返回值主要用于记录最终状态，详细进度通过回调处理
    logger.info("DownloadService 对 [%s] 的最终结果: %s", item_iid, result.get('status', '未知'))
    # 此函数不再负责返回成功/失败计数


# --- Optional test code ---
if __name__ == '__main__':
     logging.basicConfig(level=logging.INFO) # Ensure logger works for tests
     logger.info("YouTube Logic Module - Test Execution")

     # --- 模拟 App Controller ---
     # 需要模拟 DownloadService 和相关方法
     import time
     try:
          # Try importing DownloadService assuming it's in core relative to project root
          import sys
          project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
          if project_root not in sys.path: sys.path.insert(0, project_root)
          from core.download_service import DownloadService
          SERVICE_AVAILABLE = True
     except ImportError as e:
          logger.error("无法导入 DownloadService 进行测试: %s", e)
          DownloadService = None # Placeholder if import fails
          SERVICE_AVAILABLE = False

     class MockAppController:
          def __init__(self):
               self._config = {'api_key': os.environ.get("YOUTUBE_API_KEY", None)}
               self._cancel_requested = False
               # 实例化 DownloadService (如果可用)
               self.download_service = DownloadService() if SERVICE_AVAILABLE else None
               logger.info(f"MockApp initialized. API Key: {'Set' if self._config['api_key'] else 'Not Set'}, DownloadService: {'Available' if self.download_service else 'Unavailable'}")

          def get_config(self, key, default=None):
               return self._config.get(key, default)

          def update_download_progress(self, data):
               log_id = data.get('id', 'No ID')
               logger.info(f"  Progress ({log_id}): {data.get('status')} - {data.get('description', '')} {data.get('percent', '')}")

          def is_cancel_requested(self): return self._cancel_requested
          def request_cancel(self): self._cancel_requested = True; logger.info("MockApp: Cancel Requested")

     mock_app = MockAppController()

     # Test Search (Requires API Key)
     if mock_app.get_config('api_key'):
          logger.info("\n--- Testing Search ---")
          results, error = search_videos(mock_app, "blender tutorial beginner", max_results=2)
          if error: logger.error("Search Error: %s", error)
          elif results:
               logger.info("Found %d videos:", len(results))
               for video in results: logger.info("  - %s (%s) ID: %s", video['name'], video['duration'], video['id'])
          else: logger.info("Search returned no results.")
     else: logger.info("\n--- Skipping Search Test (No API Key) ---")

     # Test Download (Requires DownloadService)
     if mock_app.download_service:
          logger.info("\n--- Testing Download (Single Item via download_item) ---")
          test_iid = "YouTube_dQw4w9WgXcQ" # Rick Astley
          download_path = "test_youtube_logic_refactored"
          os.makedirs(download_path, exist_ok=True)
          logger.info("Starting download for: %s", test_iid)
          mock_app._cancel_requested = False # Reset cancel flag

          # --- 调用重构后的 download_item ---
          # 在实际应用中，这会在一个单独的线程中被调用
          # 这里为了简单直接调用，但它会阻塞
          download_item(mock_app, test_iid, download_path)
          # ---------------------------------

          logger.info("\nDownload test call finished.")
     else:
          logger.info("\n--- Skipping Download Test (DownloadService Unavailable) ---")


     logger.info("\n--- Test Finished ---")