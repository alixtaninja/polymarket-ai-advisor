import os
# Ensure NO_PROXY / no_proxy is compatible with httpx URL parsing (strip [::1] brackets)
for key in ("NO_PROXY", "no_proxy"):
    val = os.environ.get(key)
    if val and ",[::1]" in val:
        os.environ[key] = val.replace(",[::1]", "")

import httpx
from typing import Optional, List, Dict, Any


class PolymarketClient:
    def __init__(
        self,
        gamma_url: str = "https://gamma-api.polymarket.com",
        clob_url: str = "https://clob.polymarket.com",
        data_url: str = "https://data-api.polymarket.com",
        timeout: float = 15.0,
    ):
        self.gamma_url = gamma_url.rstrip("/")
        self.clob_url = clob_url.rstrip("/")
        self.data_url = data_url.rstrip("/")
        self.headers = {
            "User-Agent": "PolymarketUnifiedClient/1.0 (Python)",
            "Accept": "application/json",
        }
        self.client = httpx.AsyncClient(headers=self.headers, timeout=timeout)

    async def close(self):
        await self.client.aclose()

    # ==========================================
    # 1. GAMMA API: Discovery & Metadata
    # ==========================================

    async def get_events(
        self,
        limit: int = 20,
        offset: int = 0,
        active: bool = True,
        closed: bool = False,
        order: str = "volume24hr",
        ascending: bool = False,
        tag_id: Optional[str] = None,
        slug: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch events with market information."""
        params: Dict[str, Any] = {
            "limit": limit,
            "offset": offset,
            "active": str(active).lower(),
            "closed": str(closed).lower(),
            "order": order,
            "ascending": str(ascending).lower(),
        }
        if tag_id:
            params["tag_id"] = tag_id
        if slug:
            params["slug"] = slug

        r = await self.client.get(f"{self.gamma_url}/events", params=params)
        r.raise_for_status()
        return r.json()

    async def get_markets(
        self,
        limit: int = 20,
        offset: int = 0,
        active: bool = True,
        closed: bool = False,
        order: str = "volume24hr",
        ascending: bool = False,
        slug: Optional[str] = None,
        id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch individual markets."""
        params: Dict[str, Any] = {
            "limit": limit,
            "offset": offset,
            "active": str(active).lower(),
            "closed": str(closed).lower(),
            "order": order,
            "ascending": str(ascending).lower(),
        }
        if slug:
            params["slug"] = slug
        if id:
            params["id"] = id

        r = await self.client.get(f"{self.gamma_url}/markets", params=params)
        r.raise_for_status()
        return r.json()

    async def search(self, query: str, limit: int = 20) -> Dict[str, Any]:
        """Search across events and markets."""
        params = {"query": query, "limit": limit}
        # Gamma API provides search via /events or /markets with search/slug queries
        r = await self.client.get(f"{self.gamma_url}/events", params={"title": query, "limit": limit})
        if r.status_code == 200 and r.json():
            return {"events": r.json()}
        # Fallback to query param
        r = await self.client.get(f"{self.gamma_url}/markets", params={"search": query, "limit": limit})
        if r.status_code == 200:
            return {"markets": r.json()}
        return {"results": []}

    async def get_event_comments(
        self,
        event_id: str,
        limit: int = 20,
        offset: int = 0,
        order: str = "createdAt",
        ascending: bool = False,
    ) -> List[Dict[str, Any]]:
        """Get public community comments for an event."""
        params = {
            "parent_entity_type": "Event",
            "parent_entity_id": str(event_id),
            "limit": limit,
            "offset": offset,
            "order": order,
            "ascending": str(ascending).lower(),
        }
        r = await self.client.get(f"{self.gamma_url}/comments", params=params)
        r.raise_for_status()
        return r.json()

    # ==========================================
    # 2. CLOB API: Real-time Orderbook & Prices
    # ==========================================

    async def get_orderbook(self, token_id: str) -> Dict[str, Any]:
        """Fetch full order book (bids and asks) for an outcome token."""
        r = await self.client.get(f"{self.clob_url}/book", params={"token_id": token_id})
        r.raise_for_status()
        return r.json()

    async def get_price(self, token_id: str, side: str = "buy") -> Dict[str, Any]:
        """Get best execution price for buy or sell side."""
        r = await self.client.get(f"{self.clob_url}/price", params={"token_id": token_id, "side": side.lower()})
        r.raise_for_status()
        return r.json()

    async def get_midpoint(self, token_id: str) -> Dict[str, Any]:
        """Get midpoint price between best bid and best ask."""
        r = await self.client.get(f"{self.clob_url}/midpoint", params={"token_id": token_id})
        r.raise_for_status()
        return r.json()

    async def get_spread(self, token_id: str) -> Dict[str, Any]:
        """Get spread for a token."""
        r = await self.client.get(f"{self.clob_url}/spread", params={"token_id": token_id})
        r.raise_for_status()
        return r.json()

    async def get_price_history(self, token_id: str, interval: str = "1d") -> Dict[str, Any]:
        """Get historical prices timeseries."""
        r = await self.client.get(f"{self.clob_url}/prices-history", params={"market": token_id, "interval": interval})
        r.raise_for_status()
        return r.json()

    async def get_server_time(self) -> Dict[str, Any]:
        """Get CLOB server unix timestamp."""
        r = await self.client.get(f"{self.clob_url}/time")
        r.raise_for_status()
        return {"timestamp": int(r.text.strip())}

    # ==========================================
    # 3. DATA API (v2): Holders, Positions, Trades
    # ==========================================

    async def get_recent_trades(self, limit: int = 20) -> Dict[str, Any]:
        """Fetch latest platform-wide trades."""
        r = await self.client.get(f"{self.data_url}/v2/trades", params={"limit": limit})
        r.raise_for_status()
        return r.json()

    async def get_top_holders(self, condition_id: str, limit: int = 10) -> Dict[str, Any]:
        """Get top share holders for a market condition."""
        r = await self.client.get(f"{self.data_url}/v2/holders", params={"condition_id": condition_id, "limit": limit})
        r.raise_for_status()
        return r.json()

    async def get_user_positions(self, user_address: str, limit: int = 50) -> Dict[str, Any]:
        """Fetch active positions held by an address."""
        r = await self.client.get(f"{self.data_url}/v2/positions", params={"user": user_address, "limit": limit})
        r.raise_for_status()
        return r.json()
