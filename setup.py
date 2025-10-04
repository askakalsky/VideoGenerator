#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages
from pathlib import Path

# Читаем README
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(
    encoding="utf-8") if readme_file.exists() else ""

# Читаем requirements
requirements_file = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_file.exists():
    with open(requirements_file, 'r', encoding='utf-8') as f:
        requirements = [
            line.strip()
            for line in f
            if line.strip() and not line.startswith('#') and not line.startswith('-r')
        ]

setup(
    name="video-production-studio",
    version="1.0.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="Professional video production toolkit with Streamlit UI",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/video-production-studio",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Content Creators",
        "Topic :: Multimedia :: Video",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        'dev': [
            'pytest>=7.4.0',
            'black>=23.7.0',
            'mypy>=1.5.0',
        ],
        'minimal': [
            'streamlit>=1.28.0',
            'moviepy>=1.0.3',
            'yt-dlp>=2023.10.13',
        ],
    },
    entry_points={
        'console_scripts': [
            'video-studio=app:main',
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
