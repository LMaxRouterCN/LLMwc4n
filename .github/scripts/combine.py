import os
import sys
import re

def extract_tags(filename):
    """
    支持中英文括号和逗号分隔符的标签提取
    """
    # 匹配中英文括号：()（），并捕获括号内的内容
    match = re.search(r'[（(]([^）)]+?[）)]', filename)
    if not match:
        return []
    
    tags_str = match.group(1)
    # 支持中文逗号和英文逗号分隔
    return [tag.strip() for tag in re.split('[,，]', tags_str) if tag.strip()]

def remove_tags(filename):
    """
    移除文件名中的标签部分，支持中英文括号
    """
    return re.sub(r'[（(][^）)]+?[）)]', '', filename, 1).strip()

def main():
    # 从环境变量获取配置
    common_dir = os.getenv('COMMON_DIR', 'common')
    special_dir = os.getenv('SPECIAL_DIR', 'special')
    end_dir = os.getenv('END_DIR', 'end')
    output_dir = os.getenv('OUTPUT_DIR', '.')
    combine_order = os.getenv('COMBINE_ORDER', 'common-first')
    separator = os.getenv('SEPARATOR', '\n').replace('\\n', '\n')
    extension_mode = os.getenv('EXTENSION_MODE', 'common')
    enable_tag_matching = os.getenv('ENABLE_TAG_MATCHING', 'true').lower() == 'true'
    
    # 校验核心目录
    for dir_path in [common_dir, special_dir]:
        if not os.path.exists(dir_path):
            print(f"Error: 目录'{dir_path}'不存在，请检查配置。", file=sys.stderr)
            sys.exit(1)

    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)

    # 准备common文件列表
    print("\n===== 处理common文件 =====")
    common_files = []
    for file in os.listdir(common_dir):
        path = os.path.join(common_dir, file)
        if os.path.isfile(path):
            tags = extract_tags(file)
            base_name = remove_tags(file)
            
            # 显示详细处理信息
            print(f" - 文件: '{file}'")
            print(f"   提取标签: {tags}")
            print(f"   处理后名称: '{base_name}'")
            
            common_files.append({
                'path': path,
                'tags': tags,
                'name': base_name,
                'orig_name': file
            })
    print(f"找到 {len(common_files)} 个common文件")

    # 准备special文件列表
    print("\n===== 处理special文件 =====")
    special_files = []
    for file in os.listdir(special_dir):
        path = os.path.join(special_dir, file)
        if os.path.isfile(path):
            tags = extract_tags(file)
            base_name = remove_tags(file)
            
            print(f" - 文件: '{file}'")
            print(f"   提取标签: {tags}")
            print(f"   处理后名称: '{base_name}'")
            
            special_files.append({
                'path': path,
                'tags': tags,
                'name': base_name,
                'orig_name': file
            })
    print(f"找到 {len(special_files)} 个special文件")

    # 准备end文件列表（带标签匹配）
    print("\n===== 处理end文件 =====")
    end_files = []
    if os.path.exists(end_dir):
        for file in os.listdir(end_dir):
            path = os.path.join(end_dir, file)
            if os.path.isfile(path):
                tags = extract_tags(file)
                base_name = remove_tags(file)
                
                print(f" - 文件: '{file}'")
                print(f"   提取标签: {tags}")
                print(f"   处理后名称: '{base_name}'")
                
                # 读取文件内容
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        content = f.read()
                except Exception as e:
                    print(f"Error 读取end文件: {e}", file=sys.stderr)
                    continue
                    
                end_files.append({
                    'path': path,
                    'tags': tags,
                    'name': base_name,
                    'orig_name': file,
                    'content': content
                })
        print(f"找到 {len(end_files)} 个end文件")
    else:
        print(f"ℹ️ end文件夹'{end_dir}'不存在，不添加end内容")

    # 核心匹配逻辑
    print("\n===== 开始匹配组合 =====")
    matches_found = 0
    skipped_no_match = 0
    skipped_no_tags = 0

    for common in common_files:
        common_name, common_ext = os.path.splitext(common['name'])
        common_tags = set(common['tags'])  # 使用集合便于匹配

        for special in special_files:
            special_tags = set(special['tags'])
            special_name, special_ext = os.path.splitext(special['name'])
            
            # 显示当前匹配的文件对
            print(f"\n尝试组合: '{common['orig_name']}' & '{special['orig_name']}'")
            
            # 检查是否需要跳过标签匹配
            if not enable_tag_matching:
                print(" → 标签匹配功能已禁用，强制组合")
                skip = False
            else:
                # 检查双方是否有标签
                if not common_tags:
                    print(" → 跳过: common文件无标签")
                    skipped_no_tags += 1
                    continue
                    
                if not special_tags:
                    print(" → 跳过: special文件无标签")
                    skipped_no_tags += 1
                    continue
                
                # 计算交集（共同标签）
                shared_tags = common_tags & special_tags
                
                if not shared_tags:
                    print(f" → 跳过: 无共享标签 ({common_tags} vs {special_tags})")
                    skipped_no_match += 1
                    continue
                else:
                    print(f" → 匹配成功! 共享标签: {shared_tags}")
                    skip = False
            
            # 如果没有跳过，则进行文件组合
            if not skip:
                # 读取common和special文件内容
                try:
                    with open(common['path'], 'r', encoding='utf-8') as f:
                        common_content = f.read()
                    with open(special['path'], 'r', encoding='utf-8') as f:
                        special_content = f.read()
                except Exception as e:
                    print(f"Error 读取文件: {e}", file=sys.stderr)
                    continue
                
                # 确定扩展名
                if extension_mode == 'special':
                    final_ext = special_ext
                elif extension_mode == 'end' and end_files:
                    final_ext = os.path.splitext(end_files[0]['name'])[1]
                else:
                    final_ext = common_ext
                
                # 处理end文件：为每个end文件创建单独的输出
                if end_files:
                    for end in end_files:
                        # 组合最终内容
                        if combine_order == 'special-first':
                            combined_content = special_content + separator + common_content
                        else:
                            combined_content = common_content + separator + special_content
                        
                        # 添加end内容
                        combined_content += separator + end['content']
                        
                        # 生成输出文件名（包含end文件名）
                        end_base = os.path.splitext(end['name'])[0]
                        output_filename = f"{common_name}-{special_name}-{end_base}{final_ext}"
                        output_path = os.path.join(output_dir, output_filename)
                        
                        # 写入文件
                        try:
                            with open(output_path, 'w', encoding='utf-8') as f:
                                f.write(combined_content)
                            print(f" ✓ 生成文件: '{output_filename}' (包含end: {end['orig_name']})")
                            matches_found += 1
                        except Exception as e:
                            print(f"Error 写入文件: {e}", file=sys.stderr)
                else:
                    # 没有end文件的情况
                    if combine_order == 'special-first':
                        combined_content = special_content + separator + common_content
                    else:
                        combined_content = common_content + separator + special_content
                    
                    # 生成输出文件名
                    output_filename = f"{common_name}-{special_name}{final_ext}"
                    output_path = os.path.join(output_dir, output_filename)
                    
                    # 写入文件
                    try:
                        with open(output_path, 'w', encoding='utf-8') as f:
                            f.write(combined_content)
                        print(f" ✓ 生成文件: '{output_filename}' (无end内容)")
                        matches_found += 1
                    except Exception as e:
                        print(f"Error 写入文件: {e}", file=sys.stderr)

    # 统计信息
    print(f"\n===== 完成 =====")
    print(f"成功生成: {matches_found} 个文件")
    if enable_tag_matching:
        print(f"因无标签跳过: {skipped_no_tags} 个组合")
        print(f"因标签不匹配跳过: {skipped_no_match} 个组合")

if __name__ == "__main__":
    main()