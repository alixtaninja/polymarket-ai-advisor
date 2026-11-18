# Polymarket AI Prediction Advisor & Risk Engine

Hệ thống tích hợp trực tiếp API của Polymarket (Gamma API, CLOB API, Data API v2) kèm bộ lọc rủi ro **5 Quy tắc Cốt lõi**, tính toán **Expected Value (EV)**, chia vốn **Half-Kelly Criterion**, tạo payload ký **EIP-712 Polygon L2**, và Dashboard theo dõi hiệu suất trực quan.

## Cấu trúc dự án

- `client.py`: Async `PolymarketClient` kết nối Gamma, CLOB và Data API v2 (đã xử lý `NO_PROXY` sanitization và CLOB headers).
- `engine.py`: `PredictionEngine` với bộ lọc rủi ro `check_market_risk_policy()`, tính EV, Half-Kelly và EIP-712 order builder.
- `advisor.py`: `AdvisorManager` quản lý sổ cái `decisions.json` và thống kê hiệu suất (`Win Rate`, `Net PnL`, `Profit Factor`).
- `server.py`: FastAPI backend cung cấp REST API, Swagger UI (`/docs`), Market Explorer (`/`) và Advisor Dashboard (`/advisor`).
- `dashboard.html` & `advisor_dashboard.html`: Giao diện Web UI tương tác bằng Tailwind CSS.
- `decisions.json`: Lịch sử đối soát các quyết định từ `REC-101` đến nay.
- `skills/polymarket-advisor/SKILL.md`: Skill đóng gói toàn bộ quy trình vận hành hàng ngày cho AI Agent.
- `GEMINI_GEM_PROMPT.md`: System Prompt copy-paste trực tiếp vào ứng dụng **Gemini (Gemini Gems)**.

## Cài đặt & Chạy Local

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn server:app --host 0.0.0.0 --port 8000
```

Truy cập:
- Advisor Dashboard: `http://localhost:8000/advisor`
- Market Explorer: `http://localhost:8000/`
- API Docs: `http://localhost:8000/docs`

## 5 Quy tắc Quản trị Rủi ro Bắt buộc

1. **Cấm kèo Nội gián / Black Swan** (`REC-102`): Không cược CEO từ chức/sa thải/bê bối cá nhân.
2. **Chỉ đánh Moneyline / Match Winner** (`REC-109`): Cấm cược phương thức thắng (`KO/TKO`, `Distance`, `Round X`, `Handicap`).
3. **Cấm ngưỡng giá Crypto ngắn hạn** (`REC-113`, `REC-114`): Không cược `bitcoin above`, `ethereum above`, `what price will ... hit`.
4. **Kỷ luật EV ≥ +10% & Half-Kelly** (`REC-105`): Giới hạn tối đa `$120–$150/kèo`.
5. **Thanh khoản ≥ `$200,000` & Spread ≤ `$0.03`**: Ưu tiên Sports Moneyline, Tier-1 Esports Moneyline và Macro/Tech thanh khoản cao.
