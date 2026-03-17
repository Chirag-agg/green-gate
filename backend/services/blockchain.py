"""
Blockchain service for interacting with the CarbonReportRegistry smart contract
on Polygon Amoy testnet via web3.py.
"""

import hashlib
import json
import os
import logging
from datetime import datetime, timezone
from typing import Any

from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

logger = logging.getLogger(__name__)

# Minimal ABI for the CarbonReportRegistry contract
CONTRACT_ABI: list[dict[str, Any]] = [
    {
        "inputs": [
            {"internalType": "string", "name": "reportId", "type": "string"},
            {"internalType": "bytes32", "name": "reportHash", "type": "bytes32"},
            {"internalType": "string", "name": "companyName", "type": "string"},
            {"internalType": "uint256", "name": "co2Tonnes", "type": "uint256"},
        ],
        "name": "submitReport",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "bytes32", "name": "reportHash", "type": "bytes32"}
        ],
        "name": "verifyReport",
        "outputs": [
            {"internalType": "bool", "name": "isValid", "type": "bool"},
            {"internalType": "string", "name": "reportId", "type": "string"},
            {"internalType": "uint256", "name": "timestamp", "type": "uint256"},
        ],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "string", "name": "reportId", "type": "string"}
        ],
        "name": "getReport",
        "outputs": [
            {
                "components": [
                    {"internalType": "bytes32", "name": "reportHash", "type": "bytes32"},
                    {"internalType": "address", "name": "submitter", "type": "address"},
                    {"internalType": "uint256", "name": "timestamp", "type": "uint256"},
                    {"internalType": "string", "name": "reportId", "type": "string"},
                    {"internalType": "string", "name": "companyName", "type": "string"},
                    {"internalType": "uint256", "name": "co2Tonnes", "type": "uint256"},
                    {"internalType": "bool", "name": "isValid", "type": "bool"},
                ],
                "internalType": "struct CarbonReportRegistry.CarbonReport",
                "name": "",
                "type": "tuple",
            }
        ],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "string", "name": "reportId", "type": "string"}
        ],
        "name": "revokeReport",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "getAllReportIds",
        "outputs": [
            {"internalType": "string[]", "name": "", "type": "string[]"}
        ],
        "stateMutability": "view",
        "type": "function",
    },
]


class BlockchainService:
    """Service for interacting with the CarbonReportRegistry smart contract."""

    def __init__(self) -> None:
        """Initialize Web3 connection and contract instance."""
        rpc_url: str = os.getenv(
            "POLYGON_RPC_URL", "https://rpc-amoy.polygon.technology"
        )
        contract_address: str = os.getenv("CONTRACT_ADDRESS", "")
        self.signer_key: str = os.getenv("SIGNER_PRIVATE_KEY", "")

        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        # Inject POA middleware for Polygon (Amoy is a POA chain)
        self.w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

        self.is_connected: bool = self.w3.is_connected()
        if not self.is_connected:
            logger.warning(f"Could not connect to blockchain RPC at {rpc_url}")

        # Try to load full ABI from compiled artifact, fall back to minimal ABI
        abi = CONTRACT_ABI
        artifact_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "data",
            "CarbonReportRegistry.json",
        )
        if os.path.exists(artifact_path):
            try:
                with open(artifact_path, "r", encoding="utf-8") as f:
                    artifact = json.load(f)
                    abi = artifact.get("abi", CONTRACT_ABI)
            except Exception:
                pass

        if contract_address and contract_address != "0x_fill_after_deploy":
            self.contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(contract_address), abi=abi
            )
        else:
            self.contract = None
            logger.warning("CONTRACT_ADDRESS not set — blockchain features disabled")

        if self.signer_key and self.signer_key != "0x_your_backend_wallet_private_key":
            self.account = self.w3.eth.account.from_key(self.signer_key)
        else:
            self.account = None
            logger.warning(
                "SIGNER_PRIVATE_KEY not set — blockchain write features disabled"
            )

    @staticmethod
    def generate_report_hash(report_dict: dict[str, Any]) -> str:
        """
        Generate a SHA-256 hash of the report data.

        Args:
            report_dict: The full report data dictionary.

        Returns:
            Hex string with 0x prefix (e.g., "0xabcdef...")
        """
        serialized: str = json.dumps(report_dict, sort_keys=True, separators=(",", ":"))
        hash_bytes: bytes = hashlib.sha256(serialized.encode("utf-8")).digest()
        return "0x" + hash_bytes.hex()

    async def submit_to_blockchain(
        self,
        report_id: str,
        report_hash: str,
        company_name: str,
        co2_kg: int,
    ) -> dict[str, Any]:
        """
        Submit a carbon report to the blockchain.

        Args:
            report_id: Unique report identifier.
            report_hash: SHA-256 hash (0x-prefixed hex string).
            company_name: Name of the MSME company.
            co2_kg: Total CO2 in kg (integer for blockchain precision).

        Returns:
            Dictionary with tx_hash, block_number, and polygonscan_url.
        """
        if not self.contract or not self.account:
            raise ValueError(
                "Blockchain service not configured. "
                "Set CONTRACT_ADDRESS and SIGNER_PRIVATE_KEY in .env"
            )

        try:
            hash_bytes = bytes.fromhex(report_hash[2:]) if report_hash.startswith("0x") else bytes.fromhex(report_hash)

            # Build the transaction
            nonce: int = self.w3.eth.get_transaction_count(self.account.address)
            gas_price = self.w3.eth.gas_price

            tx = self.contract.functions.submitReport(
                report_id,
                hash_bytes,
                company_name,
                co2_kg,
            ).build_transaction(
                {
                    "from": self.account.address,
                    "nonce": nonce,
                    "gasPrice": gas_price,
                    "chainId": 80002,
                }
            )

            # Estimate gas
            try:
                tx["gas"] = self.w3.eth.estimate_gas(tx)
            except Exception:
                tx["gas"] = 300000  # Fallback gas limit

            # Sign and send
            signed_tx = self.w3.eth.account.sign_transaction(tx, self.signer_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)

            # Wait for receipt
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)

            tx_hash_hex: str = receipt["transactionHash"].hex()
            if not tx_hash_hex.startswith("0x"):
                tx_hash_hex = f"0x{tx_hash_hex}"
            block_number: int = receipt["blockNumber"]

            return {
                "tx_hash": tx_hash_hex,
                "block_number": block_number,
                "polygonscan_url": f"https://amoy.polygonscan.com/tx/{tx_hash_hex}",
            }

        except ValueError as e:
            raise e
        except Exception as e:
            logger.error(f"Blockchain submission failed: {e}")
            raise RuntimeError(f"Blockchain transaction failed: {str(e)}")

    async def verify_on_blockchain(self, report_hash: str) -> dict[str, Any]:
        """
        Verify a report on the blockchain (read-only, no gas required).

        Args:
            report_hash: The SHA-256 hash to verify (0x-prefixed hex string).

        Returns:
            Dictionary with is_valid, report_id, timestamp, and timestamp_readable.
        """
        if not self.contract:
            raise ValueError(
                "Blockchain service not configured. Set CONTRACT_ADDRESS in .env"
            )

        try:
            hash_bytes = bytes.fromhex(report_hash[2:]) if report_hash.startswith("0x") else bytes.fromhex(report_hash)

            is_valid, report_id, timestamp = self.contract.functions.verifyReport(
                hash_bytes
            ).call()

            timestamp_readable: str = ""
            if timestamp > 0:
                timestamp_readable = datetime.fromtimestamp(
                    timestamp, tz=timezone.utc
                ).strftime("%Y-%m-%d %H:%M:%S UTC")

            return {
                "is_valid": is_valid,
                "report_id": report_id,
                "timestamp": timestamp,
                "timestamp_readable": timestamp_readable,
            }

        except ValueError as e:
            raise e
        except Exception as e:
            logger.error(f"Blockchain verification failed: {e}")
            raise RuntimeError(f"Blockchain verification failed: {str(e)}")
