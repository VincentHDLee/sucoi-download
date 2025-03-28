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
            part='snippet', q=query, type='video', maxResults=max_results
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

def download_videos(video_ids, output_path, progress_callback=None):
    """
    使用 yt-dlp 下载指定的 YouTube 视频列表。
    返回: tuple (成功数量, 失败数量)
    """
    global _progress_callback
    _progress_callback = progress_callback
    # ... (ydl_opts 定义同上, 省略) ...
    ydl_opts = {
        'outtmpl': os.path.join(output_path, '%(title)s [%(id)s].%(ext)s'),
        'progress_hooks': [_youtube_progress_hook],
        'quiet': False,'noplaylist': True,'encoding': 'utf-8',
        'nocheckcertificate': True, 'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'ignoreerrors': True,
    }
    download_success_count = 0
    download_error_count = 0
    final_statuses = {}
    def set_final_status(data):
        nonlocal final_statuses
        vid = data.get('id')
        status = data.get('status')
        if vid and status in ('finished', 'error'): final_statuses[vid] = status
        if _progress_callback: _progress_callback(data)
    _progress_callback = set_final_status
    for video_id in video_ids:
        url = f"https://www.youtube.com/watch?v={video_id}"
        final_statuses[video_id] = 'pending'
        if _progress_callback: _progress_callback({'id': video_id, 'status': 'preparing'})
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
        except Exception as e:
            print(f"下载视频 {url} 时发生严重初始化错误: {e}")
            final_statuses[video_id] = 'error'
            if _progress_callback: _progress_callback({'id': video_id, 'status': 'error', 'description': str(e)[:100]})
    for vid, status in final_statuses.items():
        if status != 'error': download_success_count += 1
        else: download_error_count += 1
    _progress_callback = None
    return download_success_count, download_error_count

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

    # 筛选条件放在第 2, 3 行
    duration_label.grid(row=2, column=0, sticky=tk.W, padx=(10,0), pady=5)
    duration_combo.grid(row=2, column=1, columnspan=4, sticky=tk.EW, padx=(0,10), pady=5)
    order_label.grid(row=3, column=0, sticky=tk.W, padx=(10,0), pady=5)
    order_combo.grid(row=3, column=1, columnspan=4, sticky=tk.EW, padx=(0,10), pady=5)

    # 搜索结果表格放在第 4 行
    app.youtube_search_frame.grid(row=4, column=0, columnspan=5, sticky='nsew', padx=10, pady=5)

    return youtube_tab

# --- 可选的测试代码 ---
if __name__ == '__main__':
     # ... (下载测试代码保持不变) ...
     # ... (搜索测试代码保持不变) ...
     pass # 避免语法错误