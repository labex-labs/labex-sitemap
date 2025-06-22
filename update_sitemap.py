import requests
import xml.etree.ElementTree as ET
from datetime import datetime, UTC
from collections import defaultdict
from pathlib import Path
import json
import os


def fetch_sitemap(url):
    """获取 sitemap 内容"""
    try:
        headers = {}
        # 如果是 labex.io 的请求，添加 x-auth 头
        if "labex.io" in url:
            x_auth = os.getenv("LABEX_X_AUTH")
            if x_auth:
                headers["x-auth"] = x_auth
            else:
                print("Warning: LABEX_X_AUTH environment variable not found")

        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        print(f"Error fetching sitemap: {e}")
        return None


def parse_sitemap_index(xml_content):
    """解析 sitemap 索引文件"""
    root = ET.fromstring(xml_content)
    sitemaps = {}

    for sitemap in root.findall(
        ".//{http://www.sitemaps.org/schemas/sitemap/0.9}sitemap"
    ):
        loc = sitemap.find("{http://www.sitemaps.org/schemas/sitemap/0.9}loc").text
        sitemap_type = loc.split("/")[-1].replace("-sitemap.xml", "")
        sitemaps[sitemap_type] = loc

    return sitemaps


def parse_sub_sitemap(xml_content):
    """解析子 sitemap 文件，获取所有 URL"""
    root = ET.fromstring(xml_content)
    urls = []

    for url in root.findall(".//{http://www.sitemaps.org/schemas/sitemap/0.9}url"):
        loc = url.find("{http://www.sitemaps.org/schemas/sitemap/0.9}loc").text
        lastmod_elem = url.find("{http://www.sitemaps.org/schemas/sitemap/0.9}lastmod")
        lastmod = lastmod_elem.text if lastmod_elem is not None else None

        urls.append({"loc": loc, "lastmod": lastmod})

    return urls


def get_repository_structure():
    """获取仓库的实际目录结构"""

    def create_tree(path, prefix="", is_last=True):
        """递归创建目录树"""
        output = []
        path_obj = Path(path)

        # 忽略的目录和文件
        ignore = {".git", ".github", "__pycache__", ".gitignore", ".DS_Store"}

        # 获取目录内容并排序
        items = sorted([x for x in path_obj.iterdir() if x.name not in ignore])

        for i, item in enumerate(items):
            is_last_item = i == len(items) - 1

            # 确定显示的前缀
            current_prefix = "└── " if is_last_item else "├── "
            child_prefix = "    " if is_last_item else "│   "

            # 添加当前项
            output.append(f"{prefix}{current_prefix}{item.name}")

            # 如果是目录，递归处理
            if item.is_dir():
                output.extend(
                    create_tree(
                        item, prefix=prefix + child_prefix, is_last=is_last_item
                    )
                )

        return output

    # 从当前目录开始生成树
    tree_lines = ["```", "labex-sitemap/"] + create_tree(".")
    tree_lines.append("```")

    return "\n".join(tree_lines)


def generate_category_markdown(category, data):
    """生成每个类别的 markdown 内容"""
    markdown = f"""---
layout: default
---

# {category.title()} Sitemap

> Last updated: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}

This file contains all {category.lower()} related links from LabEx website.

## Sitemap

[{data['sitemap_url'].split('/')[-1]}]({data['sitemap_url']})

## Links

"""
    if data["urls"]:
        # 将 URL 按照路径深度和字母顺序排序
        sorted_urls = sorted(
            data["urls"], key=lambda x: (len(x["loc"].split("/")), x["loc"])
        )

        # 创建一个基于路径的树状结构
        url_tree = defaultdict(list)
        for url_data in sorted_urls:
            url = url_data["loc"]
            path_parts = url.replace("https://labex.io/", "").split("/")
            if len(path_parts) > 1:
                key = path_parts[0]
                url_tree[key].append(url_data)
            else:
                url_tree["root"].append(url_data)

        # 按照分组生成 markdown
        for group, urls in sorted(url_tree.items()):
            if group != "root":
                markdown += f"\n### {group}\n\n"
            for url_data in urls:
                url = url_data["loc"]
                lastmod = url_data["lastmod"]
                display_name = (
                    url.split("/")[-1] if url.split("/")[-1] else url.split("/")[-2]
                )
                markdown += f"- [{display_name}]({url})"
                if lastmod:
                    markdown += f" *(Last modified: {lastmod})*"
                markdown += "\n"

    return markdown


def generate_main_readme(sitemaps_with_urls):
    """生成主 README 文件的内容"""
    markdown = f"""---
layout: default
---

# LabEx Sitemap

[LabEx](https://labex.io) is a hands-on learning platform for Linux, DevOps, and Cybersecurity. Learn by doing with guided labs, courses, and tutorials. Get started for free!

> Last updated: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}

This repository maintains an auto-updated list of LabEx website sitemaps.

## Categories

"""
    # 添加分类统计信息
    total_links = 0
    for category, data in sorted(sitemaps_with_urls.items()):
        num_links = len(data["urls"])
        total_links += num_links
        markdown += f"- [{category.title()}](categories/{category.lower()}.md) ({num_links} links)\n"

    markdown += f"\n> **Total Links: {total_links}**\n"

    return markdown


def ensure_directory_exists(directory):
    """确保目录存在"""
    Path(directory).mkdir(parents=True, exist_ok=True)


def update_files(sitemaps_with_urls):
    """更新所有 markdown 文件"""
    # 确保 sitemaps 目录存在
    ensure_directory_exists("categories")

    # 更新主 README
    main_content = generate_main_readme(sitemaps_with_urls)
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(main_content)

    # 更新每个类别的文件
    for category, data in sitemaps_with_urls.items():
        category_content = generate_category_markdown(category, data)
        filename = f"categories/{category.lower()}.md"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(category_content)


def update_package_version():
    """Update package.json version number"""
    try:
        # Read the current package.json
        with open("package.json", "r") as f:
            package_data = json.load(f)

        # Split version into parts
        major, minor, patch = map(int, package_data["version"].split("."))

        # Increment patch version
        patch += 1

        # Update version in package data
        package_data["version"] = f"{major}.{minor}.{patch}"

        # Write back to package.json with proper formatting
        with open("package.json", "w") as f:
            json.dump(package_data, f, indent=2)
            # Add newline at end of file
            f.write("\n")

        print(f"Updated package version to {package_data['version']}")

    except Exception as e:
        print(f"Error updating package version: {e}")


def generate_llms_txt(sitemaps_with_urls):
    """Generate a llms.txt file with all categories and links"""
    content = ""

    # Process each category
    for category, data in sorted(sitemaps_with_urls.items()):
        # Add category header
        content += f"# {category.title()}\n\n"

        # Create a tree structure similar to what's done in generate_category_markdown
        url_tree = defaultdict(list)
        sorted_urls = sorted(
            data["urls"], key=lambda x: (len(x["loc"].split("/")), x["loc"])
        )

        for url_data in sorted_urls:
            url = url_data["loc"]
            path_parts = url.replace("https://labex.io/", "").split("/")
            if len(path_parts) > 1:
                key = path_parts[0]
                url_tree[key].append(url_data)
            else:
                url_tree["root"].append(url_data)

        # Process each group in the category
        for group, urls in sorted(url_tree.items()):
            if group != "root":
                content += f"## {group}\n\n"
            else:
                content += "## \n\n"  # Empty section header for root items

            # Add links
            for url_data in urls:
                url = url_data["loc"]
                display_name = (
                    url.split("/")[-1] if url.split("/")[-1] else url.split("/")[-2]
                )
                content += f"- [{display_name}]({url})\n"

            content += "\n"

    # Write content to file
    with open("llms.txt", "w", encoding="utf-8") as f:
        f.write(content)

    print("Generated llms.txt file")


def main():
    # 获取 sitemap 索引
    sitemap_index_url = "https://labex.io/sitemap_index.xml"
    xml_content = fetch_sitemap(sitemap_index_url)

    if xml_content:
        # 解析主 sitemap
        sitemaps = parse_sitemap_index(xml_content)

        # 存储所有 sitemap 及其包含的 URL
        sitemaps_with_urls = {}

        # 获取每个子 sitemap 的内容
        for sitemap_type, sitemap_url in sitemaps.items():
            print(f"Fetching {sitemap_type} sitemap...")
            sub_sitemap_content = fetch_sitemap(sitemap_url)

            if sub_sitemap_content:
                urls = parse_sub_sitemap(sub_sitemap_content)
                sitemaps_with_urls[sitemap_type] = {
                    "sitemap_url": sitemap_url,
                    "urls": urls,
                }
                print(f"Found {len(urls)} URLs in {sitemap_type} sitemap")
            else:
                print(f"Failed to fetch {sitemap_type} sitemap")
                sitemaps_with_urls[sitemap_type] = {
                    "sitemap_url": sitemap_url,
                    "urls": [],
                }

        # 更新所有文件
        update_files(sitemaps_with_urls)

        # Generate llms.txt file
        generate_llms_txt(sitemaps_with_urls)

        # Update package version
        update_package_version()

        print("All files have been updated successfully!")
    else:
        print("Failed to fetch sitemap index.")


if __name__ == "__main__":
    main()
