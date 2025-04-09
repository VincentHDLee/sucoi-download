# ui/main_window.py - Main Application Window UI
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog, messagebox
import os

# 导入平台 UI 模块 (稍后用于动态加载)
# import ui.tiktok_tab as tiktok_ui
# import ui.youtube_tab as youtube_ui # (如果存在)

class MainWindow:
    """负责主应用程序窗口的创建、布局和基本 UI 事件处理。"""

    def __init__(self, root, app_controller):
        """
        初始化主窗口 UI。

        参数:
            root (tk.Tk): Tkinter 的根窗口。
            app_controller: 主应用程序逻辑控制器实例，用于回调和获取数据。
        """
        self.root = root
        self.app = app_controller # 引用主应用逻辑控制器

        # --- 初始化 ttk 样式 ---
        self.style = ttk.Style()
        # 为停止按钮配置特殊样式
        self.style.configure('Danger.TButton', foreground='black') # 前景色
        # 使用 map 配置不同状态下的背景色
        self.style.map('Danger.TButton',
                       background=[('active', '#f5c6cb'), # 鼠标悬停/按下时的颜色
                                   ('!disabled', '#f8d7da')]) # 正常状态下的颜色

        self.root.title("Sucoidownload - 模块化视频下载器")
        self.root.geometry("1280x720") # 调整初始大小

        # --- 定义通用控件变量 ---
        self.path_var = tk.StringVar() # 下载路径变量 (主窗口使用)

        # --- 创建主窗口框架 ---
        self._create_widgets()
        self._setup_layout()

        # --- 初始化和配置 ---
        self.app._initialize_download_path(self.path_var) # 请求控制器初始化路径
        self.path_var.trace_add("write", self.app.save_download_path_to_config) # 路径变化时通知控制器

        # --- 绑定事件 ---
        self.download_tree.bind('<Button-1>', self._toggle_download_selection)

    def _create_widgets(self):
        """创建窗口中的所有主要控件。"""
        # --- 顶部区域 (状态、设置) ---
        self.top_frame = ttk.Frame(self.root) # tk -> ttk
        self.status_label = ttk.Label(self.top_frame, text="状态: 就绪") # tk -> ttk
        self.settings_button = ttk.Button(self.top_frame, text="设置", command=self.open_settings_window) # tk -> ttk

        # --- 路径选择区域 ---
        self.path_frame = ttk.Frame(self.root) # tk -> ttk
        self.path_button = ttk.Button(self.path_frame, text="选择下载路径", command=self.select_path) # tk -> ttk
        self.path_entry = ttk.Entry(self.path_frame, textvariable=self.path_var) # tk -> ttk

        # --- 创建 Notebook (中部区域) ---
        self.notebook = ttk.Notebook(self.root)

        # --- 全局下载列表框架和 Treeview ---
        self.download_frame = ttk.LabelFrame(self.root, text="下载列表")
        download_cols = ('select', 'filename', 'size', 'status', 'eta', 'speed', 'platform', 'description')
        self.download_tree = ttk.Treeview(self.download_frame, columns=download_cols, show='headings', height=10)
        self._setup_download_tree_columns(download_cols) # 配置列
        self.download_scrollbar = ttk.Scrollbar(self.download_frame, orient=tk.VERTICAL, command=self.download_tree.yview)
        self.download_tree.configure(yscrollcommand=self.download_scrollbar.set)

        # --- 下载列表下方的控件 (移除进度条, 父容器改为 self.root) ---
        self.controls_frame = ttk.Frame(self.root) # tk -> ttk
        self.remove_button = ttk.Button(self.controls_frame, text="移除选中项", command=self.remove_selected_downloads) # tk -> ttk
        self.download_selected_button = ttk.Button(self.controls_frame, text="下载选中项", command=self.app.start_selected_downloads) # tk -> ttk
        # 修改：使用 ttk.Style 代替 background
        # self.stop_button = ttk.Button(...) # 停止按钮已移除

        # --- 主进度条已移除 ---

    def _setup_layout(self):
        """配置主窗口控件的布局。"""
        # --- 主窗口网格配置 ---
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=0) # top_frame
        self.root.rowconfigure(1, weight=0) # path_frame
        self.root.rowconfigure(2, weight=1) # notebook
        self.root.rowconfigure(3, weight=2) # download_frame (给它更多权重)
        # self.root.rowconfigure(4, weight=0) # progress_bar row 已移除
        self.root.rowconfigure(5, weight=0) # controls_frame row (原下载列表下方控件)

        # --- 顶部区域布局 ---
        self.top_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 0))
        self.top_frame.columnconfigure(0, weight=1) # Status label stretches
        self.top_frame.columnconfigure(1, weight=0) # Settings button doesn't stretch
        self.status_label.grid(row=0, column=0, sticky=tk.W)
        self.settings_button.grid(row=0, column=1, sticky=tk.E, padx=(10, 0))

        # --- 路径选择区域布局 ---
        self.path_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(5, 5))
        self.path_frame.columnconfigure(1, weight=1) # Entry stretches
        self.path_button.grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.path_entry.grid(row=0, column=1, sticky=tk.EW)

        # --- Notebook 布局 ---
        self.notebook.grid(row=2, column=0, sticky="nsew", padx=10, pady=5)

        # --- 下载列表布局 ---
        self.download_frame.grid(row=3, column=0, sticky='nsew', padx=10, pady=5)
        self.download_frame.grid_rowconfigure(0, weight=1) # Treeview row stretches
        self.download_frame.grid_columnconfigure(0, weight=1) # Treeview column stretches
        self.download_tree.grid(row=0, column=0, sticky='nsew')
        self.download_scrollbar.grid(row=0, column=1, sticky='ns')

        # --- 主进度条布局已移除 ---

        # --- 原下载列表下方控件布局 (现在放在主进度条下方) ---
        # 注意: 父容器已改为 self.root，所以 grid 在主窗口上
        self.controls_frame.grid(row=5, column=0, sticky=tk.EW, padx=10, pady=(0, 5))
        # 改为使用 pack 布局 controls_frame 内部的按钮，从右到左排列
        # 注意 pack 的顺序与 grid 不同，先 pack 的控件离指定边更近
        # self.stop_button.pack(...) # 停止按钮已移除
        self.download_selected_button.pack(in_=self.controls_frame, side=tk.RIGHT, padx=(5, 0))
        self.remove_button.pack(in_=self.controls_frame, side=tk.RIGHT, padx=(0, 0)) # 最右边的按钮（逻辑上是 remove）

    # --- Public Methods for Controller to Use ---

    def add_platform_tab(self, platform_name, create_tab_func):
        """
        动态添加一个平台标签页到 Notebook。

        参数:
            platform_name (str): 平台的名称 (用于标签文本)。
            create_tab_func (function): 一个函数，调用时传入 notebook 和 app controller，
                                         返回该平台 UI 的 Frame。
        """
        try:
            tab_frame = create_tab_func(self.notebook, self.app)
            self.notebook.add(tab_frame, text=platform_name)
            # 可以考虑存储 tab_frame 引用，如果需要单独控制
            print(f"成功添加 '{platform_name}' 标签页 UI。")
            return tab_frame # 返回创建的 Frame
        except Exception as e:
            print(f"添加 {platform_name} 标签页 UI 时出错: {e}")
            self._add_error_tab(platform_name, f"加载界面失败:\n{e}")
            return None

    def update_status_bar(self, message):
        """更新状态栏文本。"""
        self.status_label.config(text=str(message)) # 直接显示传入的消息
        self.root.update_idletasks() # 强制更新界面

    def show_message(self, title, message, msg_type='info', parent=None):
        """显示消息框。"""
        parent_window = parent if parent else self.root
        if msg_type == 'info':
            messagebox.showinfo(title, message, parent=parent_window)
        elif msg_type == 'warning':
            messagebox.showwarning(title, message, parent=parent_window)
        elif msg_type == 'error':
            messagebox.showerror(title, message, parent=parent_window)
        else:
            messagebox.showinfo(title, message, parent=parent_window)

    def get_download_treeview(self):
        """返回下载列表 Treeview 控件的引用。"""
        return self.download_tree

    # get_progress_bar 方法已移除

    def get_path_variable(self):
        """返回下载路径 tk.StringVar 的引用。"""
        return self.path_var

    def disable_controls(self, disable=True):
        """禁用或启用界面上的主要交互控件。"""
        state = tk.DISABLED if disable else tk.NORMAL
        # 修改：移除 self.remove_button，不再由通用逻辑禁用/启用
        # 将 stop_button 移出通用控制列表，单独处理
        widgets_to_toggle = [
            self.settings_button, self.path_button, self.download_selected_button
            # 注意：添加了 self.download_selected_button 到通用禁用列表
        ]
        # 还需要禁用/启用各个 Tab 内部的按钮，这需要在 add_platform_tab 后处理
        # 或者让 Tab UI 模块提供 enable/disable 方法

        for widget in widgets_to_toggle:
             try: widget.config(state=state)
             except (AttributeError, tk.TclError): pass # 忽略控件不存在或已销毁的错误

        # 禁用/启用 Notebook 标签切换 (可选)
        # try: self.notebook.config(state=state)
        # except tk.TclError: pass

    # --- UI Helper and Internal Methods ---

    def _setup_download_tree_columns(self, cols):
        """配置下载列表 Treeview 的列。"""
        headings = {'select': '选择', 'filename': '文件名', 'size': '大小', 'status': '状态',
                    'eta': '剩余时间', 'speed': '传输速度', 'platform': '平台', 'description': '描述'}
        widths = {'select': 40, 'filename': 250, 'size': 80, 'status': 100, 'eta': 80,
                  'speed': 100, 'platform': 60, 'description': 150}
        minwidths = {'select': 40, 'filename': 150, 'size': 60, 'status': 80, 'eta': 60,
                     'speed': 80, 'platform': 50, 'description': 100}
        stretches = {'select': False, 'filename': True, 'size': False, 'status': False, 'eta': False,
                     'speed': False, 'platform': False, 'description': True} # 让描述列也拉伸
        anchors = {'select': tk.CENTER, 'size': tk.E, 'eta': tk.E, 'speed': tk.E}
        for col in cols:
            self.download_tree.heading(col, text=headings.get(col, col))
            self.download_tree.column(col, width=widths.get(col, 100), minwidth=minwidths.get(col, 40),
                                      stretch=stretches.get(col, False), anchor=anchors.get(col, tk.W))

    def _add_error_tab(self, name, error_message):
        """在 Notebook 中添加一个显示错误的标签页"""
        error_tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(error_tab, text=f'{name} (错误)')
        ttk.Label(error_tab, text=error_message, foreground="red").pack(padx=5, pady=5)

    def select_path(self):
        """打开文件夹选择对话框，更新路径输入框"""
        folder = filedialog.askdirectory(parent=self.root) # 指定父窗口
        if folder:
            self.path_var.set(os.path.abspath(folder)) # 更新变量，会自动触发 trace 回调

    def _toggle_download_selection(self, event):
        """处理下载列表 Treeview 的点击事件，切换第一列的选择状态。"""
        region = self.download_tree.identify_region(event.x, event.y)
        if region != "cell": return
        column = self.download_tree.identify_column(event.x)
        if column != '#1': return # '#1' 是 Treeview 的第一列标识符
        item_iid = self.download_tree.identify_row(event.y)
        if not item_iid: return

        current_value = self.download_tree.set(item_iid, column='select')
        new_value = '☑' if current_value == '☐' else '☐'
        self.download_tree.set(item_iid, column='select', value=new_value)

    def remove_selected_downloads(self):
        """从下载列表中移除所有选中的项，并标记它们以便不再持久化。"""
        items_to_remove = []
        for item_iid in self.download_tree.get_children(''):
            try:
                if self.download_tree.set(item_iid, column='select') == '☑':
                    items_to_remove.append(item_iid)
            except tk.TclError: print(f"检查行 {item_iid} 的选择状态时出错。"); continue

        if not items_to_remove:
            self.show_message("提示", "没有选中的下载项可移除。")
            return

            # --- 新增：通知 Controller 标记这些项为已移除 ---
            if hasattr(self.app, 'mark_items_as_removed'):
                self.app.mark_items_as_removed(items_to_remove)
            else:
                print("警告: App Controller 没有 mark_items_as_removed 方法，无法标记移除项。")
            # -----------------------------------------
        if messagebox.askyesno("确认", f"确定要移除选中的 {len(items_to_remove)} 个下载项吗？\n（移除后下次启动不会加载）", parent=self.root):
            for item_iid in items_to_remove:
                try:
                    if self.download_tree.exists(item_iid): self.download_tree.delete(item_iid)
                except tk.TclError: print(f"移除行 {item_iid} 时出错。")
            self.update_status_bar(f"移除了 {len(items_to_remove)} 个下载项。")

    def open_settings_window(self):
        """打开设置窗口。"""
        settings_window = tk.Toplevel(self.root)
        settings_window.title("设置")
        settings_window.transient(self.root)
        settings_window.grab_set()

        settings_frame = ttk.Frame(settings_window, padding="10")
        settings_frame.pack(expand=True, fill="both")

        placeholder_api_key = "你的API key (用于YouTube)"; placeholder_color = 'grey'
        try: default_fg_color = settings_window.cget('fg')
        except tk.TclError: default_fg_color = 'black'

        # --- 定义 Tkinter 变量 ---
        api_key_var = tk.StringVar()
        concurrency_var = tk.StringVar()

        # --- API Key ---
        ttk.Label(settings_frame, text="YouTube API Key:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        api_key_entry = ttk.Entry(settings_frame, textvariable=api_key_var, width=40)
        api_key_entry.grid(row=0, column=1, columnspan=2, padx=5, pady=5, sticky=tk.EW)

        # --- 下载地址行已移除 ---

        # --- 并发下载数 (行号调整为 1) ---
        ttk.Label(settings_frame, text="最大并发下载数:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        concurrency_combobox = ttk.Combobox(
            settings_frame,
            textvariable=concurrency_var,
            values=[str(i) for i in range(1, 11)], # 1 到 10
            state='readonly',
            width=5
        )
        concurrency_combobox.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)

        # --- 下载限速行已移除 ---


        # --- 底部按钮 (行号调整为 2) ---
        button_frame_settings = ttk.Frame(settings_frame)
        button_frame_settings.grid(row=2, column=0, columnspan=3, pady=15, sticky=tk.EW) # 行号改为 2

        # 配置 button_frame_settings 的列权重，让中间列扩展
        # button_frame_settings.columnconfigure(0, weight=0) # 选择路径按钮列 (移除)
        button_frame_settings.columnconfigure(0, weight=1) # 空白列 (改为0)
        button_frame_settings.columnconfigure(1, weight=0) # 保存按钮列 (改为1)
        button_frame_settings.columnconfigure(2, weight=0) # 取消按钮列 (改为2)

        # '选择路径' 按钮已移除

        # 定义保存按钮的回调函数
        def _save_settings_action():
            api_key = api_key_var.get()
            # download_path 已移除
            concurrency = concurrency_var.get()
            print(f"Debug: Saving settings - api_key='{api_key}', concurrency='{concurrency}'")
            # 移除调用 save_settings 的 download_path 和 placeholder_pth 参数
            self.app.save_settings(
                api_key=api_key,
                concurrency_str=concurrency,
                window=settings_window,
                placeholder_api=placeholder_api_key
            )

        # 将保存按钮放在第 1 列 (改为1)
        save_button = ttk.Button(
            button_frame_settings,
            text="保存",
            command=_save_settings_action
        )
        save_button.grid(row=0, column=1, sticky=tk.E, padx=(5, 5)) # column=1

        # 将取消按钮放在第 2 列 (改为2)
        cancel_button = ttk.Button(button_frame_settings, text="取消", command=settings_window.destroy)
        cancel_button.grid(row=0, column=2, sticky=tk.E, padx=(5, 0)) # column=2

        # --- Placeholder Logic (使用 ttk.Style) ---
        placeholder_style_name = 'Placeholder.TEntry'
        normal_style_name = 'TEntry'
        style = getattr(self, 'style', ttk.Style())
        style.map(placeholder_style_name,
                  foreground=[('!disabled', 'grey')],
                  fieldbackground=[('!disabled', style.lookup('TEntry', 'fieldbackground'))])

        def setup_placeholder_logic(entry, var, placeholder_text):
            def apply_style(*args):
                try:
                    if entry.winfo_exists():
                        if var.get() == placeholder_text:
                            entry.config(style=placeholder_style_name)
                        else:
                            entry.config(style=normal_style_name)
                except tk.TclError: pass
            def on_focus_in(event=None):
                try:
                    if entry.winfo_exists() and var.get() == placeholder_text:
                        var.set('')
                        entry.config(style=normal_style_name)
                except tk.TclError: pass
            def on_focus_out(event=None):
                try:
                    if entry.winfo_exists() and not var.get():
                        var.set(placeholder_text)
                        entry.config(style=placeholder_style_name)
                    elif entry.winfo_exists():
                         entry.config(style=normal_style_name)
                except tk.TclError: pass
            entry.bind("<FocusIn>", on_focus_in, add='+')
            entry.bind("<FocusOut>", on_focus_out, add='+')
            apply_style()
            var.trace_add("write", apply_style)

        # --- 加载当前设置 ---
        current_api_key = self.app.get_config('api_key');
        # current_path 移除
        current_concurrency = self.app.get_config('max_concurrent_downloads', 3)

        # 设置 API Key 初始值
        if current_api_key and current_api_key != 'YOUR_YOUTUBE_DATA_API_KEY_HERE':
            api_key_var.set(current_api_key)
        else:
            api_key_var.set(placeholder_api_key)
        setup_placeholder_logic(api_key_entry, api_key_var, placeholder_api_key)

        # 设置下载路径初始值 (移除)

        # 恢复并发数加载
        concurrency_var.set(str(current_concurrency))

        # 定义输入校验函数 (移除)

        # 设置限速初始值 (移除)


        # 应用 Placeholder 逻辑
        setup_placeholder_logic(api_key_entry, api_key_var, placeholder_api_key)
        # setup_placeholder_logic(download_path_entry, ...) 移除

        settings_frame.columnconfigure(1, weight=1) # 让 Entry 和 Combobox 列可伸展
        settings_window.update_idletasks()

        self.center_window(settings_window)
        settings_window.resizable(False, False)

        # --- 绑定输入校验 (移除) ---

        settings_window.wait_window()

    # select_default_download_path 方法已不再需要，可以移除
    # def select_default_download_path(self, path_var, parent_window): ...

    def center_window(self, window):
        """将给定窗口在其父窗口或屏幕上居中。"""
        window.update_idletasks()
        width = window.winfo_width()
        height = window.winfo_height()
        try:
             parent = self.root
             parent_x = parent.winfo_x(); parent_y = parent.winfo_y()
             parent_width = parent.winfo_width(); parent_height = parent.winfo_height()
             x = parent_x + (parent_width // 2) - (width // 2)
             y = parent_y + (parent_height // 2) - (height // 2)
        except Exception:
             screen_width = window.winfo_screenwidth(); screen_height = window.winfo_screenheight()
             x = (screen_width // 2) - (width // 2); y = (screen_height // 2) - (height // 2)
        window.geometry(f'{width}x{height}+{x}+{y}')

# --- 用于本地测试的 Mock AppController 和主循环 ---
if __name__ == '__main__':
    class MockAppController:
        """模拟主应用程序控制器，用于 UI 测试。"""
        def __init__(self, root_window):
            self.root = root_window
            self.config = {
                'api_key': 'YOUR_YOUTUBE_DATA_API_KEY_HERE',
                'default_download_path': '',
                'max_concurrent_downloads': 3
            }
            self.download_queue_data = {}

        def _initialize_download_path(self, path_var):
            path_var.set(self.config.get('default_download_path', ''))

        def save_download_path_to_config(self, *args):
            new_path = self.root.children['!mainwindow'].path_var.get()
            self.config['default_download_path'] = new_path
            print(f"模拟保存主窗口下载路径到配置: {new_path}")

        def get_config(self, key, default=None):
            return self.config.get(key, default)

        def request_cancel(self):
            print("模拟请求停止下载")
            self.root.children['!mainwindow'].update_status_bar("停止请求已发送...")

        # 修改 save_settings 签名，移除 download_path, placeholder_pth
        def save_settings(self, *, api_key, concurrency_str, window, placeholder_api):
             try:
                concurrency = int(concurrency_str)
                if not 1 <= concurrency <= 10: raise ValueError("并发数必须在 1 到 10 之间")
                self.config['max_concurrent_downloads'] = concurrency
             except ValueError as e:
                messagebox.showerror("错误", f"无效的并发下载数: {e}", parent=window)
                return

             self.config['api_key'] = api_key if api_key != placeholder_api else ''
             # download_path 不再从此窗口保存

             print("模拟保存设置:", self.config)
             messagebox.showinfo("成功", "设置已保存。", parent=window)
             window.destroy()

        def start_selected_downloads(self):
            print("模拟开始下载选中项")

        def mark_items_as_removed(self, item_iids):
            print(f"模拟标记移除项: {item_iids}")

        def load_tabs(self):
            try:
                from ui.tiktok_tab import create_tiktok_tab
                main_window = self.root.children['!mainwindow']
                main_window.add_platform_tab("TikTok", create_tiktok_tab)
                print("TikTok 标签页尝试加载")
            except ImportError as e: print(f"无法导入 TikTok UI 模块: {e}")
            except KeyError: print("无法找到 MainWindow 实例")

    root = tk.Tk()
    mock_app = MockAppController(root)
    main_window = MainWindow(root, mock_app)
    mock_app.load_tabs()
    root.mainloop()