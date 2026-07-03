from pathlib import Path


MAIN = Path(__file__).resolve().parents[1] / "src" / "main.py"


def test_x402_supports_base_mainnet():
    source = MAIN.read_text()

    assert 'X402_BASE_NETWORK = "eip155:8453"' in source
    assert "https://api.cdp.coinbase.com/platform/v2/x402" in source
    assert "CreateHeadersAuthProvider" in source
    assert "create_cdp_auth_headers" in source
    assert "FacilitatorConfig(" in source
    assert "HTTPFacilitatorClient()" not in source


def test_x402_supports_bsc_multichain():
    source = MAIN.read_text()

    assert 'X402_BSC_NETWORK = "eip155:56"' in source
    assert "X402_IS_MULTICHAIN" in source
    assert "X402_NETWORKS" in source
    assert "_payment_options" in source


def test_x402_manifest_advertises_networks():
    source = MAIN.read_text()

    assert "networks" in source
    assert "eip155:8453" in source
    assert "base-sepolia-testnet" not in source
    assert "eip155:84532" not in source


def test_requirements_include_x402_extensions_extra():
    requirements = (MAIN.parents[1] / "requirements.txt").read_text()

    assert "x402[fastapi,httpx,evm,extensions]" in requirements
