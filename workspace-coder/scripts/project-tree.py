#!/usr/bin/env python3
"""
项目结构扫描器 — 为 Coder bot 的 Context Scan 步骤提供项目概览。

用法:
    python3 project-tree.py /path/to/project
    python3 project-tree.py /path/to/project --depth 3
    python3 project-tree.py /path/to/project --git  # 附带 git 状态

输出适合直接粘贴到 Claude Code prompt 的 Context 段。
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

# 始终忽略的目录/文件
IGNORE_DIRS = {
    '.git', 'node_modules', '__pycache__', '.next', '.nuxt',
    'dist', 'build', '.cache', '.vscode', '.idea',
    'vendor', '.tox', '.mypy_cache', '.pytest_cache',
    'coverage', '.nyc_output', 'target',
}

IGNORE_FILES = {
    '.DS_Store', 'Thumbs.db', '*.pyc', '*.pyo',
}

# 文件类型 → 语言映射
EXT_LANG = {
    '.go': 'Go', '.py': 'Python', '.ts': 'TypeScript', '.tsx': 'TypeScript',
    '.js': 'JavaScript', '.jsx': 'JavaScript', '.rs': 'Rust',
    '.java': 'Java', '.rb': 'Ruby', '.sh': 'Shell', '.bash': 'Shell',
    '.md': 'Markdown', '.json': 'JSON', '.yaml': 'YAML', '.yml': 'YAML',
    '.toml': 'TOML', '.html': 'HTML', '.css': 'CSS', '.scss': 'SCSS',
    '.sql': 'SQL', '.proto': 'Protobuf', '.graphql': 'GraphQL',
}


def should_ignore(name: str) -> bool:
    if name in IGNORE_DIRS or name in IGNORE_FILES:
        return True
    if name.startswith('.') and name not in ('.github', '.openclaw'):
        return True
    return False


def scan_tree(root: Path, depth: int, prefix: str = '', current_depth: int = 0):
    """递归扫描目录，输出 tree 格式。"""
    if current_depth >= depth:
        return []

    lines = []
    try:
        entries = sorted(root.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower()))
    except PermissionError:
        return lines

    visible = [e for e in entries if not should_ignore(e.name)]

    for i, entry in enumerate(visible):
        is_last = (i == len(visible) - 1)
        connector = '└── ' if is_last else '├── '
        child_prefix = '    ' if is_last else '│   '

        if entry.is_dir():
            # 统计子项数量
            try:
                child_count = len([c for c in entry.iterdir() if not should_ignore(c.name)])
            except PermissionError:
                child_count = 0
            suffix = f' ({child_count} items)' if current_depth == depth - 1 and child_count > 0 else ''
            lines.append(f'{prefix}{connector}{entry.name}/{suffix}')
            lines.extend(scan_tree(entry, depth, prefix + child_prefix, current_depth + 1))
        else:
            size = entry.stat().st_size
            if size > 1024 * 1024:
                size_str = f' ({size / 1024 / 1024:.1f}MB)'
            elif size > 1024:
                size_str = f' ({size / 1024:.0f}KB)'
            else:
                size_str = ''
            lines.append(f'{prefix}{connector}{entry.name}{size_str}')

    return lines


def scan_tree_json(root: Path, depth: int, current_depth: int = 0) -> list:
    """递归扫描目录，返回嵌套 dict 结构用于 JSON 输出。"""
    if current_depth >= depth:
        return []

    result = []
    try:
        entries = sorted(root.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower()))
    except PermissionError:
        return result

    visible = [e for e in entries if not should_ignore(e.name)]

    for entry in visible:
        if entry.is_dir():
            node = {
                'name': entry.name,
                'type': 'dir',
                'children': scan_tree_json(entry, depth, current_depth + 1),
            }
            result.append(node)
        else:
            node = {
                'name': entry.name,
                'type': 'file',
                'size': entry.stat().st_size,
                'ext': entry.suffix,
            }
            result.append(node)

    return result


def detect_languages(root: Path) -> dict:
    """统计项目中各语言的文件数量。"""
    lang_count = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not should_ignore(d)]
        for f in filenames:
            ext = Path(f).suffix.lower()
            lang = EXT_LANG.get(ext)
            if lang:
                lang_count[lang] = lang_count.get(lang, 0) + 1
    return dict(sorted(lang_count.items(), key=lambda x: -x[1]))


def detect_build_system(root: Path) -> list:
    """检测项目使用的构建系统。"""
    markers = {
        'go.mod': 'Go modules (`go build .`)',
        'package.json': 'Node.js (`npm run build` or check scripts)',
        'Cargo.toml': 'Rust (`cargo build`)',
        'Makefile': 'Make (`make`)',
        'pyproject.toml': 'Python (pyproject)',
        'setup.py': 'Python (setup.py)',
        'pom.xml': 'Maven (`mvn package`)',
        'build.gradle': 'Gradle (`./gradlew build`)',
        'CMakeLists.txt': 'CMake',
        'docker-compose.yml': 'Docker Compose',
        'Dockerfile': 'Docker',
    }
    found = []
    for marker, desc in markers.items():
        if (root / marker).exists():
            found.append(desc)
    return found


def git_status(root: Path) -> str:
    """获取 git 状态摘要。"""
    lines = []
    try:
        # 当前分支
        branch = subprocess.run(
            ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
            capture_output=True, text=True, cwd=root
        ).stdout.strip()
        lines.append(f'Branch: {branch}')

        # 脏文件统计
        status = subprocess.run(
            ['git', 'status', '--porcelain'],
            capture_output=True, text=True, cwd=root
        ).stdout.strip()
        if status:
            status_lines = status.split('\n')
            modified = sum(1 for l in status_lines if l.startswith(' M') or l.startswith('M '))
            added = sum(1 for l in status_lines if l.startswith('A ') or l.startswith('??'))
            deleted = sum(1 for l in status_lines if l.startswith(' D') or l.startswith('D '))
            parts = []
            if modified:
                parts.append(f'{modified} modified')
            if added:
                parts.append(f'{added} untracked/added')
            if deleted:
                parts.append(f'{deleted} deleted')
            lines.append(f'Working tree: {", ".join(parts)}')
        else:
            lines.append('Working tree: clean')

        # diff --stat (staged + unstaged)
        diff_stat = subprocess.run(
            ['git', 'diff', '--stat', '--no-color'],
            capture_output=True, text=True, cwd=root
        ).stdout.strip()
        if diff_stat:
            # 只取最后一行摘要
            summary = diff_stat.split('\n')[-1].strip()
            lines.append(f'Unstaged changes: {summary}')

        # 最近 5 条 commit
        log = subprocess.run(
            ['git', 'log', '--oneline', '-5'],
            capture_output=True, text=True, cwd=root
        ).stdout.strip()
        if log:
            lines.append(f'Recent commits:\n{log}')

    except FileNotFoundError:
        lines.append('Git: not installed or not a git repo')

    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description='项目结构扫描器')
    parser.add_argument('path', help='项目根目录路径')
    parser.add_argument('--depth', type=int, default=2, help='扫描深度 (default: 2)')
    parser.add_argument('--git', action='store_true', help='包含 git 状态信息')
    parser.add_argument('--json', action='store_true', help='输出 JSON 格式的项目结构')
    parser.add_argument('--context', action='store_true', help='输出可直接粘贴到 prompt 的 Context 格式')
    args = parser.parse_args()

    root = Path(args.path).resolve()
    if not root.is_dir():
        print(f'Error: {root} is not a directory', file=sys.stderr)
        sys.exit(1)

    project_name = root.name

    # 语言和构建系统
    languages = detect_languages(root)
    build_systems = detect_build_system(root)

    if args.json:
        output = {
            'project': project_name,
            'languages': languages,
            'build_systems': build_systems,
        }
        if args.git:
            branch = subprocess.run(
                ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                capture_output=True, text=True, cwd=root
            ).stdout.strip()
            status = subprocess.run(
                ['git', 'status', '--porcelain'],
                capture_output=True, text=True, cwd=root
            ).stdout.strip()
            output['git'] = {
                'branch': branch,
                'clean': len(status) == 0,
            }
        output['tree'] = scan_tree_json(root, args.depth)
        print(json.dumps(output, indent=2, ensure_ascii=False))
        return

    # 目录树
    tree_lines = scan_tree(root, args.depth)

    if args.context:
        # 输出 prompt-ready 的 Context 段
        print('Context:')
        lang_str = ', '.join(f'{lang}({count})' for lang, count in languages.items())
        print(f'- Project: {project_name} — {lang_str}')
        if build_systems:
            print(f'- Build: {", ".join(build_systems)}')
        if args.git:
            git_info = git_status(root)
            for line in git_info.split('\n'):
                print(f'- {line}')
        print(f'- Structure:')
        print(f'  {project_name}/')
        for line in tree_lines[:40]:  # 限制行数
            print(f'  {line}')
        if len(tree_lines) > 40:
            print(f'  ... ({len(tree_lines) - 40} more entries)')
    else:
        # 标准输出
        print(f'# {project_name}')
        print()
        if languages:
            print(f'Languages: {", ".join(f"{lang}({count})" for lang, count in languages.items())}')
        if build_systems:
            print(f'Build: {", ".join(build_systems)}')
        print()

        if args.git:
            print('## Git Status')
            print(git_status(root))
            print()

        print('## Structure')
        print(f'{project_name}/')
        for line in tree_lines:
            print(line)


if __name__ == '__main__':
    main()
