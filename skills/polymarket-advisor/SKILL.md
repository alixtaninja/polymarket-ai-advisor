---
name: polymarket-advisor
description: Daily AI Prediction Advisor & Risk Manager for Polymarket. Use when asked to check daily Polymarket bets, reconcile pending UMA Oracle resolutions, scan high-liquidity opportunities, or continue daily Polymarket prediction advisory work.
---
# Polymarket AI Advisor — Daily Operations & Risk Playbook

This skill encodes all architecture, API quirks, historical lessons, and hard risk rules so any AI can seamlessly run daily Polymarket prediction advisory and performance tracking.

## 1. Persistent Storage & Workspace

- **Persistent Directory (survives across conversations):** `/home/antigravity/.gemini/polymarket/`
  - `decisions.json`: Source of truth for all historical & pending bets (`REC-101` onwards).
  - Backup copies of `client.py`, `engine.py`, `advisor.py`, `server.py`, `dashboard.html`, `advisor_dashboard.html`.
- **Workspace Directory:** `/home/antigravity/polymarket_hub/`
  - If `/home/antigravity/polymarket_hub/` is missing in a fresh VM, restore it from `/home/antigravity/.gemini/polymarket/` and create a `.venv` with `uv venv .venv && uv pip install -r requirements.txt`.
  - `advisor.py` automatically reads `/home/antigravity/.gemini/polymarket/decisions.json` first. Always keep both copies in sync if editing locally.

## 2. Environment & Polymarket API Quirks

1. **`NO_PROXY` Sanitization for `httpx`:**
   The VM sets `NO_PROXY=localhost,127.0.0.1,::1,[::1]`, which causes `httpx.InvalidURL: Invalid port: ':1]'`. Always strip `,[::1]` from `NO_PROXY` and `no_proxy` before importing `httpx` (already handled in `client.py`).
2. **CLOB Headers:**
   `clob.polymarket.com` blocks default Python `urllib` User-Agents (HTTP 403) and requires `Accept: application/json` (avoids 406).
3. **Data API v2 & Comments:**
   Data API v1 `/trades` is retired (410 Gone). Use `/v2/trades`, `/v2/holders`, `/v2/positions`. Comments require both `parent_entity_type=Event` and `parent_entity_id=<id>`.
4. **Geoblock Constraint:**
   The VM IP (`SG`) is geoblocked for live order submission (`POST /order`). Read, analysis, Gamma/CLOB scanning, and EIP-712 order payload generation work normally; live order execution requires a non-blocked IP + Polygon wallet private key + `pUSD`/`USDC` collateral.
5. **Order Constraints:**
   `orderMinSize = 5` shares, `orderPriceMinTickSize = 0.01` (or `0.001` on extreme markets).

## 3. Five Hard Risk Rules (Learned from Real Losses)

Never violate these rules, regardless of apparent EV:

1. **NO Insider / Executive / Personal Markets (`REC-102` Lesson):**
   Never bet on CEO resignation, removal, rejoin, divorce, scandal, or private corporate/insider events.
2. **NO Finish / Method-of-Victory / Handicap Props (`REC-109` Lesson):**
   Never bet on `KO/TKO`, `Submission`, `Go the Distance`, `Round X`, `Map Handicap`, or `Spread` props. **ONLY trade Moneyline / Match Winner.**
3. **NO Short-Term Speculative Crypto Price Thresholds (`REC-113` & `REC-114` Lesson):**
   Never bet on short-term crypto price targets (`bitcoin above`, `ethereum above`, `what price will ... hit`, `sol above`). High whale/stop-hunt manipulation and correlation risk.
4. **Strict Positive EV & Half-Kelly Sizing (`REC-105` Lesson):**
   Require **EV >= +10%** with a real fundamental/news edge. Use **Half-Kelly** sizing capped at **$120–$150** per trade on a $1,000 bankroll. Never enter negative-EV or low-conviction poll guesses.
5. **Liquidity & Spread Gate + Diversified Markets:**
   - Minimum event liquidity: **`>= $200,000`**
   - Maximum bid-ask spread: **`<= $0.03`**
   - Allowed categories: **Sports Moneyline** (NBA, NFL, UFC Winner, Soccer, Tennis), **Tier-1 Esports Moneyline** (CS2, LoL, Dota 2, Valorant — only if liquidity `>= $200,000`), and **High-Liquidity Macro/Fed/Geopolitics/Tech** with verifiable public data.
   - Avoid correlated duplicate bets on the same day/asset class.

## 4. Daily Execution Workflow

When the user asks for daily Polymarket updates, results, or new picks:

1. **Step 1 — Reconcile Pending Decisions:**
   - Load `/home/antigravity/.gemini/polymarket/decisions.json` (or `decisions.json`).
   - For every entry with `status == "PENDING"`, query Gamma API:
     `GET https://gamma-api.polymarket.com/events?slug=<slug>`
   - Check `closed`, `umaResolutionStatus == "resolved"`, and `outcomePrices` (e.g., `["1", "0"]` or `["0", "1"]`).
   - If resolved, compute exact PnL:
     - **WON:** `round(kelly_stake * (1.0 / market_price - 1.0), 2)`
     - **LOST:** `-kelly_stake`
   - Update `decisions.json`. Never fabricate outcomes.

2. **Step 2 — Scan & Filter Live Opportunities:**
   - Query Gamma API: `GET https://gamma-api.polymarket.com/events?active=true&closed=false&order=volume24hr&ascending=false&limit=50`
   - Run `PredictionEngine.check_market_risk_policy()` (`engine.py`) to reject blacklisted markets, low liquidity (`< $200,000`), or wide spreads (`> $0.03`).

3. **Step 3 — Multi-Source News & Context Check:**
   - Before recommending any Moneyline or Macro bet, verify current injuries, lineups, form, or macro releases via web search (similar to `last30days` multi-source grounding).
   - Never rely solely on market price without a concrete catalyst/edge.

4. **Step 4 — Recommend, Size & Log:**
   - Compute `EV = (ai_prob / market_price) - 1` (must be `>= +10%`) and Half-Kelly stake (max `$120–$150`).
   - Generate `eip712_order` payload via `engine.generate_order_payload()` if needed.
   - Append new `PENDING` recommendations (next `REC-XXX` ID) to `decisions.json` with `https://polymarket.com/event/<slug>`.

5. **Step 5 — Report in Vietnamese:**
   - Present reconciled results (Win/Loss, PnL), updated portfolio stats (`Win Rate`, `Net PnL`, `Profit Factor`, `W-L`), and any new filtered high-conviction opportunities with clickable Polymarket links.
