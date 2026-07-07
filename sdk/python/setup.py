from setuptools import setup, find_packages

setup(
    name="aiservices",
    version="2.0.0",
    description="Python SDK for AgentServices — paid APIs for AI agents (crypto data, DeFi yields, market intelligence, and dispute resolution)",
    long_description="""AgentServices SDK
============
Paid APIs for AI agents with built-in x402 payments.

Features:
- Crypto prices (BTC, ETH, XRP, SOL — FREE)
- Technical indicators (RSI, MACD — $0.02)
- DeFi yields across protocols ($0.02)
- Fear & Greed index (FREE)
- IP geolocation (FREE)
- URL metadata extraction ($0.01)
- AI-powered market intelligence, and dispute resolution ($0.05)

Works as a LangChain tool, CrewAI tool, or standalone client.""",
    long_description_content_type="text/markdown",
    packages=find_packages(),
    install_requires=["httpx>=0.27", "pydantic>=2.0"],
    python_requires=">=3.10",
    author="Vivek Kotecha",
    author_email="support@aiservices.to",
    url="https://agentservices.to",
    license="MIT",
    keywords=["x402", "crypto", "ai-agents", "langchain", "crewai", "dispute-resolution", "base", "usdc", "mcp"],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Topic :: Office/Business :: Financial",
    ]
)
