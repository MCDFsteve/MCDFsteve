#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import re
import os
import sys

# GitHub API配置
GITHUB_API_BASE = "https://api.github.com/repos"

# 项目配置 - 需要更新star数的项目
PROJECTS = [
    {
        "name": "SakiEngine",
        "repo": "MCDFsteve/SakiEngine",
        "description": "视觉小说游戏引擎，语法类似Ren'Py",
        "tech": "Flutter"
    },
    {
        "name": "NipaPlay-Reload", 
        "repo": "MCDFsteve/NipaPlay-Reload",
        "description": "现代化 Flutter 跨平台播放器，支持弹幕/多字幕/多音轨",
        "tech": "Flutter"
    },
    {
        "name": "Kurisu",
        "repo": "MCDFsteve/Kurisu", 
        "description": "口头描述转换文件格式的程序",
        "tech": "Electron"
    },
    {
        "name": "Amadeus-R",
        "repo": "MCDFsteve/Amadeus-R",
        "description": "基于 Renpy+ChatGPT 的角色 AI 聊天",
        "tech": "Ren'Py, Python"
    },
    {
        "name": "Misuzu Music",
        "repo": "MCDFsteve/misuzumusic",
        "description": "跨平台本地音乐播放器，自动匹配封面和歌词", 
        "tech": "Flutter"
    },
    {
        "name": "LaRfu",
        "repo": "MCDFsteve/LaRfu",
        "description": "下落式双轨音乐游戏",
        "tech": "Python"
    }
]

def get_repo_stars(repo_name):
    """获取GitHub仓库的star数"""
    try:
        url = f"{GITHUB_API_BASE}/{repo_name}"
        headers = {}
        
        # 如果有GitHub Token，使用它来避免API限制
        github_token = os.environ.get('GITHUB_TOKEN')
        if github_token:
            headers['Authorization'] = f'token {github_token}'
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        return data.get('stargazers_count', 0)
    
    except requests.exceptions.RequestException as e:
        print(f"获取 {repo_name} 的star数失败: {e}")
        return 0

def update_readme():
    """更新README文件中的项目表格"""
    
    # 读取当前的README文件
    try:
        with open('README.md', 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print("README.md 文件不存在!")
        return False
    
    # 生成新的项目表格
    table_lines = [
        "| 项目名 | 简介 | 技术栈 | Star |",
        "| ------ | ------------------------------------------------------------ | ------ | ---- |"
    ]
    
    print("正在获取项目star数...")
    
    # 获取所有项目的star数并添加到项目信息中
    projects_with_stars = []
    for project in PROJECTS:
        stars = get_repo_stars(project['repo'])
        print(f"{project['name']}: {stars} stars")
        
        # 将star数添加到项目信息中
        project_with_stars = project.copy()
        project_with_stars['stars'] = stars
        projects_with_stars.append(project_with_stars)
    
    # 按照star数从高到低排序
    projects_with_stars.sort(key=lambda x: x['stars'], reverse=True)
    print("\n按star数排序后:")
    
    for project in projects_with_stars:
        print(f"{project['name']}: {project['stars']} stars")
        
        # 格式化表格行
        row = f"| [{project['name']}](https://github.com/{project['repo']}) | {project['description']} | {project['tech']} | {project['stars']} |"
        table_lines.append(row)
    
    new_table = '\n'.join(table_lines)
    
    # 使用正则表达式替换表格部分
    # 匹配从第一个项目行到最后一个项目行
    pattern = r'(\| 项目名 \| 简介 \| 技术栈 \| Star \|\n\| ------ \| ------------------------------------------------------------ \| ------ \| ---- \|\n)(.*?)(\n\n---)'
    
    def replace_table(match):
        return match.group(1) + '\n'.join(table_lines[2:]) + match.group(3)
    
    new_content = re.sub(pattern, replace_table, content, flags=re.DOTALL)
    
    # 如果没有找到表格，说明格式可能有变化
    if new_content == content:
        print("警告: 未找到需要更新的项目表格，请检查README格式")
        return False
    
    # 写入更新后的内容
    try:
        with open('README.md', 'w', encoding='utf-8') as f:
            f.write(new_content)
        print("README.md 更新成功!")
        return True
    except Exception as e:
        print(f"写入README.md失败: {e}")
        return False

if __name__ == "__main__":
    success = update_readme()
    sys.exit(0 if success else 1) 
