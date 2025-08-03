import os
import sys

def main():
    # 从环境变量获取配置（支持自定义）
    common_dir = os.getenv('COMMON_DIR', 'common')  # 参与文件名的通用部分
    special_dir = os.getenv('SPECIAL_DIR', 'special')# 参与文件名的特殊部分
    end_dir = os.getenv('END_DIR', 'end')            # 新增：不参与文件名的通用部分（追加内容）
    output_dir = os.getenv('OUTPUT_DIR', '.')        # 输出到根目录
    combine_order = os.getenv('COMBINE_ORDER', 'common-first')  # 拼接顺序
    separator = os.getenv('SEPARATOR', '\n').replace('\\n', '\n')  # 内容分隔符（处理转义）
    extension_mode = os.getenv('EXTENSION_MODE', 'common')  # 扩展名规则

    # 校验核心目录是否存在（common/special必须存在，end可选）
    for dir_path in [common_dir, special_dir]:
        if not os.path.exists(dir_path):
            print(f"Error: 目录'{dir_path}'不存在，请检查配置。", file=sys.stderr)
            sys.exit(1)

    # ------------------------------
    # 新增：读取end文件夹的内容（合并所有文件）
    # ------------------------------
    end_content = ""
    if os.path.exists(end_dir):
        print(f"ℹ️ 读取end文件夹内容（{end_dir}）...")
        # 按文件名排序，确保内容顺序一致（避免随机顺序）
        for end_file in sorted(os.listdir(end_dir)):
            end_path = os.path.join(end_dir, end_file)
            if os.path.isfile(end_path):
                try:
                    with open(end_path, 'r', encoding='utf-8') as f:
                        # 每个end文件内容添加分隔符（避免内容粘连）
                        end_content += f.read().strip() + separator
                except Exception as e:
                    print(f"Warning: 读取end文件'{end_file}'失败：{e}", file=sys.stderr)
        # 去除末尾多余的分隔符
        end_content = end_content.rstrip(separator)
        if end_content:
            print(f"ℹ️ end内容合并完成（共{len(end_content)}字符）")
        else:
            print(f"ℹ️ end文件夹为空，不添加end内容")
    else:
        print(f"ℹ️ end文件夹'{end_dir}'不存在，不添加end内容")

    # 创建输出目录（若不存在）
    os.makedirs(output_dir, exist_ok=True)

    # ------------------------------
    # 核心逻辑：遍历common与special文件组合，拼接内容
    # ------------------------------
    for common_file in os.listdir(common_dir):
        common_path = os.path.join(common_dir, common_file)
        if not os.path.isfile(common_path):
            continue  # 跳过文件夹
        common_name, common_ext = os.path.splitext(common_file)  # 分离文件名与扩展名（如base.md→(base, .md)）

        for special_file in os.listdir(special_dir):
            special_path = os.path.join(special_dir, special_file)
            if not os.path.isfile(special_path):
                continue  # 跳过文件夹
            special_name, _ = os.path.splitext(special_file)  # 特殊文件的扩展名不影响文件名（由extension_mode决定）

            # ------------------------------
            # 文件名规则（不变）：common文件名-special文件名+通用扩展名
            # ------------------------------
            if extension_mode == 'common':
                new_ext = common_ext  # 保留通用文件的扩展名（如base.md+feature1.txt→base-feature1.md）
            elif extension_mode == 'special':
                new_ext = special_ext  # 保留特殊文件的扩展名（如base.md+feature1.txt→base-feature1.txt）
            elif extension_mode == 'none':
                new_ext = ''  # 无扩展名（如base.md+feature1.txt→base-feature1）
            else:
                new_ext = common_ext  # 默认保留通用扩展名
            new_filename = f"{common_name}-{special_name}{new_ext}"
            new_path = os.path.join(output_dir, new_filename)

            # ------------------------------
            # 读取common与special文件内容
            # ------------------------------
            try:
                with open(common_path, 'r', encoding='utf-8') as f:
                    common_content = f.read().strip()  # 去除首尾空白（可选）
                with open(special_path, 'r', encoding='utf-8') as f:
                    special_content = f.read().strip()  # 去除首尾空白（可选）
            except Exception as e:
                print(f"Error 读取文件'{common_file}'或'{special_file}'：{e}", file=sys.stderr)
                continue

            # ------------------------------
            # 拼接内容（原顺序 + end内容）
            # ------------------------------
            if combine_order == 'special-first':
                # 特殊内容在前，通用内容在后（如feature1内容→base内容→end内容）
                combined_content = f"{special_content}{separator}{common_content}"
            else:
                # 默认：通用内容在前，特殊内容在后（如base内容→feature1内容→end内容）
                combined_content = f"{common_content}{separator}{special_content}"

            # 追加end内容（如果有的话）
            if end_content:
                combined_content += f"{separator}{end_content}"

            # ------------------------------
            # 写入新文件（覆盖旧文件）
            # ------------------------------
            try:
                with open(new_path, 'w', encoding='utf-8') as f:
                    f.write(combined_content)
                # 输出日志（区分是否包含end内容）
                if end_content:
                    print(f"✅ 生成文件：{new_path}（包含end内容）")
                else:
                    print(f"✅ 生成文件：{new_path}")
            except Exception as e:
                print(f"Error 写入文件'{new_path}'：{e}", file=sys.stderr)
                continue

if __name__ == '__main__':
    main()
