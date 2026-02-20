# HalluciGuard - AI Hallucination Detection Middleware
# Copyright (C) 2026 HalluciGuard Contributors
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="halluciGuard",
    version="0.1.0",
    author="HalluciGuard Contributors",
    description="Open-source AI hallucination detection middleware for LLM pipelines",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Hermes-Lekkas/HalluciGuard",
    license="AGPL-3.0",
    packages=find_packages(),
    python_requires=">=3.9",
    install_requires=[
        "requests>=2.31.0",
        "pydantic>=2.0.0",
    ],
    extras_require={
        "openai": ["openai>=1.0.0"],
        "anthropic": ["anthropic>=0.25.0"],
        "google": ["google-genai>=1.0.0"],
        "server": ["fastapi>=0.100.0", "uvicorn>=0.20.0"],
        "langchain": ["langchain-core>=0.1.0"],
        "dev": [
            "pytest>=7.0",
            "pytest-cov",
            "pytest-mock",
            "black",
            "ruff",
            "openai>=1.0.0",
            "anthropic>=0.25.0",
            "google-genai>=1.0.0",
            "fastapi>=0.100.0",
            "uvicorn>=0.20.0",
            "langchain-core>=0.1.0",
        ],
        "all": [
            "openai>=1.0.0",
            "anthropic>=0.25.0",
            "google-genai>=1.0.0",
            "fastapi>=0.100.0",
            "uvicorn>=0.20.0",
            "langchain-core>=0.1.0",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU Affero General Public License v3",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    keywords=["ai", "llm", "hallucination", "safety", "reliability", "openai", "anthropic"],
)
