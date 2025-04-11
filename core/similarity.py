"""
相似度计算模块
提供各种文本相似度计算方法，支持中文数据的相似度计算。
"""

import re
import numpy as np
import jieba


class SimilarityCalculator:
    """文本相似度计算器"""
    
    @staticmethod
    def preprocess_text(text, remove_punctuation=True, remove_spaces=True):
        """预处理文本
        
        Args:
            text (str): 要处理的文本
            remove_punctuation (bool): 是否移除标点符号
            remove_spaces (bool): 是否移除空格
            
        Returns:
            str: 预处理后的文本
        """
        if not isinstance(text, str):
            return str(text)
            
        # 统一转为字符串并去除首尾空格
        text = str(text).strip()
        
        if remove_punctuation:
            # 移除标点符号
            text = re.sub(r'[^\w\s]', '', text)
            
        if remove_spaces:
            # 移除空格
            text = re.sub(r'\s+', '', text)
            
        return text
    
    @staticmethod
    def segment_chinese(text):
        """中文分词
        
        Args:
            text (str): 要分词的中文文本
            
        Returns:
            list: 分词结果列表
        """
        if not isinstance(text, str):
            text = str(text)
            
        # 使用jieba进行中文分词
        words = jieba.cut(text)
        return list(words)
    
    @staticmethod
    def levenshtein_distance(str1, str2):
        """计算两个字符串的Levenshtein距离（编辑距离）
        
        Levenshtein距离是指两个字符串之间，由一个转换成另一个所需的最少编辑操作次数。
        操作包括：插入、删除、替换。
        
        Args:
            str1 (str): 第一个字符串
            str2 (str): 第二个字符串
            
        Returns:
            int: 编辑距离值
        """
        # 预处理输入
        str1 = SimilarityCalculator.preprocess_text(str1)
        str2 = SimilarityCalculator.preprocess_text(str2)
        
        # 空字符串处理
        if len(str1) == 0:
            return len(str2)
        if len(str2) == 0:
            return len(str1)
            
        # 创建距离矩阵
        matrix = np.zeros((len(str1) + 1, len(str2) + 1), dtype=int)
        
        # 初始化第一行和第一列
        for i in range(len(str1) + 1):
            matrix[i, 0] = i
        for j in range(len(str2) + 1):
            matrix[0, j] = j
            
        # 填充矩阵
        for i in range(1, len(str1) + 1):
            for j in range(1, len(str2) + 1):
                if str1[i-1] == str2[j-1]:
                    matrix[i, j] = matrix[i-1, j-1]
                else:
                    # 取插入、删除、替换三种操作的最小值
                    matrix[i, j] = min(
                        matrix[i-1, j] + 1,     # 删除
                        matrix[i, j-1] + 1,     # 插入
                        matrix[i-1, j-1] + 1    # 替换
                    )
                    
        return matrix[len(str1), len(str2)]
    
    @staticmethod
    def levenshtein_similarity(str1, str2):
        """计算基于Levenshtein距离的相似度
        
        相似度计算公式: 1 - (编辑距离 / max(len(str1), len(str2)))
        结果范围是0到1之间，1表示完全相同，0表示完全不同
        
        Args:
            str1 (str): 第一个字符串
            str2 (str): 第二个字符串
            
        Returns:
            float: 相似度值，范围[0, 1]
        """
        # 预处理输入
        processed_str1 = SimilarityCalculator.preprocess_text(str1)
        processed_str2 = SimilarityCalculator.preprocess_text(str2)
        
        # 处理空字符串情况
        if len(processed_str1) == 0 and len(processed_str2) == 0:
            return 1.0
        if len(processed_str1) == 0 or len(processed_str2) == 0:
            return 0.0
        
        # 计算编辑距离
        distance = SimilarityCalculator.levenshtein_distance(processed_str1, processed_str2)
        
        # 计算相似度
        max_length = max(len(processed_str1), len(processed_str2))
        similarity = 1.0 - (distance / max_length)
        
        return similarity
    
    @staticmethod
    def word_based_similarity(str1, str2, use_chinese_segment=True):
        """基于分词的相似度计算
        
        计算两个文本分词后的相似度，适合中文文本
        使用Jaccard相似系数: 交集大小 / 并集大小
        
        Args:
            str1 (str): 第一个字符串
            str2 (str): 第二个字符串
            use_chinese_segment (bool): 是否使用中文分词
            
        Returns:
            float: 相似度值，范围[0, 1]
        """
        # 预处理输入
        str1 = SimilarityCalculator.preprocess_text(str1, remove_spaces=False)
        str2 = SimilarityCalculator.preprocess_text(str2, remove_spaces=False)
        
        # 处理空字符串情况
        if not str1 and not str2:
            return 1.0
        if not str1 or not str2:
            return 0.0
            
        # 进行分词
        if use_chinese_segment:
            words1 = set(SimilarityCalculator.segment_chinese(str1))
            words2 = set(SimilarityCalculator.segment_chinese(str2))
        else:
            words1 = set(str1.split())
            words2 = set(str2.split())
            
        # 计算Jaccard相似系数
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        if union == 0:
            return 0.0
            
        return intersection / union
    
    @staticmethod
    def is_similar(str1, str2, threshold=0.7, method='levenshtein'):
        """判断两个字符串是否相似
        
        Args:
            str1 (str): 第一个字符串
            str2 (str): 第二个字符串
            threshold (float): 相似度阈值，默认0.7
            method (str): 相似度计算方法，可选'levenshtein'或'word_based'
            
        Returns:
            bool: 如果相似度大于等于阈值则返回True，否则返回False
        """
        if method == 'levenshtein':
            similarity = SimilarityCalculator.levenshtein_similarity(str1, str2)
        elif method == 'word_based':
            similarity = SimilarityCalculator.word_based_similarity(str1, str2)
        else:
            raise ValueError(f"不支持的相似度计算方法: {method}")
            
        return similarity >= threshold 