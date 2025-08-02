import os
import sys

def main():
    # 从环境变量获取配置（默认值为 fallback）
    common_dir = os.getenv('COMMON_DIR', 'common')
    special_dir = os.getenv('SPECIAL_DIR', 'special')
    output_dir = os.getenv('OUTPUT_DIR', '.')
    combine_order = os.getenv('COMBINE_ORDER', 'common-first')  # 拼接顺序
    separator = os.getenv('SEPARATOR', '\n').replace('\\n', '\n')  # 内容分隔符（处理转义）
    extension_mode = os.getenv('EXTENSION_MODE', 'common')  # 扩展名规则

    # 校验目录是否存在
    for dir_path in [common_dir, special_dir]:
        if not os.path.exists(dir_path):
            print(f"Error: 目录'{dir_path}'不存在，请检查配置。", file=sys.stderr)
            sys.exit(1)

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

            # 读取文件内容（处理编码问题）
            try:
                with open(common_path, 'r', encoding='utf-8') as f:
                    common_content = f.read().strip()  # 去除首尾空白（可选）
                with open(special_path, 'r', encoding='utf-8') as f:
                    special_content = f.read().strip()  # 去除首尾空白（可选）
            except Exception as e:
                print(f"Error 读取文件'{common_file}'或'{special_file}'：{e}", file=sys.stderr)
                continue

            # 拼接内容（根据顺序调整）
            if combine_order == 'special-first':
                combined_content = f"{special_content}{separator}{common_content}"
            else:  # 默认common-first
                combined_content = f"{common_content}{separator}{special_content}"

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