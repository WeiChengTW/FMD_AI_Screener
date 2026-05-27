# 運用 AI 技術判別精細動作之早期遲緩篩檢系統

**系統全名：** AI-based Early Screening System for Fine Motor Developmental Delay Identification  
**系統代號：** FMD_AI_Screener  
**團隊成員：** 洪偉城、林政維、呂昊宸、林宛瑩  
**指導教授：** 趙一平教授  
**文件版本：** v1.0（2026-05-27）

---

## 系統簡介

本系統針對偏鄉地區兒童精細動作發展遲緩篩檢資源不足的問題，設計一套可攜式、遊戲化的評量工具。以 PDMS-2（皮巴迪動作發展量表第二版）為評分基準，整合 YOLO 物件偵測、SAM 影像分割、TensorFlow 分類與 RAG 智慧建議等 AI 技術，讓衛生所人員無需職能治療師在場即可完成篩檢，並自動生成個人化居家練習建議。

**系統架構：** 三層式架構（施測端 PC / Mac Mini 分析伺服器 / MySQL 資料庫），透過 Tailscale VPN 安全通訊。

**評測任務：** 17 個 PDMS-2 子關卡，涵蓋積木建構（Ch1）、圖形描繪（Ch2）、剪紙（Ch3）、折紙（Ch4）、儀器量測（Ch5）。

---

## 硬體組成

| 設備 | 規格 | 用途 |
|------|------|------|
| 施測端 PC | Intel i5+，8GB RAM，Windows 11 | 前端 Web 介面 + 施測端 Flask |
| PW313D 攝影機 | 雙鏡頭（俯視 + 側視），1080P USB | 拍攝兒童動作影像 |
| 14 吋觸控螢幕 | IPS，1920×1080 | 兒童遊戲化操作介面 |
| Mac Mini M2 Pro | 16GB RAM，512GB SSD，macOS | AI 推論伺服器 + MySQL 資料庫 |
| Arduino Uno | — | Ch5 側重儀器豆子計數 |

---

## 軟體架構

```
FMD_AI_Screener/
├── PDMS2_web/          # 施測端 Flask（port 8000）+ 管理端 Flask（port 8001）
│   ├── run.py          # 施測端主程式
│   ├── admin.py        # 管理端主程式
│   ├── utils/rag_advisor.py   # PDMS2Advisor（RAG 建議模組）
│   ├── html/           # 前端 Web 頁面
│   ├── ch1-t1~ch5-t1/ # 各子關卡 AI 分析模組
│   └── rag_db/         # ChromaDB 向量資料庫
├── MacWeb/web.py        # 分析伺服器 Flask（port 3000）
└── RAG/                 # PDMS-2 知識庫文件
```

---

## 物件導向設計文件（OO Course Deliverables）

本節為物件導向程式設計課程期末專題的 OO 設計文件，依課程第四章至第八章規範撰寫。  
所有 UML 圖表使用 **Mermaid 語法**，可在 GitHub 直接渲染，或於 VS Code 安裝 Markdown PDF 擴充套件後匯出 PDF。

### 文件清單

| 文件 | 章節 | 說明 |
|------|------|------|
| [docs/ch04-vocabulary.md](docs/ch04-vocabulary.md) | 第四章 | **詞彙表** — 25 個系統核心術語，含中英文名稱、定義與備註 |
| [docs/ch05-use-case-diagrams.md](docs/ch05-use-case-diagrams.md) | 第五章 | **使用案例圖** — 6 個主要功能域，對應 6 張 Mermaid 使用案例圖 |
| [docs/ch06-use-case-descriptions.md](docs/ch06-use-case-descriptions.md) | 第六章 | **使用案例描述** — 6 組使用案例，每組含 1 張正常情節與 1–2 張例外情節，共 14 張描述表 |
| [docs/ch07-activity-diagrams.md](docs/ch07-activity-diagrams.md) | 第七章 | **活動圖** — 對應 6 張使用案例的完整活動流程（Mermaid flowchart TD） |
| [docs/ch08-class-diagram.md](docs/ch08-class-diagram.md) | 第八章 | **類別圖** — 系統完整 OO 類別架構，含繼承與使用關係（Mermaid classDiagram） |

### 使用案例功能域總覽

| UC | 功能域 | 主要執行者 | 簡述 |
|----|--------|-----------|------|
| UC-01 | 兒童帳號管理 | 管理者 | 兒童 UID 建立、查詢、刪除 |
| UC-02 | 進行精細動作測驗 | 施測者、兒童 | 妙妙屋情境化測驗，完成 17 個 PDMS-2 子關卡 |
| UC-03 | AI 影像分析與評分 | AI 分析引擎（Mac Mini） | YOLO → SAM → TF / 幾何規則，輸出 0–2 分 |
| UC-04 | 成績管理與查詢 | 管理者、家長 | 分項得分查詢、手動修改、成績歷史追蹤 |
| UC-05 | 生成 AI 居家建議 | PDMS2Advisor（RAG） | ChromaDB + LLM 生成個人化練習建議，score_signature 快取 |
| UC-06 | 系統設定與機器管理 | 超級管理者、施測者 | 攝影機 ROI 校正、px2cm 設定、管理者帳號管理 |

### 類別架構層次

```
資料實體層   User / AdminUser / Task / ScoreRecord / MachineConfig / AIAdviceHistory
AI 服務層    AIAnalyzer（抽象）→ BlockAnalyzer / DrawingAnalyzer / CuttingAnalyzer / FoldingAnalyzer / InstrumentAnalyzer
             PyramidChecker / StairChecker / Analyze_graphics / PaperDetector_YOLO / PaperDetector_Edge / PDMS2Advisor
後端應用層   FlaskApp（抽象）→ TestingApp (port 8000) / AdminApp (port 8001) / ServerApp (port 3000)
             CameraController
前端控制層   CameraPage / TaskPage / AdminPage / MainPage
```
