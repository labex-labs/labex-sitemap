import requests
import xml.etree.ElementTree as ET
from datetime import datetime, UTC
import os
from collections import defaultdict

def fetch_sitemap(url):
    """获取sitemap内容"""
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        print(f"Error fetching sitemap: {e}")
        return None

def parse_sitemap_index(xml_content):
    """解析sitemap索引文件"""
    root = ET.fromstring(xml_content)
    sitemaps = {}
    
    # 提取每个sitemap的URL并按类型分类
    for sitemap in root.findall(".//{http://www.sitemaps.org/schemas/sitemap/0.9}sitemap"):
        loc = sitemap.find("{http://www.sitemaps.org/schemas/sitemap/0.9}loc").text
        # 从URL中提取类型（例如：从 skilltrees-sitemap.xml 提取 skilltrees）
        sitemap_type = loc.split('/')[-1].replace('-sitemap.xml', '')
        sitemaps[sitemap_type] = loc
    
    return sitemaps

def parse_sub_sitemap(xml_content):
    """解析子sitemap文件，获取所有URL"""
    root = ET.fromstring(xml_content)
    urls = []
    
    # 提取所有URL
    for url in root.findall(".//{http://www.sitemaps.org/schemas/sitemap/0.9}url"):
        loc = url.find("{http://www.sitemaps.org/schemas/sitemap/0.9}loc").text
        # 可选：获取lastmod信息
        lastmod_elem = url.find("{http://www.sitemaps.org/schemas/sitemap/0.9}lastmod")
        lastmod = lastmod_elem.text if lastmod_elem is not None else None
        
        urls.append({
            'loc': loc,
            'lastmod': lastmod
        })
    
    return urls

def generate_markdown(sitemaps_with_urls):
    """生成markdown格式的内容"""
    markdown = f"""# LabEx Sitemap Links

> Last updated: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}

This repository maintains an auto-updated list of LabEx website sitemaps.

## Table of Contents

"""
    # 添加目录
    for sitemap_type in sorted(sitemaps_with_urls.keys()):
        markdown += f"- [{sitemap_type.title()}](#{sitemap_type.lower()})\n"
    
    markdown += "\n## Available Sitemaps\n\n"
    
    # 按类型分类添加链接
    for sitemap_type, data in sorted(sitemaps_with_urls.items()):
        sitemap_url = data['sitemap_url']
        urls = data['urls']
        
        markdown += f"### {sitemap_type.title()}<a name='{sitemap_type.lower()}'></a>\n\n"
        markdown += f"Sitemap: [{sitemap_url.split('/')[-1]}]({sitemap_url})\n\n"
        
        if urls:
            markdown += "#### Links:\n\n"
            # 对URL进行排序以保持一致性
            for url_data in sorted(urls, key=lambda x: x['loc']):
                url = url_data['loc']
                lastmod = url_data['lastmod']
                # 从URL中提取一个更友好的显示名称
                display_name = url.split('/')[-1] if url.split('/')[-1] else url.split('/')[-2]
                markdown += f"- [{display_name}]({url})"
                if lastmod:
                    markdown += f" *(Last modified: {lastmod})*"
                markdown += "\n"
            markdown += "\n"
    
    return markdown

def update_readme(content):
    """更新README.md文件"""
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(content)

def main():
    # 获取sitemap索引
    sitemap_index_url = "https://labex.io/sitemap_index.xml"
    xml_content = fetch_sitemap(sitemap_index_url)
    
    if xml_content:
        # 解析主sitemap
        sitemaps = parse_sitemap_index(xml_content)
        
        # 存储所有sitemap及其包含的URL
        sitemaps_with_urls = {}
        
        # 获取每个子sitemap的内容
        for sitemap_type, sitemap_url in sitemaps.items():
            print(f"Fetching {sitemap_type} sitemap...")
            sub_sitemap_content = fetch_sitemap(sitemap_url)
            
            if sub_sitemap_content:
                urls = parse_sub_sitemap(sub_sitemap_content)
                sitemaps_with_urls[sitemap_type] = {
                    'sitemap_url': sitemap_url,
                    'urls': urls
                }
                print(f"Found {len(urls)} URLs in {sitemap_type} sitemap")
            else:
                print(f"Failed to fetch {sitemap_type} sitemap")
                sitemaps_with_urls[sitemap_type] = {
                    'sitemap_url': sitemap_url,
                    'urls': []
                }
        
        # 生成markdown内容
        markdown_content = generate_markdown(sitemaps_with_urls)
        
        # 更新README
        update_readme(markdown_content)
        print("README.md has been updated successfully!")
    else:
        print("Failed to fetch sitemap index.")

if __name__ == "__main__":
    main()