# 去重核心功能模块
import pandas as pd
import numpy as np
from core.similarity import SimilarityCalculator
from core.model_inference import get_model_service
from PyQt5.QtCore import QSettings

def deduplicate_dataframe(df, key_columns, keep_option='first'):
    """
    对数据框执行去重操作
    
    参数:
        df (pandas.DataFrame): 要去重的数据框
        key_columns (list): 用作去重依据的列名列表
        keep_option (str): 保留重复项的方式，可选值为'first', 'last', 'False'
        
    返回:
        pandas.DataFrame: 去重后的数据框
    """
    # 将字符串'False'转换为Python的False
    if keep_option == 'False':
        keep_option = False
        
    # 执行去重操作
    return df.drop_duplicates(subset=key_columns, keep=keep_option)

def similarity_based_deduplication(df, columns, threshold=0.7, method="levenshtein", keep_option='first', use_model=False, model_id=None):
    """
    基于相似度的去重操作
    
    参数:
        df (pandas.DataFrame): 要去重的数据框
        columns (dict): 相似度比较配置，格式为 {列名: 相似度方法}
                        例如 {'name': 'levenshtein', 'address': 'word_based'}
        threshold (float或dict): 相似度阈值，可以是全局阈值或按列设置，
                              例如 {'name': 0.8, 'address': 0.6}
        method (str): 默认的相似度计算方法
        keep_option (str): 保留重复项的方式，可选值为'first', 'last'
        use_model (bool): 是否使用模型进行相似度计算
        model_id (str): 模型ID，如果为None则使用默认模型
        
    返回:
        pandas.DataFrame: 去重后的数据框
        dict: 相似组信息，格式为 {组ID: [索引列表]}
    """
    if df.empty:
        return df, {}
        
    # 确保输入格式正确
    if isinstance(columns, list):
        columns = {col: method for col in columns}
        
    if isinstance(threshold, (int, float)):
        thresholds = {col: threshold for col in columns}
    else:
        thresholds = threshold
        
    # 创建结果表和标记
    result_df = df.copy()
    is_duplicate = np.zeros(len(df), dtype=bool)
    group_info = {}  # 存储相似组信息
    group_id = 0

    # 如果使用模型，获取模型服务
    model_service = None
    if use_model:
        model_service = get_model_service()
        if not model_id:
            # 尝试从设置中获取默认模型
            settings = QSettings("ExcelDeduplication", "ModelSettings")
            model_id = settings.value("default_model", "")
    
    # 获取混合策略设置
    settings = QSettings("ExcelDeduplication", "ModelSettings")
    strategy = settings.value("hybrid_strategy", "always_model")
    prefilter_threshold = settings.value("prefilter_threshold", 0.5, type=float)
    min_text_length = settings.value("min_text_length", 50, type=int)
    
    # 按行遍历数据框
    for i in range(len(df)):
        # 如果当前行已被标记为重复，则跳过
        if is_duplicate[i]:
            continue
            
        # 当前行的相似组
        similar_indices = [i]
        current_row = df.iloc[i]
        
        # 与之后的行比较
        for j in range(i + 1, len(df)):
            # 如果已被标记为重复，则跳过
            if is_duplicate[j]:
                continue
                
            compare_row = df.iloc[j]
            is_similar = True
            
            # 检查所有指定列的相似度
            for col, sim_method in columns.items():
                if col not in df.columns:
                    continue
                
                # 获取要比较的文本
                text1 = str(current_row[col])
                text2 = str(compare_row[col])
                
                # 计算相似度
                similarity = 0.0
                
                # 判断是否使用模型
                use_model_for_current = False
                
                if use_model and model_service:
                    # 根据混合策略决定是否使用模型
                    if strategy == "always_model":
                        use_model_for_current = True
                    elif strategy == "basic_then_model":
                        # 先使用基本算法计算，如果相似度达到预筛选阈值，再使用模型
                        basic_similarity = calculate_basic_similarity(text1, text2, sim_method)
                        if basic_similarity >= prefilter_threshold:
                            use_model_for_current = True
                        else:
                            similarity = basic_similarity
                    elif strategy == "length_based":
                        # 根据文本长度选择算法
                        if len(text1) > min_text_length or len(text2) > min_text_length:
                            use_model_for_current = True
                    
                    if use_model_for_current:
                        try:
                            similarity = model_service.calculate_similarity(text1, text2, model_id)
                        except Exception as e:
                            print(f"模型计算相似度失败，回退到基本算法: {e}")
                            similarity = calculate_basic_similarity(text1, text2, sim_method)
                    elif strategy != "basic_then_model":  # basic_then_model已经计算过
                        similarity = calculate_basic_similarity(text1, text2, sim_method)
                else:
                    # 使用基本算法
                    similarity = calculate_basic_similarity(text1, text2, sim_method)
                
                # 如果任一列不满足相似度要求，则不相似
                if similarity < thresholds.get(col, threshold):
                    is_similar = False
                    break
            
            # 如果相似，添加到相似组
            if is_similar:
                similar_indices.append(j)
                is_duplicate[j] = True
        
        # 如果找到相似行
        if len(similar_indices) > 1:
            group_info[group_id] = similar_indices
            group_id += 1
            
            # 根据keep_option确定保留哪一行
            if keep_option == 'first':
                # 保留第一行，移除其他行
                for idx in similar_indices[1:]:
                    result_df = result_df.drop(df.index[idx])
            elif keep_option == 'last':
                # 保留最后一行，移除其他行
                for idx in similar_indices[:-1]:
                    result_df = result_df.drop(df.index[idx])
            else:
                # 保留所有行
                pass
    
    return result_df, group_info

def calculate_basic_similarity(text1, text2, method):
    """使用基本算法计算文本相似度"""
    if method == 'levenshtein':
        return SimilarityCalculator.levenshtein_similarity(text1, text2)
    elif method == 'word_based':
        return SimilarityCalculator.word_based_similarity(text1, text2)
    else:
        # 默认使用编辑距离
        return SimilarityCalculator.levenshtein_similarity(text1, text2)

def deduplicate_with_similarity(df, exact_key_columns=None, similarity_columns=None, 
                              similarity_threshold=0.7, similarity_method="levenshtein", 
                              keep_option='first', use_model=False, model_id=None):
    """
    组合精确去重和相似度去重
    
    参数:
        df (pandas.DataFrame): 要去重的数据框
        exact_key_columns (list): 精确匹配的列名列表
        similarity_columns (dict): 相似度比较配置，格式为 {列名: 相似度方法}
        similarity_threshold (float或dict): 相似度阈值
        similarity_method (str): 默认的相似度计算方法
        keep_option (str): 保留重复项的方式
        use_model (bool): 是否使用模型进行相似度计算
        model_id (str): 模型ID，如果为None则使用默认模型
        
    返回:
        pandas.DataFrame: 去重后的数据框
        dict: 相似组信息
    """
    # 步骤1: 先进行精确去重
    if exact_key_columns:
        df_exact = deduplicate_dataframe(df, exact_key_columns, keep_option)
    else:
        df_exact = df.copy()
        
    # 步骤2: 再进行相似度去重
    if similarity_columns:
        # 检查是否使用模型
        settings = QSettings("ExcelDeduplication", "ModelSettings")
        enable_model = settings.value("enable_model", False, type=bool)
        
        # 如果设置中禁用了模型，强制使用基本算法
        use_model_actual = use_model and enable_model
        
        df_similar, group_info = similarity_based_deduplication(
            df_exact, 
            similarity_columns, 
            similarity_threshold,
            similarity_method, 
            keep_option,
            use_model_actual,
            model_id
        )
        return df_similar, group_info
    else:
        return df_exact, {} 