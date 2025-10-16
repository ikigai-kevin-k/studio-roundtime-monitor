# Studio Round Time Monitor

一個獨立的時間監控模組，用於統計 SDP 遊戲系統中各個組件的時間間隔，包括 TableAPI 調用時間、Roulette 設備運行時間和 Sicbo 設備運行時間。

## 功能特點

- **非侵入式監控**: 通過事件發布/訂閱系統收集時間數據，不干擾主遊戲邏輯
- **多遊戲支持**: 支持 Roulette (Speed/VIP) 和 Sicbo 遊戲的時間監控
- **全面覆蓋**: 監控 TableAPI 調用、設備狀態變化和 MQTT 消息時間
- **數據持久化**: 支持 JSON、CSV 和數據庫存儲
- **實時分析**: 提供時間間隔統計和異常檢測

## 監控指標

### TableAPI 時間間隔
- `start-to-betStop`: 開始下注到停止下注的時間
- `betStop-to-deal`: 停止下注到發牌的時間  
- `deal-to-finish`: 發牌到結束的時間
- `finish-to-start`: 結束到下一輪開始的時間

### Roulette 設備時間間隔
- `*X;2-to-*X;3`: 球發射到球落下的時間
- `*X;3-to-*X;4`: 球落下到檢測的時間
- `*X;4-to-*X;5`: 檢測到結果公布的時間
- `*X;5-to-*X;2`: 結果公布到下一輪開始的時間

### Sicbo 設備時間間隔

#### Shaker 設備
- `shakerStop-to-shakerShake`: 搖骰器停止到開始搖骰的時間
- `shakerShake-to-shakerStop`: 搖骰到搖骰器停止的時間

#### IDP 設備  
- `sendDetect-to-receiveResult`: 發送檢測命令到接收結果的時間
- `receiveResult-to-sendDetect`: 接收結果到下次發送檢測的時間

## 安裝

```bash
cd studio-roundtime-monitor
pip install -r requirements.txt
```

## 使用方法

### 1. 作為獨立服務運行

```bash
python -m studio_roundtime_monitor.main --config config/monitor_config.yaml
```

### 2. 集成到現有遊戲模組

```python
from studio_roundtime_monitor import TimeMonitor

# 初始化監控器
monitor = TimeMonitor(config)

# 在主遊戲模組中發布事件
monitor.publish_event('tableapi_start', {'table': 'PRD', 'round_id': '123'})
monitor.publish_event('tableapi_betstop', {'table': 'PRD', 'round_id': '123'})
```

## 配置

監控器支持通過 YAML 配置文件進行配置：

```yaml
# config/monitor_config.yaml
monitor:
  enabled: true
  game_types: ['roulette', 'sicbo']
  
storage:
  type: 'json'  # json, csv, database
  path: './data/time_intervals.json'
  
events:
  tableapi:
    enabled: true
    topics: ['tableapi_start', 'tableapi_betstop', 'tableapi_deal', 'tableapi_finish']
  roulette:
    enabled: true
    topics: ['roulette_x2', 'roulette_x3', 'roulette_x4', 'roulette_x5']
  sicbo:
    enabled: true
    topics: ['sicbo_shaker_start', 'sicbo_shaker_stop', 'sicbo_idp_send', 'sicbo_idp_receive']
```

## 輸出格式

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

## 架構設計

```
studio-roundtime-monitor/
├── studio_roundtime_monitor/
│   ├── __init__.py
│   ├── core/
│   │   ├── event_system.py      # 事件發布/訂閱系統
│   │   ├── time_monitor.py      # 主監控器類
│   │   └── interval_calculator.py # 時間間隔計算器
│   ├── monitors/
│   │   ├── tableapi_monitor.py  # TableAPI 監控器
│   │   ├── roulette_monitor.py  # Roulette 設備監控器
│   │   └── sicbo_monitor.py     # Sicbo 設備監控器
│   ├── storage/
│   │   ├── json_storage.py      # JSON 存儲
│   │   ├── csv_storage.py       # CSV 存儲
│   │   └── database_storage.py  # 數據庫存儲
│   └── utils/
│       ├── config.py            # 配置管理
│       └── logger.py            # 日誌管理
├── config/
│   └── monitor_config.yaml      # 配置文件
├── examples/
│   ├── roulette_integration.py  # Roulette 整合示例
│   └── sicbo_integration.py     # Sicbo 整合示例
└── tests/
    ├── test_monitors.py
    └── test_storage.py
```

## 整合指南

### 在 main_speed.py 中整合

```python
# 在文件開頭導入
from studio_roundtime_monitor import TimeMonitor

# 在 main() 函數中初始化
monitor = TimeMonitor(config)

# 在關鍵時間點發布事件
monitor.publish_event('tableapi_start', {
    'table': table['name'], 
    'round_id': round_id
})
```

### 在 main_sicbo.py 中整合

```python
# 在 SDPGame 類中初始化監控器
self.time_monitor = TimeMonitor(config)

# 在關鍵操作後發布事件
await self.time_monitor.publish_event('sicbo_shaker_start', {
    'round_id': round_id
})
```

## 開發狀態

- [x] 架構設計
- [x] 事件系統
- [ ] TableAPI 監控器
- [ ] Roulette 監控器  
- [ ] Sicbo 監控器
- [ ] 數據存儲
- [ ] 整合指南
