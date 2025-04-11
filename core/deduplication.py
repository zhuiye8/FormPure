# 去重核心功能模块
import pandas as pd
import numpy as np
from core.similarity import SimilarityCalculator

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

def similarity_based_deduplication(df, columns, threshold=0.7, method="levenshtein", keep_option='first'):
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
                    
                # 计算相似度
                similarity = SimilarityCalculator.levenshtein_similarity(
                    str(current_row[col]), 
                    str(compare_row[col])
                ) if sim_method == 'levenshtein' else SimilarityCalculator.word_based_similarity(
                    str(current_row[col]), 
                    str(compare_row[col])
                )
                
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

def deduplicate_with_similarity(df, exact_key_columns=None, similarity_columns=None, 
                              similarity_threshold=0.7, similarity_method="levenshtein", 
                              keep_option='first'):
    """
    组合精确去重和相似度去重
    
    参数:
        df (pandas.DataFrame): 要去重的数据框
        exact_key_columns (list): 精确匹配的列名列表
        similarity_columns (dict): 相似度比较配置，格式为 {列名: 相似度方法}
        similarity_threshold (float或dict): 相似度阈值
        similarity_method (str): 默认的相似度计算方法
        keep_option (str): 保留重复项的方式
        
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
        df_similar, group_info = similarity_based_deduplication(
            df_exact, 
            similarity_columns, 
            similarity_threshold,
            similarity_method, 
            keep_option
        )
        return df_similar, group_info
    else:
        return df_exact, {} 