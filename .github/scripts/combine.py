import os
import sys

def get_end_content(end_dir, end_order, end_separator):
    """读取并合并end文件夹下的内容（不参与文件名命名）"""
    if not os.path.exists(end_dir):
        return ""  # 文件夹不存在，返回空字符串
    # 获取end文件夹下的所有文件（排除子文件夹）
    end_files = [f for f in os.listdir(end_dir) if os.path.isfile(os.path.join(end_dir, f))]
    if not end_files:
        return ""  # 无文件，返回空字符串
    # 按指定顺序排序（asc：升序；desc：降序）
    if end_order == "desc":
        end_files.sort(reverse=True)
    else:
        end_files.sort()  # 默认升序
    # 读取每个文件的内容（去除首尾空白）
    end_content_list = []
    for file_name in end_files:
        file_path = os.path.join(end_dir, file_name)
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                end_content_list.append(f.read().strip())
        except Exception as e:
            print(f"警告：无法读取end文件'{file_path}'：{e}", file=sys.stderr)
    # 用分隔符连接所有end内容
    return end_separator.join(end_content_list)

def main():
    # 从环境变量获取配置（默认值为 fallback）
    common_dir = os.getenv('COMMON_DIR', 'common')
    special_dir = os.getenv('SPECIAL_DIR', 'special')
    output_dir = os.getenv('OUTPUT_DIR', '.')
    combine_order = os.getenv('COMBINE_ORDER', 'common-first')  # 拼接顺序
    separator = os.getenv('SEPARATOR', '\n').replace('\\n', '\n')  # 内容分隔符（处理转义）
    extension_mode = os.getenv('EXTENSION_MODE', 'common')  # 扩展名规则
    end_dir = os.getenv("END_DIR", "end")
    end_order = os.getenv("END_ORDER", "asc")
    end_separator = os.getenv("END_SEPARATOR", "\n").replace("\\n", "\n")
    end_content_separator = os.getenv("END_CONTENT_SEPARATOR", "\n").replace("\\n", "\n")


    # 校验目录是否存在
    for dir_path in [common_dir, special_dir]:
        if not os.path.exists(dir_path):
            print(f"Error: 目录'{dir_path}'不存在，请检查配置。", file=sys.stderr)
            sys.exit(1)

    # 生成end内容（合并end文件夹下的所有文件）
    merged_end_content = get_end_content(end_dir, end_order, end_separator)

    # 创建输出目录（若不存在）
    os.makedirs(output_dir, exist_ok=True)

    # 遍历所有通用文件
    for common_file in os.listdir(common_dir):
        common_path = os.path.join(common_dir, common_file)
        if not os.path.isfile(common_path):
            continue  # 跳过文件夹
        common_name, common_ext = os.path.splitext(common_file)  # 分离文件名与扩展名（例：common.txt→(common, .txt)）

        # 遍历所有特殊文件
        for special_file in os.listdir(special_dir):
            special_path = os.path.join(special_dir, special_file)
            if not os.path.isfile(special_path):
                continue  # 跳过文件夹
            special_name, special_ext = os.path.splitext(special_file)  # 分离特殊文件名与扩展名

            # 生成新文件名（规则：通用名-特殊名+扩展名）
            if extension_mode == 'common':
                new_ext = common_ext  # 保留通用文件扩展名
            elif extension_mode == 'special':
                new_ext = special_ext  # 保留特殊文件扩展名
            elif extension_mode == 'none':
                new_ext = ''  # 无扩展名
            else:
                new_ext = common_ext  # 默认保留通用扩展名
            new_filename = f"{common_name}-{special_name}{new_ext}"
            new_path = os.path.join(output_dir, new_filename)

            # 拼接内容（根据顺序调整）
            if combine_order == 'special-first':
                combined_content = f"{special_content}{separator}{common_content}"
            else:  # 默认common-first
                combined_content = f"{common_content}{separator}{special_content}"
            # 新增：添加end内容（放在末尾）
            if merged_end_content:
                combined_content += f"{end_content_separator}{merged_end_content}"

            # 写入新文件（覆盖旧文件）
            try:
                with open(new_path, 'w', encoding='utf-8') as f:
                    f.write(combined_content)
                print(f"✅ 生成文件：{new_path}")
            except Exception as e:
                print(f"Error 写入文件'{new_path}'：{e}", file=sys.stderr)
                continue

if __name__ == '__main__':
    main()
