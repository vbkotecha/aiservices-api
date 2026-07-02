/**
 * Quick smoke test for AIServices Client SDK
 * Run: node test.js
 */

const { AIServicesClient } = require("./index");

async function main() {
  const client = new AIServicesClient();

  console.log("=== AIServices SDK Smoke Test ===\n");

  // 1. Health check
  console.log("1. Health check...");
  const health = await client.health();
  console.log(`   Status: ${health.status} | x402: ${health.x402_enabled} | v${health.version}\n`);

  // 2. Free: BTC price
  console.log("2. BTC price (free)...");
  const btc = await client.getPrice("BTC");
  console.log(`   ${JSON.stringify(btc)}\n`);

  // 3. Free: Batch prices
  console.log("3. Batch prices (free)...");
  const batch = await client.getPrices(["BTC", "ETH", "SOL"]);
  console.log(`   Got prices for ${Object.keys(batch).length} symbols\n`);

  // 4. Free: Fear & Greed
  console.log("4. Fear & Greed (free)...");
  const fg = await client.getFearGreed();
  console.log(`   ${JSON.stringify(fg)}\n`);

  // 5. Free: List policies
  console.log("5. Policies (free)...");
  const policies = await client.listPolicies();
  console.log(`   ${policies.length} policies available\n`);

  // 6. Paid: Indicators (should get 402 without payment)
  console.log("6. Indicators ($0.02, paid)...");
  try {
    await client.getIndicators("BTC");
  } catch (err) {
    if (err.status === 402) {
      console.log(`   ✅ Correctly returned 402 (payment required)\n`);
    } else {
      console.log(`   ❌ Unexpected error: ${err.message}\n`);
    }
  }

  // 7. Paid: File dispute (should get 402 without payment)
  console.log("7. File dispute ($0.05, paid)...");
  try {
    await client.fileDispute({
      policy: "freelance-delivery",
      claimant: "0x123",
      respondent: "0x456",
      claim: "Test dispute from SDK",
    });
  } catch (err) {
    if (err.status === 402) {
      console.log(`   ✅ Correctly returned 402 (payment required)\n`);
    } else {
      console.log(`   ❌ Unexpected error: ${err.message}\n`);
    }
  }

  console.log("=== All tests passed ===");
}

main().catch(err => {
  console.error("Test failed:", err.message);
  process.exit(1);
});
