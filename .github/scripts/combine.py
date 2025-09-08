import os
import sys
import re

def extract_tags(filename):
    """
    从文件名中提取识别符标签列表
    格式要求：文件名以括号包裹的识别符开头，多个识别符用逗号分隔
    例如："(tag1,tag2)filename.txt" -> ['tag1', 'tag2']
    如果不匹配格式，返回空列表
    """
    match = re.match(r'^$$([^)]+)$$', filename)
    if not match:
        return []
    
    tags_str = match.group(1)
    return [tag.strip() for tag in tags_str.split(',')]

def remove_tags(filename):
    """
    移除文件名中的识别符前缀
    例如："(tag1,tag2)filename.txt" -> "filename.txt"
    """
    match = re.match(r'^$$[^)]+$$(.*)$', filename)
    return match.group(1) if match else filename

def main():
    # 从环境变量获取配置
    common_dir = os.getenv('COMMON_DIR', 'common')
    special_dir = os.getenv('SPECIAL_DIR', 'special')
    end_dir = os.getenv('END_DIR', 'end')
    output_dir = os.getenv('OUTPUT_DIR', '.')
    combine_order = os.getenv('COMBINE_ORDER', 'common-first')
    separator = os.getenv('SEPARATOR', '\n').replace('\\n', '\n')
    extension_mode = os.getenv('EXTENSION_MODE', 'common')
    
    # 新增配置：是否启用识别符匹配
    enable_tag_matching = os.getenv('ENABLE_TAG_MATCHING', 'false').lower() == 'true'

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
    common_files = []
    for file in os.listdir(common_dir):
        path = os.path.join(common_dir, file)
        if os.path.isfile(path):
            tags = extract_tags(file)
            base_name = remove_tags(file)
            common_files.append({
                'path': path,
                'tags': tags,
                'name': base_name,
                'orig_name': file
            })

    # 准备special文件列表
    special_files = []
    for file in os.listdir(special_dir):
        path = os.path.join(special_dir, file)
        if os.path.isfile(path):
            tags = extract_tags(file)
            base_name = remove_tags(file)
            special_files.append({
                'path': path,
                'tags': tags,
                'name': base_name,
                'orig_name': file
            })

    # 统计信息
    matches_found = 0
    skipped_no_tags = 0
    skipped_no_match = 0

    # 核心逻辑：遍历并匹配文件
    for common in common_files:
        common_name, common_ext = os.path.splitext(common['name'])
        common_tags = common['tags']

        for special in special_files:
            special_tags = special['tags']
            special_name, special_ext = os.path.splitext(special['name'])
            
            # 检查是否需要匹配标签
            skip_reason = None
            if enable_tag_matching:
                # 两个文件都有标签但无交集
                if common_tags and special_tags and not set(common_tags) & set(special_tags):
                    skip_reason = "标签不匹配"
                    skipped_no_match += 1
                # 一个有标签另一个没有
                elif (common_tags and not special_tags) or (special_tags and not common_tags):
                    skip_reason = "单边标签"
                    skipped_no_match += 1
                # 两边都没有标签
                elif not common_tags and not special_tags:
                    skip_reason = "双方无标签"
                    skipped_no_tags += 1
            else:
                # 未启用标签匹配时，跳过双方都有标签但无匹配的情况
                if common_tags and special_tags and not set(common_tags) & set(special_tags):
                    skip_reason = "标签不匹配（功能未启用但存在标签）"
                    skipped_no_match += 1
            
            # 如果确定跳过，记录并继续下一个
            if skip_reason:
                print(f"⏭️ 跳过组合: {common['orig_name']} + {special['orig_name']} - {skip_reason}")
                continue
            
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
                print(f"Error 读取文件'{common['orig_name']}'或'{special['orig_name']}'：{e}", file=sys.stderr)
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
                tag_info = ""
                if common_tags and special_tags:
                    common_tags_str = ",".join(common_tags)
                    special_tags_str = ",".join(special_tags)
                    tag_info = f" [标签匹配: {common_tags_str} ∩ {special_tags_str}]"
                print(f"✅ 生成文件：{new_path}{tag_info}")
            except Exception as e:
                print(f"Error 写入文件'{new_path}'：{e}", file=sys.stderr)
                continue

    # 输出统计信息
    print("\n===== 拼接统计 =====")
    print(f"匹配组合: {matches_found}")
    print(f"跳过组合（标签不匹配）: {skipped_no_match}")
    print(f"跳过组合（无标签）: {skipped_no_tags}")
    print(f"总common文件: {len(common_files)}")
    print(f"总special文件: {len(special_files)}")

if __name__ == '__main__':
    main()