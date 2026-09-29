---
version: 1
slug: "pdms2-web-html-index-html"
primary_target: "PDMS2_web/html/index.html"
related_targets: ["PDMS2_web/html/start.html","PDMS2_web/html/task.html","PDMS2_web/html/camera.html"]
---

---
version: 1
slug: "pdms2-web-html-index-html"
primary_target: "PDMS2_web/html/index.html"
related_targets: ["PDMS2_web/html/start.html","PDMS2_web/html/task.html","PDMS2_web/html/camera.html"]
---

---
version: 1
slug: "pdms2-web-html-index-html"
primary_target: "PDMS2_web/html/index.html"
related_targets: ["PDMS2_web/html/start.html","PDMS2_web/html/task.html","PDMS2_web/html/camera.html"]
---

# Surface brief：孩子闖關流程

## Scope
孩子會看到的四個畫面：`start.html`（勇者編號入口）、`index.html`（關卡與任務）、`task.html`（任務說明）、`camera.html`（拍照／錄影）。模式：Operate —— 孩子要能一眼知道現在在第幾關、點哪裡開始；大人要能一眼看出進度。設定頁不在範圍內，只繼承新字型與新按鈕。

## Constraints
- 保留：全部文案與流程、五關結構（插圖、背景、字型的最新決定見下方「使用者定案」，取代本條原本的保留項）。
- 使用者點名的 AI 感來源：漸層與發光、千篇一律的圓角白卡。這兩樣全面移除。
- 不向孩子顯示分數；「完成」只代表做完了。

## Direction contract
THESIS：整個闖關畫面就是一張台灣幼兒園牆上的注音符號掛圖 —— 粗黑格線切出格子，每格一張圖、一個詞、一個注音。拒絕「粉彩漸層背景上漂浮的圓角白卡」這個兒童 App 的預設排法。

OWN-WORLD：近白的掛圖紙底；墨黑 3–4px 格線；五關各一種平塗印刷色（朱紅、鉻黃、草綠、群青、紫），只用來標示「你在哪一關」；可按的東西只有一種：墨黑實心塊，按下反白；完成＝紅色印泥圓章。沒有漸層、沒有發光、沒有投影、沒有大圓角。字：思源黑體 TC 900 當掛圖標頭，楷體（霞鶩文楷 TC，後備標楷體）當任務名，注音字體當閱讀文字。圖示是同一筆畫粗細的自繪 SVG，不用 emoji。

STORY：孩子看到一張熟悉的掛圖，找到自己這一關的顏色，看圖認出任務，按下黑色的「開始」；做完回來，那一格被蓋上「完成」章。大人看標頭上的五個集點圈就知道整體進度。

FIRST VIEWPORT：頂端是掛圖標題列（左：色格「ㄇ」標記＋「魔法王國大冒險」，右：聽故事、集點圈、小老師模式），下緣一條 4px 墨線。下方五個關卡分頁共用格線排成一列，目前這關填滿關卡色並與下方表身連成一體。表身上緣是關卡標題列（大號關卡序號色格、楷體標題、注音導言、上一關／下一關）。其餘高度是共用格線的任務格：左上角關卡色序號、插圖、楷體任務名、注音說明、墨黑「開始」與描邊「完成」。

FORM：注音符號教室掛圖，排序第 3；seed key c4f54853；借入紀律：可按的只有墨黑塊（收束繩斗篷）、格線即版面（Crouwel）、按下反白（一位元桌面）、原地蓋章並保留（登機門看板）、粗線標示目前位置（雲採石場）、錄影中保留色（示波器）。簽名互動：蓋章。

FINISH：unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance

## Memorable moment
按下「完成」時，一顆紅色印泥圓章「咚」一聲蓋在那一格上，微微歪斜，之後一直留在那裡。

## Unresolved
- （已解決）插圖已依使用者逐張意見重畫為掛圖平塗風格，見「使用者定案」。

## Start page (入口) —— surface round
FORM：注音大字海報（surface seed b3b6e064，發牌 4/6/1，使用者選 4）。
FIRST VIEWPORT：全頁童話王國插畫加深色遮罩（使用者指定保留，用來凸顯前景）；上半頁兩行巨大紙白注音楷體「歡迎來到／童話王國」；其下一條五關五色條；一行注音副標；中央一整條紙白登入列：鑰匙格｜勇者編號欄｜墨黑「進入故事」。
拒絕：玻璃卡片、立體紙箱名牌、小方塊字卡。唯一動態：五色條由左畫出。

## 使用者定案（取代上方契約中相衝突的字型／素材描述）
- 字型：孩子看的所有文字用「源泉注音圓體 粗」（ButTaiwan BpmfGenSenRounded-B，依用字裁切並依 OFL 改名為 FMAS GenSen Bpmf，css/fonts/）；大人頁（設定頁、小老師面板、攝影機設定入口）用 Noto Sans TC。原契約的思源黑體 900 ＋ 楷體已由使用者否決（太細）。
- 插圖：images/chart/ 24 張，命名 chX-tY-中文名（chX-00 為關卡封面），使用者逐張核可：第一關六色立體正方體；第二關 1–3 黑色彩色筆、4–6 紅色彩色筆；第三關草綠剪刀，3-3 沿參考線剪、3-4 直接剪白紙。
- 入口背景：images/start-bg-chart.jpg（掛圖風格童話王國，含六色積木橋），加深色遮罩（使用者指定）。
- 抬頭標記維持「ㄇ」色格；使用者否決校徽。
- 任務格：插圖在上且大，標題為動作大字＋故事小字，不放說明行，不做左右各半。
- 捲軸只留 js/custom-scrollbar.js 的一條（方角墨框、關卡色握把）。
- 設定頁與其他頁同風格且要繽紛：步驟編號色格、關卡淡色區塊、實心色的鏡頭種類標籤。
