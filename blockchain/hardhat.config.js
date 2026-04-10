require("@nomicfoundation/hardhat-toolbox");
const path = require("path");
const dotenv = require("dotenv");

// Load env from both `blockchain/.env` (if present) and repo root `.env`.
// This prevents "Network amoy doesn't exist" when the private key lives in the root env file.
dotenv.config({ path: path.resolve(__dirname, ".env") });
dotenv.config({ path: path.resolve(__dirname, "../.env") });

const deployerPrivateKey =
  process.env.DEPLOYER_PRIVATE_KEY ||
  process.env.PRIVATE_KEY ||
  process.env.WALLET_PRIVATE_KEY ||
  "";

function resolveAccountPrivateKey(rawKey) {
  if (!rawKey) return "";

  let key = String(rawKey).trim();
  if (key.startsWith("0x_")) {
    key = `0x${key.slice(3)}`;
  }
  if (!key.startsWith("0x")) {
    key = `0x${key}`;
  }

  const validHexKey = /^0x[0-9a-fA-F]{64}$/.test(key);
  if (!validHexKey || key === "0x_your_wallet_private_key") {
    console.warn("[hardhat] DEPLOYER_PRIVATE_KEY is missing or invalid. Network 'amoy' will use no accounts.");
    return "";
  }
  return key;
}

const normalizedDeployerPrivateKey = resolveAccountPrivateKey(deployerPrivateKey);

/** @type import('hardhat/config').HardhatUserConfig */
const config = {
  solidity: {
    version: "0.8.20",
    settings: {
      optimizer: {
        enabled: true,
        runs: 200,
      },
    },
  },
  networks: {
    amoy: {
      url: process.env.POLYGON_RPC_URL || "https://rpc-amoy.polygon.technology",
      chainId: 80002,
      accounts:
        normalizedDeployerPrivateKey
          ? [normalizedDeployerPrivateKey]
          : [],
    },
  },
};

module.exports = config;
