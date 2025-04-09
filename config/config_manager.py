import json
import os
import shutil

class ConfigManager:
    """负责加载、保存和管理应用程序的配置。"""

    def __init__(self, config_file='config.json', example_config_file='config.example.json'):
        """
        初始化 ConfigManager。

        参数:
            config_file (str): 主配置文件的名称。
            example_config_file (str): 示例配置文件的名称。
        """
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.config_path = os.path.join(script_dir, config_file)
        self.example_config_path = os.path.join(script_dir, example_config_file)
        self.config = self.load_config()

    def load_config(self):
        """
        加载配置文件。如果配置文件不存在，则尝试从示例文件创建。

        返回:
            dict: 加载的配置信息。
        """
        if not os.path.exists(self.config_path):
            print(f"配置文件 {self.config_path} 不存在，尝试从示例文件创建...")
            if os.path.exists(self.example_config_path):
                try:
                    shutil.copyfile(self.example_config_path, self.config_path)
                    print(f"已从 {self.example_config_path} 创建配置文件 {self.config_path}。请填入您的 API Key。")
                    # 首次创建后，仍然尝试加载一次, 需要读取刚创建的文件
                    with open(self.config_path, 'r', encoding='utf-8') as f:
                         return json.load(f)
                except Exception as e:
                    print(f"从示例文件创建或加载配置文件失败: {e}")
                    return self._get_default_config() # 返回默认空配置
            else:
                print(f"警告: 示例配置文件 {self.example_config_path} 也不存在。将使用默认空配置。")
                return self._get_default_config() # 示例文件也不在，返回空配置

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
                # 可以在这里添加配置项校验逻辑
                return config_data
        except json.JSONDecodeError:
            print(f"错误: 配置文件 {self.config_path} 格式错误，无法解析。")
            # 可以考虑加载默认配置或抛出异常
            return self._get_default_config()
        except Exception as e:
            print(f"加载配置文件时出错: {e}")
            return self._get_default_config()

    def save_config(self):
        """将当前配置保存到文件。"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            return True, None # 修改：成功时返回 True 和 None
        except Exception as e:
            error_msg = f"保存配置文件时出错: {e}"
            print(error_msg)
            return False, error_msg # 修改：失败时返回 False 和错误信息

    def get_config(self, key, default=None):
        """
        获取指定键的配置值。

        参数:
            key (str): 配置项的键。
            default: 如果键不存在时返回的默认值。

        返回:
            配置项的值或默认值。
        """
        return self.config.get(key, default)

    def update_config(self, key, value):
        """
        更新单个配置项并保存。

        参数:
            key (str): 要更新的配置项的键。
            value: 新的配置值。
        """
        self.config[key] = value
        self.save_config()

    def update_multiple_configs(self, updates):
        """
        批量更新多个配置项并保存一次。

        参数:
            updates (dict): 包含要更新的键值对的字典。
        返回:
            tuple[bool, str | None]: 一个元组，第一个元素表示是否成功，
                                      第二个元素在失败时包含错误信息。
        """
        self.config.update(updates)
        return self.save_config() # 修改：直接返回 save_config 的结果

    def _get_default_config(self):
        """返回一个默认的空配置字典。"""
        # 实际应用中可以定义更复杂的默认结构
        return {"api_key": ""} # 移除 default_download_path

# 可以在此添加简单的测试代码
if __name__ == '__main__':
    config_manager = ConfigManager()
    print("当前配置:", config_manager.config)
    # 测试获取
    api_key = config_manager.get_config('api_key')
    print("API Key:", api_key if api_key else "未设置")
    # 测试更新
    # config_manager.update_config('test_key', 'test_value')
    # print("更新后配置:", config_manager.config)