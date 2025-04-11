"""
模型推理接口模块
负责模型加载和相似度计算的推理功能
"""

import os
import json
from typing import Dict, List, Optional, Tuple, Any, Union
import numpy as np
from abc import ABC, abstractmethod

# 导入本地模块
from core.model_manager import ModelInfo, get_model_manager

class BaseModelWrapper(ABC):
    """模型包装器基类，定义统一的模型接口"""
    
    def __init__(self, model_info: ModelInfo):
        """
        初始化模型包装器
        
        Args:
            model_info: 模型信息
        """
        self.model_info = model_info
        self.model = None
        self.is_loaded = False
    
    @abstractmethod
    def load(self) -> bool:
        """
        加载模型
        
        Returns:
            bool: 是否成功加载
        """
        pass
    
    @abstractmethod
    def unload(self) -> bool:
        """
        卸载模型
        
        Returns:
            bool: 是否成功卸载
        """
        pass
    
    @abstractmethod
    def encode_text(self, text: str) -> np.ndarray:
        """
        将文本编码为向量
        
        Args:
            text: 输入文本
            
        Returns:
            np.ndarray: 文本向量
        """
        pass
    
    @abstractmethod
    def calculate_similarity(self, text1: str, text2: str) -> float:
        """
        计算两段文本的相似度
        
        Args:
            text1: 第一段文本
            text2: 第二段文本
            
        Returns:
            float: 相似度得分，范围[0, 1]
        """
        pass
    
    def is_ready(self) -> bool:
        """
        检查模型是否准备好使用
        
        Returns:
            bool: 模型是否准备好
        """
        return self.is_loaded and self.model is not None


class TorchModelWrapper(BaseModelWrapper):
    """PyTorch模型包装器，使用transformers库加载和使用模型"""
    
    def __init__(self, model_info: ModelInfo):
        """
        初始化PyTorch模型包装器
        
        Args:
            model_info: 模型信息
        """
        super().__init__(model_info)
        self.tokenizer = None
        
        # 最大序列长度
        self.max_length = 128
        
        # 设备，默认使用CPU
        self.device = "cpu"
    
    def load(self) -> bool:
        """
        加载模型
        
        Returns:
            bool: 是否成功加载
        """
        try:
            # 延迟导入，避免在不需要时加载大型依赖
            import torch
            from transformers import AutoModel, AutoTokenizer
            
            # 检查模型文件存在性
            if not self.model_info.is_downloaded or not self.model_info.local_path:
                print(f"模型 {self.model_info.model_id} 未下载或路径不存在")
                return False
            
            # 检查是否有GPU可用
            if torch.cuda.is_available():
                self.device = "cuda"
                print(f"使用GPU进行模型推理")
            else:
                print(f"使用CPU进行模型推理")
            
            # 加载模型和分词器
            model_path = self.model_info.local_path
            self.model = AutoModel.from_pretrained(model_path).to(self.device)
            self.tokenizer = AutoTokenizer.from_pretrained(model_path)
            
            # 设置为评估模式
            self.model.eval()
            
            self.is_loaded = True
            print(f"模型 {self.model_info.name} 加载成功")
            return True
            
        except Exception as e:
            print(f"加载模型失败: {e}")
            self.model = None
            self.tokenizer = None
            self.is_loaded = False
            return False
    
    def unload(self) -> bool:
        """
        卸载模型，释放资源
        
        Returns:
            bool: 是否成功卸载
        """
        try:
            # 释放模型资源
            import torch
            
            if self.model:
                del self.model
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            
            if self.tokenizer:
                del self.tokenizer
                
            self.model = None
            self.tokenizer = None
            self.is_loaded = False
            
            print(f"模型 {self.model_info.name} 已卸载")
            return True
            
        except Exception as e:
            print(f"卸载模型时出错: {e}")
            return False
    
    def encode_text(self, text: str) -> np.ndarray:
        """
        将文本编码为向量
        
        Args:
            text: 输入文本
            
        Returns:
            np.ndarray: 文本向量
        """
        if not self.is_ready():
            raise ValueError("模型未加载，请先调用load()")
        
        try:
            import torch
            
            # 对文本进行分词
            tokens = self.tokenizer(
                text,
                padding=True,
                truncation=True,
                max_length=self.max_length,
                return_tensors="pt"
            )
            
            # 将tokens移到设备上
            tokens = {k: v.to(self.device) for k, v in tokens.items()}
            
            # 不计算梯度
            with torch.no_grad():
                # 获取模型输出
                outputs = self.model(**tokens)
                
                # 使用最后一层隐藏状态的 [CLS] token作为文本表示
                embeddings = outputs.last_hidden_state[:, 0, :].cpu().numpy()
                
                return embeddings[0]  # 返回第一个样本的表示（批处理中只有一个样本）
                
        except Exception as e:
            print(f"编码文本时出错: {e}")
            raise
    
    def calculate_similarity(self, text1: str, text2: str) -> float:
        """
        计算两段文本的相似度
        
        Args:
            text1: 第一段文本
            text2: 第二段文本
            
        Returns:
            float: 相似度得分，范围[0, 1]
        """
        try:
            # 获取文本向量
            vec1 = self.encode_text(text1)
            vec2 = self.encode_text(text2)
            
            # 计算余弦相似度
            similarity = self._cosine_similarity(vec1, vec2)
            
            # 将相似度转换到[0,1]范围
            similarity = (similarity + 1) / 2
            
            return similarity
            
        except Exception as e:
            print(f"计算相似度时出错: {e}")
            return 0.0
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """
        计算余弦相似度
        
        Args:
            vec1: 第一个向量
            vec2: 第二个向量
            
        Returns:
            float: 余弦相似度，范围[-1, 1]
        """
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
            
        return np.dot(vec1, vec2) / (norm1 * norm2)


class LightModelWrapper(BaseModelWrapper):
    """轻量级模型包装器，使用预先量化的模型，资源消耗更少"""
    
    def __init__(self, model_info: ModelInfo):
        """
        初始化轻量级模型包装器
        
        Args:
            model_info: 模型信息
        """
        super().__init__(model_info)
        
        # 词汇表路径
        self.vocab_path = None
        
        # 词向量路径
        self.embedding_path = None
        
        # 词汇表和词向量
        self.vocab = {}
        self.embeddings = None
    
    def load(self) -> bool:
        """
        加载模型
        
        Returns:
            bool: 是否成功加载
        """
        try:
            if not self.model_info.is_downloaded or not self.model_info.local_path:
                print(f"模型 {self.model_info.model_id} 未下载或路径不存在")
                return False
            
            # 词汇表路径
            self.vocab_path = os.path.join(self.model_info.local_path, "vocab.json")
            
            # 词向量路径
            self.embedding_path = os.path.join(self.model_info.local_path, "embeddings.npy")
            
            # 检查文件是否存在
            if not os.path.exists(self.vocab_path) or not os.path.exists(self.embedding_path):
                print(f"模型文件不完整，缺少词汇表或词向量文件")
                return False
            
            # 加载词汇表
            with open(self.vocab_path, 'r', encoding='utf-8') as f:
                self.vocab = json.load(f)
            
            # 加载词向量
            self.embeddings = np.load(self.embedding_path)
            
            self.is_loaded = True
            print(f"轻量级模型 {self.model_info.name} 加载成功")
            return True
            
        except Exception as e:
            print(f"加载轻量级模型失败: {e}")
            self.vocab = {}
            self.embeddings = None
            self.is_loaded = False
            return False
    
    def unload(self) -> bool:
        """
        卸载模型，释放资源
        
        Returns:
            bool: 是否成功卸载
        """
        try:
            self.vocab = {}
            self.embeddings = None
            self.is_loaded = False
            
            print(f"轻量级模型 {self.model_info.name} 已卸载")
            return True
            
        except Exception as e:
            print(f"卸载轻量级模型时出错: {e}")
            return False
    
    def encode_text(self, text: str) -> np.ndarray:
        """
        将文本编码为向量（平均词向量方法）
        
        Args:
            text: 输入文本
            
        Returns:
            np.ndarray: 文本向量
        """
        if not self.is_ready():
            raise ValueError("模型未加载，请先调用load()")
        
        try:
            # 对文本进行分词
            import jieba
            tokens = list(jieba.cut(text))
            
            # 计算词向量的平均值
            vectors = []
            for token in tokens:
                if token in self.vocab:
                    token_id = self.vocab[token]
                    vectors.append(self.embeddings[token_id])
            
            if not vectors:
                # 如果没有匹配到任何词向量，返回零向量
                return np.zeros(self.embeddings.shape[1])
            
            # 计算平均向量
            return np.mean(vectors, axis=0)
            
        except Exception as e:
            print(f"编码文本时出错: {e}")
            raise
    
    def calculate_similarity(self, text1: str, text2: str) -> float:
        """
        计算两段文本的相似度
        
        Args:
            text1: 第一段文本
            text2: 第二段文本
            
        Returns:
            float: 相似度得分，范围[0, 1]
        """
        try:
            # 获取文本向量
            vec1 = self.encode_text(text1)
            vec2 = self.encode_text(text2)
            
            # 计算余弦相似度
            similarity = self._cosine_similarity(vec1, vec2)
            
            # 将相似度转换到[0,1]范围
            similarity = (similarity + 1) / 2
            
            return similarity
            
        except Exception as e:
            print(f"计算相似度时出错: {e}")
            return 0.0
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """
        计算余弦相似度
        
        Args:
            vec1: 第一个向量
            vec2: 第二个向量
            
        Returns:
            float: 余弦相似度，范围[-1, 1]
        """
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
            
        return np.dot(vec1, vec2) / (norm1 * norm2)


class ModelService:
    """模型服务，管理模型加载和推理"""
    
    def __init__(self):
        """初始化模型服务"""
        self.model_manager = get_model_manager()
        self.active_models = {}  # {model_id: model_wrapper}
    
    def get_model_wrapper(self, model_id: str) -> Optional[BaseModelWrapper]:
        """
        获取模型包装器
        
        Args:
            model_id: 模型ID
            
        Returns:
            Optional[BaseModelWrapper]: 模型包装器，如果模型不存在则返回None
        """
        # 如果模型已经加载，直接返回
        if model_id in self.active_models:
            return self.active_models[model_id]
        
        # 获取模型信息
        model_info = self.model_manager.get_model_info(model_id)
        if not model_info:
            print(f"模型 {model_id} 不存在")
            return None
        
        # 创建并加载模型
        if not model_info.is_downloaded:
            print(f"模型 {model_id} 未下载")
            return None
        
        # 根据模型信息决定使用哪种包装器
        # 这里简化处理，实际应该根据模型类型或配置决定
        if model_id.startswith("light-"):
            wrapper = LightModelWrapper(model_info)
        else:
            wrapper = TorchModelWrapper(model_info)
        
        # 加载模型
        success = wrapper.load()
        if not success:
            return None
        
        # 将模型加入活跃模型列表
        self.active_models[model_id] = wrapper
        return wrapper
    
    def unload_model(self, model_id: str) -> bool:
        """
        卸载模型
        
        Args:
            model_id: 模型ID
            
        Returns:
            bool: 是否成功卸载
        """
        if model_id not in self.active_models:
            return False
        
        wrapper = self.active_models[model_id]
        success = wrapper.unload()
        
        if success:
            del self.active_models[model_id]
        
        return success
    
    def unload_all_models(self) -> None:
        """卸载所有模型"""
        for model_id in list(self.active_models.keys()):
            self.unload_model(model_id)
    
    def calculate_similarity(self, text1: str, text2: str, model_id: str = None) -> float:
        """
        计算两段文本的相似度
        
        Args:
            text1: 第一段文本
            text2: 第二段文本
            model_id: 模型ID，如果为None则使用默认模型
            
        Returns:
            float: 相似度得分，范围[0, 1]
        """
        # 如果没有指定模型，使用默认模型
        if model_id is None:
            # 获取第一个可用模型
            available_models = self.model_manager.get_downloaded_models()
            if not available_models:
                print("没有可用的模型")
                return 0.0
            
            model_id = available_models[0].model_id
        
        # 获取模型包装器
        wrapper = self.get_model_wrapper(model_id)
        if not wrapper:
            print(f"无法获取模型 {model_id}")
            return 0.0
        
        # 计算相似度
        return wrapper.calculate_similarity(text1, text2)


# 全局模型服务实例
global_model_service = None

def get_model_service() -> ModelService:
    """
    获取全局模型服务实例
    
    Returns:
        ModelService: 模型服务实例
    """
    global global_model_service
    if global_model_service is None:
        global_model_service = ModelService()
    return global_model_service 