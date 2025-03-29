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

        self.root.title("Sucoidownload - 模块化视频下载器")
        self.root.geometry("1280x720") # 调整初始大小

        # --- 定义通用控件变量 ---
        self.path_var = tk.StringVar() # 下载路径变量

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
        self.top_frame = tk.Frame(self.root)
        self.status_label = tk.Label(self.top_frame, text="状态: 就绪")
        self.settings_button = tk.Button(self.top_frame, text="设置", command=self.open_settings_window)

        # --- 路径选择区域 ---
        self.path_frame = tk.Frame(self.root)
        self.path_button = tk.Button(self.path_frame, text="选择下载路径", command=self.select_path)
        self.path_entry = tk.Entry(self.path_frame, textvariable=self.path_var)

        # --- 创建 Notebook (中部区域) ---
        self.notebook = ttk.Notebook(self.root)

        # --- 全局下载列表框架和 Treeview ---
        self.download_frame = ttk.LabelFrame(self.root, text="下载列表")
        download_cols = ('select', 'filename', 'size', 'status', 'eta', 'speed', 'platform', 'description')
        self.download_tree = ttk.Treeview(self.download_frame, columns=download_cols, show='headings', height=10)
        self._setup_download_tree_columns(download_cols) # 配置列
        self.download_scrollbar = ttk.Scrollbar(self.download_frame, orient=tk.VERTICAL, command=self.download_tree.yview)
        self.download_tree.configure(yscrollcommand=self.download_scrollbar.set)

        # --- 下载列表下方的控件 ---
        self.controls_frame = tk.Frame(self.download_frame)
        self.progress_bar = ttk.Progressbar(self.controls_frame, orient=tk.HORIZONTAL, length=100, mode='determinate')
        self.remove_button = tk.Button(self.controls_frame, text="移除选中项", command=self.remove_selected_downloads)
        self.stop_button = tk.Button(self.controls_frame, text="停止下载", command=self.app.request_cancel) # 通知控制器取消

    def _setup_layout(self):
        """配置主窗口控件的布局。"""
        # --- 主窗口网格配置 ---
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=0) # top_frame
        self.root.rowconfigure(1, weight=0) # path_frame
        self.root.rowconfigure(2, weight=1) # notebook
        self.root.rowconfigure(3, weight=1) # download_frame

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

        # --- 下载列表下方控件布局 ---
        self.controls_frame.grid(row=1, column=0, columnspan=2, sticky=tk.EW, padx=5, pady=5)
        self.controls_frame.columnconfigure(0, weight=1) # Progress bar stretches
        self.controls_frame.columnconfigure(1, weight=0) # Remove button doesn't stretch
        self.controls_frame.columnconfigure(2, weight=0) # Stop button doesn't stretch
        self.progress_bar.grid(row=0, column=0, sticky=tk.EW, padx=(0, 10))
        self.remove_button.grid(row=0, column=1, sticky=tk.E, padx=(0, 5))
        self.stop_button.grid(row=0, column=2, sticky=tk.E, padx=(5, 0))

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
        self.status_label.config(text=f"状态: {message}")
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

    def get_progress_bar(self):
        """返回进度条控件的引用。"""
        return self.progress_bar

    def get_path_variable(self):
        """返回下载路径 tk.StringVar 的引用。"""
        return self.path_var

    def disable_controls(self, disable=True):
        """禁用或启用界面上的主要交互控件。"""
        state = tk.DISABLED if disable else tk.NORMAL
        widgets_to_toggle = [
            self.settings_button, self.path_button, self.remove_button, self.stop_button
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
        """从下载列表中移除所有选中的项。"""
        items_to_remove = []
        for item_iid in self.download_tree.get_children(''):
            try:
                if self.download_tree.set(item_iid, column='select') == '☑':
                    items_to_remove.append(item_iid)
            except tk.TclError: print(f"检查行 {item_iid} 的选择状态时出错。"); continue

        if not items_to_remove:
            self.show_message("提示", "没有选中的下载项可移除。")
            return

        if messagebox.askyesno("确认", f"确定要移除选中的 {len(items_to_remove)} 个下载项吗？", parent=self.root):
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

        placeholder_api_key = "你的API key (用于YouTube)"; placeholder_path = "软件根目录download文件夹"; placeholder_color = 'grey'
        try: default_fg_color = settings_window.cget('fg')
        except tk.TclError: default_fg_color = 'black'

        api_key_var = tk.StringVar(); download_path_var = tk.StringVar()

        tk.Label(settings_frame, text="YouTube API Key:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        api_key_entry = tk.Entry(settings_frame, textvariable=api_key_var, width=40); api_key_entry.grid(row=0, column=1, columnspan=2, padx=5, pady=5, sticky=tk.EW)

        tk.Label(settings_frame, text="默认下载地址:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        download_path_entry = tk.Entry(settings_frame, textvariable=download_path_var, width=40); download_path_entry.grid(row=1, column=1, padx=5, pady=5, sticky=tk.EW)
        select_path_button = tk.Button(settings_frame, text="...", command=lambda: self.select_default_download_path(download_path_var, settings_window)); select_path_button.grid(row=1, column=2, padx=5, pady=5, sticky=tk.W)

        button_frame_settings = tk.Frame(settings_frame); button_frame_settings.grid(row=2, column=0, columnspan=3, pady=15)
        # 保存按钮调用 app controller 的方法
        save_button = tk.Button(button_frame_settings, text="保存", command=lambda: self.app.save_settings(api_key_var.get(), download_path_var.get(), settings_window, placeholder_api_key, placeholder_path)); save_button.pack(side=tk.LEFT, padx=10)
        cancel_button = tk.Button(button_frame_settings, text="取消", command=settings_window.destroy); cancel_button.pack(side=tk.LEFT, padx=10)

        def setup_placeholder_logic(entry, var, placeholder_text):
            def on_focus_in(event):
                if var.get() == placeholder_text: var.set(''); entry.config(fg=default_fg_color)
            def on_focus_out(event):
                if not var.get(): var.set(placeholder_text); entry.config(fg=placeholder_color)
            entry.bind("<FocusIn>", on_focus_in); entry.bind("<FocusOut>", on_focus_out)

        current_api_key = self.app.get_config('api_key'); current_path = self.app.get_config('default_download_path')
        if current_api_key and current_api_key != 'YOUR_YOUTUBE_DATA_API_KEY_HERE': api_key_var.set(current_api_key); api_key_entry.config(fg=default_fg_color)
        else: api_key_var.set(placeholder_api_key); api_key_entry.config(fg=placeholder_color)

        if current_path: download_path_var.set(current_path); download_path_entry.config(fg=default_fg_color)
        else: download_path_var.set(placeholder_path); download_path_entry.config(fg=placeholder_color)

        setup_placeholder_logic(api_key_entry, api_key_var, placeholder_api_key); setup_placeholder_logic(download_path_entry, download_path_var, placeholder_path)

        settings_frame.columnconfigure(1, weight=1); settings_window.update_idletasks()

        self.center_window(settings_window)
        settings_window.resizable(False, False)
        settings_window.wait_window()

    def select_default_download_path(self, path_var, parent_window):
        """为设置窗口中的下载路径选择文件夹。"""
        folder = filedialog.askdirectory(parent=parent_window)
        if folder: abs_path = os.path.abspath(folder); path_var.set(abs_path); parent_window.focus()

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

# 可选的测试代码
if __name__ == '__main__':
    root = tk.Tk()

    # 模拟 App Controller
    class MockAppController:
        def __init__(self, root_window):
            self.root = root_window
            self._config = {'api_key': '', 'default_download_path': ''}
            self._cancel_requested = False
            self.download_items = {} # 模拟下载列表数据

        def _initialize_download_path(self, path_var):
            path_var.set(self.get_fallback_download_path())
            print("MockApp: Initialized download path.")

        def save_download_path_to_config(self, *args):
            print("MockApp: Download path trace triggered.") # 仅打印，不真的保存

        def request_cancel(self):
            self._cancel_requested = True
            print("MockApp: Cancel requested.")
            # 在真实应用中，这里会更新 UI 状态
            self.view.update_status_bar("请求停止下载...")

        def is_cancel_requested(self):
            return self._cancel_requested

        def reset_cancel_request(self):
             self._cancel_requested = False

        def get_config(self, key, default=None):
             return self._config.get(key, default)

        def save_settings(self, api_key, download_path, window, placeholder_api, placeholder_pth):
             final_api_key = api_key if api_key != placeholder_api else ''
             final_download_path = os.path.abspath(download_path) if download_path and download_path != placeholder_pth else ''
             self._config['api_key'] = final_api_key
             self._config['default_download_path'] = final_download_path
             print(f"MockApp: Settings saved - API Key: {final_api_key}, Path: {final_download_path}")
             self.view.show_message("设置", "设置已保存（模拟）。", parent=window)
             window.destroy()

        def get_fallback_download_path(self):
            return os.path.join(os.path.dirname(__file__), "test_download_ui")

        # 模拟添加一个 TikTok 标签页
        def load_tabs(self):
            try:
                from ui import tiktok_tab # 尝试导入
                self.view.add_platform_tab("TikTok", tiktok_tab.create_tab)
            except ImportError as e:
                 print(f"Could not load TikTok tab UI: {e}")
                 self.view._add_error_tab("TikTok", f"无法加载UI模块:\n{e}")


    app_controller = MockAppController(root)
    main_window = MainWindow(root, app_controller)
    app_controller.view = main_window # 让控制器能访问视图

    # 模拟加载标签页
    app_controller.load_tabs()

    root.mainloop()