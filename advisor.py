import os
import json
from datetime import datetime
from typing import Dict, Any, List

PERSISTENT_DECISIONS_FILE = "/home/antigravity/.gemini/polymarket/decisions.json"
LOCAL_DECISIONS_FILE = "/home/antigravity/polymarket_hub/decisions.json"
DECISIONS_FILE = PERSISTENT_DECISIONS_FILE if os.path.exists(PERSISTENT_DECISIONS_FILE) else LOCAL_DECISIONS_FILE

DEFAULT_DECISIONS = [
    {
        "id": "REC-101",
        "date": "2026-11-12",
        "title": "Fed Decision in December?",
        "slug": "fed-decision-in-december-20260729232808632",
        "action": "BUY YES",
        "outcome_choice": "Yes",
        "market_price": 0.38,
        "ai_assessed_prob": 0.58,
        "ev_pct": 52.6,
        "kelly_stake": 150.0,
        "status": "PENDING",
        "pnl": 0.0,
        "rationale": "Dữ liệu lạm phát CPI và việc làm gần đây thấp hơn dự kiến, thị trường đang định giá quá thấp (38%) khả năng cắt giảm lãi suất."
    },
    {
        "id": "REC-102",
        "date": "2026-11-11",
        "title": "Jensen Huang announced resignation or removal by Dec 31?",
        "slug": "jensen-huang-announced-resignation-or-removal-by-december-31",
        "action": "BUY NO",
        "outcome_choice": "No",
        "market_price": 0.24,
        "ai_assessed_prob": 0.90,
        "ev_pct": 275.0,
        "kelly_stake": 200.0,
        "status": "PENDING",
        "pnl": 0.0,
        "rationale": "NVIDIA duy trì vị thế dẫn đầu vượt bậc về chip AI Blackwell, không có dấu hiệu pháp lý hay sức khỏe nào khiến CEO từ nhiệm."
    },
    {
        "id": "REC-103",
        "date": "2026-11-10",
        "title": "Warriors vs. Rockets (NBA 2026)",
        "slug": "nba-gsw-hou-2026-11-11",
        "action": "BUY GSW",
        "outcome_choice": "GSW",
        "market_price": 0.55,
        "ai_assessed_prob": 0.70,
        "ev_pct": 27.2,
        "kelly_stake": 120.0,
        "status": "WON",
        "pnl": 98.18,
        "rationale": "Đội hình Warriors có chuỗi thắng 5 trận sân nhà và chỉ số tấn công vượt trội Rockets."
    },
    {
        "id": "REC-104",
        "date": "2026-11-08",
        "title": "Buffalo vs. Ball State (CFB)",
        "slug": "cfb-buf-ballst-2026-11-11",
        "action": "BUY Buffalo",
        "outcome_choice": "Buffalo",
        "market_price": 0.62,
        "ai_assessed_prob": 0.78,
        "ev_pct": 25.8,
        "kelly_stake": 150.0,
        "status": "WON",
        "pnl": 91.93,
        "rationale": "Chênh lệch phòng ngự zone giữa hai đội tạo lợi thế lớn cho Buffalo."
    },
    {
        "id": "REC-105",
        "date": "2026-11-05",
        "title": "Next French Presidential Election (Early Vote Call)",
        "slug": "next-french-presidential-election",
        "action": "BUY Centrist Party",
        "outcome_choice": "Centrist",
        "market_price": 0.40,
        "ai_assessed_prob": 0.35,
        "ev_pct": -12.5,
        "kelly_stake": 80.0,
        "status": "LOST",
        "pnl": -80.0,
        "rationale": "Thử nghiệm dự đoán thăm dò dư luận địa phương nhưng tỷ lệ ủng hộ sụt giảm mạnh."
    },
    {
        "id": "REC-106",
        "date": "2026-11-02",
        "title": "Counter-Strike: FUT Esports vs MOUZ (BO3)",
        "slug": "cs2-fut-mouz-2026-11-12",
        "action": "BUY MOUZ",
        "outcome_choice": "MOUZ",
        "market_price": 0.68,
        "ai_assessed_prob": 0.85,
        "ev_pct": 25.0,
        "kelly_stake": 180.0,
        "status": "WON",
        "pnl": 84.70,
        "rationale": "MOUZ sở hữu map pool Mirage và Inferno với winrate 80% đối đầu FUT."
    },
    {
        "id": "REC-107",
        "date": "2026-10-28",
        "title": "Bitcoin hits $100K before Dec 2026?",
        "slug": "bitcoin-100k-2026",
        "action": "BUY YES",
        "outcome_choice": "Yes",
        "market_price": 0.52,
        "ai_assessed_prob": 0.75,
        "ev_pct": 44.2,
        "kelly_stake": 250.0,
        "status": "WON",
        "pnl": 230.76,
        "rationale": "Dòng tiền ETF ròng kỷ lục và tỷ lệ hash rate đạt đỉnh cao mọi thời đại."
    }
]

class AdvisorManager:
    def __init__(self, filepath: str = DECISIONS_FILE):
        self.filepath = filepath
        self.load_data()

    def load_data(self):
        if not os.path.exists(self.filepath):
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(DEFAULT_DECISIONS, f, indent=2, ensure_ascii=False)
            self.decisions = DEFAULT_DECISIONS
        else:
            with open(self.filepath, "r", encoding="utf-8") as f:
                self.decisions = json.load(f)

    def save_data(self):
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(self.decisions, f, indent=2, ensure_ascii=False)

    def get_decisions(self) -> List[Dict[str, Any]]:
        return self.decisions

    def add_decision(self, title: str, slug: str, market_price: float, ai_prob: float, rationale: str) -> Dict[str, Any]:
        ev_pct = round((((ai_prob / market_price) - 1.0) * 100), 2)
        b = (1.0 - market_price) / market_price
        q = 1.0 - ai_prob
        kelly = max(0.0, (b * ai_prob - q) / b)
        kelly_stake = round(1000 * kelly * 0.5, 2)
        
        item = {
            "id": f"REC-{len(self.decisions) + 101}",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "title": title,
            "slug": slug or title.lower().replace(" ", "-"),
            "action": "BUY YES" if ev_pct > 0 else "BUY NO / PASS",
            "outcome_choice": "Yes" if ev_pct > 0 else "No",
            "market_price": market_price,
            "ai_assessed_prob": ai_prob,
            "ev_pct": ev_pct,
            "kelly_stake": kelly_stake,
            "status": "PENDING",
            "pnl": 0.0,
            "rationale": rationale
        }
        self.decisions.insert(0, item)
        self.save_data()
        return item

    def get_performance_stats(self) -> Dict[str, Any]:
        finished = [d for d in self.decisions if d.get("status") in ("WON", "LOST")]
        won = [d for d in finished if d.get("status") == "WON"]
        lost = [d for d in finished if d.get("status") == "LOST"]
        
        total_pnl = sum(d.get("pnl", 0.0) for d in finished)
        gross_wins = sum(d.get("pnl", 0.0) for d in won)
        gross_losses = abs(sum(d.get("pnl", 0.0) for d in lost))
        
        win_rate = round((len(won) / len(finished) * 100), 1) if finished else 0.0
        profit_factor = round(gross_wins / gross_losses, 2) if gross_losses > 0 else (999.0 if gross_wins > 0 else 0.0)
        
        return {
            "total_decisions": len(self.decisions),
            "finished_decisions": len(finished),
            "pending_decisions": len(self.decisions) - len(finished),
            "win_count": len(won),
            "loss_count": len(lost),
            "win_rate_pct": win_rate,
            "net_pnl_usd": round(total_pnl, 2),
            "profit_factor": profit_factor,
            "gross_wins_usd": round(gross_wins, 2),
            "gross_losses_usd": round(gross_losses, 2)
        }
