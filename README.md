# 運用 AI 技術判別精細動作之早期遲緩篩檢系統

**專案名稱：** AI-based Early Screening System for Fine Motor Developmental Delay Identification  
**團隊名稱：** 現在發現還不遲，你說對不隊（獵遲小隊）  
**團隊成員：** 洪偉城、林政維、呂昊宸、林宛瑩  
**指導教授：** 趙一平教授  
**文件版本：** v1.0（2026-05-27）

[![Python 3.10+](https://img.shields.io/badge/Python-3.10-blue.svg)](https://www.python.org/) [![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT) [![Frontend](https://img.shields.io/badge/Frontend-HTML5%2FCSS3%2FJavaScript-E34F26.svg)](https://developer.mozilla.org/docs/Web) [![Backend](https://img.shields.io/badge/Backend-Flask-black.svg)](https://flask.palletsprojects.com/) [![Database](https://img.shields.io/badge/Database-MySQL%208.0+-4479A1.svg)](https://www.mysql.com/) [![CV](https://img.shields.io/badge/Computer%20Vision-OpenCV-green.svg)](https://opencv.org/) [![Model](https://img.shields.io/badge/Model-YOLO-red.svg)](https://github.com/ultralytics) [![Segmentation](https://img.shields.io/badge/Segmentation-SAM-purple.svg)](https://github.com/facebookresearch/segment-anything) [![DL](https://img.shields.io/badge/Deep%20Learning-TensorFlow%2FPyTorch-EE4C2C.svg)](https://www.tensorflow.org/) [![CANS Lab](https://img.shields.io/badge/CANS-Lab-orange.svg)](https://canslab1.github.io/)

---

## 介紹影片

[運用AI技術判別精細動作之早期遲緩篩檢系統介紹影片](https://youtu.be/uGfGr5dzklI?si=zy6J9WrYJ886j5G3)

## 獲得的獎項

- [114年度「為桃園做研究」桃園市政府大專校院學生創新點子及研究實作競賽 金質研究獎](https://sccdc.tycg.gov.tw/News_Content.aspx?n=16792&s=1600221#lg=1&slide=1)
- [2025 全國 AI 專題創意競賽 佳作](https://phpweb2.nutn.edu.tw/ilt/wordpress/wp-content/uploads/2025/12/%E6%B1%BA%E8%B3%BD%E7%B5%90%E6%9E%9C.pdf)

---

## 目錄

1. [主題說明](#1-主題說明)
2. [系統特色](#2-系統特色)
3. [AI 應用與模型流程](#3-ai-應用與模型流程)
4. [系統架構](#4-系統架構)
5. [設計理念](#5-設計理念)
6. [使用情境](#6-使用情境)
7. [預期成果](#7-預期成果)
8. [安裝與使用指南](#8-安裝與使用指南)
9. [開發工具](#9-開發工具)
10. [物件導向設計文件](#10-物件導向設計文件)
11. [參考資料](#11-參考資料)

---

## 1. 主題說明

### 什麼是兒童發展遲緩？

根據 Guralnick 的觀點，兒童發展遲緩通常源自於生物性風險（先天性疾病、神經發展問題）與環境性風險等多重因素，使得兒童在社交、動作或認知發展上落後於同齡。早期療育（Early Intervention, EI）是針對有發展遲緩或身心障礙的嬰幼兒及其家庭所提供的各類服務與支持，可能包括語言治療、物理治療等。由於幼兒發展具有高度可塑性，及早發現與介入能在黃金時期發揮最大療效。

### 為什麼需要提早介入？

6 歲前是兒童發展的黃金時期。根據統計，110 年底早期療育個案中，「3–5 歲未滿」占比 42.3% 為最高，「5–6 歲未滿」占 23.4%，兩者合計達 66%。這顯示多數孩子是在 3–6 歲才被發現問題，很多兒童已經錯過了最早期的介入時機。

研究顯示，經過八週職能治療師主導的精細動作介入後，精細動作遲緩的比例從 85.7% 降至僅 7%。然而偏鄉地區往往因醫療與教育資源不足，導致問題不易被及時發現——來自偏鄉的家庭其發展遲緩診斷平均延後約 5 個月，凸顯了建立低門檻、可攜式檢測系統的重要性。

### 系統設計目的

本系統以國際通用的 **PDMS-2（皮巴迪動作發展量表第二版）** 為評分基準，專為 4-6 歲兒童設計，透過「妙妙屋」故事情境與遊戲化介面，讓偏鄉衛生所人員無需職能治療師在場即可完成篩檢，並自動生成個人化居家練習建議。

**為何選擇 PDMS-2？**
根據 Relebo 等人(2021)針對 392 名 12-48 個月兒童的驗證研究，PDMS-2 具有良好的內部一致性（α = 0.85）及極高的重測信度（ICC = 0.98–0.99），能穩定且有效區分兒童的動作發展能力。

---

## 2. 系統特色

| 特色 | 說明 |
|------|------|
| 🎯 **標準化評估** | 基於 PDMS-2 專業量表，17 個子關卡涵蓋積木建構、圖形描繪、剪紙、折紙、儀器量測 |
| 🎮 **遊戲化體驗** | 故事情境降低兒童測試抗拒，5 分鐘快速架設 |
| 🚀 **AI 多階段判讀** | YOLO → SAM → TensorFlow/幾何規則，輸出 0-2 分 |
| 📱 **可攜式設計** | 一袋帶走，適合偏鄉巡迴使用 |
| ☁️ **雲端記錄** | MySQL 資料庫完整追蹤兒童發展歷程，透過 Tailscale 安全連線 |

### 系統架構

```
FMD_AI_Screener/
├── PDMS2_web/          # 施測端 Flask（port 8000）+ 管理端 Flask（port 8001）
│   ├── run.py          # 施測端主程式
│   ├── admin.py        # 管理端主程式
│   ├── utils/rag_advisor.py   # PDMS2Advisor（RAG 建議模組）
│   ├── html/           # 前端 Web 頁面
│   ├── ch1-t1~ch5-t1/ # 各子關卡 AI 分析模組
│   └── rag_db/         # ChromaDB 向量資料庫
├── MacWeb/web.py       # 分析伺服器 Flask（port 3000）
└── RAG/                # PDMS-2 知識庫文件
```

---

## 3. AI 應用與模型流程

本專案的 AI 不是單一模型，而是依題型拆成多條可重用的視覺流程：

### Ch1 積木建構題
以 YOLO 偵測積木位置，再用 SAM 取得精準遮罩，配合骨架化與層級分組，判斷金字塔、階梯與牆面堆疊是否符合 PDMS-2 標準。

### Ch2 圖形描繪題
先做 A4 紙校正與像素/公分換算，再透過 YOLO 切出待辨識圖形，搭配 TensorFlow 分類模型區分圓形、橢圓、四邊形、十字等目標，並以骨架與端點分析評分。

### Ch3 剪紙題
以 YOLO 偵測紙張與物件遮罩，再利用 ArUco 標記完成尺度校正，最後根據輪廓到中心點的最短/最長距離計算是否達標。

### Ch4 折紙題
以彩色邊緣與最大面積四邊形偵測為主，搭配幾何量測與影像分析判定折線與紙張形狀。

### Ch5 側重儀器題
以側重儀器搭配 Arduino 進行即時量測，持續計算數量與時間，並結合遊戲狀態紀錄做即時回饋與最終評分。

### 設計原則
**「先偵測、再分割、後分類、最後用規則或量測轉成分數」**——使模型結果更接近臨床情境下的人工判讀方式。

---

## 4. 系統架構

### 硬體組成

| 設備 | 規格 | 用途 |
|------|------|------|
| 施測端 PC | Intel i5+，8GB RAM，Windows 11 | 前端 Web 介面 + 施測端 Flask |
| PW313D 攝影機 | 雙鏡頭（俯視 + 側視），1080P USB | 拍攝兒童動作影像 |
| 14 吋觸控螢幕 | IPS，1920×1080 | 兒童遊戲化操作介面 |
| Mac Mini M2 Pro | 16GB RAM，512GB SSD，macOS | AI 推論伺服器 + MySQL 資料庫 |
| Arduino Uno | — | Ch5 側重儀器豆子計數 |

### 三層式架構

```
施測端 PC（Flask + 前端）
    ↕ Tailscale VPN
Mac Mini M2 Pro（AI 分析伺服器 + MySQL）
```

---

## 5. 設計理念

### 問題背景

根據 WHO 統計，0-6 歲兒童發展遲緩發生率約 7%，台灣每年約有 1.4 萬名小朋友可能出現發展遲緩。然而：
- 偏鄉評估中心數量僅占全國 6%
- 發展遲緩診斷平均延後約 5 個月
- 接受早期療育服務人數從 2016 年的 34,450 人次上升至 2024 年的 61,000 人次

### 解決方案

1. **把測驗變成遊戲，把檢測變成故事** — 提升投入、數據自然、降低測試效應
2. **AI 輔助評分** — 降低人工逐張判讀的負擔
3. **雲端追蹤** — MySQL 記錄單次與縱向表現，便於後續轉介與追蹤
4. **可攜式設計** — 五分鐘架設，一袋帶走

---

## 6. 使用情境

### 妙妙屋互動測驗

小朋友走進「妙妙屋」，平板會播放自製故事，小朋友隨著故事引導完成任務：
- 疊魔法石頭（積木題）
- 用魔法畫筆完成線條（圖形題）
- 剪出魔法形狀（剪紙題）
- 折出魔法形狀（折紙題）
- 數豆子（儀器題）

### 適用場域

- 偏鄉衛生所巡迴篩檢
- 幼兒園日常評估
- 課後輔導與社區活動中心

---

## 7. 預期成果

| 對象 | 成果 |
|------|------|
| **老師** | 減少依賴經驗判斷，快速獲得具客觀依據的孩童精細動作表現紀錄 |
| **家長** | 每項動作均有系統記錄，提高家長信任，降低焦慮 |
| **孩童** | 遊戲化篩檢減少測驗壓力，表現更真實自然 |
| **學校** | 累積標準化量表指標與影音紀錄，建立完整發展史 |
| **長期** | 減少偏鄉兒童因延誤而惡化，促使提早發現、提早轉介 |

---

## 8. 安裝與使用指南

### 系統需求

#### 硬體需求
- **處理器：** Intel i5 或同等級以上
- **記憶體：** 8GB RAM 以上
- **儲存空間：** 10GB 可用空間
- **攝影機：** PW313D 雙鏡頭網路攝影機或相容裝置
- **顯示器：** 觸控螢幕（建議 14 吋 IPS 1080P）

#### 軟體需求
- **作業系統：** Windows 11 / macOS
- **Python 版本：** 3.7 / 3.10 / 3.13
- **資料庫：** MySQL 8.0+
- **瀏覽器：** Chrome / Edge（支援觸控功能）

### Installation

#### Python Version
- Python 3.10 or later (tested on Python 3.12 and 3.13)

#### Setup

```bash
git clone https://github.com/WeiChengTW/FMD_AI_Screener.git
cd FMD_AI_Screener
pip install -r requirements.txt
```

#### Dependencies

Install all required packages:

```bash
pip install -r requirements.txt
```

Or install individually:

```bash
pip install flask flask-cors mysql-connector-python opencv-python>=4.8.0 \
    ultralytics torch tensorflow pillow pyserial chromadb langchain-community \
    numpy scipy matplotlib
```

#### Standard Library Modules (no installation needed)

`tkinter`, `random`, `os`, `time`, `math`, `threading`, `pickle`, `warnings`, `json`, `csv`

---

## 9. 開發工具

### 核心技術框架

| 類別 | 技術 |
|------|------|
| 機器學習/深度學習 | YOLO、 SAM、 TensorFlow、 PyTorch |
| 影像處理 | OpenCV、 PIL、骨架化、輪廓分析、 ArUco 校正 |
| Web 框架 | Flask (Python 後端) |
| 前端技術 | HTML5、 CSS3、 JavaScript (ES6+) |
| 資料庫 | MySQL 關聯式資料庫 |
| 遠端連線 | Tailscale VPN |

---

## 10. 物件導向設計文件

本節為物件導向程式設計課程期末專題設計文件，依課程第四章至第八章規範撰寫。
所有 UML 圖表使用 **Mermaid 語法**，可在 GitHub 直接渲染，或於 VS Code 安裝 Markdown PDF 擴充套件後匯出 PDF。

### 文件清單

| 文件 | 章節 | 說明 |
|------|------|------|
| [docs/ch04-vocabulary.md](docs/ch04-vocabulary.md) | 第四章 | **詞彙表** — 25 個系統核心術語，含中英文名稱、定義與備註 |
| [docs/ch05-use-case-diagrams.md](docs/ch05-use-case-diagrams.md) | 第五章 | **使用案例圖** — 6 個主要功能域，對應 6 張 Mermaid 使用案例圖 |
| [docs/ch06-use-case-descriptions.md](docs/ch06-use-case-descriptions.md) | 第六章 | **使用案例描述** — 6 組使用案例，每組含 1 張正常情節與 1-2 張例外情節，共 14 張描述表 |
| [docs/ch07-activity-diagrams.md](docs/ch07-activity-diagrams.md) | 第七章 | **活動圖** — 對應 6 張使用案例的完整活動流程（Mermaid flowchart TD） |
| [docs/ch08-class-diagram.md](docs/ch08-class-diagram.md) | 第八章 | **類別圖** — 系統完整類別架構，含繼承與使用關係（Mermaid classDiagram） |

### 使用案例功能域總覽

| UC | 功能域 | 主要執行者 | 簡述 |
|----|--------|-----------|------|
| UC-01 | 兒童帳號管理 | 管理者 | 兒童 UID 建立、查詢、刪除 |
| UC-02 | 進行精細動作測驗 | 施測者、兒童 | 妙妙屋情境化測驗，完成 17 個 PDMS-2 子關卡 |
| UC-03 | AI 影像分析與評分 | AI 分析引擎（Mac Mini） | YOLO → SAM → TF / 幾何規則，輸出 0-2 分 |
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

---

## 11. 參考資料

[1] Guralnick (2011), "Why Early Intervention Works: A Systems Perspective." *Infants & Young Children*

[2] CDC, "Learn the Signs. Act Early: Early Intervention."

[3] 行政院主計總處, "國情統計通報 — 110年底早期療育人數占比"

[4] Hennigan et al. (2021), "The effects of occupational therapy-led fine motor centers on preschoolers' fine motor skills." *Journal of Occupational Therapy, Schools, & Early Intervention*

[5] Barnard-Brak et al. (2021), "Rural and Racial/Ethnic Differences in Children Receiving Early Intervention Services." *Fam Community Health*

[6] Hsieh et al. (2020), "Collaborative Home-Visit Program for Young Children With Motor Delays in Rural Taiwan." *Phys Ther*

[7] Rebelo et al. (2021), "Validity and reliability of the Portuguese version of the Peabody Developmental Motor Scales-II." *PLOS ONE*

[8] 衛生福利部, "未滿 7 歲兒童新增 6 次兒童發展篩檢服務"

[9] 衛生福利部國民健康署, "兒童發展聯合評估中心名單"

[10] 衛生福利部, "我國偏鄉離島地區醫療資源及相關提升計畫執行成效之探討"

[11] 衛生福利部, "優化偏鄉醫療精進計畫第二期" (2024)

[12] Choo et al. (2019), "Developmental delay: identification and management at primary care level." *Singapore Med J*
