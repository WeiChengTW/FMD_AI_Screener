---
name: FMAS 妙妙屋
description: 把 PDMS-2 精細動作篩檢畫成一張台灣幼兒園牆上的注音符號掛圖
colors:
  ink: "#1D1C1A"
  ink-hover: "#3A3834"
  ink-soft: "#5B5953"
  paper: "#FBFBF8"
  paper-dim: "#EDECE6"
  print-white: "#FFFFFF"
  ch1: "#C92F25"
  ch1-tint: "#F4DEDA"
  ch2: "#F2B705"
  ch2-tint: "#FAF1D6"
  ch3: "#17804A"
  ch3-tint: "#DBEAE0"
  ch4: "#2447B0"
  ch4-tint: "#DDE2EE"
  ch5: "#6D3BA5"
  ch5-tint: "#E7E0EC"
  chart-orange: "#EE7D1A"
  stamp: "#BF1330"
  rec: "#C8006A"
  rec-deep: "#A30057"
  status-warn: "#8A5300"
  disabled-line: "#B9B7B0"
  disabled-text: "#9C9A93"
  placeholder: "#6B6963"
  on-ink-muted: "#D8D5CC"
  poster-scrim: "rgba(29, 28, 26, 0.55)"
typography:
  display:
    fontFamily: "FMAS GenSen Bpmf, BpmfGenYoGothic, PingFang TC, sans-serif"
    fontSize: "clamp(64px, 12.5vmin, 150px)"
    fontWeight: 400
    lineHeight: 1.12
    letterSpacing: "0.02em"
  headline:
    fontFamily: "FMAS GenSen Bpmf, BpmfGenYoGothic, PingFang TC, Microsoft JhengHei UI, sans-serif"
    fontSize: "30px"
    fontWeight: 400
    lineHeight: 1.4
  title:
    fontFamily: "FMAS GenSen Bpmf, BpmfGenYoGothic, PingFang TC, Microsoft JhengHei UI, sans-serif"
    fontSize: "1.8rem"
    fontWeight: 400
    lineHeight: 1.45
  title-story:
    fontFamily: "FMAS GenSen Bpmf, BpmfGenYoGothic, PingFang TC, Microsoft JhengHei UI, sans-serif"
    fontSize: "1.15rem"
    fontWeight: 400
    lineHeight: 1.6
  body:
    fontFamily: "FMAS GenSen Bpmf, BpmfGenYoGothic, PingFang TC, Microsoft JhengHei UI, sans-serif"
    fontSize: "19px"
    fontWeight: 400
    lineHeight: 2.2
  button-kid:
    fontFamily: "FMAS GenSen Bpmf, BpmfGenYoGothic, PingFang TC, Microsoft JhengHei UI, sans-serif"
    fontSize: "1.3rem"
    fontWeight: 400
    lineHeight: 1.2
    letterSpacing: "0"
  numeral:
    fontFamily: "FMAS GenSen Bpmf, BpmfGenYoGothic, PingFang TC, Microsoft JhengHei UI, sans-serif"
    fontSize: "52px"
    fontWeight: 900
    lineHeight: 1
  adult-headline:
    fontFamily: "Noto Sans TC, PingFang TC, Microsoft JhengHei UI, Microsoft JhengHei, sans-serif"
    fontSize: "clamp(24px, 3vw, 32px)"
    fontWeight: 900
    lineHeight: 1.2
    letterSpacing: "0.06em"
  adult-body:
    fontFamily: "Noto Sans TC, PingFang TC, Microsoft JhengHei UI, Microsoft JhengHei, sans-serif"
    fontSize: "15px"
    fontWeight: 400
    lineHeight: 1.7
  label:
    fontFamily: "Noto Sans TC, PingFang TC, Microsoft JhengHei UI, Microsoft JhengHei, sans-serif"
    fontSize: "16px"
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: "0.04em"
  stamp:
    fontFamily: "BiauKai, DFKai-SB, 標楷體, Kaiti TC, Noto Sans TC, serif"
    fontSize: "38px"
    fontWeight: 700
rounded:
  none: "0px"
  field: "4px"
  btn: "6px"
  dot: "50%"
spacing:
  rule: "3px"
  rule-heavy: "4px"
  gap-sm: "8px"
  gap-md: "12px"
  gap-lg: "16px"
  gutter: "20px"
components:
  button-primary:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.paper}"
    typography: "{typography.label}"
    rounded: "{rounded.btn}"
    padding: "10px 18px"
    height: "48px"
  button-primary-hover:
    backgroundColor: "{colors.ink-hover}"
  button-primary-active:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
  button-outline:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    typography: "{typography.label}"
    rounded: "{rounded.btn}"
    padding: "10px 18px"
    height: "48px"
  button-outline-hover:
    backgroundColor: "{colors.paper-dim}"
  button-outline-active:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.paper}"
  button-danger:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.stamp}"
    rounded: "{rounded.btn}"
  button-danger-active:
    backgroundColor: "{colors.stamp}"
    textColor: "{colors.paper}"
  button-task-start:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.paper}"
    typography: "{typography.button-kid}"
    rounded: "{rounded.btn}"
    height: "58px"
  button-rec:
    backgroundColor: "{colors.rec}"
    textColor: "{colors.print-white}"
    rounded: "{rounded.btn}"
    padding: "16px 34px"
    height: "78px"
  button-rec-hover:
    backgroundColor: "{colors.rec-deep}"
  kidbar:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    padding: "8px 20px"
    height: "84px"
  chapter-tab:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    padding: "12px 16px"
  chapter-tab-active:
    backgroundColor: "{colors.ch1}"
    textColor: "{colors.print-white}"
  story-row:
    backgroundColor: "{colors.ch1-tint}"
    textColor: "{colors.ink}"
    typography: "{typography.headline}"
    padding: "14px 20px 14px 0"
  story-number:
    backgroundColor: "{colors.ch1}"
    textColor: "{colors.print-white}"
    typography: "{typography.numeral}"
    width: "84px"
  task-cell:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    padding: "10px 14px 14px"
  task-picture:
    backgroundColor: "{colors.ch1-tint}"
    padding: "12px 12px 8px"
  task-number:
    backgroundColor: "{colors.ch1}"
    textColor: "{colors.print-white}"
    size: "44px"
  progress-dot:
    backgroundColor: "{colors.paper}"
    rounded: "{rounded.dot}"
    size: "24px"
  progress-dot-lit:
    backgroundColor: "{colors.stamp}"
  input-field:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.field}"
    padding: "8px 12px"
    height: "44px"
  entry-row:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    width: "min(720px, 92vw)"
  entry-key-cell:
    backgroundColor: "{colors.ch2}"
    textColor: "{colors.ink}"
    width: "68px"
  enter-button:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.paper}"
    rounded: "{rounded.none}"
  step-number:
    backgroundColor: "{colors.ch1}"
    textColor: "{colors.print-white}"
    size: "40px"
  stat-badge-total:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.paper}"
    rounded: "{rounded.none}"
    padding: "4px 18px"
    height: "44px"
  stat-badge-external:
    backgroundColor: "{colors.ch4}"
    textColor: "{colors.print-white}"
  stat-badge-builtin:
    backgroundColor: "{colors.ch2}"
    textColor: "{colors.ink}"
  stat-badge-continuity:
    backgroundColor: "{colors.ch5}"
    textColor: "{colors.print-white}"
  scrollbar-thumb:
    backgroundColor: "{colors.ch1}"
    rounded: "{rounded.field}"
    width: "38px"
---

# Design System: FMAS 妙妙屋

## Overview

**Creative North Star: "注音符號教室掛圖"**

整個孩子端畫面就是一張台灣幼兒園牆上的注音符號掛圖：近白的掛圖紙上，墨黑格線切出一格一格，每格一張平塗插圖、一個動作大字、一個注音。版面本身就是格線，格線不是畫上去的框，而是墨黑底色從紙格之間的縫隙透出來。孩子找到自己這一關的顏色，看圖認出任務，按下黑色的「開始」；做完回來，那一格被蓋上紅色印泥「完成」章，章一直留在那裡。大人看抬頭上的五個集點圈就知道整體進度。

五種平塗印刷色（朱紅、鉻黃、草綠、群青、紫）是完整的調色盤，但每一種只負責一件事：標示「你在哪一關」。可以按的東西只有一種語言：墨黑實心塊與墨黑描邊塊，按下就黑白對調。沒有漸層、沒有發光、沒有投影、沒有大圓角；深度只靠格線的粗細（3px 與 4px）和紙與墨的明暗。

孩子看的每一行字都用源泉注音圓體 粗（注音直接長在字形裡），字重來自字型本身而不是瀏覽器加粗；大人用的設定頁與小老師面板換成 Noto Sans TC。入口頁是同一個世界的大字報：加深色遮罩的掛圖風格童話王國、巨大的紙白注音大字、一條五色條、一整條紙白登入列。

**Key Characteristics:**
- 墨黑格線即版面：3px 分格、4px 分區，格線由墨黑底色從縫隙透出。
- 五關五色平塗，只標示位置；按鈕永遠是墨黑。
- 單一控制語言：實心墨塊與描邊墨塊，按下反白。
- 簽名互動：紅色印泥圓章原地蓋下、微歪、永久保留。
- 孩子的字全帶注音（源泉注音圓體 粗），大人的字用 Noto Sans TC。
- 版面先看高度再看寬度；直向觸控裝置一律擋在「請把螢幕轉橫」。

## Colors

一張掛圖的印刷色：紙、墨、五關平塗色，再加兩種只屬於單一事件的保留色。

### Primary
- **掛圖墨黑** (ink)：所有文字、所有格線、所有可以按的東西。主要按鈕（開始、下一關、進入故事）是實心墨塊；格線是墨黑底色從紙格縫隙透出。
- **滑鼠懸停墨** (ink-hover)：只在有滑鼠的裝置上，實心墨塊懸停時略微提亮。觸控裝置沒有懸停狀態。
- **次要墨** (ink-soft)：故事小字、步驟標題、副標、面板標籤。

### Secondary
- **朱紅** (ch1) / **鉻黃** (ch2) / **草綠** (ch3) / **群青** (ch4) / **紫** (ch5)：五關各一種平塗印刷色，填在關卡分頁的頂邊與目前這關的整格、關卡序號色格、任務序號色格、捲軸握把。由 JS 依目前關卡改寫 `--accent`、`--accent-on`、`--accent-tint` 三個變數。鉻黃上的字用墨黑，其餘四色上的字用印刷白 (print-white)。
- **五關淡底** (ch1-tint 至 ch5-tint)：同色的平塗淡底，鋪在關卡標題列、任務插圖區、任務頁影片欄；設定頁用來區分各步驟區塊。
- **插圖橘** (chart-orange)：只出現在 `images/chart/` 的插圖平塗裡（例如第一關的積木），不是介面色，不寫進 CSS。

### Tertiary
- **印泥紅** (stamp)：只給「完成」章、已完成任務的描邊、集點圈的已蓋點，以及大人端的危險操作（重設所有進度）與錯誤狀態。
- **錄影洋紅** (rec)：只在相機頁錄影中出現：狀態列底色、相機格的 8px 內框、停止錄影鍵。**錄影深洋紅** (rec-deep) 是該鍵在滑鼠懸停時的深一階。

### Neutral
- **掛圖紙** (paper)：所有格子的底色、按鈕描邊款的底色、登入列。
- **暗紙** (paper-dim)：描邊按鈕的懸停底、蓋章瞬間格子閃一下的底、捲軸軌道、設定頁摘要框。
- **停用灰** (disabled-line / disabled-text)：停用按鈕的描邊與字；實心款停用時整塊變成 disabled-line。
- **提示字灰** (placeholder)：紙白輸入欄的佔位字。
- **墨底淡字** (on-ink-muted)：墨黑相機格上的提示與佔位文字。
- **大字報遮罩** (poster-scrim)：入口頁插畫上的 55% 墨色遮罩（使用者指定），讓紙白大字與登入列站到前面。
- **警告褐** (status-warn)：只用在設定頁的警告狀態字。

### Named Rules
**The Location-Only Rule.** 關卡色只標示「你在哪一關」：分頁、序號色格、淡底、捲軸握把。可以按的動作按鈕永遠是墨黑或紙白描邊，從不填關卡色。

**The Reserved Ink Rule.** 印泥紅只屬於「完成」與危險操作，錄影洋紅只屬於錄影中。兩者都不准拿來做裝飾、強調或標題。

**The No Score Colours Rule.** 孩子端從不用綠色或紅色評判表現。「完成」只代表做完了，紅章是印泥不是打叉；相機頁出錯時用紙白底加一塊當關顏色，而不是粉紅或紅底。

## Typography

**Display Font:** FMAS GenSen Bpmf（源泉注音圓體 粗依用字裁切、依 OFL 改名；後備 BpmfGenYoGothic、PingFang TC）
**Body Font:** FMAS GenSen Bpmf（孩子端）；Noto Sans TC（大人端，後備 PingFang TC、Microsoft JhengHei UI）
**Label/Mono Font:** 印章字用標楷體系（BiauKai、DFKai-SB、Kaiti TC），不帶注音

**Character:** 圓體粗字加上內建注音，像掛圖上印好的字卡：飽滿、好認、不需要瀏覽器加粗。大人端的 Noto Sans TC 900 則是同一張掛圖的標籤，粗而方正。

### Hierarchy
- **Display** (400，clamp(64px, 12.5vmin, 150px)，1.12)：入口頁兩行紙白大字「歡迎來到／童話王國」，只此一處。
- **Headline** (400，30px，1.4)：關卡標題列的關卡名，單行、超出以省略號收尾。
- **Title** (400，1.8rem，1.45)：任務格的動作大字（畫圓、疊城堡）；後面接 **Title-story** (400，1.15rem，1.6，次要墨) 的故事小字，兩者同一行基線對齊，可換行，永不截斷。
- **Body** (400，19px，2.2)：注音導言、任務說明、步驟；行高 2.2 是為了讓注音不撞上一行。
- **Button-kid** (400，1.3rem，字距 0)：孩子會按的按鈕（開始、完成、聽故事、上一關／下一關、相機頁操作）。
- **Numeral** (900，52px，1)：關卡序號色格裡的大數字；任務序號色格同字型縮為 24px。
- **Adult-headline / Adult-body / Label** (Noto Sans TC 900 與 400 與 700)：設定頁標題、說明文字、大人端按鈕與欄位標籤；標籤字距 0.04em。
- **Stamp** (標楷體 700)：只寫在印章圓圈裡的「完成」兩字。

### Named Rules
**The Zhuyin Everywhere Rule.** 孩子會讀的每一段字（標題、導言、任務名、步驟、按鈕、轉向提示）都用注音字型，字重維持 400，靠字型本身的粗度，不讓瀏覽器合成粗體。

**The Adult Switch Rule.** 大人端（`body.adult`、小老師面板、小老師模式鈕、入口頁的攝影機設定標籤）一律換回 Noto Sans TC，不帶注音，讓孩子一眼分得出哪些不是給他按的。

## Layout

整頁是一張不捲動的掛圖：抬頭（最小 84px 高，下緣 4px 墨線）→ 五格關卡分頁列（3px 分格）→ 關卡標題列 → 共用格線的任務格填滿剩下的高度。各區之間以 4px 墨縫分開，同區格子之間以 3px 墨縫分開，縫隙就是墨黑底色。任務格欄數由 JS 依任務數與寬度決定，列高有下限（300px，矮螢幕 220px／200px，大桌機 340px）；只有任務格本身可以捲動。

任務格永遠是「插圖在上」：插圖區吃掉所有剩餘高度，下方只放動作大字＋故事小字與兩顆按鈕（開始 1.6 份、完成 1 份）。任務頁左右分成兩格：左 60% 是淡底上的示範影片（依自身長寬比放到最大，墨框貼著影片），右邊是任務名、編號步驟與底部兩顆大按鈕。相機頁是三列：狀態列、墨黑相機格、紙白操作列。設定頁是置中最寬 1320px 的單欄，兩台鏡頭以 3px 墨縫並排。

斷點先看高度：施測裝置從 iPad 橫向（1024×768）到 1920×1080，孩子端不整頁捲動，所以 `max-height: 960px` 讓格子與字級縮小、`max-height: 720px` 再縮一階；寬度斷點（1180px、900px）只負責抬頭與分頁的緊縮；寬而矮的螢幕另有一條規則壓縮分頁；`min-width: 1600px` 且 `min-height: 961px` 時格子長回大尺寸。觸控樓地板（`pointer: coarse`）永遠寫在尺寸斷點之後：按鈕至少 50px、開始鍵 58px。直向觸控裝置不做版面，全畫面顯示 10px 墨框的「請把螢幕轉橫」。

間距沒有正式刻度，反覆出現的是 8px、12px、16px、20px；左右留白一律與 `env(safe-area-inset-*)` 取大值。

### Named Rules
**The Height-First Rule.** 孩子端的斷點先問「還剩多高」，再問寬度；新畫面不得依賴整頁捲動。

**The Landscape Gate Rule.** 直向的觸控裝置只顯示轉向提示，不為直向另做版面。

## Elevation & Depth

完全平面。沒有投影、沒有發光、沒有漸層、沒有浮起來的卡片；深度只有兩種來源：格線的粗細（3px 分格、4px 分區、面板外框 4px），以及紙與墨的明暗反轉（墨黑的面板標頭、墨黑的相機格）。系統裡僅有的兩個 `box-shadow` 都是內框，不是陰影：集點圈已蓋點用 3px 紙白內圈做出印章的留白，錄影中的相機格用 8px 錄影洋紅內框。

### Named Rules
**The Flat Print Rule.** 掛圖是印刷品：任何元素都不投影、不發光。需要分層時加粗墨線或反白，不要抬高。

## Shapes

直角是預設：格子、分頁、序號色格、面板、登入列、狀態標籤全部 0 圓角。按鈕是唯一稍帶圓角的東西（6px），讓「可以按」在直角格線裡被認出來；輸入欄與捲軸握把是 4px。圓形只出現在集點圈、印章與錄影指示點。描邊一律墨黑：3px 是標準，2px 給次要（完成鈕、小老師模式鈕、清單分隔），4px 給區塊邊界。圖示是同一筆畫粗細（2.4 至 3）的自繪 SVG，以遮罩上色跟著文字顏色走。

## Components

### Buttons
可以按的只有墨塊，按下就黑白對調，像一位元桌面的反白。
- **Shape:** 微圓角 (6px)，3px 墨黑描邊，最小高度 48px（觸控 50px）。
- **Primary:** 實心墨黑、紙白字，內距 10px 18px。任務格的「開始」佔 1.6 份寬、最小 58px 高；入口頁的「進入故事」是登入列右端的一整格墨塊。
- **Hover / Focus:** 懸停只在 `hover: hover` 且 `pointer: fine` 時生效：實心款變為懸停墨，描邊款變為暗紙。按下 (`:active`) 反白，0.12s ease-out。焦點是 3px 墨黑外框、外推 3px。
- **Outline:** 紙白底、墨黑描邊與字；「完成」用 2px 描邊，已完成時描邊與字改為印泥紅。
- **Danger:** 印泥紅描邊與字，按下填滿印泥紅；只在大人端。
- **Recording:** 相機頁的停止錄影鍵是實心錄影洋紅，按下改紙白底洋紅字。
- **Playing:** 旁白播放中的「聽故事」停在反白狀態，圖示換成暫停，不做脈衝發光。

### Cards / Containers
- **Corner Style:** 直角 (0)。
- **Background:** 格子是掛圖紙；插圖區、關卡標題列、任務頁影片欄是當關淡底。
- **Shadow Strategy:** 無，見 Elevation & Depth。
- **Border:** 不自己畫框；格子之間的線是墨黑底色透出的縫。獨立的面板（小老師面板、設定頁區塊）用 3 至 4px 墨框。
- **Internal Padding:** 任務文字區 10px 14px 14px；設定頁區塊 18px 20px。

### Inputs / Fields
- **Style:** 紙白底、2px 墨框、4px 圓角、最小 44px 高（設定頁下拉 52px）。入口頁的勇者編號欄沒有自己的框，而是登入列裡的一格：鉻黃鑰匙格｜輸入欄｜墨黑進入故事，外框 4px 墨黑。
- **Focus:** 小老師面板是 3px 當關色外框；設定頁是 3px 墨框；入口登入列整條加 4px 鉻黃外框、外推 4px。
- **Error / Disabled:** 勇者編號錯誤時鑰匙圖示左右搖一下（0.38s），不變紅。

### Navigation
- **關卡分頁：** 五格一列、3px 墨縫；每格頂邊 10px 關卡色、紙白底、左側一格小插圖、「第 N 關」與注音關卡名。目前這關整格填滿關卡色，字改用該色的上字色；按下反白；滑鼠懸停填淡底。窄視窗改成上下排。
- **抬頭：** 左邊是關卡色方格裡的「ㄇ」標記、注音標題、換人玩；右邊是聽故事、五個集點圈、小老師模式。下緣 4px 墨線。

### Chapter Story Row
關卡標題列是掛圖的一格：左端一整條高的關卡色序號格（84px 寬，右側 3px 墨線，52px 大數字），接著 76px 墨框插圖小格、注音關卡名與導言，右端上一關（描邊）與下一關（實心）。

### Stamp-Slot Progress
抬頭的五個集點圈：24px 空心圓、2.5px 墨框；做完一部分就填成印泥紅，留一圈 3px 紙白內緣，像蓋在點數卡上的章。

### Completion Stamp (Signature)
按下「完成」時，一顆紅色印泥圓章（外圈 7、內圈 2.5 的雙圓，標楷體「完成」）從 1.9 倍大落下，0.34s `cubic-bezier(.16, 1, .3, 1)` 回彈到 -14° 定位，同時整格閃一下暗紙。印章用 SVG 雜訊濾鏡做出吃墨不均的斑駁邊緣，之後一直留在任務格右上角，不移動、不消失。彩紙效果已退場，慶祝只由印章承擔。

### Scrollbar
全站只有一條捲軸，由 `js/custom-scrollbar.js` 畫：60px 觸控熱區、38px 寬握把、3px 墨框、4px 圓角、當關色握把、暗紙軌道；原生捲軸一律隱藏。

### Setting Steps
大人設定頁與孩子頁同一套紙、墨、格線，但更繽紛：每一步以 40px 關卡色序號方格開頭（1 朱紅、2 群青、3 草綠、4 鉻黃、5 紫），區塊鋪同色淡底；鏡頭種類標籤是實心色塊（總數墨黑、外接群青、內建鉻黃、接續互通紫）；抬頭下緣是一條 12px 五色條。設定頁的 `--accent` 固定為群青。

## Do's and Don'ts

### Do:
- **Do** 讓版面本身就是格線：區與區之間 4px 墨縫、格與格之間 3px 墨縫，由墨黑底色透出。
- **Do** 讓可以按的東西只有墨黑實心塊或墨黑描邊塊，按下 0.12s 黑白對調。
- **Do** 在任務格裡讓插圖成為最大的元素：插圖在上、吃掉剩餘高度，下方只放動作大字＋故事小字與兩顆按鈕。
- **Do** 讓孩子讀的每一個字都用注音字型 (FMAS GenSen Bpmf)，大人端換成 Noto Sans TC。
- **Do** 在做完時原地蓋章並讓章留著，位置不動。
- **Do** 先寫高度斷點，觸控樓地板寫在所有尺寸斷點之後。
- **Do** 為每個動畫提供 `prefers-reduced-motion` 的靜止版本。

### Don't:
- **Don't** 把關卡色填到動作按鈕上；關卡色只標示位置。
- **Don't** 在孩子端用綠色或紅色表示對或錯，也不要顯示分數。
- **Don't** 把印泥紅或錄影洋紅用在它們的單一事件以外。
- **Don't** 用漸層、發光、投影或浮起來的圓角白卡；五色條這種硬邊色帶不算漸層。
- **Don't** 用超過 6px 的圓角；格子與面板一律直角。
- **Don't** 用 emoji 或字元當圖示；圖示是同一筆畫粗細的 SVG。
- **Don't** 加第二條捲軸，也不要露出原生捲軸。
- **Don't** 為直向觸控裝置另做版面；顯示轉向提示。
