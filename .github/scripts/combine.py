import os
import sys
import re

def extract_tags(filename):
    """
    支持中英文括号和逗号分隔符的标签提取
    """
    # 匹配中英文括号：()（），并捕获括号内的内容
    match = re.search(r'[（(]([^）)]+?)[）)]', filename)
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
                # 不要把扩展名纳入 end 的 name，用于输出文件名拼接时不带扩展名
                base_name_no_ext = os.path.splitext(base_name)[0]
                
                print(f" - 文件: '{file}'")
                print(f"   提取标签: {tags}")
                print(f"   处理后名称(不含扩展名): '{base_name_no_ext}'")
                
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
                    'name': base_name_no_ext,  # 存储不含扩展名的名字
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
                # 当标签匹配被禁用时，不使用 end 文件（保持原始行为）
                shared_tags = set()
                matched_ends = []
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
                
                print(f" → 匹配成功! 共享标签: {shared_tags}")

                # 选择匹配共享标签的 end 文件（但不要把内容一次性追加到 combined_content）
                matched_ends = []
                for end in end_files:
                    end_tags = set(end['tags'])
                    add_end_file = False
                    reason = ""
                    
                    # 规则1: 无标签的end文件始终添加
                    if not end_tags:
                        add_end_file = True
                        reason = "无标签（通用）"
                    
                    # 规则2: 完全匹配 - end文件标签是共享标签的子集
                    elif end_tags.issubset(shared_tags):
                        add_end_file = True
                        reason = f"完全匹配 ({end_tags} ⊆ {shared_tags})"
                    
                    # 规则3: 部分匹配 - 有至少一个共同标签
                    else:
                        common_end_tags = end_tags & shared_tags
                        if common_end_tags:
                            add_end_file = True
                            reason = f"部分匹配 ({common_end_tags})"
                    
                    if add_end_file:
                        matched_ends.append((end, reason))
                        print(f" → 匹配到 end 文件: {end['orig_name']} - {reason}")
                
                if matched_ends:
                    print(f" → 找到 {len(matched_ends)} 个匹配的 end 文件")
                else:
                    print(" → 没有匹配的 end 文件")

            # 生成基础输出文件名（不含 end 部分）
            if extension_mode == 'common':
                new_ext = common_ext
            elif extension_mode == 'special':
                new_ext = special_ext
            elif extension_mode == 'none':
                new_ext = ''
            else:
                new_ext = common_ext
                
            new_filename_base = f"{common_name}-{special_name}"
            
            # 读取文件内容
            try:
                with open(common['path'], 'r', encoding='utf-8') as f:
                    common_content = f.read()
                with open(special['path'], 'r', encoding='utf-8') as f:
                    special_content = f.read()
            except Exception as e:
                print(f"Error 读取文件: {e}", file=sys.stderr)
                continue

            # 组合基础内容（不含 end）
            if combine_order == 'special-first':
                combined_content = f"{special_content}{separator}{common_content}"
            else:
                combined_content = f"{common_content}{separator}{special_content}"
            
            # 如果启用了标签匹配并且有匹配的 end 文件，则为每个匹配的 end 文件生成单独文件（文件名不含 end 扩展名）
            if enable_tag_matching and end_files:
                if matched_ends:
                    for end, reason in matched_ends:
                        end_content = end['content'] + separator
                        new_filename = f"{new_filename_base}-{end['name']}{new_ext}"
                        new_path = os.path.join(output_dir, new_filename)
                        try:
                            with open(new_path, 'w', encoding='utf-8') as f:
                                f.write(combined_content + end_content)
                            matches_found += 1
                            print(f"✅ 生成文件: {new_path}  ({end['orig_name']} - {reason})")
                        except Exception as e:
                            print(f"Error 写入文件: {e}", file=sys.stderr)
                            continue
                else:
                    # 没有匹配到任何 end 文件，按照原有逻辑仍然输出一个普通组合文件（不附加 end）
                    new_filename = f"{new_filename_base}{new_ext}"
                    new_path = os.path.join(output_dir, new_filename)
                    try:
                        with open(new_path, 'w', encoding='utf-8') as f:
                            f.write(combined_content)
                        matches_found += 1
                        print(f"✅ 生成文件(无匹配end): {new_path}")
                    except Exception as e:
                        print(f"Error 写入文件: {e}", file=sys.stderr)
                        continue
            else:
                # 标签匹配被禁用或没有 end 文件：生成单个组合文件（不附加任何 end）
                new_filename = f"{new_filename_base}{new_ext}"
                new_path = os.path.join(output_dir, new_filename)
                try:
                    with open(new_path, 'w', encoding='utf-8') as f:
                        f.write(combined_content)
                    matches_found += 1
                    print(f"✅ 生成文件: {new_path}")
                except Exception as e:
                    print(f"Error 写入文件: {e}", file=sys.stderr)
                    continue

    # 输出统计信息
    print("\n===== 拼接统计 =====")
    print(f"匹配组合: {matches_found}")
    print(f"跳过组合（无共享标签）: {skipped_no_match}")
    print(f"跳过组合（文件无标签）: {skipped_no_tags}")
    print(f"总common文件: {len(common_files)}")
    print(f"总special文件: {len(special_files)}")
    print(f"总end文件: {len(end_files)}")

if __name__ == '__main__':
    main()
