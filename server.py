"""
FastAPI Server exposing Polymarket unified capabilities:
- Direct Polymarket API wrapper (Gamma, CLOB, Data v2)
- Prediction Intelligence & EV / Kelly staking
- Order generation & Simulation
- Interactive Web Dashboard
"""

import os
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

from client import PolymarketClient
from engine import PredictionEngine
from advisor import AdvisorManager

app = FastAPI(
    title="Polymarket Prediction & Interaction Hub",
    description="Unified API & Intelligence Hub connecting directly to official Polymarket endpoints",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = PolymarketClient()
engine = PredictionEngine(client)
advisor = AdvisorManager()


# ==========================================
# Data Models
# ==========================================

class EVRequest(BaseModel):
    market_price: float = Field(..., description="Current market price (0.01 to 0.99)", ge=0.01, le=0.99)
    estimated_probability: float = Field(..., description="Your forecast probability (0.01 to 0.99)", ge=0.01, le=0.99)
    bankroll: float = Field(default=1000.0, description="Available capital in USD", gt=0)

class OrderRequest(BaseModel):
    token_id: str = Field(..., description="Polymarket outcome clobTokenId")
    side: str = Field(default="BUY", description="BUY or SELL")
    price: float = Field(..., description="Target limit price (0.01 to 0.99)", ge=0.01, le=0.99)
    size: float = Field(..., description="Number of shares to buy/sell", gt=0)
    order_type: str = Field(default="GTC", description="GTC, GTD, FOK, or FAK")

# ==========================================
# 1. MARKETS & DISCOVERY (Gamma API)
# ==========================================

@app.get("/api/events", summary="Get trending / active events")
async def list_events(
    limit: int = 15,
    offset: int = 0,
    order: str = "volume24hr",
    ascending: bool = False,
    slug: Optional[str] = None
):
    try:
        return await client.get_events(limit=limit, offset=offset, order=order, ascending=ascending, slug=slug)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/markets", summary="Get markets directly")
async def list_markets(
    limit: int = 20,
    offset: int = 0,
    order: str = "volume24hr",
    ascending: bool = False,
    slug: Optional[str] = None
):
    try:
        return await client.get_markets(limit=limit, offset=offset, order=order, ascending=ascending, slug=slug)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/search", summary="Search markets by keyword")
async def search_markets(q: str = Query(..., description="Search term")):
    try:
        return await client.search(query=q)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/comments", summary="Get event discussion comments")
async def get_comments(event_id: str, limit: int = 20):
    try:
        return await client.get_event_comments(event_id=event_id, limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==========================================
# 2. ORDERBOOK & REALTIME DATA (CLOB API)
# ==========================================

@app.get("/api/clob/book", summary="Get live CLOB orderbook for a token")
async def get_orderbook(token_id: str):
    try:
        return await client.get_orderbook(token_id=token_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/clob/price", summary="Get best buy/sell price")
async def get_price(token_id: str, side: str = "buy"):
    try:
        return await client.get_price(token_id=token_id, side=side)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/clob/midpoint", summary="Get midpoint price")
async def get_midpoint(token_id: str):
    try:
        return await client.get_midpoint(token_id=token_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/clob/prices-history", summary="Get historical price time-series")
async def get_price_history(token_id: str, interval: str = "1d"):
    try:
        return await client.get_price_history(token_id=token_id, interval=interval)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==========================================
# 3. ON-CHAIN & ANALYTICS (Data API v2)
# ==========================================

@app.get("/api/analytics/trades", summary="Get platform-wide recent trades")
async def get_trades(limit: int = 20):
    try:
        return await client.get_recent_trades(limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analytics/holders", summary="Get top holders for a market condition")
async def get_top_holders(condition_id: str, limit: int = 10):
    try:
        return await client.get_top_holders(condition_id=condition_id, limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analytics/user-positions", summary="Get positions of a specific wallet")
async def get_user_positions(address: str, limit: int = 50):
    try:
        return await client.get_user_positions(user_address=address, limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==========================================
# 4. PREDICTION ENGINE & ASSISTANT
# ==========================================

@app.get("/api/predict/summary/{event_id}", summary="Comprehensive event summary & intelligence")
async def event_intelligence_summary(event_id: str):
    try:
        return await engine.analyze_and_summarize(event_id=event_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/predict/calculate-ev", summary="Calculate Expected Value (EV) & Kelly Stake")
async def calculate_ev(req: EVRequest):
    return engine.calculate_expected_value(
        market_price=req.market_price,
        user_estimated_probability=req.estimated_probability,
        bankroll=req.bankroll
    )

@app.post("/api/predict/prepare-order", summary="Formulate signed EIP-712 order for Polymarket")
async def prepare_order(req: OrderRequest):
    return engine.generate_order_payload(
        token_id=req.token_id,
        side=req.side,
        price=req.price,
        size=req.size,
        order_type=req.order_type
    )

@app.get("/api/predict/scan-opportunities", summary="Scan Polymarket for high-liquidity, low-spread, policy-compliant opportunities")
async def scan_safe_opportunities(
    limit: int = 50,
    min_liquidity_usd: float = 200000.0,
    max_spread: float = 0.03
):
    try:
        events = await client.get_events(limit=limit, active=True, closed=False, order="volume24hr", ascending=False)
        approved = []
        rejected_summary = {"low_liquidity": 0, "wide_spread": 0, "risk_blacklisted": 0}

        for ev in events:
            liq = float(ev.get("liquidity") or 0)
            vol24 = float(ev.get("volume24hr") or 0)
            title = ev.get("title", "")
            slug = ev.get("slug", "")
            
            if liq < min_liquidity_usd:
                rejected_summary["low_liquidity"] += 1
                continue

            valid_markets = []
            for m in ev.get("markets", []):
                if m.get("closed"):
                    continue
                q = m.get("question", "")
                sp = float(m.get("spread") or 0)
                policy = engine.check_market_risk_policy(
                    market_question=q,
                    event_title=title,
                    liquidity_usd=liq,
                    spread=sp,
                    min_liquidity_usd=min_liquidity_usd,
                    max_spread=max_spread
                )
                if not policy["allowed"]:
                    if "WIDE SPREAD" in policy["reason"]:
                        rejected_summary["wide_spread"] += 1
                    else:
                        rejected_summary["risk_blacklisted"] += 1
                    continue

                outcomes = engine.parse_market_tokens(m)
                valid_markets.append({
                    "question": q,
                    "spread": sp,
                    "outcomes": outcomes,
                    "policy_category": policy.get("category")
                })

            if valid_markets:
                approved.append({
                    "event_id": ev.get("id"),
                    "title": title,
                    "polymarket_url": f"https://polymarket.com/event/{slug}",
                    "liquidity_usd": liq,
                    "volume24hr_usd": vol24,
                    "end_date": (ev.get("endDate") or "")[:10],
                    "markets_count": len(valid_markets),
                    "sample_markets": valid_markets[:3]
                })

        return {
            "policy_config": {
                "min_liquidity_usd": min_liquidity_usd,
                "max_spread": max_spread
            },
            "approved_events_count": len(approved),
            "rejected_counts": rejected_summary,
            "opportunities": approved
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# 5. AI ADVISOR & PERFORMANCE TRACKER
# ==========================================

class NewDecisionRequest(BaseModel):
    title: str
    slug: Optional[str] = None
    market_price: float = Field(..., ge=0.01, le=0.99)
    ai_prob: float = Field(..., ge=0.01, le=0.99)
    rationale: str

@app.get("/api/advisor/decisions", summary="Get all advisor recommendations & audit history")
async def get_advisor_decisions():
    return advisor.get_decisions()

@app.post("/api/advisor/decisions", summary="Record a new AI recommendation")
async def create_advisor_decision(req: NewDecisionRequest):
    return advisor.add_decision(
        title=req.title,
        slug=req.slug or "",
        market_price=req.market_price,
        ai_prob=req.ai_prob,
        rationale=req.rationale
    )

@app.get("/api/advisor/performance", summary="Get AI prediction win rate, ROI, PnL and Profit Factor")
async def get_advisor_performance():
    return advisor.get_performance_stats()

# ==========================================
# 6. WEB DASHBOARD
# ==========================================

@app.get("/", response_class=HTMLResponse, summary="Interactive Web UI")
async def get_dashboard():
    with open("/home/antigravity/polymarket_hub/dashboard.html", "r", encoding="utf-8") as f:
        return f.read()

@app.get("/advisor", response_class=HTMLResponse, summary="AI Advisor Performance Dashboard")
async def get_advisor_dashboard():
    with open("/home/antigravity/.gemini/jetski/brain/v1/default/jetski_remote_agents_3p/e86fb567-3e83-4fe9-a1ff-f038199a905b/advisor_dashboard.html", "r", encoding="utf-8") as f:
        return f.read()
