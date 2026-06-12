# fadacai-mcp-servers

兩個輕量、自寫的 [MCP](https://modelcontextprotocol.io) server，供投資研究使用。可獨立運行，也是 [fadacai-portfolio](https://github.com/PatrickSUDO/fadacai-portfolio) 框架的數據來源之一。另含一個第三方 server 的**薄整合**（fmp，僅安裝設定，非自有原始碼）。

| Server | 功能 | 需要 API key？ | 資料來源 | 性質 |
|--------|------|:--------------:|----------|------|
| **`technical`** | 技術指標：RSI、MACD、布林通道、ATR、動量分數、支撐/壓力、52 週區間、板塊輪動 | ❌ | yfinance（免費爬蟲） | 自寫 |
| **`eodhd`** | 新聞情緒分析：個股 AI 情緒分數（-1 → +1）、每日情緒軌跡 | ✅ `EODHD_API_TOKEN` | [EODHD API](https://eodhd.com) | 自寫 |
| **`fmp`** | 行情/基本面/peers/市場異動等（HTTP transport，:8081） | ✅ `FMP_ACCESS_TOKEN` | [FMP API](https://financialmodelingprep.com) | **第三方薄整合** → [`fmp/README.md`](fmp/README.md) |

`technical` / `eodhd` 為 stdio transport、基於 `FastMCP`、自寫且**不含任何金鑰**。`fmp` 是第三方 [imbenrabi/Financial-Modeling-Prep-MCP-Server](https://github.com/imbenrabi/Financial-Modeling-Prep-MCP-Server) 的本機安裝設定——此 repo **不 vendor 其原始碼**，僅存 README + `.env.example` + sanitized launchd 範本，詳見 [`fmp/`](fmp/)。

---

## 前置需求

- Python **3.12+**
- [uv](https://github.com/astral-sh/uv)（建議；也可用 pip + venv）

## 安裝與啟動

### technical（免 key）

```bash
cd technical
uv sync            # 安裝依賴（mcp, pandas-ta, yfinance, numpy）
uv run server.py   # 啟動 stdio MCP server
```

### eodhd（需 EODHD token）

```bash
cd eodhd
uv sync                       # 安裝依賴（mcp, requests）
cp .env.example .env          # 填入你的 EODHD_API_TOKEN
export EODHD_API_TOKEN=xxxx   # 或由 MCP host 注入環境變數
uv run server.py
```

> EODHD token 申請：<https://eodhd.com>（有免費額度）。ticker 需用 EODHD 格式，加交易所後綴，例 `AAPL.US`、`TSLA.US`、`TSM.US`。

## 在 Claude Code 註冊

用 `claude mcp add`（stdio）指向各自的 `server.py`：

```bash
# technical
claude mcp add technical -- uv --directory /abs/path/to/mcp-servers/technical run server.py

# eodhd（透過 --env 注入 token，勿把 token 寫進任何 commit 的檔案）
claude mcp add eodhd --env EODHD_API_TOKEN=xxxx -- uv --directory /abs/path/to/mcp-servers/eodhd run server.py
```

或在專案 `.mcp.json` 等價設定 `command` / `args` / `env`。

## 工具一覽

**technical**
- `get_technical_indicators(ticker, period="6mo")` — 單檔完整技術分析（RSI / MACD / BB / ATR / MA / 動量 / 趨勢）
- `get_support_resistance(ticker, period)` — 支撐壓力、樞紐點、52 週區間
- `get_batch_indicators(tickers, period)` — 多檔精簡技術摘要
- `get_sector_rotation(...)` — 板塊輪動：相對 SPY 超額報酬、RS 動量、leading/improving/weakening/lagging 分類

**eodhd**
- `get_news_sentiment(ticker, days=7, limit=10)` — 近期新聞 + AI 情緒分數（polarity/pos/neg/neu）
- `get_sentiment_trend(ticker, days=30)` — 每日情緒軌跡（-1 → +1）+ 趨勢分類

## 安全

- 原始碼不含任何金鑰；`eodhd` 一律從 `EODHD_API_TOKEN` 環境變數讀取（見 `eodhd/eodhd_client.py`）。
- `.env`、`.venv/`、`uv.lock`、`__pycache__/` 已於 `.gitignore` 排除。
- 請勿把真實 token commit 進此 repo 或任何下游 fork。

## 授權

[MIT License](LICENSE)。本工具僅供研究參考，所提供之數據不構成投資建議。
