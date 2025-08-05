from setuptools import setup, find_packages

setup(
    name="AgenticAiCore",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "fastapi>=0.115.6",  # Updated to meet fast-agent-mcp requirement
        "uvicorn==0.34.1",
        "python-dotenv>=1.1.0",  # Updated to meet fastmcp requirement
        "pytest==8.1.1",
        "pytest-asyncio==0.23.5",
    ],
) 