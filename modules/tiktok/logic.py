# modules/tiktok/logic.py - TikTok Platform Specific Business Logic
import hashlib # 用于生成 ID

# 注意：这个文件不应直接依赖 Tkinter 控件。
# 它通过 app 实例 (主程序控制器) 与 UI 和核心功能交互。

PLATFORM_NAME = "TikTok" # 定义平台名称常量

def add_tiktok_urls(urls, app):
    """
    验证 TikTok URL 列表，并请求主程序将有效的 URL 添加到下载队列。

    参数:
        urls (list[str]): 从 UI 提取并处理过的 URL 字符串列表。
        app: 主应用程序控制器实例 (SucoidownloadApp)。
             需要提供 add_urls_to_download_queue 和 show_message 方法。
    """
    if not urls:
        if hasattr(app, 'show_message'):
            # 尝试获取主窗口作为父窗口，如果可用
            parent_window = app.view.root if hasattr(app, 'view') and hasattr(app.view, 'root') else None
            app.show_message("提示", "未提供有效的 TikTok 视频 URL。", msg_type='warning', parent=parent_window)
        else:
             print("警告: 未提供有效的 TikTok 视频 URL (且无法显示消息框)。")
        return

    print(f"准备添加 {len(urls)} 个 TikTok URL 到下载队列")
    # 调用 app (主程序实例) 的方法将 urls 添加到通用下载队列 (download_tree)
    if hasattr(app, 'add_urls_to_download_queue'):
        # 传递 platform 参数很重要
        app.add_urls_to_download_queue(urls, platform=PLATFORM_NAME)
        # 由 add_urls_to_download_queue 负责显示最终状态或消息
    else:
        error_msg = "主程序缺少 'add_urls_to_download_queue' 方法。"
        print(f"错误: {error_msg}")
        if hasattr(app, 'show_message'):
            parent_window = app.view.root if hasattr(app, 'view') and hasattr(app.view, 'root') else None
            app.show_message("错误", error_msg, msg_type='error', parent=parent_window)


def download_tiktok_urls(urls, app):
    """
    准备 TikTok URL 对应的下载任务信息，并请求主程序立即开始下载。

    参数:
        urls (list[str]): 从 UI 提取并处理过的 URL 字符串列表。
        app: 主应用程序控制器实例 (SucoidownloadApp)。
             需要提供 get_download_path, start_immediate_downloads,
             update_status, show_message 方法。
    """
    if not urls:
        if hasattr(app, 'show_message'):
            parent_window = app.view.root if hasattr(app, 'view') and hasattr(app.view, 'root') else None
            app.show_message("提示", "未提供有效的 TikTok 视频 URL。", msg_type='warning', parent=parent_window)
        else:
            print("警告: 未提供有效的 TikTok 视频 URL (且无法显示消息框)。")
        return

    # 检查主程序是否提供必要方法
    required_methods = ['get_download_path', 'start_immediate_downloads', 'update_status', 'show_message']
    missing_methods = [m for m in required_methods if not hasattr(app, m)]
    if missing_methods:
         error_msg = f"主程序实例缺少必要方法: {', '.join(missing_methods)}"
         print(f"错误: {error_msg}")
         if hasattr(app, 'show_message'):
             parent_window = app.view.root if hasattr(app, 'view') and hasattr(app.view, 'root') else None
             app.show_message("错误", error_msg, msg_type='error', parent=parent_window)
         return

    # 从主程序获取保存路径
    output_path = app.get_download_path() # 注意：路径由主程序保证有效性或提供回退

    if not output_path:
        # get_download_path 内部应处理路径无效的情况并可能提示用户
        # 此处无需再次提示，主程序会处理
        return

    # --- 构造 item_info 列表 ---
    items_to_download = []
    skipped_count = 0
    for url in urls:
        # 在这里也做一次基本的 URL 格式检查
        if not url or not isinstance(url, str) or not (url.startswith("http://") or url.startswith("https://")):
             print(f"逻辑层: 跳过无效格式的 URL: {url}")
             skipped_count += 1
             continue
        try:
            # 生成唯一 ID
            url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
            item_id = f"{PLATFORM_NAME}_{url_hash}"
            item_info = {
                'id': item_id,
                'url': url,
                # output_path 由主程序的 start_immediate_downloads 统一处理/覆盖
                # 'output_path': output_path, # 不在此处设置，由调用者决定最终路径
                # 可以添加特定于 TikTok 的 ydl_opts (如果需要)
                'ydl_opts': {
                    # 例如: 'format': 'best' # TikTok 可能不需要复杂格式选择
                }
            }
            items_to_download.append(item_info)
        except Exception as e:
             print(f"为 URL '{url}' 准备下载信息时出错: {e}")
             skipped_count += 1
    # --------------------------

    if items_to_download:
        print(f"请求立即下载 {len(items_to_download)} 个 TikTok 任务...")
        # 调用主程序的方法来处理这些任务的异步执行
        app.start_immediate_downloads(items_to_download, platform=PLATFORM_NAME)
        status_msg = f"已提交 {len(items_to_download)} 个 TikTok 任务进行立即下载。"
        if skipped_count > 0:
            status_msg += f" (跳过 {skipped_count} 个无效或处理错误的 URL)"
        app.update_status(status_msg)
        # 可以考虑清空输入框，但这应由 UI 模块决定是否执行
        # app.clear_tiktok_input() # 假设 app 提供这样的接口给 UI 调用
    else:
        error_msg = "没有有效的任务可供下载。"
        if skipped_count > 0:
            error_msg += f" (跳过 {skipped_count} 个无效或处理错误的 URL)"
        if hasattr(app, 'show_message'):
            parent_window = app.view.root if hasattr(app, 'view') and hasattr(app.view, 'root') else None
            app.show_message("提示", error_msg, parent=parent_window)
        else:
            print(f"提示: {error_msg}")