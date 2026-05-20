# 💼 Portfolio Tracker

> Real-time Ethereum portfolio tracker — ETH balance, ERC-20 tokens, NFT holdings & DeFi positions delivered via Telegram bot.

![Python](https://img.shields.io/badge/Python-3.12+-blue?style=flat-square&logo=python)
![Web3](https://img.shields.io/badge/Web3.py-6.x-orange?style=flat-square)
![Telegram](https://img.shields.io/badge/Telegram-Bot-26A5E4?style=flat-square&logo=telegram)
![Etherscan](https://img.shields.io/badge/Etherscan-V2_API-21325B?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

---

## ✨ Features

- 🔷 **ETH Balance** — real-time ETH holdings + USD value
- 🪙 **ERC-20 Tokens** — detect all token holdings with USD valuation
- 🖼️ **NFT Holdings** — track all NFTs owned by a wallet
- 🏦 **DeFi Positions** — Aave V3 lending/borrowing positions
- 👀 **Watchlist** — monitor multiple wallets with auto-refresh
- 🤖 **Telegram Bot** — interactive dashboard via 6 commands
- 📊 **Portfolio Breakdown** — ETH vs tokens vs DeFi vs NFTs

---

## 🚀 Quick Start

### 1. Install dependencies

```bash
pip install web3 requests
```

### 2. Set environment variables

```powershell
# Windows PowerShell
$env:ETHERSCAN_API_KEY = "your_etherscan_api_key"
$env:INFURA_URL        = "https://mainnet.infura.io/v3/your_infura_key"
$env:TELEGRAM_TOKEN    = "your_telegram_bot_token"
$env:TELEGRAM_CHAT_ID  = "your_chat_id"
```

```bash
# Linux / Mac
export ETHERSCAN_API_KEY="your_etherscan_api_key"
export INFURA_URL="https://mainnet.infura.io/v3/your_infura_key"
export TELEGRAM_TOKEN="your_telegram_bot_token"
export TELEGRAM_CHAT_ID="your_chat_id"
```

### 3. Run as Telegram Bot

```bash
python portfolio_tracker.py
```

### 4. Quick Analyze (one-time)

```bash
python portfolio_tracker.py analyze 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045
```

---

## 🤖 Telegram Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome & instructions |
| `/track <address>` | Full portfolio analysis |
| `/watch <address>` | Add wallet to watchlist |
| `/watchlist` | View all watched wallets |
| `/unwatch <address>` | Remove from watchlist |
| `/refresh` | Refresh all watchlist wallets |
| `/txs <address>` | Recent transactions |

### Example

```
/track 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045
/watch 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045
/watchlist
/refresh
```

---

## 📊 Sample Output

```
💼 PORTFOLIO TRACKER
━━━━━━━━━━━━━━━━━━━━━━
👛 0xd8dA...6045
⏰ 2026-05-19T14:06:23

💰 Total Value: $12,112.08
━━━━━━━━━━━━━━━━━━━━━━
🔷 ETH
• Balance : 5.676722 ETH
• Price   : $2,133.64
• Value   : $12,112.08

🪙 Top Tokens
• USDC: 1,500.0 (~$1,500.00)
• WETH: 2.5 (~$5,334.10)

🖼️ NFTs (7079 total)
• Goldie #438
• Crownless King #5

━━━━━━━━━━━━━━━━━━━━━━
📊 Breakdown
• ETH    : $12,112.08
• Tokens : $6,834.10 (256 tokens)
• NFTs   : 7079 items
```

---

## 🏗️ Architecture

```
portfolio_tracker.py
├── PriceClient          → CoinGecko API (ETH + token prices)
├── EtherscanClient      → Etherscan V2 API (balances, tokens, NFTs, TXs)
├── Web3Client           → Web3.py RPC (direct blockchain connection)
├── DeFiTracker          → Aave V3 positions
├── PortfolioAnalyzer    → Core engine (combines all data sources)
├── TelegramReporter     → Format & send dashboard to Telegram
└── PortfolioBot         → Telegram bot with interactive commands
```

---

## 🔧 API Keys

| Service | Get Key | Free Tier |
|---------|---------|-----------|
| Etherscan | [etherscan.io/apis](https://etherscan.io/apis) | 5 req/sec |
| Infura | [infura.io](https://infura.io) | 100K req/day |
| CoinGecko | [coingecko.com/api](https://www.coingecko.com/api/documentation) | Free |
| Telegram Bot | [@BotFather](https://t.me/BotFather) | Free |

---

## 👤 Author

**Rizal** — [@rizalcodes](https://github.com/rizalcodes)

> Building Web3 tools with Python 🐍⛓️

---

## 📄 License

MIT License — free to use, modify, and distribute.
