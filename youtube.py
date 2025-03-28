# youtube.py - YouTube Platform Specific Logic
import isodate
from datetime import timedelta
from googleapiclient.discovery import build
import yt_dlp # 需要导入 yt_dlp
import os

# --- Helper Functions ---
def _format_duration(duration_str):
    """将 ISO 8601 时长字符串转换为 HH:MM:SS 或 MM:SS 格式。"""
    # ... (代码同上, 省略) ...
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

def _format_large_number(num_str):
     """格式化数字，如果太大则显示 K, M, B"""
     # ... (代码同上, 省略) ...
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

# --- Search Function ---
def search_videos(api_key, query, max_results=50):
    """
    使用 YouTube Data API 搜索视频并获取详细信息。
    返回: (list | None, str | None) - (结果列表, 错误消息)
    """
    # ... (代码同上, 省略) ...
    if not api_key or api_key == 'YOUR_YOUTUBE_DATA_API_KEY_HERE':
        return None, "无效或未配置 YouTube API Key。"

    try:
        youtube = build('youtube', 'v3', developerKey=api_key)

        search_request = youtube.search().list(
            part='snippet',
            q=query,
            type='video',
            maxResults=max_results
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
                 print(f"警告: 发现无效的 YouTube 搜索结果项: {item}")

        if not video_ids:
             return [], None

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

                 view_count = _format_large_number(stats.get('viewCount'))
                 like_count = _format_large_number(stats.get('likeCount'))
                 favorite_count = 'N/A'
                 comment_count = _format_large_number(stats.get('commentCount', '0'))
                 duration = _format_duration(content.get('duration'))

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

        return detailed_videos_info, None

    except Exception as e:
        print(f"调用 YouTube API 时出错: {e}")
        error_message = f"搜索视频时发生错误: {e}"
        if "quotaExceeded" in str(e):
             error_message = "YouTube API 配额已用尽。请稍后重试或检查您的配额限制。"
        elif "invalidKey" in str(e):
             error_message = "无效的 YouTube API Key。请检查 config.json 中的配置。"
        elif "accessNotConfigured" in str(e) or "forbidden" in str(e).lower():
             error_message = "YouTube API 未启用或无权访问。请检查 Google Cloud 项目设置。"
        return None, error_message

# --- Download Logic ---

# 全局变量存储回调函数，以便 progress_hook 可以访问
_progress_callback = None

def _youtube_progress_hook(d):
    """yt-dlp 进度回调钩子，处理数据并调用外部回调。"""
    global _progress_callback
    if not _progress_callback:
        return

    video_id = d.get('info_dict', {}).get('id')
    status = d['status']
    progress_data = {'id': video_id, 'status': status}

    if status == 'downloading':
        progress_data['percent'] = d.get('_percent_str', '0%').strip()
        progress_data['size'] = d.get('_total_bytes_str') or d.get('_downloaded_bytes_str', '未知')
        progress_data['speed'] = d.get('_speed_str', 'N/A')
        progress_data['eta'] = d.get('_eta_str', 'N/A')
        progress_data['filename'] = os.path.basename(d.get('filename', ''))
    elif status == 'finished':
        progress_data['filename'] = os.path.basename(d.get('filename', ''))
        progress_data['size'] = d.get('_total_bytes_str', '未知')
        progress_data['description'] = '合并/转换中...' if d.get('postprocessor') else '完成'
    elif status == 'error':
        progress_data['description'] = str(d.get('error', '下载错误'))[:100]

    # 调用外部传入的回调函数
    try:
        _progress_callback(progress_data)
    except Exception as cb_e:
        print(f"调用进度回调时出错: {cb_e}")

def download_videos(video_ids, output_path, progress_callback=None):
    """
    使用 yt-dlp 下载指定的 YouTube 视频列表。

    参数:
        video_ids (list): 包含视频 ID 的列表。
        output_path (str): 视频保存的目录路径。
        progress_callback (callable, optional): 用于报告进度的回调函数。
                                                接收一个包含进度信息的字典参数。
                                                例如: {'id': 'xxx', 'status': 'downloading', 'percent': '50.0%', ...}

    返回:
        tuple: (成功数量, 失败数量)
    """
    global _progress_callback
    _progress_callback = progress_callback # 将回调存储在全局变量中

    ydl_opts = {
        'outtmpl': os.path.join(output_path, '%(title)s [%(id)s].%(ext)s'),
        'progress_hooks': [_youtube_progress_hook], # 使用内部钩子
        'quiet': False,
        'noplaylist': True,
        'encoding': 'utf-8',
        'nocheckcertificate': True,
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'ignoreerrors': True, # 重要：忽略单个错误，继续下载
        # 'ffmpeg_location': '/path/to/ffmpeg', # 如有需要，取消注释并设置路径
    }

    download_success_count = 0
    download_error_count = 0
    final_statuses = {} # 用于存储每个视频的最终状态

    # 在调用 _youtube_progress_hook 之前设置最终状态的回调
    def set_final_status(data):
        nonlocal final_statuses
        vid = data.get('id')
        status = data.get('status')
        if vid and status in ('finished', 'error'):
             final_statuses[vid] = status
        if _progress_callback: # 调用外部回调
             _progress_callback(data)

    # 更新全局回调为包含最终状态记录的回调
    _progress_callback = set_final_status

    for video_id in video_ids:
        url = f"https://www.youtube.com/watch?v={video_id}"
        final_statuses[video_id] = 'pending' # 初始化状态

        if _progress_callback:
             _progress_callback({'id': video_id, 'status': 'preparing'}) # 报告准备下载状态

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # download 调用会触发 progress_hook
                ydl.download([url])
        except Exception as e: # 捕捉 yt-dlp 初始化等非下载过程中的错误
            print(f"下载视频 {url} 时发生严重初始化错误: {e}")
            final_statuses[video_id] = 'error'
            if _progress_callback:
                 _progress_callback({'id': video_id, 'status': 'error', 'description': str(e)[:100]})

    # 根据最终状态计数
    for vid, status in final_statuses.items():
        # 'finished' 且没有后处理步骤的算成功，或者描述是 '完成'
        hook_data_finished = {'id': vid, 'status': 'finished'}
        # _youtube_progress_hook(hook_data_finished) # 不能直接调用，需要从yt-dlp触发
        # 这里需要一种方法来确定 'finished' 是否真的成功
        # 简化：暂时认为只要状态不是 error 就是成功 (可能需要改进)
        if status != 'error':
            download_success_count += 1
        else:
            download_error_count += 1

    # 清理全局回调
    _progress_callback = None
    return download_success_count, download_error_count


# --- 可选的测试代码 ---
if __name__ == '__main__':
     # 测试下载
     def my_test_progress_callback(data):
         print(f"下载进度: ID={data.get('id')}, Status={data.get('status')}, "
               f"Percent={data.get('percent', '')}, Speed={data.get('speed', '')}, ETA={data.get('eta', '')}")

     test_video_ids = ['dQw4w9WgXcQ', 'invalid_id_test'] # 一个有效ID，一个无效ID
     test_output_path = 'test_download'
     os.makedirs(test_output_path, exist_ok=True)
     print(f"\n测试下载到: {test_output_path}")
     success, error = download_videos(test_video_ids, test_output_path, my_test_progress_callback)
     print(f"\n下载测试完成 - 成功: {success}, 失败: {error}")

     # ... (搜索测试代码保持不变) ...