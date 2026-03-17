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
        deployerPrivateKey && deployerPrivateKey !== "0x_your_wallet_private_key"
          ? [deployerPrivateKey]
          : [],
    },
  },
};

module.exports = config;
