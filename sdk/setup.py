from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="cllova",
    version="1.0.0",
    author="Ali Khan",
    author_email="hello@trustagent.io",
    description="Cryptographic identity + ML behavioral trust scoring for AI agent networks",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/fayazali8826-bo/trustagent",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Security",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Intended Audience :: Developers",
        "Development Status :: 5 - Production/Stable",
    ],
    python_requires=">=3.9",
    install_requires=[
        "requests>=2.28.0",
        "cryptography>=40.0.0",
    ],
    extras_require={
        "dev": ["pytest", "pytest-mock", "responses"]
    },
    keywords=[
        "ai agents", "trust", "security", "verification",
        "cryptography", "llm", "langchain", "crewai", "autogen",
        "multi-agent", "anomaly detection", "agent security",
        "behavioral scoring", "ml security"
    ],
    project_urls={
        "Documentation": "https://github.com/fayazali8826-bo/trustagent",
        "Bug Reports": "https://github.com/fayazali8826-bo/trustagent/issues",
        "Source": "https://github.com/fayazali8826-bo/trustagent",
    },
)