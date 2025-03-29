# ui/youtube_tab.py - YouTube Tab UI Definition
import tkinter as tk
from tkinter import ttk

def create_tab(notebook, app):
    """创建并返回 YouTube 标签页的 Frame。"""
    youtube_tab = ttk.Frame(notebook, padding="10")

    # --- 控件定义 ---
    # 搜索关键词
    keyword_label = tk.Label(youtube_tab, text="搜索关键词 (多个用空格分隔):")
    # 注意：控件引用存储在 app 实例上，以便主逻辑访问
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
    app.youtube_search_frame = ttk.LabelFrame(youtube_tab, text="搜索结果")
    search_cols = ('name', 'views', 'likes', 'favorites', 'comments', 'published', 'duration')
    app.youtube_search_tree = ttk.Treeview(app.youtube_search_frame, columns=search_cols, show='headings', height=5)

    # --- 配置搜索结果 Treeview ---
    _setup_search_tree_columns(app.youtube_search_tree, search_cols) # 调用辅助函数

    search_scrollbar = ttk.Scrollbar(app.youtube_search_frame, orient=tk.VERTICAL, command=app.youtube_search_tree.yview)
    app.youtube_search_tree.configure(yscrollcommand=search_scrollbar.set)


    # 按钮 (command 指向 app 实例的方法)
    app.youtube_search_button = tk.Button(youtube_tab, text="搜索视频", command=app.handle_search)
    app.youtube_add_button = tk.Button(youtube_tab, text="添加到下载列表", command=app.add_selected_to_download)
    # 全局开始下载按钮在 MainWindow 中，这里不需要单独的下载按钮
    # app.youtube_download_button = tk.Button(youtube_tab, text="开始下载", command=app.start_selected_downloads)


    # --- YouTube 标签页内部布局 ---
    # 配置列权重
    youtube_tab.columnconfigure(0, weight=0) # 标签列
    youtube_tab.columnconfigure(1, weight=1) # 输入框/下拉框列 (主要拉伸)
    youtube_tab.columnconfigure(2, weight=0) # 按钮列
    youtube_tab.columnconfigure(3, weight=0) # 按钮列
    # 配置行权重
    youtube_tab.rowconfigure(4, weight=1)    # 搜索结果表格行

    # 第 0 行: 关键词标签
    keyword_label.grid(row=0, column=0, columnspan=4, sticky=tk.W, padx=10, pady=(5, 0))

    # 第 1 行: 关键词输入框 + 搜索按钮
    app.youtube_keyword_entry.grid(row=1, column=0, columnspan=3, sticky=tk.EW, padx=(10, 5), pady=5)
    app.youtube_search_button.grid(row=1, column=3, sticky=tk.E, padx=(0, 10), pady=5)

    # 第 2 行: 时长筛选 + 添加按钮 (移除下载按钮)
    duration_label.grid(row=2, column=0, sticky=tk.E, padx=(10, 5), pady=5)
    duration_combo.grid(row=2, column=1, sticky=tk.W, padx=(0, 5), pady=5)
    app.youtube_add_button.grid(row=2, column=2, columnspan=2, sticky=tk.E, padx=(5, 10), pady=5) # 占两列靠右

    # 第 3 行: 排序筛选
    order_label.grid(row=3, column=0, sticky=tk.E, padx=(10, 5), pady=5)
    order_combo.grid(row=3, column=1, sticky=tk.W, padx=(0, 5), pady=5)

    # 第 4 行: 搜索结果表格
    app.youtube_search_frame.grid(row=4, column=0, columnspan=4, sticky='nsew', padx=10, pady=5)
    app.youtube_search_tree.grid(row=0, column=0, sticky='nsew') # Treeview 在 Frame 内
    search_scrollbar.grid(row=0, column=1, sticky='ns')    # Scrollbar 在 Frame 内
    app.youtube_search_frame.grid_rowconfigure(0, weight=1) # 让 Treeview 行在 Frame 内拉伸
    app.youtube_search_frame.grid_columnconfigure(0, weight=1) # 让 Treeview 列在 Frame 内拉伸

    return youtube_tab

def _setup_search_tree_columns(tree, cols):
    """辅助函数：配置 YouTube 搜索结果 Treeview 的列。"""
    headings = {'name': '视频名称', 'views': '播放量', 'likes': '点赞量', 'favorites': '收藏量',
                'comments': '评论数', 'published': '更新时间', 'duration': '时长'}
    widths = {'name': 250, 'views': 80, 'likes': 80, 'favorites': 80, 'comments': 80,
              'published': 100, 'duration': 60}
    minwidths = {'name': 150, 'views': 60, 'likes': 60, 'favorites': 60, 'comments': 60,
                 'published': 80, 'duration': 50}
    stretches = {'name': True, 'views': False, 'likes': False, 'favorites': False, 'comments': False,
                 'published': False, 'duration': False}
    anchors = {'views': tk.E, 'likes': tk.E, 'favorites': tk.E, 'comments': tk.E, 'duration': tk.E}

    for col in cols:
        tree.heading(col, text=headings.get(col, col))
        tree.column(col, width=widths.get(col, 100), minwidth=minwidths.get(col, 40),
                      stretch=stretches.get(col, False), anchor=anchors.get(col, tk.W))


# 可选的测试代码
if __name__ == '__main__':
    root = tk.Tk()
    root.title("YouTube Tab Test")
    notebook = ttk.Notebook(root)

    # 模拟 App Controller
    class MockAppController:
        def __init__(self):
            self.root = root
            # Add attributes that create_tab expects to store controls on
            self.youtube_keyword_entry = None
            self.youtube_duration_var = None
            self.youtube_order_var = None
            self.youtube_search_frame = None
            self.youtube_search_tree = None
            self.youtube_search_button = None
            self.youtube_add_button = None
            # self.youtube_download_button = None # Removed

        # Mock methods called by buttons
        def handle_search(self):
            print("MockApp: Handle Search triggered.")
            if self.youtube_keyword_entry:
                 print(f"Keyword: {self.youtube_keyword_entry.get()}")
            if self.youtube_duration_var:
                 print(f"Duration: {self.youtube_duration_var.get()}")
            if self.youtube_order_var:
                 print(f"Order: {self.youtube_order_var.get()}")
            # Simulate adding dummy data
            if self.youtube_search_tree:
                 for i in self.youtube_search_tree.get_children(): self.youtube_search_tree.delete(i)
                 self.youtube_search_tree.insert('', tk.END, values=('Test Video 1', '1.2M', '10K', 'N/A', '1K', '2024-01-01', '05:30'), iid='vid1')
                 self.youtube_search_tree.insert('', tk.END, values=('Test Video 2', '500K', '5K', 'N/A', '500', '2024-01-02', '15:00'), iid='vid2')


        def add_selected_to_download(self):
            print("MockApp: Add Selected triggered.")
            if self.youtube_search_tree:
                 selected_ids = self.youtube_search_tree.selection()
                 print(f"Selected IDs: {selected_ids}")

        def start_selected_downloads(self): # Keep for potential future use? Or remove if truly global only
            print("MockApp: Start Download triggered (from YouTube tab - likely unused).")

    mock_app = MockAppController()
    youtube_tab_frame = create_tab(notebook, mock_app)
    notebook.add(youtube_tab_frame, text='YouTube')
    notebook.pack(expand=True, fill='both', padx=10, pady=10)

    root.geometry("800x600")
    root.mainloop()