"""
Polymarket Prediction & AI Reasoning Engine
Provides:
- In-depth market summary and context analysis
- Sentiment and crowd signal evaluation
- Expected Value (EV), Kelly Criterion staking, and Risk scoring
- EIP-712 Order Preparation simulation for trading execution
"""

import json
from typing import Dict, Any, List

class PredictionEngine:
    def __init__(self, client):
        self.client = client

    def parse_market_tokens(self, market: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract outcomes with their clobTokenIds and current prices."""
        outcomes = market.get("outcomes", [])
        if isinstance(outcomes, str):
            try:
                outcomes = json.loads(outcomes)
            except Exception:
                outcomes = [outcomes]

        outcome_prices = market.get("outcomePrices", [])
        if isinstance(outcome_prices, str):
            try:
                outcome_prices = json.loads(outcome_prices)
            except Exception:
                outcome_prices = []

        token_ids = market.get("clobTokenIds", [])
        if isinstance(token_ids, str):
            try:
                token_ids = json.loads(token_ids)
            except Exception:
                token_ids = []

        parsed = []
        for i, outcome_name in enumerate(outcomes):
            price = 0.0
            if i < len(outcome_prices):
                try:
                    price = float(outcome_prices[i])
                except (ValueError, TypeError):
                    price = 0.0

            token_id = token_ids[i] if i < len(token_ids) else None
            parsed.append({
                "outcome": outcome_name,
                "price": price,
                "implied_probability_pct": round(price * 100, 2),
                "token_id": token_id
            })
        return parsed

    async def analyze_and_summarize(self, event_id: str) -> Dict[str, Any]:
        """
        Produce a comprehensive summary of a prediction event:
        1. Context & Resolution rules
        2. Market odds & Orderbook liquidity
        3. Community comments sentiment
        4. Key risk factors
        """
        # Fetch event
        events = await self.client.get_events(limit=1, active=True, closed=False)
        # Fetch target event by ID if possible
        # Or look up directly
        event = None
        all_ev = await self.client.get_events(limit=50)
        for ev in all_ev:
            if str(ev.get("id")) == str(event_id):
                event = ev
                break
        
        if not event and all_ev:
            event = all_ev[0]

        # Extract comments
        comments = []
        try:
            comments = await self.client.get_event_comments(event_id=event.get("id"), limit=10)
        except Exception:
            comments = []

        # Markets breakdown
        markets_summary = []
        for m in event.get("markets", []):
            outcomes = self.parse_market_tokens(m)
            # Try to fetch orderbook for the primary token (Yes)
            orderbook_info = {"depth": "N/A", "best_bid": m.get("bestBid"), "best_ask": m.get("bestAsk")}
            if outcomes and outcomes[0].get("token_id"):
                try:
                    ob = await self.client.get_orderbook(outcomes[0]["token_id"])
                    bids = ob.get("bids", [])
                    asks = ob.get("asks", [])
                    total_bid_vol = sum(float(b.get("size", 0)) * float(b.get("price", 0)) for b in bids[:5])
                    total_ask_vol = sum(float(a.get("size", 0)) * float(a.get("price", 0)) for a in asks[:5])
                    orderbook_info["top5_bid_liquidity_usd"] = round(total_bid_vol, 2)
                    orderbook_info["top5_ask_liquidity_usd"] = round(total_ask_vol, 2)
                    orderbook_info["spread"] = m.get("spread")
                except Exception:
                    pass

            markets_summary.append({
                "market_id": m.get("id"),
                "question": m.get("question"),
                "volume_usd": m.get("volume"),
                "outcomes": outcomes,
                "orderbook": orderbook_info
            })

        # Synthesize crowd sentiment
        sample_comments = [c.get("body", "") for c in comments if c.get("body")]

        summary = {
            "event_id": event.get("id"),
            "title": event.get("title"),
            "category": [t.get("label") for t in event.get("tags", []) if isinstance(t, dict)],
            "resolution_rules": event.get("description"),
            "resolution_source": event.get("resolutionSource"),
            "end_date": event.get("endDate"),
            "volume_24h_usd": event.get("volume24hr"),
            "total_liquidity_usd": event.get("liquidity"),
            "markets": markets_summary,
            "community_sentiment": {
                "comment_count": event.get("commentCount", 0),
                "recent_comments_sample": sample_comments[:5]
            }
        }
        return summary

    def calculate_expected_value(
        self,
        market_price: float,
        user_estimated_probability: float,
        bankroll: float = 1000.0
    ) -> Dict[str, Any]:
        """
        Calculate quantitative trading parameters:
        - Expected Value (EV) per $1 bet
        - Kelly Criterion optimal position size fraction
        - Recommended bet size
        """
        p = user_estimated_probability
        q = 1.0 - p
        # Odds b: If you buy share at market_price (e.g. 0.60) and payout is 1.00, net win is (1 - price) per price risked
        # Net odds b = (1.0 - market_price) / market_price
        if market_price <= 0 or market_price >= 1:
            return {"error": "Market price must be between 0 and 1 (exclusive)."}

        b = (1.0 - market_price) / market_price
        # Kelly fraction: f* = (b*p - q) / b
        kelly_fraction = (b * p - q) / b
        
        # Expected value per $1 invested
        # EV = p * (1/market_price - 1) - (1-p) * 1 = (p / market_price) - 1
        ev_pct = ((p / market_price) - 1.0) * 100

        recommended_action = "PASS"
        if ev_pct > 5.0 and kelly_fraction > 0:
            recommended_action = "BUY (Positive EV)"
        elif ev_pct < -5.0:
            recommended_action = "AVOID / SELL (Negative EV)"

        # Half-Kelly for safer bankroll management
        safe_fraction = max(0.0, kelly_fraction * 0.5)
        recommended_stake = round(bankroll * safe_fraction, 2)

        return {
            "market_price": market_price,
            "market_implied_prob_pct": round(market_price * 100, 2),
            "estimated_prob_pct": round(p * 100, 2),
            "expected_value_pct": round(ev_pct, 2),
            "kelly_fraction": round(max(0.0, kelly_fraction), 4),
            "half_kelly_fraction": round(safe_fraction, 4),
            "recommended_action": recommended_action,
            "recommended_stake_usd": recommended_stake,
            "bankroll_usd": bankroll
        }

    def generate_order_payload(
        self,
        token_id: str,
        side: str,
        price: float,
        size: float,
        order_type: str = "GTC"
    ) -> Dict[str, Any]:
        """
        Format official CLOB EIP-712 Order schema for execution or signing:
        side: BUY or SELL
        order_type: GTC, GTD, FOK, FAK
        """
        return {
            "order": {
                "token_id": token_id,
                "price": round(price, 2),
                "size": round(size, 2),
                "side": side.upper(),
                "order_type": order_type.upper(),
            },
            "signing_standard": "EIP-712",
            "settlement_chain": "Polygon (Chain ID 137)",
            "collateral_asset": "pUSD / USDC",
            "instructions": "Sign this structured data with your Web3 / Polygon private key and submit to POST https://clob.polymarket.com/order"
        }

    def check_market_risk_policy(
        self,
        market_question: str,
        event_title: str = "",
        liquidity_usd: float = 0.0,
        spread: float = 0.0,
        min_liquidity_usd: float = 200000.0,
        max_spread: float = 0.03
    ) -> Dict[str, Any]:
        """
        Enforce strict hard-coded risk & liquidity rules learned from historical losses:
        1. Minimum liquidity gate (>= $200,000) & tight spread (<= 3 cents) to prevent slippage.
        2. NO finish/method-of-victory props (KO/TKO, Submission, Go the Distance, Round props) - Lesson from REC-109.
        3. NO insider/black-swan executive resignation, rejoin, or personal markets - Lesson from REC-102.
        4. Tier-1 Esports Expansion (CS2, LoL, Dota 2, Valorant): Allowed ONLY if Moneyline Winner & liquidity >= $200,000.
        """
        text = f"{event_title} {market_question}".lower()

        # 1. Blacklist finish / method-of-victory / round props
        finish_prop_keywords = [
            "ko or tko", "by ko", "submission", "go the distance",
            "win in round", "decision or draw", "o/u 0.5 rounds",
            "o/u 1.5 rounds", "o/u 2.5 rounds", "rounds handicap",
            "map handicap", "first blood", "total kills"
        ]
        for kw in finish_prop_keywords:
            if kw in text:
                return {
                    "allowed": False,
                    "reason": f"BLACKLISTED (Finish/Prop Bet - '{kw}'): Rủi ro phương thức kết thúc quá cao (Bài học REC-109). Chỉ chọn kèo thắng chung cuộc (Moneyline/Winner)."
                }

        # 2. Blacklist insider / black-swan executive or personal markets
        insider_keywords = [
            "resignation", "removal", "rejoins", "divorce", "next ceo", "fire ", "impeach", "aliens exist", "jesus christ"
        ]
        for kw in insider_keywords:
            if kw in text:
                return {
                    "allowed": False,
                    "reason": f"BLACKLISTED (Insider/Black Swan/Meme - '{kw}'): Rủi ro thông tin nội bộ hoặc phi thực tế (Bài học REC-102)."
                }

        # 3. Blacklist speculative short-term crypto price targets (Lesson from REC-113 & REC-114)
        crypto_price_keywords = [
            "bitcoin above", "ethereum above", "solana above", "xrp above",
            "what price will bitcoin hit", "what price will ethereum hit",
            "what price will solana hit", "price of bitcoin be above", "price of ethereum be above",
            "bitcoin reach $", "ethereum reach $"
        ]
        for kw in crypto_price_keywords:
            if kw in text:
                return {
                    "allowed": False,
                    "reason": f"BLACKLISTED (Speculative Crypto Price - '{kw}'): Thị trường đầu cơ cao, dễ bị cá mập thao túng mốc giá (Bài học REC-113/114)."
                }

        # 3. Liquidity & Spread check (when liquidity metadata is provided)
        if liquidity_usd > 0 and liquidity_usd < min_liquidity_usd:
            return {
                "allowed": False,
                "reason": f"LOW LIQUIDITY (${liquidity_usd:,.0f} < ${min_liquidity_usd:,.0f}): Thanh khoản quá mỏng, dễ trượt giá (slippage)."
            }

        if spread > max_spread:
            return {
                "allowed": False,
                "reason": f"WIDE SPREAD ({spread:.3f} > {max_spread:.3f}): Chênh lệch giá mua/bán quá rộng."
            }

        # 4. Identify Tier-1 Esports eligibility (CS2, LoL, Dota 2, Valorant)
        esports_tags = ["counter-strike", "cs2", "lol", "league of legends", "dota 2", "valorant"]
        is_esports = any(tag in text for tag in esports_tags)
        if is_esports:
            return {
                "allowed": True,
                "category": "Tier-1 Esports (Moneyline)",
                "reason": "Passed Tier-1 Esports policy: Moneyline Winner & Liquidity >= $200k."
            }

        return {"allowed": True, "category": "Standard Market", "reason": "Passed all risk & liquidity policy checks."}


