# youtube.py - YouTube Platform Specific Logic
import tkinter as tk
from tkinter import ttk
import isodate
from datetime import timedelta
from googleapiclient.discovery import build
import yt_dlp
import os

# --- Helper Functions ---
def _format_duration(duration_str):
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

def _format_large_number(num_str):
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

# --- Search Function ---
def search_videos(api_key, query, max_results=50, video_duration='any', order='relevance'):
    """
    使用 YouTube Data API 搜索视频并获取详细信息。
    支持按时长和排序方式筛选。
    返回: (list | None, str | None) - (结果列表, 错误消息)
    """
    if not api_key or api_key == 'YOUR_YOUTUBE_DATA_API_KEY_HERE':
        return None, "无效或未配置 YouTube API Key。"
    try:
        youtube = build('youtube', 'v3', developerKey=api_key)

        # 构建基础搜索参数
        search_params = {
            'part': 'snippet',
            'q': query,
            'type': 'video',
            'maxResults': max_results,
            'order': order  # 始终传递 order 参数
        }
        # 仅当 video_duration 不是默认值 'any' 时才添加 videoDuration 参数
        if video_duration != 'any':
            search_params['videoDuration'] = video_duration

        # 使用解包方式传递参数
        search_request = youtube.search().list(**search_params)
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
        if not video_ids: return [], None
        detailed_videos_info = []
        batch_size = 50
        for i in range(0, len(video_ids), batch_size):
             batch_ids = video_ids[i:i + batch_size]
             ids_str = ','.join(batch_ids)
             video_request = youtube.videos().list(
                 part='snippet,statistics,contentDetails', id=ids_str
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
                     'id': vid,'name': title,'views': view_count, 'likes': like_count,
                     'favorites': favorite_count, 'comments': comment_count,
                     'published': published_display, 'duration': duration
                 })
        return detailed_videos_info, None
    except Exception as e:
        print(f"调用 YouTube API 时出错: {e}")
        error_message = f"搜索视频时发生错误: {e}"
        if "quotaExceeded" in str(e): error_message = "YouTube API 配额已用尽。"
        elif "invalidKey" in str(e): error_message = "无效的 YouTube API Key。"
        elif "accessNotConfigured" in str(e) or "forbidden" in str(e).lower(): error_message = "YouTube API 未启用或无权访问。"
        return None, error_message

# --- Download Logic ---
_progress_callback = None
def _youtube_progress_hook(d):
    """yt-dlp 进度回调钩子，处理数据并调用外部回调。"""
    global _progress_callback
    if not _progress_callback: return
    # ... (代码同上, 省略) ...
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
    try: _progress_callback(progress_data)
    except Exception as cb_e: print(f"调用进度回调时出错: {cb_e}")

def download_videos(app, video_ids, output_path, progress_callback=None): # 添加 app 参数
    """
    使用 yt-dlp 下载指定的 YouTube 视频列表。
    支持通过 app.cancel_requested 标志中断。
    返回: tuple (成功数量, 失败/取消数量)
    """
    global _progress_callback # 注意: global 在这里可能不是最佳实践，但暂不修改
    original_callback = progress_callback # 保存原始回调
    final_statuses = {} # 用于记录每个视频的最终状态 (finished, error, cancelled)

    # 包装回调，用于记录最终状态并调用原始回调
    def status_recorder_callback(data):
        nonlocal final_statuses
        vid = data.get('info_dict', {}).get('id') or data.get('id') # 尝试从 info_dict 获取 ID
        status = data.get('status')
        if vid and status in ('finished', 'error'):
            final_statuses[vid] = status
            # print(f"记录最终状态: {vid} -> {status}") # 调试用
        if original_callback:
            try:
                original_callback(data) # 调用原始回调传递给主程序
            except Exception as cb_e:
                 print(f"原始回调出错: {cb_e}")

    _progress_callback = status_recorder_callback # 在下载期间使用包装后的回调

    ydl_opts = {
        'outtmpl': os.path.join(output_path, '%(title)s [%(id)s].%(ext)s'),
        'progress_hooks': [_youtube_progress_hook], # 钩子内部会调用 _progress_callback
        'quiet': False,'noplaylist': True,'encoding': 'utf-8',
        'nocheckcertificate': True, 'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'ignoreerrors': True, # 使得即使部分下载失败，循环也能继续
    }

    processed_count = 0
    for index, video_id in enumerate(video_ids):
        # 在每次循环开始时检查取消标志
        if app.cancel_requested:
            print(f"下载任务被用户取消。停止处理 video_id: {video_id}")
            # 将剩余未处理的任务标记为取消
            remaining_ids = video_ids[index:]
            for rem_id in remaining_ids:
                if rem_id not in final_statuses: # 避免覆盖已完成或已出错的状态
                     final_statuses[rem_id] = 'cancelled'
                     if _progress_callback:
                          _progress_callback({'id': rem_id, 'status': 'error', 'description': '用户取消'})
            break # 跳出循环

        url = f"https://www.youtube.com/watch?v={video_id}"
        if video_id not in final_statuses: # 可能在钩子中已被标记为 error
            final_statuses[video_id] = 'pending' # 初始化状态
        if _progress_callback:
            _progress_callback({'id': video_id, 'status': 'preparing'})
        try:
            # 为每个视频创建一个新的 YoutubeDL 实例，避免状态污染
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
                # 下载成功与否最终由 status_recorder_callback 记录到 final_statuses
        except Exception as e:
            # 捕获初始化或下载过程中的严重错误
            print(f"下载视频 {url} 时发生严重错误: {e}")
            final_statuses[video_id] = 'error' # 标记为错误
            if _progress_callback:
                _progress_callback({'id': video_id, 'status': 'error', 'description': str(e)[:100]})
        processed_count += 1

    # 根据最终记录的状态统计成功和失败/取消
    actual_success = 0
    actual_error_or_cancelled = 0
    for vid in video_ids:
        status = final_statuses.get(vid, 'unknown') # 获取最终状态
        if status == 'finished':
            actual_success += 1
        else: # pending, error, cancelled, unknown 都算作失败/取消
            actual_error_or_cancelled += 1
            if status == 'unknown' and vid in video_ids[:processed_count]: # 如果处理过但没记录到状态，也算错误
                print(f"警告: 视频 {vid} 状态未知，计为错误。")

    _progress_callback = original_callback # 恢复原始回调，以防万一
    return actual_success, actual_error_or_cancelled

# --- GUI Creation ---
def create_tab(notebook, app):
    """创建并返回 YouTube 标签页的 Frame。"""
    youtube_tab = ttk.Frame(notebook, padding="10")

    # --- 控件定义 (从 sucoidownload.py 迁移) ---
    # 搜索关键词
    keyword_label = tk.Label(youtube_tab, text="搜索关键词 (多个用空格分隔):")
    # 注意：keyword_entry 需要能在主程序中访问，以便 handle_search 获取值
    # 将其存储在 app 实例上
    app.youtube_keyword_entry = tk.Entry(youtube_tab)

    # 筛选条件
    duration_label = tk.Label(youtube_tab, text="时长:")
    app.youtube_duration_var = tk.StringVar() # 存储在 app 上
    duration_combo = ttk.Combobox(youtube_tab, textvariable=app.youtube_duration_var,
                                       values=["任意", "短片 (<4分钟)", "中等 (4-20分钟)", "长片 (>20分钟)"],
                                       state='readonly')
    duration_combo.current(0)

    order_label = tk.Label(youtube_tab, text="排序:")
    app.youtube_order_var = tk.StringVar() # 存储在 app 上
    order_combo = ttk.Combobox(youtube_tab, textvariable=app.youtube_order_var,
                                    values=["相关性", "上传日期", "观看次数", "评分"],
                                    state='readonly')
    order_combo.current(0)

    # 搜索结果框架和 Treeview
    # 注意：search_frame 和 search_tree 需要能在主程序中访问
    app.youtube_search_frame = ttk.LabelFrame(youtube_tab, text="搜索结果")
    search_cols = ('name', 'views', 'likes', 'favorites', 'comments', 'published', 'duration')
    app.youtube_search_tree = ttk.Treeview(app.youtube_search_frame, columns=search_cols, show='headings', height=5)

    app.youtube_search_tree.heading('name', text='视频名称')
    # ... (其他 heading 和 column 定义) ...
    app.youtube_search_tree.heading('views', text='播放量')
    app.youtube_search_tree.heading('likes', text='点赞量')
    app.youtube_search_tree.heading('favorites', text='收藏量')
    app.youtube_search_tree.heading('comments', text='评论数')
    app.youtube_search_tree.heading('published', text='更新时间')
    app.youtube_search_tree.heading('duration', text='时长')
    app.youtube_search_tree.column('name', width=200, stretch=True)
    app.youtube_search_tree.column('views', width=80, anchor=tk.E, stretch=False)
    app.youtube_search_tree.column('likes', width=80, anchor=tk.E, stretch=False)
    app.youtube_search_tree.column('favorites', width=80, anchor=tk.E, stretch=False)
    app.youtube_search_tree.column('comments', width=80, anchor=tk.E, stretch=False)
    app.youtube_search_tree.column('published', width=100, stretch=False)
    app.youtube_search_tree.column('duration', width=60, anchor=tk.E, stretch=False)

    search_scrollbar = ttk.Scrollbar(app.youtube_search_frame, orient=tk.VERTICAL, command=app.youtube_search_tree.yview)
    app.youtube_search_tree.configure(yscrollcommand=search_scrollbar.set)
    app.youtube_search_tree.grid(row=0, column=0, sticky='nsew')
    search_scrollbar.grid(row=0, column=1, sticky='ns')
    app.youtube_search_frame.grid_rowconfigure(0, weight=1)
    app.youtube_search_frame.grid_columnconfigure(0, weight=1)

    # 按钮 (command 指向 app 实例的方法)
    # 注意: 这些按钮也需要能在主程序中访问以禁用/启用
    app.youtube_search_button = tk.Button(youtube_tab, text="搜索视频", command=app.handle_search)
    app.youtube_add_button = tk.Button(youtube_tab, text="添加到下载列表", command=app.add_selected_to_download)
    # 注意：全局的下载按钮可能更合适，这里暂时保留，指向主程序方法
    app.youtube_download_button = tk.Button(youtube_tab, text="开始下载", command=app.start_download)


    # --- YouTube 标签页内部布局 ---
    youtube_tab.columnconfigure(0, weight=1) # 搜索框/表格列
    # ... 配置其他需要的列 ...
    youtube_tab.columnconfigure(4, weight=0) # 最后一列按钮不扩展
    youtube_tab.rowconfigure(4, weight=1)    # 搜索结果表格行

    keyword_label.grid(row=0, column=0, columnspan=5, sticky=tk.W, padx=10, pady=(5, 0))
    app.youtube_keyword_entry.grid(row=1, column=0, columnspan=1, sticky=tk.EW, padx=(10, 5), pady=5) # 只占第一列

    # 按钮放在第 1 行
    app.youtube_search_button.grid(row=1, column=1, sticky=tk.W, padx=(0, 5), pady=5)
    app.youtube_add_button.grid(row=1, column=2, sticky=tk.W, padx=(0, 5), pady=5)
    app.youtube_download_button.grid(row=1, column=3, sticky=tk.W, padx=(0, 5), pady=5)

    # 筛选条件放在第 2 行
    duration_label.grid(row=2, column=0, sticky=tk.E, padx=(10, 5), pady=5) # 右对齐标签
    duration_combo.grid(row=2, column=1, sticky=tk.W, padx=(0, 10), pady=5) # 左对齐下拉框
    order_label.grid(row=2, column=2, sticky=tk.E, padx=(10, 5), pady=5)    # 右对齐标签
    order_combo.grid(row=2, column=3, sticky=tk.W, padx=(0, 10), pady=5)     # 左对齐下拉框

    # 搜索结果表格放在第 3 行
    app.youtube_search_frame.grid(row=3, column=0, columnspan=4, sticky='nsew', padx=10, pady=5) # 修正缩进，行号改为 3, columnspan 改为 4

    return youtube_tab

# --- 可选的测试代码 ---
if __name__ == '__main__':
     # ... (下载测试代码保持不变) ...
     # ... (搜索测试代码保持不变) ...
     pass # 避免语法错误