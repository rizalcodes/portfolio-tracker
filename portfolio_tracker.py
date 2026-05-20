"""
portfolio_tracker.py - Crypto Portfolio Tracker
By Rizal | github.com/rizalcodes
Track ETH balance, ERC-20 tokens, NFT holdings, DeFi positions
Multi-source: Etherscan V2 + CoinGecko + Web3.py
Output: Real-time Telegram dashboard
"""

import os
import time
import logging
import requests
from datetime import datetime
from web3 import Web3

# ─────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
log = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY", "Your_Etherscan_Api_Here")
INFURA_URL        = os.getenv("INFURA_URL",        "https://mainnet.infura.io/v3/Your_Infure_Key_Here")
TELEGRAM_TOKEN    = os.getenv("TELEGRAM_TOKEN",    "Your_Telegram_Bot_Token_Here")
TELEGRAM_CHAT_ID  = os.getenv("TELEGRAM_CHAT_ID",  "Your_Chat_ID_Here")

# Interval auto-refresh (menit)
REFRESH_INTERVAL = 60


# ─────────────────────────────────────────────
# 1. PRICE CLIENT (CoinGecko)
# ─────────────────────────────────────────────
class PriceClient:
    BASE = "https://api.coingecko.com/api/v3"

    def __init__(self):
        self.session = requests.Session()
        self._cache  = {}
        self._cache_ts = {}

    def get_price(self, coin_id: str, currency: str = "usd") -> float:
        """Ambil harga coin dari CoinGecko."""
        # Cache 5 menit
        now = time.time()
        if coin_id in self._cache and now - self._cache_ts.get(coin_id, 0) < 300:
            return self._cache[coin_id]

        try:
            r = self.session.get(
                f"{self.BASE}/simple/price",
                params={"ids": coin_id, "vs_currencies": currency},
                timeout=10
            )
            data = r.json()
            price = data.get(coin_id, {}).get(currency, 0)
            self._cache[coin_id] = price
            self._cache_ts[coin_id] = now
            return price
        except Exception as e:
            log.error(f"Price fetch error ({coin_id}): {e}")
            return 0

    def get_eth_price(self) -> float:
        return self.get_price("ethereum")

    def get_token_price(self, contract_address: str) -> float:
        """Ambil harga token ERC-20 by contract address."""
        try:
            r = self.session.get(
                f"{self.BASE}/simple/token_price/ethereum",
                params={
                    "contract_addresses": contract_address.lower(),
                    "vs_currencies": "usd",
                },
                timeout=10
            )
            data = r.json()
            return data.get(contract_address.lower(), {}).get("usd", 0)
        except Exception as e:
            log.error(f"Token price error: {e}")
            return 0

    def get_multiple_prices(self, coin_ids: list) -> dict:
        """Ambil harga banyak coin sekaligus."""
        try:
            ids = ",".join(coin_ids)
            r = self.session.get(
                f"{self.BASE}/simple/price",
                params={"ids": ids, "vs_currencies": "usd"},
                timeout=10
            )
            return r.json()
        except Exception as e:
            log.error(f"Multiple price error: {e}")
            return {}


# ─────────────────────────────────────────────
# 2. ETHERSCAN CLIENT
# ─────────────────────────────────────────────
class EtherscanClient:
    BASE = "https://api.etherscan.io/v2/api"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = requests.Session()

    def _get(self, params: dict) -> dict:
        params["apikey"]  = self.api_key
        params["chainid"] = 1
        try:
            r = self.session.get(self.BASE, params=params, timeout=15)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            log.error(f"Etherscan error: {e}")
            return {}

    def get_eth_balance(self, address: str) -> float:
        """Ambil ETH balance dalam ETH."""
        data = self._get({
            "module" : "account",
            "action" : "balance",
            "address": address,
            "tag"    : "latest",
        })
        try:
            wei = int(data.get("result", 0))
            return wei / 1e18
        except Exception:
            return 0

    def get_token_balances(self, address: str) -> list:
        """Ambil semua ERC-20 token balance."""
        data = self._get({
            "module" : "account",
            "action" : "tokentx",
            "address": address,
            "sort"   : "desc",
        })
        txs = data.get("result", [])
        if not isinstance(txs, list):
            return []

        # Aggregate token balances dari transactions
        tokens = {}
        for tx in txs:
            symbol    = tx.get("tokenSymbol", "")
            name      = tx.get("tokenName", "")
            contract  = tx.get("contractAddress", "").lower()
            decimals  = int(tx.get("tokenDecimal", 18))
            value     = int(tx.get("value", 0))
            to_addr   = tx.get("to", "").lower()
            from_addr = tx.get("from", "").lower()

            if contract not in tokens:
                tokens[contract] = {
                    "symbol"  : symbol,
                    "name"    : name,
                    "contract": contract,
                    "decimals": decimals,
                    "balance" : 0,
                }

            if to_addr == address.lower():
                tokens[contract]["balance"] += value
            elif from_addr == address.lower():
                tokens[contract]["balance"] -= value

        # Filter yang balance > 0
        result = []
        for contract, data in tokens.items():
            balance = data["balance"] / (10 ** data["decimals"])
            if balance > 0:
                result.append({
                    **data,
                    "balance": round(balance, 6),
                })

        return result

    def get_nft_holdings(self, address: str) -> list:
        """Ambil NFT holdings."""
        data = self._get({
            "module" : "account",
            "action" : "tokennfttx",
            "address": address,
            "sort"   : "desc",
        })
        txs = data.get("result", [])
        if not isinstance(txs, list):
            return []

        # Track NFT ownership
        nfts = {}
        for tx in txs:
            token_id  = tx.get("tokenID", "")
            contract  = tx.get("contractAddress", "").lower()
            name      = tx.get("tokenName", "")
            symbol    = tx.get("tokenSymbol", "")
            to_addr   = tx.get("to", "").lower()
            from_addr = tx.get("from", "").lower()
            key       = f"{contract}_{token_id}"

            if to_addr == address.lower():
                nfts[key] = {
                    "name"    : name,
                    "symbol"  : symbol,
                    "contract": contract,
                    "token_id": token_id,
                }
            elif from_addr == address.lower() and key in nfts:
                del nfts[key]

        return list(nfts.values())

    def get_recent_transactions(self, address: str, limit: int = 10) -> list:
        """Ambil transaksi terbaru."""
        data = self._get({
            "module"    : "account",
            "action"    : "txlist",
            "address"   : address,
            "sort"      : "desc",
            "offset"    : limit,
            "page"      : 1,
        })
        result = data.get("result", [])
        return result if isinstance(result, list) else []


# ─────────────────────────────────────────────
# 3. WEB3 CLIENT
# ─────────────────────────────────────────────
class Web3Client:
    def __init__(self, rpc_url: str):
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        if self.w3.is_connected():
            log.info(f"✅ Web3 connected — block #{self.w3.eth.block_number}")
        else:
            log.warning("⚠️ Web3 tidak terkoneksi")

    def get_eth_balance(self, address: str) -> float:
        try:
            checksum = Web3.to_checksum_address(address)
            bal = self.w3.eth.get_balance(checksum)
            return self.w3.from_wei(bal, "ether")
        except Exception as e:
            log.error(f"Web3 balance error: {e}")
            return 0


# ─────────────────────────────────────────────
# 4. DEFI TRACKER
# ─────────────────────────────────────────────
class DeFiTracker:
    """Track posisi DeFi di Aave & Compound via API."""

    def __init__(self):
        self.session = requests.Session()

    def get_aave_position(self, address: str) -> dict:
        """Cek posisi lending di Aave V3."""
        try:
            # Aave V3 user data endpoint
            r = self.session.get(
                f"https://aave-api-v2.aave.com/data/users/{address.lower()}",
                timeout=10
            )
            if r.status_code == 200:
                data = r.json()
                return {
                    "protocol"          : "Aave V3",
                    "total_collateral"  : data.get("totalCollateralUSD", 0),
                    "total_debt"        : data.get("totalDebtUSD", 0),
                    "health_factor"     : data.get("healthFactor", 0),
                    "net_worth"         : float(data.get("totalCollateralUSD", 0)) - float(data.get("totalDebtUSD", 0)),
                }
        except Exception as e:
            log.debug(f"Aave position error: {e}")
        return {}

    def get_defi_summary(self, address: str) -> list:
        """Ambil summary semua posisi DeFi."""
        positions = []
        aave = self.get_aave_position(address)
        if aave:
            positions.append(aave)
        return positions


# ─────────────────────────────────────────────
# 5. PORTFOLIO ANALYZER
# ─────────────────────────────────────────────
class PortfolioAnalyzer:
    """Core engine untuk analisis portfolio."""

    def __init__(self):
        self.etherscan = EtherscanClient(ETHERSCAN_API_KEY)
        self.web3      = Web3Client(INFURA_URL)
        self.prices    = PriceClient()
        self.defi      = DeFiTracker()

    def analyze(self, wallet_address: str) -> dict:
        """Analisis lengkap portfolio satu wallet."""
        log.info(f"📊 Analyzing portfolio: {wallet_address[:10]}...")
        address = wallet_address.strip()

        # 1. ETH Balance
        eth_balance = float(self.web3.get_eth_balance(address))
        eth_price   = self.prices.get_eth_price()
        eth_value   = eth_balance * eth_price

        # 2. ERC-20 Tokens
        tokens      = self.etherscan.get_token_balances(address)
        token_total = 0
        for token in tokens[:20]:  # limit 20 tokens
            price = self.prices.get_token_price(token["contract"])
            token["price_usd"] = price
            token["value_usd"] = round(token["balance"] * price, 2)
            token_total += token["value_usd"]

        # Sort by value
        tokens = sorted(tokens, key=lambda x: x.get("value_usd", 0), reverse=True)

        # 3. NFTs
        nfts = self.etherscan.get_nft_holdings(address)

        # 4. DeFi Positions
        defi_positions = self.defi.get_defi_summary(address)
        defi_total     = sum(p.get("net_worth", 0) for p in defi_positions)

        # 5. Recent TXs
        recent_txs = self.etherscan.get_recent_transactions(address, limit=5)

        # 6. Total Portfolio Value
        total_value = eth_value + token_total + defi_total

        return {
            "address"       : address,
            "timestamp"     : datetime.now().isoformat(),
            "eth"           : {
                "balance"   : round(eth_balance, 6),
                "price_usd" : eth_price,
                "value_usd" : round(eth_value, 2),
            },
            "tokens"        : tokens,
            "nfts"          : nfts,
            "defi"          : defi_positions,
            "summary"       : {
                "total_value_usd" : round(total_value, 2),
                "eth_value"       : round(eth_value, 2),
                "token_value"     : round(token_total, 2),
                "defi_value"      : round(defi_total, 2),
                "nft_count"       : len(nfts),
                "token_count"     : len(tokens),
            }
        }


# ─────────────────────────────────────────────
# 6. TELEGRAM REPORTER
# ─────────────────────────────────────────────
class TelegramReporter:
    def __init__(self, token: str, chat_id: str):
        self.token   = token
        self.chat_id = chat_id
        self.base    = f"https://api.telegram.org/bot{token}"

    def send(self, text: str):
        try:
            r = requests.post(
                f"{self.base}/sendMessage",
                json={
                    "chat_id"   : self.chat_id,
                    "text"      : text,
                    "parse_mode": "Markdown",
                },
                timeout=10
            )
            if r.status_code == 200:
                log.info("✅ Telegram message sent")
        except Exception as e:
            log.error(f"Telegram error: {e}")

    def send_portfolio(self, data: dict):
        """Format dan kirim portfolio report ke Telegram."""
        summary = data["summary"]
        eth     = data["eth"]
        tokens  = data["tokens"][:5]  # top 5 tokens
        nfts    = data["nfts"][:3]    # top 3 NFTs
        defi    = data["defi"]

        addr = data["address"]
        short_addr = f"{addr[:6]}...{addr[-4:]}"

        msg = f"""
💼 *PORTFOLIO TRACKER*
━━━━━━━━━━━━━━━━━━━━━━
👛 Wallet: `{short_addr}`
⏰ {data['timestamp'][:19]}

💰 *Total Value: ${summary['total_value_usd']:,.2f}*
━━━━━━━━━━━━━━━━━━━━━━

🔷 *ETH*
• Balance : `{eth['balance']} ETH`
• Price   : `${eth['price_usd']:,.2f}`
• Value   : `${eth['value_usd']:,.2f}`
        """.strip()

        # Top tokens
        if tokens:
            msg += "\n\n🪙 *Top Tokens*"
            for t in tokens:
                val = t.get("value_usd", 0)
                if val > 0:
                    msg += f"\n• {t['symbol']}: `{t['balance']}` (~`${val:,.2f}`)"
                else:
                    msg += f"\n• {t['symbol']}: `{t['balance']}`"

        # NFTs
        if nfts:
            msg += f"\n\n🖼️ *NFTs ({len(data['nfts'])} total)*"
            for n in nfts:
                msg += f"\n• {n['name']} #{n['token_id']}"

        # DeFi
        if defi:
            msg += "\n\n🏦 *DeFi Positions*"
            for p in defi:
                msg += f"\n• {p['protocol']}: Net `${p['net_worth']:,.2f}`"
                if p.get("health_factor"):
                    msg += f" | HF: `{p['health_factor']:.2f}`"

        # Summary
        msg += f"""

━━━━━━━━━━━━━━━━━━━━━━
📊 *Breakdown*
• ETH    : `${summary['eth_value']:,.2f}`
• Tokens : `${summary['token_value']:,.2f}` ({summary['token_count']} tokens)
• DeFi   : `${summary['defi_value']:,.2f}`
• NFTs   : `{summary['nft_count']} items`
        """

        self.send(msg.strip())

    def send_recent_txs(self, txs: list, address: str):
        """Kirim recent transactions."""
        if not txs:
            return
        msg = "📋 *Recent Transactions*\n━━━━━━━━━━━━━━━━━━━━━━\n"
        for tx in txs[:5]:
            ts     = datetime.fromtimestamp(int(tx.get("timeStamp", 0))).strftime("%m-%d %H:%M")
            value  = int(tx.get("value", 0)) / 1e18
            to     = tx.get("to", "")[:8]
            status = "✅" if tx.get("isError") == "0" else "❌"
            msg   += f"{status} `{ts}` → `{to}...` | `{value:.4f} ETH`\n"
        self.send(msg)


# ─────────────────────────────────────────────
# 7. PORTFOLIO BOT (Telegram Commands)
# ─────────────────────────────────────────────
class PortfolioBot:
    def __init__(self):
        self.token    = TELEGRAM_TOKEN
        self.chat_id  = TELEGRAM_CHAT_ID
        self.base     = f"https://api.telegram.org/bot{self.token}"
        self.reporter = TelegramReporter(self.token, self.chat_id)
        self.analyzer = PortfolioAnalyzer()
        self.offset   = 0
        self.running  = True
        self.watchlist = []  # wallet addresses to monitor
        log.info("🤖 PortfolioBot initialized")

    def send(self, chat_id: str, text: str):
        try:
            requests.post(
                f"{self.base}/sendMessage",
                json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
                timeout=10
            )
        except Exception as e:
            log.error(f"Send error: {e}")

    def get_updates(self) -> list:
        try:
            r = requests.get(
                f"{self.base}/getUpdates",
                params={"offset": self.offset, "timeout": 10},
                timeout=15
            )
            return r.json().get("result", [])
        except Exception:
            return []

    # ── Commands ──────────────────────────────
    def cmd_start(self, chat_id: str):
        self.send(chat_id, """
🚀 *Portfolio Tracker Bot*
━━━━━━━━━━━━━━━━━━━━━━

Track semua aset crypto kamu dalam satu dashboard!

📋 *Commands:*
/track `<address>` — Analisis portfolio wallet
/watch `<address>` — Tambah ke watchlist (auto-refresh)
/watchlist — Lihat semua wallet di watchlist
/remove `<address>` — Hapus dari watchlist
/refresh — Refresh semua wallet di watchlist
/txs `<address>` — Lihat recent transactions
/help — Bantuan

*Contoh:*
`/track 0x742d35Cc6634C0532925a3b8D4C9C7D1a8E3F4b`
        """.strip())

    def cmd_track(self, chat_id: str, args: list):
        if not args:
            self.send(chat_id, "⚠️ Masukkan wallet address!\nContoh: `/track 0x742d35...`")
            return
        address = args[0].strip()
        if not address.startswith("0x") or len(address) != 42:
            self.send(chat_id, "❌ Address tidak valid. Format: `0x...` (42 karakter)")
            return

        self.send(chat_id, f"🔍 Menganalisis portfolio...\n`{address}`\n⏳ Mohon tunggu ~30 detik...")
        try:
            data = self.analyzer.analyze(address)
            self.reporter.send_portfolio(data)
        except Exception as e:
            self.send(chat_id, f"❌ Error: `{str(e)[:200]}`")

    def cmd_watch(self, chat_id: str, args: list):
        if not args:
            self.send(chat_id, "⚠️ Masukkan wallet address!")
            return
        address = args[0].strip()
        if address not in self.watchlist:
            self.watchlist.append(address)
            self.send(chat_id, f"✅ `{address[:10]}...` ditambahkan ke watchlist!\nKamu akan dapat update setiap {REFRESH_INTERVAL} menit.")
        else:
            self.send(chat_id, "⚠️ Address ini sudah ada di watchlist.")

    def cmd_watchlist(self, chat_id: str):
        if not self.watchlist:
            self.send(chat_id, "📭 Watchlist kosong.\nGunakan `/watch <address>` untuk menambahkan wallet.")
            return
        lines = ["👀 *Watchlist*\n━━━━━━━━━━━━━━━━━━━━━━"]
        for i, addr in enumerate(self.watchlist, 1):
            lines.append(f"{i}. `{addr[:10]}...{addr[-4:]}`")
        self.send(chat_id, "\n".join(lines))

    def cmd_remove(self, chat_id: str, args: list):
        if not args:
            self.send(chat_id, "⚠️ Masukkan address yang mau dihapus.")
            return
        address = args[0].strip()
        if address in self.watchlist:
            self.watchlist.remove(address)
            self.send(chat_id, f"✅ `{address[:10]}...` dihapus dari watchlist.")
        else:
            self.send(chat_id, "❌ Address tidak ditemukan di watchlist.")

    def cmd_refresh(self, chat_id: str):
        if not self.watchlist:
            self.send(chat_id, "📭 Watchlist kosong.")
            return
        self.send(chat_id, f"🔄 Refreshing {len(self.watchlist)} wallet...")
        for address in self.watchlist:
            try:
                data = self.analyzer.analyze(address)
                self.reporter.send_portfolio(data)
                time.sleep(2)
            except Exception as e:
                self.send(chat_id, f"❌ Error untuk `{address[:10]}...`: `{str(e)[:100]}`")

    def cmd_txs(self, chat_id: str, args: list):
        if not args:
            self.send(chat_id, "⚠️ Masukkan wallet address!")
            return
        address = args[0].strip()
        self.send(chat_id, f"📋 Mengambil transaksi terbaru...")
        try:
            txs = self.analyzer.etherscan.get_recent_transactions(address, limit=5)
            self.reporter.send_recent_txs(txs, address)
        except Exception as e:
            self.send(chat_id, f"❌ Error: `{str(e)[:200]}`")

    # ── Message Router ────────────────────────
    def handle(self, message: dict):
        text     = message.get("text", "").strip()
        chat_id  = str(message.get("chat", {}).get("id", ""))
        if not text or not chat_id:
            return

        parts   = text.split()
        command = parts[0].lower()
        args    = parts[1:]
        log.info(f"📨 {command} from {chat_id}")

        if command in ("/start", "/help"): self.cmd_start(chat_id)
        elif command == "/track":          self.cmd_track(chat_id, args)
        elif command == "/watch":          self.cmd_watch(chat_id, args)
        elif command == "/watchlist":      self.cmd_watchlist(chat_id)
        elif command == "/remove":         self.cmd_remove(chat_id, args)
        elif command == "/refresh":        self.cmd_refresh(chat_id)
        elif command == "/txs":            self.cmd_txs(chat_id, args)
        else:
            self.send(chat_id, "❓ Command tidak dikenal. Ketik /help untuk bantuan.")

    # ── Main Loop ─────────────────────────────
    def run(self):
        log.info("🚀 PortfolioBot started!")
        last_refresh = time.time()

        while self.running:
            try:
                updates = self.get_updates()
                for update in updates:
                    self.offset = update["update_id"] + 1
                    msg = update.get("message", {})
                    if msg:
                        self.handle(msg)

                # Auto-refresh watchlist
                if self.watchlist and time.time() - last_refresh > REFRESH_INTERVAL * 60:
                    log.info(f"🔄 Auto-refreshing {len(self.watchlist)} wallets...")
                    for address in self.watchlist:
                        try:
                            data = self.analyzer.analyze(address)
                            self.reporter.send_portfolio(data)
                            time.sleep(2)
                        except Exception as e:
                            log.error(f"Auto-refresh error: {e}")
                    last_refresh = time.time()

            except KeyboardInterrupt:
                log.info("🛑 Bot stopped.")
                self.running = False
            except Exception as e:
                log.error(f"Polling error: {e}")
                time.sleep(5)


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "analyze":
        # Mode: python portfolio_tracker.py analyze <address>
        if len(sys.argv) < 3:
            print("Usage: python portfolio_tracker.py analyze <wallet_address>")
            sys.exit(1)

        address  = sys.argv[2]
        analyzer = PortfolioAnalyzer()
        reporter = TelegramReporter(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)

        print(f"\n📊 Analyzing: {address}")
        data = analyzer.analyze(address)

        print(f"\n💰 Total Value: ${data['summary']['total_value_usd']:,.2f}")
        print(f"🔷 ETH: {data['eth']['balance']} ETH (${data['eth']['value_usd']:,.2f})")
        print(f"🪙 Tokens: {data['summary']['token_count']} (${data['summary']['token_value']:,.2f})")
        print(f"🖼️ NFTs: {data['summary']['nft_count']}")

        reporter.send_portfolio(data)
        print("\n✅ Report sent to Telegram!")

    else:
        # Mode: Telegram Bot
        bot = PortfolioBot()
        bot.run()
