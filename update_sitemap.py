import requests
import xml.etree.ElementTree as ET
from datetime import datetime, UTC
from collections import defaultdict
from pathlib import Path
import json
import os
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(message)s", datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)


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
                logger.warning("未找到 LABEX_X_AUTH 环境变量")

        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        logger.error(f"获取站点地图失败：{e}")
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


def save_link_counts(sitemaps_with_urls):
    """Save current link counts to a file for comparison"""
    counts = {}
    for category, data in sitemaps_with_urls.items():
        counts[category] = len(data["urls"])

    counts_file = "link_counts.json"
    with open(counts_file, "w", encoding="utf-8") as f:
        json.dump(counts, f, indent=2)

    return counts


def load_previous_link_counts():
    """Load previous link counts from file"""
    counts_file = "link_counts.json"
    try:
        if os.path.exists(counts_file):
            with open(counts_file, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        logger.warning(f"加载历史链接数据失败：{e}")

    return {}


def send_feishu_notification(title, text):
    """Send notification to Feishu webhook"""
    webhook_url = os.getenv("FEISHU_WEBHOOK_URL")
    if not webhook_url:
        logger.warning("未找到飞书 Webhook 地址")
        return False

    try:
        response = requests.post(
            webhook_url,
            json={"title": title, "text": text, "to": "huhuhang"},
        )
        response.raise_for_status()
        logger.info("飞书通知发送成功")
        return True
    except requests.RequestException as e:
        logger.error(f"飞书通知发送失败：{e}")
        return False


def check_and_notify_link_changes(current_counts, previous_counts):
    """Check for significant link count changes and send notifications"""
    if not previous_counts:
        logger.info("首次运行，跳过变化检测")
        return

    total_current = sum(current_counts.values())
    total_previous = sum(previous_counts.values())
    total_change = total_current - total_previous

    # Check total change only
    if abs(total_change) > 100:
        # Prepare notification message
        title = "LabEx 网站地图链接数量变化提醒"

        text_parts = [
            f"🔔 **网站地图链接变化检测**",
            f"",
            f"📊 **总链接数统计：**",
            f"• 之前数量：{total_previous:,}",
            f"• 当前数量：{total_current:,}",
            f"• 变化数量：{total_change:+,}",
            f"",
            f"🕐 **更新时间：** {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}",
            f"🔗 **代码仓库：** https://github.com/labex-labs/labex-sitemap",
        ]

        text = "\n".join(text_parts)

        logger.info(f"检测到重大变化：{total_change:+,} 个链接")
        send_feishu_notification(title, text)
    else:
        logger.info(f"链接变化在阈值范围内：{total_change:+,}")


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

        logger.info(f"版本更新至 {package_data['version']}")

    except Exception as e:
        logger.error(f"版本更新失败：{e}")


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

    logger.info("生成 llms.txt 文件")


def main():
    logger.info("开始更新站点地图")

    # Load previous link counts for comparison
    previous_counts = load_previous_link_counts()

    # 获取 sitemap 索引
    sitemap_index_url = "https://labex.io/sitemap_index.xml"
    logger.info("获取站点地图索引")
    xml_content = fetch_sitemap(sitemap_index_url)

    if xml_content:
        # 解析主 sitemap
        sitemaps = parse_sitemap_index(xml_content)
        logger.info(f"发现 {len(sitemaps)} 个子站点地图")

        # 存储所有 sitemap 及其包含的 URL
        sitemaps_with_urls = {}
        total_urls = 0

        # 获取每个子 sitemap 的内容
        for sitemap_type, sitemap_url in sitemaps.items():
            logger.info(f"处理 {sitemap_type} 站点地图")
            sub_sitemap_content = fetch_sitemap(sitemap_url)

            if sub_sitemap_content:
                urls = parse_sub_sitemap(sub_sitemap_content)
                sitemaps_with_urls[sitemap_type] = {
                    "sitemap_url": sitemap_url,
                    "urls": urls,
                }
                total_urls += len(urls)
                logger.info(f"{sitemap_type}: {len(urls)} 个链接")
            else:
                logger.error(f"{sitemap_type} 站点地图获取失败")
                sitemaps_with_urls[sitemap_type] = {
                    "sitemap_url": sitemap_url,
                    "urls": [],
                }

        logger.info(f"总计 {total_urls} 个链接")

        # Save current link counts and check for significant changes
        current_counts = save_link_counts(sitemaps_with_urls)
        check_and_notify_link_changes(current_counts, previous_counts)

        # 更新所有文件
        logger.info("更新 Markdown 文件")
        update_files(sitemaps_with_urls)

        # Generate llms.txt file
        generate_llms_txt(sitemaps_with_urls)

        # Update package version
        update_package_version()

        logger.info("所有文件更新完成")
    else:
        logger.error("站点地图索引获取失败")


if __name__ == "__main__":
    main()
