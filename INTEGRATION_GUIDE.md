# Studio Round Time Monitor - 整合指南

本指南說明如何將 `studio-roundtime-monitor` 整合到現有的遊戲模組中，以收集各種時間間隔數據。

## 概述

`studio-roundtime-monitor` 是一個獨立的時間監控模組，通過事件發布/訂閱系統收集時間數據，不會干擾主遊戲邏輯的運行。

## 整合原則

### 非侵入式設計
- 監控模組不直接存取 serial port，避免干擾 `main_vip.py` 和 `main_speed.py` 的執行
- 監控模組不直接發送 MQTT 命令，避免干擾 `main_sicbo.py` 的 IDP 檢測
- 通過事件發布系統進行通信，保持模組間的解耦

### 性能考量
- 事件發布是異步的，不會阻塞主遊戲流程
- 數據處理在後台進行，不影響遊戲性能
- 可配置的處理間隔和歷史數據限制

## 整合步驟

### 1. 安裝依賴

```bash
cd studio-roundtime-monitor
pip install -r requirements.txt
```

### 2. 配置監控系統

創建配置文件 `config/monitor_config.yaml`：

```yaml
# Monitor settings
monitor:
  enabled: true
  tableapi_enabled: true
  roulette_enabled: true
  sicbo_enabled: true

# Storage configuration
storage:
  type: "json"  # Options: json, csv, database
  path: "./data/time_intervals.json"

# Processing configuration
processing:
  interval: 5.0  # Processing interval in seconds
  max_history: 1000  # Maximum number of intervals to keep in memory
```

### 3. 整合到 Roulette 遊戲 (main_speed.py / main_vip.py)

#### 3.1 導入監控模組

```python
# 在文件開頭添加
from studio_roundtime_monitor.examples.roulette_integration import RouletteTimeMonitorIntegration
```

#### 3.2 初始化監控器

```python
# 在 main() 函數中初始化
async def main():
    # 初始化時間監控
    time_monitor = RouletteTimeMonitorIntegration()
    await time_monitor.initialize()
    
    try:
        # 現有的遊戲邏輯...
        pass
    finally:
        await time_monitor.cleanup()
```

#### 3.3 在關鍵時間點記錄事件

**TableAPI 事件記錄：**

```python
# 在 execute_start_post 函數中，成功調用 start_post 後
def execute_start_post(table, token):
    # ... 現有邏輯 ...
    if round_id != -1:
        # 記錄 TableAPI start 事件
        time_monitor.record_tableapi_start(table["name"], round_id)
        # ... 現有邏輯 ...

# 在 execute_deal_post 函數中，成功調用 deal_post 後
def execute_deal_post(table, token, win_num):
    # ... 現有邏輯 ...
    # 記錄 TableAPI deal 事件
    time_monitor.record_tableapi_deal(table["name"], table["round_id"], win_num)
    # ... 現有邏輯 ...

# 在 execute_finish_post 函數中，成功調用 finish_post 後
def execute_finish_post(table, token):
    # ... 現有邏輯 ...
    # 記錄 TableAPI finish 事件
    time_monitor.record_tableapi_finish(table["name"], table["round_id"])
    # ... 現有邏輯 ...

# 在 bet stop countdown 中
def _bet_stop_countdown(table, round_id, bet_period, token, ...):
    # ... 現有邏輯 ...
    result = betStop_round_for_table(table, token)
    if result[1]:
        # 記錄 TableAPI betstop 事件
        time_monitor.record_tableapi_betstop(table["name"], round_id)
    # ... 現有邏輯 ...
```

**Roulette 設備事件記錄：**

```python
# 在 read_from_serial 函數中
def read_from_serial():
    # ... 現有邏輯 ...
    
    # 處理 *X;2 消息
    if "*X;2" in data:
        # ... 現有邏輯 ...
        # 解析 warning_flag
        parts = data.split(";")
        warning_flag = parts[4] if len(parts) >= 5 else "0"
        
        # 記錄 *X;2 事件
        time_monitor.record_roulette_x2(table["name"], round_id, warning_flag)
    
    # 處理 *X;3 消息
    elif "*X;3" in data and not isLaunch:
        # ... 現有邏輯 ...
        # 記錄 *X;3 事件
        time_monitor.record_roulette_x3(table["name"], round_id)
    
    # 處理 *X;5 消息
    elif "*X;5" in data and not deal_post_sent:
        # ... 現有邏輯 ...
        # 記錄 *X;5 事件
        time_monitor.record_roulette_x5(table["name"], round_id, win_num)
```

### 4. 整合到 Sicbo 遊戲 (main_sicbo.py)

#### 4.1 導入監控模組

```python
# 在文件開頭添加
from studio_roundtime_monitor.examples.sicbo_integration import SicboTimeMonitorIntegration
```

#### 4.2 在 SDPGame 類中初始化

```python
class SDPGame:
    def __init__(self, config: GameConfig):
        # ... 現有邏輯 ...
        
        # 初始化時間監控
        self.time_monitor = SicboTimeMonitorIntegration()
    
    async def initialize(self):
        # ... 現有邏輯 ...
        
        # 初始化時間監控
        await self.time_monitor.initialize()
    
    async def cleanup(self):
        # ... 現有邏輯 ...
        
        # 清理時間監控
        if hasattr(self, 'time_monitor'):
            await self.time_monitor.cleanup()
```

#### 4.3 在關鍵時間點記錄事件

**TableAPI 事件記錄：**

```python
async def run_sicbo_game(self):
    # ... 現有邏輯 ...
    
    # 在 start_post 成功後
    for table, round_id, bet_period in round_ids:
        self.time_monitor.record_tableapi_start(table["name"], round_id)
    
    # 在 deal_post 成功後
    for table, round_id, _ in round_ids:
        self.time_monitor.record_tableapi_deal(table["name"], round_id, dice_result)
    
    # 在 finish_post 成功後
    for table, round_id, _ in round_ids:
        self.time_monitor.record_tableapi_finish(table["name"], round_id)
```

**Sicbo 設備事件記錄：**

```python
async def run_sicbo_game(self):
    # ... 現有邏輯 ...
    
    # 在 shake 命令發送後
    await self.shaker_controller.shake(first_round_id)
    self.time_monitor.record_shaker_start("SBO-001", first_round_id)
    
    # 在 shaker 達到 S0 狀態後
    s0_reached = await self.shaker_controller.wait_for_s0_state()
    if s0_reached:
        self.time_monitor.record_shaker_s0("SBO-001", first_round_id)
    
    # 在 IDP detect 命令發送後
    success, dice_result = await self.idp_controller.detect(first_round_id)
    self.time_monitor.record_idp_send("SBO-001", first_round_id)
    
    # 在 IDP 接收到結果後
    if is_valid_result:
        self.time_monitor.record_idp_receive("SBO-001", first_round_id, dice_result)
```

**Bet Stop 事件記錄：**

```python
async def _bet_stop_countdown(self, table, round_id, bet_period):
    # ... 現有邏輯 ...
    
    result = await betStop_round_for_table(table, self.token)
    if result[1]:
        # 記錄 bet stop 事件
        self.time_monitor.record_tableapi_betstop(table["name"], round_id)
    
    # ... 現有邏輯 ...
```

## 監控的指標

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

## 數據存儲

監控數據會根據配置保存到：

- **JSON 格式**: `./data/time_intervals.json`
- **CSV 格式**: `./data/time_intervals.csv`
- **數據庫**: 支持 SQLite、PostgreSQL、MySQL

## 運行監控系統

### 作為獨立服務運行

```bash
# 啟動監控服務
python -m studio_roundtime_monitor.main --config config/monitor_config.yaml

# 查看狀態
python -m studio_roundtime_monitor.main --status

# 創建默認配置
python -m studio_roundtime_monitor.main --create-config
```

### 與遊戲模組一起運行

監控系統會自動與整合的遊戲模組一起運行，無需額外啟動。

## 故障排除

### 常見問題

1. **監控器初始化失敗**
   - 檢查配置文件是否存在和格式正確
   - 確保所有依賴已安裝

2. **事件記錄失敗**
   - 檢查監控器是否已初始化
   - 確保事件發布不會阻塞主流程

3. **數據未保存**
   - 檢查存儲路徑是否可寫
   - 查看日誌文件了解錯誤信息

### 日誌查看

```bash
# 查看監控日誌
tail -f logs/roundtime_monitor.json.log

# 查看應用程序日誌
tail -f logs/roundtime_monitor_console.log
```

## 性能監控

監控系統本身也會記錄性能指標：

- 事件處理延遲
- 數據存儲性能
- 內存使用情況
- 異常檢測統計

## 擴展功能

### 自定義事件類型

可以通過繼承 `EventType` 枚舉來添加自定義事件類型：

```python
from studio_roundtime_monitor.core.event_system import EventType

class CustomEventType(EventType):
    CUSTOM_EVENT = "custom_event"
```

### 自定義存儲後端

可以通過實現存儲接口來添加自定義存儲後端：

```python
from studio_roundtime_monitor.storage.base_storage import BaseStorage

class CustomStorage(BaseStorage):
    async def save_intervals(self, intervals):
        # 自定義存儲邏輯
        pass
```

## 總結

通過遵循本指南，您可以成功將 `studio-roundtime-monitor` 整合到現有的遊戲模組中，實現全面的時間監控功能，同時保持系統的穩定性和性能。
