# ui/tiktok_tab.py - TikTok Tab UI Definition
import tkinter as tk
from tkinter import ttk
# 注意：这里的 command 需要调用 logic.py 中的函数，稍后处理 import 和连接
# from ..modules.tiktok import logic # 示例：可能的相对导入

def create_tab(notebook, main_app_instance):
    """创建并返回 TikTok 标签页的 Frame。"""
    # 使用 ttk.Frame 并增加内边距
    tiktok_frame = ttk.Frame(notebook, padding="15") # 增加 padding

    # --- TikTok 控件定义 ---
    # 使用 ttk.Label
    url_label = ttk.Label(tiktok_frame, text="输入 TikTok 视频 URL (每行一个):")
    # 为 Text 组件创建包含滚动条的外部 Frame
    text_frame = ttk.Frame(tiktok_frame)
    url_text = tk.Text(text_frame, height=10, width=60, relief=tk.SUNKEN, borderwidth=1) # 调整宽度，添加边框
    url_scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=url_text.yview)
    url_text.configure(yscrollcommand=url_scrollbar.set)

    # 使用 ttk.Frame 容纳按钮
    button_frame = ttk.Frame(tiktok_frame)
    # 使用 ttk.Button
    add_button = ttk.Button(button_frame, text="添加到下载队列", command=lambda: print("Add to queue placeholder")) # 临时占位
    download_now_button = ttk.Button(button_frame, text="立即下载", command=lambda: print("Download now placeholder")) # 临时占位

    # --- TikTok 布局 ---
    # 标签布局
    url_label.grid(row=0, column=0, sticky=tk.W, padx=0, pady=(0, 5)) # 调整间距

    # 文本框和滚动条布局
    text_frame.grid(row=1, column=0, sticky="nsew", pady=5)
    text_frame.rowconfigure(0, weight=1)
    text_frame.columnconfigure(0, weight=1)
    url_text.grid(row=0, column=0, sticky="nsew")
    url_scrollbar.grid(row=0, column=1, sticky="ns")

    # 按钮框架布局
    button_frame.grid(row=2, column=0, pady=(15, 0), sticky="ew") # 增加上方间距
    # 让按钮居中显示，而不是拉伸
    button_frame.columnconfigure(0, weight=1) # 左侧空白
    button_frame.columnconfigure(1, weight=0) # 添加按钮
    button_frame.columnconfigure(2, weight=0) # 下载按钮
    button_frame.columnconfigure(3, weight=1) # 右侧空白
    add_button.grid(row=0, column=1, padx=(0, 5), pady=5, sticky="ew") # 按钮间加点间距
    download_now_button.grid(row=0, column=2, padx=(5, 0), pady=5, sticky="ew")

    # 配置 TikTok Frame 的网格权重
    tiktok_frame.rowconfigure(1, weight=1) # 让 Text frame 可垂直扩展
    tiktok_frame.columnconfigure(0, weight=1) # 让 Text frame 可水平扩展

    # 将需要交互的控件附加到 frame 或 main_app_instance 上
    tiktok_frame.url_text = url_text # 暴露 url_text

    # 在创建时将按钮命令连接到 logic (需要先调整 import)
    # 注意：lambda 中直接使用 logic.add_tiktok_urls 可能导致作用域问题
    # 需要确保 lambda 创建时 logic 模块已导入
    # 更好的方式是在 main_app 中创建 tab 后再配置 command
    # 导入 tkinter.messagebox 以便在逻辑加载失败时显示错误
    from tkinter import messagebox

    def _extract_urls_from_text(text_widget):
        """从 Text 控件提取、清洗 URL 列表。"""
        urls_text = text_widget.get("1.0", tk.END).strip()
        if not urls_text:
            return []
        urls = urls_text.splitlines()
        return [url.strip() for url in urls if url.strip()]

    def setup_commands():
        try:
            from ..modules.tiktok import logic # 尝试相对导入
            # 修改：先提取 URL 列表再传递给 logic 函数
            add_button.config(command=lambda: logic.add_tiktok_urls(_extract_urls_from_text(url_text), main_app_instance))
            download_now_button.config(command=lambda: logic.download_tiktok_urls(_extract_urls_from_text(url_text), main_app_instance))
            print("TikTok tab commands configured using relative import.")
        except ImportError:
             try:
                 # 如果在顶层运行 ui 文件测试，可能需要不同的导入方式
                 import modules.tiktok.logic as logic
                 # 修改：先提取 URL 列表再传递给 logic 函数
                 add_button.config(command=lambda: logic.add_tiktok_urls(_extract_urls_from_text(url_text), main_app_instance))
                 download_now_button.config(command=lambda: logic.download_tiktok_urls(_extract_urls_from_text(url_text), main_app_instance))
                 print("TikTok tab commands configured using direct import (fallback).")
             except ImportError as e:
                 print(f"Error configuring TikTok commands: Could not import TikTok logic. {e}")
                 # 保留占位符命令，使用 messagebox 显示错误
                 add_button.config(command=lambda: messagebox.showerror("错误", "无法加载 TikTok 添加逻辑"))
                 download_now_button.config(command=lambda: messagebox.showerror("错误", "无法加载 TikTok 下载逻辑"))

    # 延迟配置 command，尝试解决导入顺序问题
    # 注意: 更好的方式是由 main_app 负责创建 tab 和配置 command
    tiktok_frame.after(100, setup_commands)


    return tiktok_frame

# 如果需要单独测试此 UI 组件，可以在这里添加代码
if __name__ == '__main__':
    # 简单的测试窗口
    root = tk.Tk()
    root.title("TikTok Tab Test")
    notebook = ttk.Notebook(root)

    # 模拟 main_app_instance
    class MockApp:
        def __init__(self, root_window):
            self.root = root_window
            self.path_var = tk.StringVar(value='test_tiktok_ui_download')
            self.status_label = tk.Label(root_window, text="Status bar placeholder")
            self.status_label.pack(side=tk.BOTTOM, fill=tk.X)
            self.cancel_requested = False # 模拟取消状态
            print("MockApp initialized for UI test.")

        # 模拟 app 需要提供的接口给 logic
        def add_urls_to_download_queue(self, urls, platform):
            print(f"MockApp: Adding {len(urls)} URLs for {platform}")

    mock_app = MockApp(root)

    # 创建 TikTok 标签页
    tiktok_tab = create_tab(notebook, mock_app)
    notebook.add(tiktok_tab, text='TikTok')
    notebook.pack(expand=True, fill='both', padx=10, pady=10)

    # 添加一个假的 logic 模块以便 setup_commands 能工作
    import sys
    import os
    # 确保能找到 modules 目录 (假设脚本在 ui/ 目录下运行)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    modules_dir = os.path.join(project_root, 'modules')
    # 模拟一个空的 modules 包
    if not os.path.exists(os.path.join(project_root, 'modules', '__init__.py')):
         with open(os.path.join(project_root, 'modules', '__init__.py'), 'w') as f: pass
    # 模拟一个空的 tiktok 包
    if not os.path.exists(os.path.join(project_root, 'modules', 'tiktok', '__init__.py')):
         with open(os.path.join(project_root, 'modules', 'tiktok', '__init__.py'), 'w') as f: pass
    # 模拟 logic.py
    mock_logic_path = os.path.join(project_root, 'modules', 'tiktok', 'logic.py')
    if not os.path.exists(mock_logic_path):
        with open(mock_logic_path, 'w') as f:
            f.write("import tkinter.messagebox as messagebox\n")
            f.write("def add_tiktok_urls(url_widget, app):\n")
            f.write("    urls = url_widget.get('1.0', 'end').strip().splitlines()\n")
            f.write("    print(f'Mock Logic: Add {len(urls)} URLs: {urls}')\n")
            f.write("    messagebox.showinfo('Mock Logic', f'Add {len(urls)} URLs requested')\n\n")
            f.write("def download_tiktok_urls(url_widget, app):\n")
            f.write("    urls = url_widget.get('1.0', 'end').strip().splitlines()\n")
            f.write("    print(f'Mock Logic: Download {len(urls)} URLs: {urls}')\n")
            f.write("    messagebox.showinfo('Mock Logic', f'Download {len(urls)} URLs requested')\n\n")


    # 将项目根目录添加到 sys.path
    if project_root not in sys.path:
        sys.path.insert(0, project_root)


    root.geometry("600x400")
    root.mainloop()
    # 清理模拟文件
    #if os.path.exists(mock_logic_path): os.remove(mock_logic_path)
    #if os.path.exists(os.path.join(project_root, 'modules', 'tiktok', '__init__.py')): os.remove(os.path.join(project_root, 'modules', 'tiktok', '__init__.py'))
    #if os.path.exists(os.path.join(project_root, 'modules', '__init__.py')): os.remove(os.path.join(project_root, 'modules', '__init__.py'))