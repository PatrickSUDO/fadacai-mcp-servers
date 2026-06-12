# fmp-mcp — Financial Modeling Prep MCP（第三方，薄整合）

⚠️ **這不是自有程式碼。** FMP 行情/基本面工具由第三方開源專案提供：
**[imbenrabi/Financial-Modeling-Prep-MCP-Server](https://github.com/imbenrabi/Financial-Modeling-Prep-MCP-Server)**
（亦發佈於 npm：`financial-modeling-prep-mcp-server`）。

本目錄**只存「如何在本機跑起來」的設定**，不 vendor 上游原始碼 —— 這樣可隨時 `git pull` 上游更新、不複製其 ~139M 依賴。eodhd / technical 是自有程式碼故含原始碼；fmp 是外部相依，故只留 pointer + 設定。

---

## 架構定位

- 以 **HTTP transport** 跑在 `localhost:8081`，由 launchd 常駐（`KeepAlive`）。
- portfolio 的 `.mcp.json` 以 `{"type": "http", "url": "http://localhost:8081/mcp"}` 連它（非 stdio，故 portfolio 不需知道安裝路徑）。
- API 金鑰 `FMP_ACCESS_TOKEN` 由 launchd plist 的 `EnvironmentVariables` 注入，**不在任何 repo 內**。
- 免費 tier 限制：多數 ratios / price-target 端點回 402，已知並略過（見 portfolio CLAUDE.md「Research Boundaries」）。

---

## 新機器安裝（重現步驟）

```bash
# 1. 取得上游（位置自訂；本機慣例放這）
git clone https://github.com/imbenrabi/Financial-Modeling-Prep-MCP-Server.git \
  ~/laptop/mcp-servers/fmp-mcp
cd ~/laptop/mcp-servers/fmp-mcp
npm install && npm run build      # 產出 dist/index.js

# 2. 取得 FMP API token → https://site.financialmodelingprep.com/developer/docs
cp <this-repo>/fmp/.env.example .env   # 填入 FMP_ACCESS_TOKEN（或直接寫進 plist）

# 3. 安裝常駐服務（先把範本的 __PLACEHOLDER__ 換成實際值）
cp <this-repo>/fmp/com.fadacai.fmp-mcp.plist ~/Library/LaunchAgents/
#   編輯：__FMP_ACCESS_TOKEN__ → 你的 token；YOUR_USERNAME / 路徑 → 實際值
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.fadacai.fmp-mcp.plist

# 4. 驗證
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8081/mcp   # 400 = 服務已起（裸 GET 正常回 400）
```

## 常用維運

```bash
# 重啟（更新 dist 或改 token 後）
launchctl kickstart -k gui/$(id -u)/com.fadacai.fmp-mcp

# 看 log
tail -f ~/laptop/mcp-servers/fmp-mcp/fmp-mcp.err

# 更新上游
cd ~/laptop/mcp-servers/fmp-mcp && git pull && npm install && npm run build && \
  launchctl kickstart -k gui/$(id -u)/com.fadacai.fmp-mcp
```

## 安全

- `FMP_ACCESS_TOKEN` 只在本機 plist（`~/Library/LaunchAgents/`，不在 repo）與本機 `.env`（gitignored）。
- 此目錄 commit 的 plist 是 **sanitized 範本**（token = `__FMP_ACCESS_TOKEN__`），切勿把真實 token 寫回再 commit。
- 上游 License 屬其作者，使用請遵其授權；本目錄僅為個人安裝設定。
