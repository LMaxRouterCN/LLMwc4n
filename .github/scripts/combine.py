#!/usr/bin/env python3
"""
文件拼接工具 v3.1 - 树形分支算法

新增配置：
1. EXTENSION_MODE: 扩展名模式 (first/last/none/custom)
2. CUSTOM_EXTENSION: 自定义扩展名
3. INCLUDE_EXTENSION_IN_NAME: 文件名是否包含扩展名
4. HIDE_MARKER: 隐藏标记
5. FILENAME_SEPARATOR: 文件名连接符号
"""

import os
import sys
import re
from typing import List, Dict, Set, Tuple
from dataclasses import dataclass, field
from copy import deepcopy


@dataclass
class FileInfo:
    """文件信息"""
    path: str
    orig_name: str
    base_name: str
    name_no_ext: str
    extension: str
    tags: Set[str] = field(default_factory=set)
    content: str = ""
    group_order: int = 0
    should_hide: bool = False  # 是否在输出文件名中隐藏


@dataclass
class GroupInfo:
    """分组信息"""
    order: int
    name: str
    folder_path: str
    files: List[FileInfo] = field(default_factory=list)


@dataclass
class Branch:
    """分支（树枝）"""
    files: List[FileInfo]
    accumulated_tags: Set[str]
    
    def copy(self) -> 'Branch':
        return Branch(
            files=self.files.copy(),
            accumulated_tags=self.accumulated_tags.copy()
        )
    
    def add_file(self, file_info: FileInfo, new_tags: Set[str]):
        self.files.append(file_info)
        self.accumulated_tags = new_tags
    
    def get_path_str(self) -> str:
        return ' → '.join([f.orig_name for f in self.files])


class ConfigManager:
    """配置管理器"""
    
    def __init__(self):
        self.config_dir = os.getenv('CONFIG_DIR', 'configs')
        self.output_dir = os.getenv('OUTPUT_DIR', '.')
        self.separator = self._parse_separator(os.getenv('SEPARATOR', '\n\n'))
        
        # 扩展名配置
        self.extension_mode = os.getenv('EXTENSION_MODE', 'first')  # first/last/none/custom
        self.custom_extension = os.getenv('CUSTOM_EXTENSION', '.txt')  # 自定义扩展名
        
        # 文件名配置
        self.include_extension_in_name = os.getenv('INCLUDE_EXTENSION_IN_NAME', 'false').lower() == 'true'
        self.hide_marker = os.getenv('HIDE_MARKER', '[hide]')  # 隐藏标记
        self.filename_separator = os.getenv('FILENAME_SEPARATOR', '-')  # 文件名连接符
        
        # 其他配置
        self.enable_tag_matching = os.getenv('ENABLE_TAG_MATCHING', 'true').lower() == 'true'
        self.tag_format = os.getenv('TAG_FORMAT', 'bracket')
        self.verbose = os.getenv('VERBOSE', 'true').lower() == 'true'
        
    @staticmethod
    def _parse_separator(sep_str: str) -> str:
        return sep_str.replace('\\n', '\n').replace('\\t', '\t')
    
    def log(self, message: str, level: str = "INFO"):
        if self.verbose:
            prefix = {"INFO": "ℹ️", "SUCCESS": "✅", "WARNING": "⚠️", "ERROR": "❌"}.get(level, "•")
            print(f"{prefix} {message}")


class TagExtractor:
    """标签提取器"""
    
    PATTERNS = {
        'bracket': r'\(([^)]+)\)',
        'bracket-cn': r'（([^）]+)）',
        'both': r'[（(]([^）)]+?)[）)]',
    }
    
    @classmethod
    def extract_tags(cls, filename: str, tag_format: str = 'both') -> Set[str]:
        pattern = cls.PATTERNS.get(tag_format, cls.PATTERNS['both'])
        match = re.search(pattern, filename)
        if not match:
            return set()
        tags_str = match.group(1)
        tags = [tag.strip() for tag in re.split('[,，]', tags_str) if tag.strip()]
        return set(tags)
    
    @classmethod
    def remove_tags(cls, filename: str, tag_format: str = 'both') -> str:
        pattern = cls.PATTERNS.get(tag_format, cls.PATTERNS['both'])
        return re.sub(pattern, '', filename, count=1).strip()


class FolderScanner:
    """文件夹扫描器"""
    
    FOLDER_PATTERN = re.compile(r'^\(([0-9]+)\)-\s*(.+)$')
    
    @classmethod
    def scan_groups(cls, config_dir: str, config: ConfigManager) -> List[GroupInfo]:
        if not os.path.exists(config_dir):
            config.log(f"配置目录不存在: {config_dir}", "ERROR")
            return []
        
        groups = []
        for folder_name in os.listdir(config_dir):
            folder_path = os.path.join(config_dir, folder_name)
            if not os.path.isdir(folder_path):
                continue
            
            match = cls.FOLDER_PATTERN.match(folder_name)
            if match:
                order = int(match.group(1))
                name = match.group(2).strip()
            else:
                config.log(f"跳过: {folder_name} (格式: (数字)-组名)", "WARNING")
                continue
            
            group = GroupInfo(order=order, name=name, folder_path=folder_path)
            group.files = cls._scan_files(folder_path, config, order)
            groups.append(group)
            config.log(f"发现分组 [{order}] {name}: {len(group.files)} 个文件")
        
        groups.sort(key=lambda g: g.order)
        return groups
    
    @classmethod
    def _scan_files(cls, folder_path: str, config: ConfigManager, group_order: int) -> List[FileInfo]:
        files = []
        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)
            if not os.path.isfile(file_path):
                continue
            
            # 检查是否包含隐藏标记
            should_hide = config.hide_marker in filename
            if should_hide:
                config.log(f"文件 {filename} 包含隐藏标记，将在输出文件名中忽略", "INFO")
            
            # 移除隐藏标记后再处理标签和名称
            clean_filename = filename.replace(config.hide_marker, '') if should_hide else filename
            
            tags = TagExtractor.extract_tags(clean_filename, config.tag_format)
            base_name = TagExtractor.remove_tags(clean_filename, config.tag_format)
            name_no_ext, extension = os.path.splitext(base_name)
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception as e:
                config.log(f"读取失败 {filename}: {e}", "ERROR")
                continue
            
            file_info = FileInfo(
                path=file_path,
                orig_name=filename,
                base_name=base_name,
                name_no_ext=name_no_ext,
                extension=extension,
                tags=tags,
                content=content,
                group_order=group_order,
                should_hide=should_hide
            )
            files.append(file_info)
        return files


class TreeBranchCombiner:
    """树形分支组合器"""
    
    def __init__(self, config: ConfigManager, groups: List[GroupInfo]):
        self.config = config
        self.groups = groups
        self.stats = {
            'total_branches': 0,
            'output_files': 0,
            'skipped_no_match': 0,
            'tag_discontinuity_warnings': 0
        }
    
    def combine(self) -> int:
        """主组合流程"""
        if not self.groups:
            self.config.log("没有找到任何分组", "ERROR")
            return 0
        
        if len(self.groups) < 2:
            self.config.log("至少需要2个分组", "ERROR")
            return 0
        
        os.makedirs(self.config.output_dir, exist_ok=True)
        
        # 初始化：从第一层的所有文件开始创建分支
        current_branches = []
        first_group = self.groups[0]
        
        for file_info in first_group.files:
            branch = Branch(
                files=[file_info],
                accumulated_tags=file_info.tags.copy()
            )
            current_branches.append(branch)
            self.config.log(f"初始化分支: {branch.get_path_str()} [标签: {branch.accumulated_tags}]")
        
        # 逐层处理
        for layer_idx in range(1, len(self.groups)):
            current_group = self.groups[layer_idx]
            self.config.log(f"\n{'='*60}")
            self.config.log(f"处理第 {layer_idx + 1} 层: {current_group.name}")
            self.config.log(f"当前分支数: {len(current_branches)}")
            self.config.log(f"{'='*60}")
            
            new_branches, output_branches = self._process_layer(
                current_branches, current_group
            )
            
            # 输出提前终止的分支
            for branch in output_branches:
                self._output_file(branch)
            
            current_branches = new_branches
            
            if not current_branches:
                self.config.log("所有分支已终止", "WARNING")
                break
        
        # 输出剩余分支
        for branch in current_branches:
            self._output_file(branch)
        
        return self.stats['output_files']
    
    def _process_layer(self, branches: List[Branch], group: GroupInfo) -> Tuple[List[Branch], List[Branch]]:
        """处理一层"""
        new_branches = []
        terminated_branches = []
        
        for branch in branches:
            branch_new, branch_terminated = self._match_branch_to_layer(branch, group)
            new_branches.extend(branch_new)
            if branch_terminated:
                terminated_branches.append(branch)
        
        return new_branches, terminated_branches
    
    def _match_branch_to_layer(self, branch: Branch, group: GroupInfo) -> Tuple[List[Branch], bool]:
        """将一个分支匹配到一层"""
        files = group.files
        
        # 分离有标签和无标签文件
        tagged_files = [f for f in files if f.tags]
        untagged_files = [f for f in files if not f.tags]
        
        # 尝试匹配有标签文件
        matched_tagged = []
        for file_info in tagged_files:
            if self._can_match(branch, file_info):
                matched_tagged.append(file_info)
        
        # 根据标签优先规则决定是否匹配无标签文件
        matched_untagged = []
        if not matched_tagged:
            for file_info in untagged_files:
                matched_untagged.append(file_info)
        
        all_matched = matched_tagged + matched_untagged
        
        # 如果没有匹配到任何文件，标记为提前终止
        if not all_matched:
            self.config.log(
                f"  分支终止: {branch.get_path_str()} [在当前层无匹配]",
                "WARNING"
            )
            return [], True
        
        # 创建新分支
        new_branches = []
        for file_info in all_matched:
            new_branch = branch.copy()
            
            # 计算新的累积标签
            if file_info.tags:
                new_tags = branch.accumulated_tags & file_info.tags
                if not new_tags:
                    new_tags = file_info.tags
            else:
                new_tags = branch.accumulated_tags.copy()
            
            new_branch.add_file(file_info, new_tags)
            new_branches.append(new_branch)
            
            self.config.log(
                f"  匹配成功: {branch.get_path_str()} → {file_info.orig_name} "
                f"[累积标签: {new_tags}]"
            )
        
        return new_branches, False
    
    def _can_match(self, branch: Branch, file_info: FileInfo) -> bool:
        """检查分支是否可以匹配文件"""
        if not self.config.enable_tag_matching:
            return True
        
        if not branch.accumulated_tags:
            return True
        
        common_tags = branch.accumulated_tags & file_info.tags
        return len(common_tags) > 0
    
    def _output_file(self, branch: Branch):
        """输出文件"""
        if not branch.files:
            return
        
        output_filename = self._build_output_filename(branch.files)
        output_path = os.path.join(self.config.output_dir, output_filename)
        
        contents = [f.content for f in branch.files]
        combined_content = self.config.separator.join(contents)
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(combined_content)
            
            self.stats['output_files'] += 1
            
            tag_info = self._get_tag_info(branch.files)
            warning_msg = self._check_tag_discontinuity(tag_info)
            
            self.config.log(
                f"输出文件: {output_filename} ({branch.get_path_str()}) "
                f"[标签: {tag_info}]{' ' + warning_msg if warning_msg else ''}",
                "SUCCESS"
            )
            
            if warning_msg:
                self.stats['tag_discontinuity_warnings'] += 1
            
        except Exception as e:
            self.config.log(f"写入失败: {e}", "ERROR")
    
    def _build_output_filename(self, files: List[FileInfo]) -> str:
        """
        构建输出文件名
        
        根据配置：
        1. HIDE_MARKER: 忽略标记为隐藏的文件
        2. INCLUDE_EXTENSION_IN_NAME: 是否包含扩展名
        3. FILENAME_SEPARATOR: 文件名连接符
        """
        # 过滤掉标记为隐藏的文件
        visible_files = [f for f in files if not f.should_hide]
        
        if not visible_files:
            # 如果所有文件都隐藏，使用第一个文件名
            visible_files = [files[0]]
        
        # 构建基础文件名
        name_parts = []
        for file_info in visible_files:
            if self.config.include_extension_in_name:
                # 包含扩展名
                name_parts.append(file_info.base_name)
            else:
                # 不包含扩展名
                name_parts.append(file_info.name_no_ext)
        
        # 使用配置的连接符连接
        base_name = self.config.filename_separator.join(name_parts)
        
        # 确定扩展名
        extension = self._determine_extension(files)
        
        return f"{base_name}{extension}"
    
    def _determine_extension(self, files: List[FileInfo]) -> str:
        """
        确定输出文件的扩展名
        
        根据配置：
        - first: 以第一个文件为准
        - last: 以最后一个文件为准
        - none: 无扩展名
        - custom: 使用自定义扩展名
        """
        if not files:
            return ''
        
        if self.config.extension_mode == 'first':
            return files[0].extension
        elif self.config.extension_mode == 'last':
            return files[-1].extension
        elif self.config.extension_mode == 'none':
            return ''
        elif self.config.extension_mode == 'custom':
            # 确保自定义扩展名以点开头
            ext = self.config.custom_extension
            if ext and not ext.startswith('.'):
                ext = '.' + ext
            return ext
        else:
            return files[0].extension
    
    def _get_tag_info(self, files: List[FileInfo]) -> Dict[str, List[int]]:
        """获取标签使用信息"""
        tag_info = {}
        for file_info in files:
            for tag in file_info.tags:
                if tag not in tag_info:
                    tag_info[tag] = []
                tag_info[tag].append(file_info.group_order)
        return tag_info
    
    def _check_tag_discontinuity(self, tag_info: Dict[str, List[int]]) -> str:
        """检查标签不连续性"""
        warnings = []
        for tag, groups in tag_info.items():
            if len(groups) < 2:
                continue
            
            groups_set = set(groups)
            min_group = min(groups_set)
            max_group = max(groups_set)
            
            expected_groups = set(range(min_group, max_group + 1))
            missing = sorted(expected_groups - groups_set)
            
            if missing:
                warnings.append(f"标签 '{tag}' 在分组 {missing} 缺失")
        
        return "; ".join(warnings) if warnings else ""
    
    def print_stats(self):
        """打印统计信息"""
        print("\n" + "="*60)
        print("拼接统计")
        print("="*60)
        print(f"输出文件数: {self.stats['output_files']}")
        print(f"提前终止分支: {self.stats['skipped_no_match']}")
        print(f"标签不连续警告: {self.stats['tag_discontinuity_warnings']}")
        print("="*60)


def main():
    print("\n" + "="*60)
    print("文件拼接工具 v3.1 - 树形分支算法")
    print("="*60)
    
    config = ConfigManager()
    config.log(f"配置目录: {config.config_dir}")
    config.log(f"输出目录: {config.output_dir}")
    config.log(f"标签匹配: {'启用' if config.enable_tag_matching else '禁用'}")
    config.log(f"扩展名模式: {config.extension_mode}" + 
               (f" ({config.custom_extension})" if config.extension_mode == 'custom' else ""))
    config.log(f"文件名包含扩展名: {'是' if config.include_extension_in_name else '否'}")
    config.log(f"隐藏标记: {config.hide_marker}")
    config.log(f"文件名连接符: '{config.filename_separator}'")
    config.log(f"分隔符: {repr(config.separator)}")
    
    print("\n" + "-"*60)
    print("扫描分组...")
    print("-"*60)
    groups = FolderScanner.scan_groups(config.config_dir, config)
    
    if not groups:
        print("\n❌ 未找到有效的分组")
        print("   文件夹命名格式: (数字)-组名")
        sys.exit(1)
    
    print(f"\n找到 {len(groups)} 个分组")
    for group in groups:
        print(f"  [{group.order}] {group.name}: {len(group.files)} 个文件")
        for f in group.files:
            tags_str = f" (标签: {', '.join(f.tags)})" if f.tags else " (无标签)"
            hide_str = " [隐藏]" if f.should_hide else ""
            print(f"      - {f.orig_name}{tags_str}{hide_str}")
    
    print("\n" + "-"*60)
    print("开始组合（树形分支算法）...")
    print("-"*60)
    combiner = TreeBranchCombiner(config, groups)
    file_count = combiner.combine()
    
    combiner.print_stats()
    print(f"\n✅ 完成！共生成 {file_count} 个文件")


if __name__ == '__main__':
    main()
