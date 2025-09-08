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

    # 读取end文件夹内容
    end_content = ""
    if os.path.exists(end_dir):
        print(f"ℹ️ 读取end文件夹内容（{end_dir}）...")
        for end_file in sorted(os.listdir(end_dir)):
            end_path = os.path.join(end_dir, end_file)
            if os.path.isfile(end_path):
                try:
                    with open(end_path, 'r', encoding='utf-8') as f:
                        end_content += f.read() + separator
                except Exception as e:
                    print(f"Warning: 读取end文件'{end_file}'失败：{e}", file=sys.stderr)
        if end_content:
            print(f"ℹ️ end内容合并完成（共{len(end_content)}字符）")
        else:
            print(f"ℹ️ end文件夹为空，不添加end内容")
    else:
        print(f"ℹ️ end文件夹'{end_dir}'不存在，不添加end内容")

    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)

    # 准备common文件列表（提取标签和处理文件名）
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
                
                print(f" → 匹配成功! 共享标签: {shared_tags}")
                skip = False
            
            # 生成新文件名
            if extension_mode == 'common':
                new_ext = common_ext
            elif extension_mode == 'special':
                new_ext = special_ext
            elif extension_mode == 'none':
                new_ext = ''
            else:
                new_ext = common_ext
                
            new_filename = f"{common_name}-{special_name}{new_ext}"
            new_path = os.path.join(output_dir, new_filename)

            # 读取文件内容
            try:
                with open(common['path'], 'r', encoding='utf-8') as f:
                    common_content = f.read()
                with open(special['path'], 'r', encoding='utf-8') as f:
                    special_content = f.read()
            except Exception as e:
                print(f"Error 读取文件: {e}", file=sys.stderr)
                continue

            # 拼接内容
            if combine_order == 'special-first':
                combined_content = f"{special_content}{separator}{common_content}"
            else:
                combined_content = f"{common_content}{separator}{special_content}"
            
            # 追加end内容
            if end_content:
                combined_content += end_content

            # 写入新文件
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

if __name__ == '__main__':
    main()
