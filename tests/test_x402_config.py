from pathlib import Path


MAIN = Path(__file__).resolve().parents[1] / "src" / "main.py"


def test_x402_uses_cdp_facilitator_on_base_mainnet():
    source = MAIN.read_text()

    assert 'X402_NETWORK = "eip155:8453"' in source
    assert "https://api.cdp.coinbase.com/platform/v2/x402" in source
    assert "CreateHeadersAuthProvider" in source
    assert "create_cdp_auth_headers" in source
    assert "FacilitatorConfig(" in source
    assert "HTTPFacilitatorClient()" not in source


def test_x402_manifest_advertises_base_mainnet():
    source = MAIN.read_text()

    assert '"network": "base-mainnet"' in source
    assert '"chain_id": "eip155:8453"' in source
    assert "base-sepolia-testnet" not in source
    assert "eip155:84532" not in source
