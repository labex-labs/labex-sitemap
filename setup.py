from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="labex-sitemap",
    version="1.0.1",
    author="LabEx",
    author_email="support@labex.io",
    description="A collection of LabEx website sitemaps - A hands-on learning platform for Linux, DevOps, and Cybersecurity",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/labex-labs/labex-sitemap",
    project_urls={
        "Homepage": "https://labex.io/",
        "Bug Tracker": "https://github.com/labex-labs/labex-sitemap/issues",
    },
    packages=find_packages(),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Education",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Topic :: Education",
        "Topic :: Documentation",
    ],
    keywords=[
        "labex",
        "labex-labs",
        "hands-on",
        "learning-platform",
        "linux",
        "devops",
        "cybersecurity",
        "tutorials",
        "courses",
        "labs",
        "guided-labs",
        "learning",
        "education",
        "practical-learning",
        "sitemap",
    ],
    python_requires=">=3.6",
    include_package_data=True,
    package_data={
        "labex_sitemap": ["sitemaps/*.md"],
    },
)
