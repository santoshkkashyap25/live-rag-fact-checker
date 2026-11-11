import os
from setuptools import setup, find_packages

readme_path = "factguard/README.md" if os.path.exists("factguard/README.md") else "README.md"
with open(readme_path, encoding="utf-8") as f:
    long_desc = f.read()

setup(
    name="factguard",
    version="2.0.0",
    packages=find_packages(include=["factguard", "factguard.*"]),
    install_requires=[
        "requests>=2.28.0",
        "pydantic>=2.0.0",
    ],
    author="Santosh Kashyap",
    author_email="santoshkkashyap25@gmail.com",
    description="Real-time web intelligence and multi-LLM fact-checking Python SDK",
    long_description=long_desc,
    long_description_content_type="text/markdown",
    url="https://github.com/santoshkkashyap25/live-rag-fact-checker",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.9",
)
