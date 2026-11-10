from setuptools import setup, find_packages

setup(
    name="factguard",
    version="1.0.0",
    packages=find_packages(include=["factguard", "factguard.*"]),
    install_requires=[
        "requests>=2.28.0",
        "pydantic>=2.0.0",
    ],
    author="Santosh Kashyap",
    author_email="santoshkkashyap25@gmail.com",
    description="Real-time web intelligence and multi-LLM fact-checking Python SDK",
    long_description=open("factguard/README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/santoshkkashyap25/live-rag-fact-checker",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.9",
)
