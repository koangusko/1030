# 活動報名系統需求規格書

> 版本：v1.1（Pro）  
> 日期：2026-10-30  
> 技術：Python FastAPI、PostgreSQL、Jinja2、HTML/CSS

## 0. 版本異動（v1.0 → v1.1 Pro）

| 項目 | v1.0 | v1.1 Pro |
| --- | --- | --- |
| 報名人數 | 只顯示剩餘名額 | 活動列表與報名名單都顯示「目前報名人數」 |
| 重複報名判斷 | 同一 Email | **同名且同電話**；報名表單新增「電話」欄位 |
| 截止報名 | 只依活動的截止時間 | 另可在活動頁按「立即截止報名」，提前結束報名 |
| 新增活動 | 只能用 SQL 匯入 | 新增「新增活動」頁面，可設定名稱、說明、地點、開始／結束時間、截止時間、名額 |

資料庫異動：`participants` 新增 `phone` 欄位，唯一鍵由 `email` 改為 `(name, phone)`。既有資料庫需重建資料表（見第 11 節）。

## 1. 專案目標

建立可供使用者瀏覽活動、填寫姓名、電話及 Email 報名、查看報名結果的簡易活動報名系統；提供新增活動與截止報名功能，以及活動報名名單頁面，供展示與測試。三位組員可依固定資料庫結構、函式介面與路由平行開發。

## 2. 範圍

### 包含
- 活動列表：顯示活動名稱、時間、地點、截止時間、**目前報名人數**、剩餘名額。
- 活動詳情：顯示完整資訊及報名表單。
- 活動報名：以姓名、電話、Email 報名，防止重複報名（同名且同電話）、額滿與逾期報名。
- 報名成功頁：顯示報名結果及活動資訊。
- 報名名單：顯示指定活動的報名者姓名、報名時間與**目前報名人數**（展示用途）。
- 新增活動：填寫活動名稱、說明、地點、開始時間、結束時間、報名截止時間、名額後建立活動。
- 截止報名：活動依截止時間自動停止報名；另可手動「立即截止報名」。
- 測試資料：提供可直接匯入的範例活動。

### 暫不包含
- 使用者登入、權限系統、付款、取消報名、候補名單、Email／簡訊通知、活動編輯與刪除、重新開放報名。
- **注意**：新增活動、截止報名與報名名單目前沒有權限控管，任何人都能操作。正式公開部署前須加上管理者驗證與適當個資保護。

## 3. 技術架構

- 後端：FastAPI（Python）。
- 資料庫：PostgreSQL。
- 前端：Jinja2 伺服器端模板與 HTML/CSS；可少量使用 JavaScript（目前僅用於截止報名的確認視窗）。
- 資料庫連線：由 `db.py` 封裝（沿用課堂範例的 lifespan＋連線池架構），連線資訊從環境變數 `DATABASE_URL` 讀取。
- 時間：資料庫使用 `TIMESTAMPTZ`，顯示時轉換為台灣時間（Asia/Taipei）；新增活動表單輸入的時間視為台灣時間。
- 表單：使用 `application/x-www-form-urlencoded`。

## 4. 資料庫設計

### 4.1 `activities` 活動

| 欄位 | 型別 | 規則 |
| --- | --- | --- |
| `activity_id` | `INTEGER GENERATED ALWAYS AS IDENTITY` | 主鍵 |
| `title` | `VARCHAR(100)` | NOT NULL，不可為空白 |
| `description` | `TEXT` | 可為 NULL |
| `location` | `VARCHAR(200)` | NOT NULL，不可為空白 |
| `start_time` | `TIMESTAMPTZ` | NOT NULL |
| `end_time` | `TIMESTAMPTZ` | NOT NULL，晚於開始時間 |
| `deadline` | `TIMESTAMPTZ` | NOT NULL，不晚於開始時間 |
| `capacity` | `INTEGER` | NOT NULL，大於 0 |
| `created_at` | `TIMESTAMPTZ` | NOT NULL，預設 `CURRENT_TIMESTAMP` |

- 「立即截止報名」不另設欄位，而是把 `deadline` 改為現在時間（若原截止時間更早則不變）。是否截止一律以 `deadline < now()` 判斷。

### 4.2 `participants` 報名者

| 欄位 | 型別 | 規則 |
| --- | --- | --- |
| `participant_id` | `INTEGER GENERATED ALWAYS AS IDENTITY` | 主鍵 |
| `name` | `VARCHAR(100)` | NOT NULL，不可為空白 |
| `phone` | `VARCHAR(20)` | NOT NULL，格式 `^\+?[0-9]{8,15}$` |
| `email` | `VARCHAR(254)` | NOT NULL，小寫且無頭尾空白 |
| `created_at` | `TIMESTAMPTZ` | NOT NULL，預設 `CURRENT_TIMESTAMP` |

- `UNIQUE(name, phone)`：**同名且同電話視為同一報名者**。同名不同電話、或不同名同電話，皆視為不同人。
- 寫入前正規化：
  - 姓名：去除頭尾空白，中間連續空白合併為一個。
  - 電話：移除空白、`-`、括號；`+886` 開頭轉為 `0`（例：`+886 912-345-678` → `0912345678`）。
  - Email：去除頭尾空白並轉小寫。
- 若已有相同姓名與電話的報名者，沿用原記錄，不因再次報名其他活動而覆寫 Email。

### 4.3 `registrations` 報名紀錄

| 欄位 | 型別 | 規則 |
| --- | --- | --- |
| `registration_id` | `INTEGER GENERATED ALWAYS AS IDENTITY` | 主鍵 |
| `activity_id` | `INTEGER` | NOT NULL，外鍵至 `activities` |
| `participant_id` | `INTEGER` | NOT NULL，外鍵至 `participants` |
| `registered_at` | `TIMESTAMPTZ` | NOT NULL，預設 `CURRENT_TIMESTAMP` |

- `UNIQUE(activity_id, participant_id)`：同一人（同名且同電話）不得重複報名同一活動。
- 報名人數 = `COUNT(registrations)`；剩餘名額 = `activities.capacity - 報名人數`，皆不得另存獨立欄位。
- 外鍵預設禁止刪除仍有報名資料的活動或報名者，避免孤兒資料。

## 5. 網頁與路由

| 方法 | 路徑 | 功能 | 模板 |
| --- | --- | --- | --- |
| GET | `/` | 活動列表、報名人數及剩餘名額 | `activities.html` |
| GET | `/activities/new` | 新增活動表單 | `activity_new.html` |
| POST | `/activities` | 接收活動資料並建立活動 | 成功後 303 轉址至活動詳情 |
| GET | `/activities/{activity_id}` | 活動詳情、報名表單、截止報名按鈕 | `activity_detail.html` |
| POST | `/activities/{activity_id}/register` | 接收 `name`、`phone`、`email` 並執行報名 | 成功後 303 轉址 |
| POST | `/activities/{activity_id}/close` | 立即截止報名 | 303 轉址回活動詳情 |
| GET | `/registrations/{registration_id}/success` | 顯示報名成功資訊 | `registration_success.html` |
| GET | `/activities/{activity_id}/registrations` | 顯示活動報名名單及報名人數 | `registrations.html` |

- `/activities/new` 必須宣告在 `/activities/{activity_id}` 之前，否則 `new` 會被當成活動 ID。
- 查無活動或報名紀錄：回傳 HTTP 404。
- 表單資料不合法：HTTP 400，顯示錯誤訊息並保留已填內容，不建立紀錄。
- 重複報名（同名且同電話）：HTTP 409，顯示「您已報名此活動」。
- 活動額滿：HTTP 409，顯示「活動名額已滿」。
- 超過截止時間或已手動截止：HTTP 409，顯示「報名已截止」。
- 報名成功：使用 HTTP 303 導向 `/registrations/{registration_id}/success`，避免重新整理重複送出。
- 已截止的活動不顯示報名表單與「立即截止報名」按鈕；按鈕送出前以確認視窗再次確認。
- **注意**：成功頁網址含報名紀錄 ID，不能視為身分驗證或授權依據；正式部署時應改為受保護頁面或不含個資的成功頁。

## 6. 後端資料存取介面（`db.py`）

```python
get_activities()
get_activity(activity_id)
register_participant(activity_id, name, phone, email)
get_registration(registration_id)
get_activity_registrations(activity_id)
create_activity(title, description, location, start_time, end_time, deadline, capacity)
close_registration(activity_id)
```

約定（皆為 `async` 函式，內部向連線池取得連線）：
- `get_activities()`：回傳活動列表，每場含 `registered`（報名人數）、`remaining`（剩餘名額）、`closed`（是否已截止）。
- `get_activity()`：回傳單一活動，欄位同上；不存在則回傳 `None`。
- `register_participant()`：成功回傳 `registration_id`；失敗時拋出下列例外（皆繼承 `RegistrationError`，帶有 `message` 屬性）：
  - `InvalidInput`：資料不合法
  - `ActivityNotFound`：查無活動
  - `AlreadyRegistered`：重複報名
  - `ActivityFull`：額滿
  - `RegistrationClosed`：已截止
- `get_registration()`：回傳報名紀錄與活動資訊；不存在回傳 `None`。
- `get_activity_registrations()`：回傳該活動報名者姓名及報名時間，依報名時間排序；不含電話與 Email。
- `create_activity()`：接收表單原始字串，驗證後建立活動並回傳 `activity_id`；不合法時拋出 `InvalidInput`。
- `close_registration()`：將截止時間提前至現在；查無活動時拋出 `ActivityNotFound`。

### 6.1 報名交易與並行安全

`register_participant()` 必須在同一個資料庫交易內：
1. 使用 `SELECT ... FOR UPDATE` 鎖定指定活動列，序列化同場活動的報名操作。
2. 確認活動存在、尚未截止。
3. 以正規化後的姓名＋電話檢查是否已報名此活動。
4. 確認尚有名額。
5. 查找既有報名者或新增報名者（以 `UNIQUE(name, phone)` 與 `ON CONFLICT` 安全處理並行建立）。
6. 寫入 `registrations`，由複合 UNIQUE 約束作最終防線。
7. 成功提交交易；任何失敗均回滾，不可留下部分寫入。

`close_registration()` 以 `UPDATE` 修改活動列，會與報名交易的列鎖互相排隊，不會出現截止後仍寫入報名的情況。

所有活動報名寫入必須走相同交易規則；不得在鎖外先計算名額再直接新增。

## 7. 輸入驗證

### 報名
- 姓名：正規化後不得為空，長度不超過 100 字元。
- 電話：正規化後須符合 `^\+?[0-9]{8,15}$`。
- Email：去除頭尾空白、轉小寫、檢查格式與長度（最多 254 字元）。
- 截止時間判定：以伺服器／資料庫時間為準，不信任瀏覽器時間。

### 新增活動
- 活動名稱：必填，最多 100 字元；地點：必填，最多 200 字元；說明：選填。
- 開始、結束、截止時間：必填，格式為 `datetime-local`（如 `2026-12-20T13:00`），視為台灣時間。
- 結束時間須晚於開始時間；截止時間不可晚於開始時間。
- 名額：1 到 100000 的整數。

### 共通
- 活動 ID：正整數且必須存在。
- 輸出資料透過 Jinja2 自動跳脫，避免 HTML 注入；資料庫查詢一律參數化。

## 8. 專案目錄

```text
project/
├── main.py                  # 入口：建立 app、掛路由與靜態檔
├── db.py                    # 連線池與資料存取函式
├── schema.sql
├── seed.sql
├── requirements.txt
├── .env.example
├── .gitignore
├── routes/
│   └── activities.py        # 所有頁面路由
├── templates/
│   ├── base.html
│   ├── _macros.html
│   ├── activities.html
│   ├── activity_new.html
│   ├── activity_detail.html
│   ├── registration_success.html
│   └── registrations.html
└── static/
    └── style.css
```

## 9. 三人分工與交付

| 角色 | 工作 | 交付項目 |
| --- | --- | --- |
| 資料庫組員 | 設計資料表、測試資料、資料存取及交易安全 | `schema.sql`、`seed.sql`、`db.py` |
| UI 組員 | 製作 Jinja2 頁面、表單、錯誤與狀態呈現 | `templates/*.html`、`static/style.css` |
| 後端組員 | 建立 FastAPI、路由、模板整合、套件與執行入口 | `main.py`、`routes/activities.py`、`requirements.txt`、`.env.example` |

共用約定：資料表、欄位、路由、表單欄位與 `db.py` 函式名稱不得自行修改；如需變更，三人先同步規格再實作。

## 10. 驗收標準

- [ ] `schema.sql` 可在全新 PostgreSQL 資料庫成功建表。
- [ ] `seed.sql` 可建立至少 3 場測試活動（可報名、額滿、已截止）。
- [ ] 首頁能正確顯示活動、目前報名人數與剩餘名額。
- [ ] 可透過「新增活動」頁面建立活動，並能設定名稱、地點、開始／結束時間、截止時間與名額。
- [ ] 新增活動時，結束早於開始、截止晚於開始、名額不合法等情況會顯示錯誤且不建立活動。
- [ ] 活動詳情頁可提交姓名、電話與 Email。
- [ ] 成功報名後產生一筆報名紀錄並導向成功頁。
- [ ] 同名且同電話不能重複報名同一活動（電話寫法不同，如 `0912-345-678` 與 `0912345678`，仍視為同一人），但能報名其他活動。
- [ ] 同名不同電話、不同名同電話皆可報名。
- [ ] 額滿與截止活動不可報名。
- [ ] 按下「立即截止報名」後，該活動立即無法報名，頁面顯示已截止。
- [ ] 無效姓名／電話／Email 不會寫入資料庫。
- [ ] 多人同時搶最後一個名額，不會超收。
- [ ] 報名名單顯示姓名、報名時間與目前報名人數，不顯示電話與 Email。
- [ ] 查無資源時正確回傳 404。
- [ ] `.env` 與資料庫密碼不進入 Git；`.env.example` 不含真實密碼。

## 11. 執行設定

`.env.example`：

```dotenv
DATABASE_URL="host=localhost port=5432 dbname=event_platform user=postgres password='replace_with_your_password'"
```

也可使用 URL 格式：`postgresql://username:password@localhost:5432/event_platform`。

`requirements.txt` 包含 FastAPI、Uvicorn、Jinja2、python-multipart、psycopg（含連線池）與 python-dotenv。

啟動：

```bash
fastapi dev main.py
```

既有資料庫升級到 v1.1：`participants` 結構有變更，需重建資料表（會清除既有報名資料）：

```sql
DROP TABLE registrations, participants, activities;
-- 再依序執行 schema.sql、seed.sql
```

## 12. 後續版本

可逐步加入管理員登入與權限、活動編輯與刪除、重新開放報名、取消報名、候補、Email／簡訊驗證與通知、資料匯出、操作日誌及正式部署安全措施。
