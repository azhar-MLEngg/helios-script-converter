"""Setup configuration for the Snowflake to StarRocks Conversion System."""

from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text() if readme_file.exists() else ""

setup(
    name="snowflake-starrocks-converter",
    version="0.1.0",
    description="AI-powered conversion system for Snowflake to StarRocks migration",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Your Name",
    author_email="your.email@example.com",
    url="https://github.com/yourusername/script-converter",
    packages=find_packages(exclude=["tests", "tests.*"]),
    include_package_data=True,
    install_requires=[
        "anthropic>=0.18.0",
        "pymysql>=1.1.0",
        "snowflake-connector-python>=3.0.0",
        "sqlparse>=0.4.4",
        "sqlglot>=20.0.0",
        "pyyaml>=6.0",
        "python-dotenv>=1.0.0",
        "pydantic>=2.0.0",
        "pydantic-settings>=2.0.0",
        "pytest>=7.4.0",
        "pytest-asyncio>=0.21.0",
        "pytest-mock>=3.12.0",
        "loguru>=0.7.0",
        "rich>=13.0.0",
        "tenacity>=8.2.0",
        "click>=8.1.0",
    ],
    extras_require={
        "dev": [
            "black>=23.0.0",
            "ruff>=0.1.0",
            "mypy>=1.7.0",
            "ipython>=8.12.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "script-converter=src.cli:cli",
        ],
    },
    python_requires=">=3.10",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Code Generators",
        "Topic :: Database",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    keywords="snowflake starrocks conversion migration ai claude",
)
