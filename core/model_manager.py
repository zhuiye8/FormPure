"""
模型管理器模块
负责管理模型的下载、存储、加载和版本控制
"""

import os
import json
import shutil
import requests
from pathlib import Path
import threading
from typing import Dict, List, Optional, Tuple, Callable
from PyQt5.QtCore import QObject, pyqtSignal

# 默认模型目录
DEFAULT_MODELS_DIR = os.path.join(os.path.expanduser("~"), ".excel_deduplication", "models")

class ModelInfo:
    """模型信息类，存储模型的元数据"""
    
    def __init__(self, 
                 model_id: str, 
                 name: str, 
                 source: str = "huggingface", 
                 version: str = "latest",
                 description: str = "",
                 size_mb: int = 0,
                 download_url: str = "",
                 local_path: str = "",
                 is_downloaded: bool = False,
                 tags: List[str] = None,
                 config: Dict = None):
        """
        初始化模型信息
        
        Args:
            model_id: 模型唯一标识
            name: 模型显示名称
            source: 模型来源，如"huggingface"
            version: 模型版本
            description: 模型描述
            size_mb: 模型大小（MB）
            download_url: 模型下载URL
            local_path: 模型本地存储路径
            is_downloaded: 是否已下载
            tags: 模型标签
            config: 模型配置
        """
        self.model_id = model_id
        self.name = name
        self.source = source
        self.version = version
        self.description = description
        self.size_mb = size_mb
        self.download_url = download_url
        self.local_path = local_path
        self.is_downloaded = is_downloaded
        self.tags = tags or []
        self.config = config or {}
    
    def to_dict(self) -> Dict:
        """转换为字典格式，用于保存"""
        return {
            "model_id": self.model_id,
            "name": self.name,
            "source": self.source,
            "version": self.version,
            "description": self.description,
            "size_mb": self.size_mb,
            "download_url": self.download_url,
            "local_path": self.local_path,
            "is_downloaded": self.is_downloaded,
            "tags": self.tags,
            "config": self.config
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ModelInfo':
        """从字典创建模型信息"""
        return cls(
            model_id=data["model_id"],
            name=data["name"],
            source=data.get("source", "huggingface"),
            version=data.get("version", "latest"),
            description=data.get("description", ""),
            size_mb=data.get("size_mb", 0),
            download_url=data.get("download_url", ""),
            local_path=data.get("local_path", ""),
            is_downloaded=data.get("is_downloaded", False),
            tags=data.get("tags", []),
            config=data.get("config", {})
        )


class ModelDownloader(QObject):
    """模型下载器，处理模型下载和进度通知"""
    
    # 定义信号
    download_progress = pyqtSignal(str, int, int)  # model_id, current, total
    download_complete = pyqtSignal(str, bool, str)  # model_id, success, message
    
    def __init__(self, models_dir: str = DEFAULT_MODELS_DIR):
        """
        初始化下载器
        
        Args:
            models_dir: 模型存储目录
        """
        super().__init__()
        self.models_dir = models_dir
        self.active_downloads = {}  # {model_id: thread}
        
        # 确保目录存在
        os.makedirs(models_dir, exist_ok=True)
    
    def download_model(self, model_info: ModelInfo) -> None:
        """
        开始下载模型
        
        Args:
            model_info: 要下载的模型信息
        """
        if model_info.model_id in self.active_downloads:
            # 已在下载中
            return
        
        # 创建模型目录
        model_dir = os.path.join(self.models_dir, model_info.model_id)
        os.makedirs(model_dir, exist_ok=True)
        
        # 启动下载线程
        thread = threading.Thread(
            target=self._download_thread,
            args=(model_info, model_dir),
            daemon=True
        )
        self.active_downloads[model_info.model_id] = thread
        thread.start()
    
    def _download_thread(self, model_info: ModelInfo, model_dir: str) -> None:
        """
        下载线程
        
        Args:
            model_info: 模型信息
            model_dir: 目标目录
        """
        try:
            # 创建下载文件的路径
            file_path = os.path.join(model_dir, f"{model_info.model_id}.zip")
            
            # 开始下载
            with requests.get(model_info.download_url, stream=True) as response:
                response.raise_for_status()
                total_size = int(response.headers.get('content-length', 0))
                
                with open(file_path, 'wb') as f:
                    downloaded = 0
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            # 更新进度
                            self.download_progress.emit(
                                model_info.model_id, 
                                downloaded, 
                                total_size
                            )
            
            # 解压文件（这里简化处理，实际可能需要更复杂的解压逻辑）
            # TODO: 添加解压代码
            
            # 更新模型信息
            model_info.local_path = model_dir
            model_info.is_downloaded = True
            
            # 发送完成信号
            self.download_complete.emit(
                model_info.model_id, 
                True, 
                "模型下载完成"
            )
            
        except Exception as e:
            # 下载失败
            self.download_complete.emit(
                model_info.model_id, 
                False, 
                f"下载失败: {str(e)}"
            )
        
        finally:
            # 清理
            if model_info.model_id in self.active_downloads:
                del self.active_downloads[model_info.model_id]
    
    def cancel_download(self, model_id: str) -> bool:
        """
        取消下载
        
        Args:
            model_id: 要取消的模型ID
            
        Returns:
            bool: 是否成功取消
        """
        if model_id not in self.active_downloads:
            return False
        
        # 线程无法直接取消，但可以标记为已取消
        # 实际实现中可能需要更复杂的取消逻辑
        del self.active_downloads[model_id]
        
        # 发送取消信号
        self.download_complete.emit(
            model_id, 
            False, 
            "下载已取消"
        )
        
        return True


class ModelManager:
    """模型管理器，负责模型的发现、下载和加载"""
    
    DEFAULT_MODELS = [
        {
            "model_id": "chinese-bert-wwm-ext",
            "name": "中文BERT-WWM",
            "source": "huggingface",
            "version": "latest",
            "description": "中文全词掩码BERT模型，适用于多种中文NLP任务",
            "size_mb": 450,
            "download_url": "https://huggingface.co/hfl/chinese-bert-wwm-ext/resolve/main/pytorch_model.bin",
            "tags": ["bert", "chinese", "text-similarity"]
        },
        {
            "model_id": "chinese-roberta-wwm-ext",
            "name": "中文RoBERTa-WWM",
            "source": "huggingface",
            "version": "latest",
            "description": "中文RoBERTa预训练模型，性能优于BERT",
            "size_mb": 480,
            "download_url": "https://huggingface.co/hfl/chinese-roberta-wwm-ext/resolve/main/pytorch_model.bin",
            "tags": ["roberta", "chinese", "text-similarity"]
        },
        {
            "model_id": "chinese-macbert-base",
            "name": "中文MacBERT",
            "source": "huggingface",
            "version": "latest",
            "description": "面向中文的MacBERT预训练模型，更适合语义相似度任务",
            "size_mb": 420,
            "download_url": "https://huggingface.co/hfl/chinese-macbert-base/resolve/main/pytorch_model.bin",
            "tags": ["macbert", "chinese", "text-similarity"]
        }
    ]
    
    def __init__(self, models_dir: str = DEFAULT_MODELS_DIR):
        """
        初始化模型管理器
        
        Args:
            models_dir: 模型存储目录
        """
        self.models_dir = models_dir
        self.models_info = {}  # Dict[model_id, ModelInfo]
        self.downloader = ModelDownloader(models_dir)
        self.loaded_models = {}  # Dict[model_id, model_object]
        
        # 确保目录存在
        os.makedirs(models_dir, exist_ok=True)
        
        # 初始化模型元数据文件路径
        self.metadata_file = os.path.join(models_dir, "models_metadata.json")
        
        # 加载本地模型信息
        self._load_models_metadata()
    
    def _load_models_metadata(self) -> None:
        """加载模型元数据"""
        if os.path.exists(self.metadata_file):
            try:
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for model_data in data:
                        model_info = ModelInfo.from_dict(model_data)
                        self.models_info[model_info.model_id] = model_info
            except Exception as e:
                print(f"加载模型元数据失败: {e}")
        
        # 如果没有模型信息，添加默认模型
        if not self.models_info:
            self._add_default_models()
    
    def _add_default_models(self) -> None:
        """添加默认模型信息"""
        for model_data in self.DEFAULT_MODELS:
            model_info = ModelInfo(
                model_id=model_data["model_id"],
                name=model_data["name"],
                source=model_data.get("source", "huggingface"),
                version=model_data.get("version", "latest"),
                description=model_data.get("description", ""),
                size_mb=model_data.get("size_mb", 0),
                download_url=model_data.get("download_url", ""),
                tags=model_data.get("tags", [])
            )
            
            # 检查是否已下载
            model_dir = os.path.join(self.models_dir, model_info.model_id)
            if os.path.exists(model_dir):
                model_info.local_path = model_dir
                model_info.is_downloaded = True
            
            self.models_info[model_info.model_id] = model_info
        
        # 保存元数据
        self._save_models_metadata()
    
    def _save_models_metadata(self) -> None:
        """保存模型元数据"""
        try:
            data = [model.to_dict() for model in self.models_info.values()]
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存模型元数据失败: {e}")
    
    def get_available_models(self) -> List[ModelInfo]:
        """
        获取所有可用的模型信息
        
        Returns:
            List[ModelInfo]: 模型信息列表
        """
        return list(self.models_info.values())
    
    def get_downloaded_models(self) -> List[ModelInfo]:
        """
        获取已下载的模型信息
        
        Returns:
            List[ModelInfo]: 已下载的模型信息列表
        """
        return [model for model in self.models_info.values() if model.is_downloaded]
    
    def download_model(self, model_id: str) -> bool:
        """
        下载指定模型
        
        Args:
            model_id: 要下载的模型ID
            
        Returns:
            bool: 是否成功启动下载
        """
        if model_id not in self.models_info:
            return False
        
        model_info = self.models_info[model_id]
        self.downloader.download_model(model_info)
        return True
    
    def get_model_info(self, model_id: str) -> Optional[ModelInfo]:
        """
        获取指定模型的信息
        
        Args:
            model_id: 模型ID
            
        Returns:
            Optional[ModelInfo]: 模型信息，如果不存在则返回None
        """
        return self.models_info.get(model_id)
    
    def update_model_metadata(self, model_id: str, **kwargs) -> bool:
        """
        更新模型元数据
        
        Args:
            model_id: 模型ID
            **kwargs: 要更新的字段
            
        Returns:
            bool: 是否成功更新
        """
        if model_id not in self.models_info:
            return False
        
        model_info = self.models_info[model_id]
        
        # 更新字段
        for key, value in kwargs.items():
            if hasattr(model_info, key):
                setattr(model_info, key, value)
        
        # 保存元数据
        self._save_models_metadata()
        return True
    
    def delete_model(self, model_id: str) -> bool:
        """
        删除指定模型
        
        Args:
            model_id: 要删除的模型ID
            
        Returns:
            bool: 是否成功删除
        """
        if model_id not in self.models_info:
            return False
        
        model_info = self.models_info[model_id]
        
        # 如果已下载，删除本地文件
        if model_info.is_downloaded and model_info.local_path:
            try:
                shutil.rmtree(model_info.local_path)
            except Exception as e:
                print(f"删除模型文件失败: {e}")
                return False
        
        # 移除模型信息
        del self.models_info[model_id]
        
        # 保存元数据
        self._save_models_metadata()
        return True
    
    def refresh_models_status(self) -> None:
        """刷新所有模型的状态"""
        for model_id, model_info in self.models_info.items():
            # 检查是否已下载
            model_dir = os.path.join(self.models_dir, model_id)
            model_info.is_downloaded = os.path.exists(model_dir)
            if model_info.is_downloaded:
                model_info.local_path = model_dir
        
        # 保存元数据
        self._save_models_metadata()


# 全局模型管理器实例
global_model_manager = None

def get_model_manager() -> ModelManager:
    """
    获取全局模型管理器实例
    
    Returns:
        ModelManager: 模型管理器实例
    """
    global global_model_manager
    if global_model_manager is None:
        global_model_manager = ModelManager()
    return global_model_manager 