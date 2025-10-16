# Studio Round Time Monitor - 項目總結

## 項目概述

`studio-roundtime-monitor` 是一個獨立的時間監控模組，專門為 SDP 遊戲系統設計，用於統計和分析各種遊戲組件的時間間隔，包括 TableAPI 調用時間、Roulette 設備運行時間和 Sicbo 設備運行時間。

## 核心特性

### 🎯 非侵入式監控
- 通過事件發布/訂閱系統收集時間數據
- 不直接存取 serial port，避免干擾 `main_vip.py` 和 `main_speed.py`
- 不直接發送 MQTT 命令，避免干擾 `main_sicbo.py` 的 IDP 檢測
- 完全解耦的架構設計

### 📊 全面覆蓋
- **TableAPI 監控**: start-to-betStop, betStop-to-deal, deal-to-finish, finish-to-start
- **Roulette 設備監控**: *X;2-to-*X;3, *X;3-to-*X;4, *X;4-to-*X;5, *X;5-to-*X;2
- **Sicbo 設備監控**: shaker 和 IDP 的各種時間間隔

### 🚀 高性能設計
- 異步事件處理，不阻塞主遊戲流程
- 可配置的處理間隔和歷史數據限制
- 後台數據處理和存儲

### 💾 靈活的數據存儲
- JSON 格式存儲
- CSV 格式存儲
- 數據庫存儲 (SQLite, PostgreSQL, MySQL)
- 支持數據導出和清理

## 架構設計

### 核心組件

```
studio-roundtime-monitor/
├── core/                    # 核心組件
│   ├── event_system.py     # 事件發布/訂閱系統
│   ├── time_monitor.py     # 主監控器
│   └── interval_calculator.py # 時間間隔計算器
├── monitors/               # 專用監控器
│   ├── tableapi_monitor.py # TableAPI 監控器
│   ├── roulette_monitor.py # Roulette 設備監控器
│   └── sicbo_monitor.py    # Sicbo 設備監控器
├── storage/               # 數據存儲
│   ├── json_storage.py    # JSON 存儲
│   ├── csv_storage.py     # CSV 存儲
│   └── database_storage.py # 數據庫存儲
├── utils/                 # 工具模組
│   ├── config.py          # 配置管理
│   └── logger.py          # 日誌管理
└── examples/              # 整合示例
    ├── roulette_integration.py
    └── sicbo_integration.py
```

### 事件系統

採用發布/訂閱模式，支持：
- 同步和異步事件處理
- 多訂閱者支持
- 事件類型枚舉
- 結構化事件數據

### 監控流程

1. **事件發布**: 遊戲模組發布時間事件
2. **事件處理**: 監控器接收並處理事件
3. **間隔計算**: 計算時間間隔和統計數據
4. **數據存儲**: 將數據保存到配置的存儲系統
5. **異常檢測**: 檢測異常時間間隔

## 監控指標

### TableAPI 時間間隔
| 間隔類型 | 描述 | 預期範圍 |
|---------|------|----------|
| start-to-betStop | 開始下注到停止下注 | 5-20 秒 |
| betStop-to-deal | 停止下注到發牌 | 1-5 秒 |
| deal-to-finish | 發牌到結束 | 1-3 秒 |
| finish-to-start | 結束到下一輪開始 | 2-5 秒 |

### Roulette 設備時間間隔
| 間隔類型 | 描述 | 預期範圍 |
|---------|------|----------|
| *X;2-to-*X;3 | 球發射到球落下 | 5-15 秒 |
| *X;3-to-*X;4 | 球落下到檢測 | 0.5-2 秒 |
| *X;4-to-*X;5 | 檢測到結果公布 | 1-3 秒 |
| *X;5-to-*X;2 | 結果公布到下一輪開始 | 2-5 秒 |

### Sicbo 設備時間間隔
| 設備 | 間隔類型 | 描述 | 預期範圍 |
|------|---------|------|----------|
| Shaker | shakerStop-to-shakerShake | 搖骰器停止到開始搖骰 | 1-3 秒 |
| Shaker | shakerShake-to-shakerStop | 搖骰到搖骰器停止 | 8-12 秒 |
| IDP | sendDetect-to-receiveResult | 發送檢測到接收結果 | 0.5-3 秒 |
| IDP | receiveResult-to-sendDetect | 接收結果到下次發送檢測 | 1-5 秒 |

## 整合方式

### 1. Roulette 遊戲整合

```python
# 導入整合模組
from studio_roundtime_monitor.examples.roulette_integration import RouletteTimeMonitorIntegration

# 初始化監控器
time_monitor = RouletteTimeMonitorIntegration()
await time_monitor.initialize()

# 在關鍵時間點記錄事件
time_monitor.record_tableapi_start(table, round_id)
time_monitor.record_roulette_x2(table, round_id, warning_flag)
```

### 2. Sicbo 遊戲整合

```python
# 導入整合模組
from studio_roundtime_monitor.examples.sicbo_integration import SicboTimeMonitorIntegration

# 在 SDPGame 類中初始化
self.time_monitor = SicboTimeMonitorIntegration()
await self.time_monitor.initialize()

# 記錄設備事件
self.time_monitor.record_shaker_start("SBO-001", round_id)
self.time_monitor.record_idp_send("SBO-001", round_id)
```

## 配置管理

### 基本配置

```yaml
# Monitor settings
monitor:
  enabled: true
  tableapi_enabled: true
  roulette_enabled: true
  sicbo_enabled: true

# Storage configuration
storage:
  type: "json"  # json, csv, database
  path: "./data/time_intervals.json"

# Processing configuration
processing:
  interval: 5.0  # Processing interval in seconds
  max_history: 1000  # Maximum intervals in memory
```

### 數據庫配置

```yaml
storage:
  type: "database"
  database_url: "sqlite:///data/monitor.db"
  # database_url: "postgresql://user:pass@localhost/monitor"
  # database_url: "mysql://user:pass@localhost/monitor"
```

## 運行方式

### 獨立服務模式

```bash
# 啟動監控服務
python -m studio_roundtime_monitor.main --config config/monitor_config.yaml

# 查看狀態
python -m studio_roundtime_monitor.main --status

# 創建默認配置
python -m studio_roundtime_monitor.main --create-config
```

### 整合模式

監控系統會自動與整合的遊戲模組一起運行，無需額外啟動。

## 數據輸出

### JSON 格式

```json
{
  "timestamp": "2024-01-15T10:30:45.123456",
  "game_type": "roulette",
  "table": "PRD", 
  "round_id": "12345",
  "intervals": {
    "start-to-betstop": 15.2,
    "betstop-to-deal": 3.1,
    "deal-to-finish": 1.8,
    "finish-to-start": 2.5
  }
}
```

### CSV 格式

```csv
timestamp,game_type,table,round_id,interval_type,duration
2024-01-15T10:30:45.123456,roulette,PRD,12345,start-to-betstop,15.2
2024-01-15T10:31:00.223456,roulette,PRD,12345,betstop-to-deal,3.1
```

## 性能優化

### 內存管理
- 可配置的歷史數據限制
- 自動清理舊數據
- 批量數據處理

### 異步處理
- 非阻塞事件發布
- 後台數據處理
- 並發事件處理

### 存儲優化
- 批量寫入操作
- 壓縮數據格式
- 可配置的清理策略

## 異常檢測

### 統計異常檢測
- 基於標準偏差的異常檢測
- 可配置的閾值
- 實時異常報告

### 性能監控
- 監控系統本身的性能
- 事件處理延遲統計
- 內存使用監控

## 測試覆蓋

### 單元測試
- 監控器功能測試
- 事件系統測試
- 間隔計算器測試
- 存儲系統測試

### 整合測試
- 完整遊戲流程測試
- 性能測試
- 異常處理測試

## 部署建議

### 開發環境
```bash
# 安裝依賴
pip install -r requirements.txt

# 運行測試
pytest tests/

# 啟動開發服務
python -m studio_roundtime_monitor.main --config config/monitor_config.yaml
```

### 生產環境
```bash
# 使用數據庫存儲
# 配置日誌輪轉
# 設置監控和告警
# 定期數據清理
```

## 未來擴展

### 功能擴展
- 更多遊戲類型支持
- 實時儀表板
- 告警系統
- 數據分析工具

### 性能擴展
- 分散式監控
- 數據流處理
- 機器學習異常檢測
- 雲端存儲支持

## 總結

`studio-roundtime-monitor` 成功實現了：

✅ **非侵入式監控**: 不干擾現有遊戲邏輯  
✅ **全面覆蓋**: 監控所有關鍵時間間隔  
✅ **高性能**: 異步處理，不影響遊戲性能  
✅ **靈活存儲**: 支持多種存儲格式  
✅ **易於整合**: 提供完整的整合指南和示例  
✅ **可擴展性**: 模組化設計，易於擴展  

這個模組為 SDP 遊戲系統提供了強大的時間監控能力，幫助開發團隊分析和優化遊戲性能，同時保持系統的穩定性和可靠性。
