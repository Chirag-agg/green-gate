const hre = require("hardhat");
const fs = require("fs");
const path = require("path");

async function main() {
  console.log("🚀 Deploying CarbonReportRegistry to Polygon Amoy...\n");

  const [deployer] = await hre.ethers.getSigners();
  console.log("Deploying with account:", deployer.address);

  const balance = await hre.ethers.provider.getBalance(deployer.address);
  console.log("Account balance:", hre.ethers.formatEther(balance), "MATIC\n");

  const CarbonReportRegistry = await hre.ethers.getContractFactory(
    "CarbonReportRegistry"
  );
  const registry = await CarbonReportRegistry.deploy();
  await registry.waitForDeployment();

  const contractAddress = await registry.getAddress();
  console.log("✅ CarbonReportRegistry deployed to:", contractAddress);
  console.log(
    "🔗 View on Polygonscan: https://amoy.polygonscan.com/address/" +
      contractAddress
  );

  // Save to backend .env
  const backendEnvPath = path.resolve(__dirname, "../../backend/.env");
  if (fs.existsSync(backendEnvPath)) {
    let envContent = fs.readFileSync(backendEnvPath, "utf8");
    envContent = envContent.replace(
      /CONTRACT_ADDRESS=.*/,
      `CONTRACT_ADDRESS=${contractAddress}`
    );
    fs.writeFileSync(backendEnvPath, envContent);
    console.log("\n📝 Updated backend/.env with CONTRACT_ADDRESS");
  } else {
    console.log("\n⚠️  backend/.env not found — please set CONTRACT_ADDRESS manually");
  }

  // Save to frontend .env
  const frontendEnvPath = path.resolve(__dirname, "../../frontend/.env");
  if (fs.existsSync(frontendEnvPath)) {
    let envContent = fs.readFileSync(frontendEnvPath, "utf8");
    envContent = envContent.replace(
      /VITE_CONTRACT_ADDRESS=.*/,
      `VITE_CONTRACT_ADDRESS=${contractAddress}`
    );
    fs.writeFileSync(frontendEnvPath, envContent);
    console.log("📝 Updated frontend/.env with VITE_CONTRACT_ADDRESS");
  } else {
    console.log("⚠️  frontend/.env not found — please set VITE_CONTRACT_ADDRESS manually");
  }

  // Copy ABI to backend for web3.py
  const artifactPath = path.resolve(
    __dirname,
    "../artifacts/contracts/CarbonReportRegistry.sol/CarbonReportRegistry.json"
  );
  const backendAbiDir = path.resolve(__dirname, "../../backend/data");
  const backendAbiPath = path.resolve(backendAbiDir, "CarbonReportRegistry.json");

  if (fs.existsSync(artifactPath)) {
    if (!fs.existsSync(backendAbiDir)) {
      fs.mkdirSync(backendAbiDir, { recursive: true });
    }
    fs.copyFileSync(artifactPath, backendAbiPath);
    console.log("📝 Copied contract ABI to backend/data/");
  }

  console.log("\n🎉 Deployment complete!");
  console.log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
  console.log(`CONTRACT_ADDRESS=${contractAddress}`);
  console.log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error("❌ Deployment failed:", error);
    process.exit(1);
  });
