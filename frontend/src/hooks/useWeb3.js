/**
 * useWeb3 hook — MetaMask wallet connection for Polygon Amoy testnet.
 */

import { useState, useCallback, useEffect } from 'react';

const POLYGON_AMOY_CONFIG = {
  chainId: '0x13882',
  chainName: 'Polygon Amoy Testnet',
  nativeCurrency: {
    name: 'MATIC',
    symbol: 'MATIC',
    decimals: 18,
  },
  rpcUrls: ['https://rpc-amoy.polygon.technology'],
  blockExplorerUrls: ['https://amoy.polygonscan.com'],
};

export default function useWeb3() {
  const [account, setAccount] = useState(null);
  const [chainId, setChainId] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState(null);

  const hasMetaMask = typeof window !== 'undefined' && typeof window.ethereum !== 'undefined';

  const switchToAmoy = useCallback(async () => {
    if (!window.ethereum) return;

    try {
      await window.ethereum.request({
        method: 'wallet_switchEthereumChain',
        params: [{ chainId: POLYGON_AMOY_CONFIG.chainId }],
      });
    } catch (switchError) {
      // Chain not added — add it
      if (switchError.code === 4902) {
        try {
          await window.ethereum.request({
            method: 'wallet_addEthereumChain',
            params: [POLYGON_AMOY_CONFIG],
          });
        } catch (addError) {
          setError('Failed to add Polygon Amoy network to MetaMask.');
        }
      } else {
        setError('Failed to switch network.');
      }
    }
  }, []);

  const connectWallet = useCallback(async () => {
    if (!hasMetaMask) {
      setError('MetaMask is not installed. Please install it from metamask.io');
      return;
    }

    setError(null);

    try {
      const accounts = await window.ethereum.request({
        method: 'eth_requestAccounts',
      });

      if (accounts.length > 0) {
        setAccount(accounts[0]);
        setIsConnected(true);

        const currentChainId = await window.ethereum.request({
          method: 'eth_chainId',
        });
        setChainId(currentChainId);

        // Auto-switch to Polygon Amoy if not on it
        if (currentChainId !== POLYGON_AMOY_CONFIG.chainId) {
          await switchToAmoy();
        }
      }
    } catch (err) {
      setError('Failed to connect wallet: ' + (err.message || 'Unknown error'));
    }
  }, [hasMetaMask, switchToAmoy]);

  // Listen for account & chain changes
  useEffect(() => {
    if (!hasMetaMask) return;

    const handleAccountsChanged = (accounts) => {
      if (accounts.length > 0) {
        setAccount(accounts[0]);
        setIsConnected(true);
      } else {
        setAccount(null);
        setIsConnected(false);
      }
    };

    const handleChainChanged = (newChainId) => {
      setChainId(newChainId);
    };

    window.ethereum.on('accountsChanged', handleAccountsChanged);
    window.ethereum.on('chainChanged', handleChainChanged);

    // Check if already connected
    window.ethereum
      .request({ method: 'eth_accounts' })
      .then(handleAccountsChanged)
      .catch(() => {});

    return () => {
      window.ethereum.removeListener('accountsChanged', handleAccountsChanged);
      window.ethereum.removeListener('chainChanged', handleChainChanged);
    };
  }, [hasMetaMask]);

  return {
    account,
    isConnected,
    connectWallet,
    chainId,
    error,
    hasMetaMask,
    switchToAmoy,
  };
}
