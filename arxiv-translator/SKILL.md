---
name: arxiv-translator
description: 將 arXiv 論文自動整理為雙語 Markdown（英文原文在前、繁體中文翻譯在後，.md），不生成 PDF。使用者提供 arXiv ID、URL、論文標題，或提到「翻譯論文」「我想讀中文版」「轉成 md」時立即使用。支援多篇論文順序處理，無需使用者手動操作。
---

# arXiv 論文雙語 Markdown 翻譯

**目標：** 將指定 arXiv 論文的 LaTeX source 整理成英文原文與繁體中文翻譯並列的雙語 Markdown（`.md`），並嵌入高品質圖片；預設不編譯 PDF。

**流程：** 必須依「第一步」到「第四步」順序執行，不得省略、合併或調換。

**互動：** 只有在論文 ID 無法確定，或搜尋結果有多個候選必須由使用者選擇時，才向使用者提問；其餘情況直接完成 Markdown。

**翻譯：** 翻譯由目前對話模型完成；不得使用外部翻譯工具，也不得下載既有翻譯版本。

---

## 第一步：確定論文 ID

- arXiv URL / ID：直接擷取 ID。
- 論文標題：搜尋 arXiv / 網頁確認 ID；若無法唯一確定，列候選請使用者確認。

---

## 第二步：取得 source 並確定翻譯範圍

```bash
python3 {SKILL_DIR}/scripts/download.py "{PAPER_ID}" "$OUTPUT_DIR/.tmp_arxiv/{PAPER_ID}"
```

`download.py` 會下載 source、解壓、遞迴尋找 `.tex`、定位主檔並取得論文標題。

`OUTPUT_DIR` 為使用者指定的保存路徑；未指定時使用目前目錄。

若論文沒有 LaTeX source、只有 PDF，告知使用者並跳過。

腳本 stdout 會輸出三行：

```text
WORK_DIR=<source 目錄絕對路徑>
MAIN_TEX=<主檔相對路徑>
PDF_NAME=<論文標題>
```

---

## 第三步：翻譯並生成 Markdown

先渲染圖片資源：

```bash
python3 {SKILL_DIR}/scripts/render_figures.py "$WORK_DIR" "$MAIN_TEX" "$OUTPUT_DIR/${PDF_NAME}_assets"
```

`render_figures.py` 會依 LaTeX `\includegraphics` 的出現順序輸出 `fig01.png`、`fig02.png`……；PDF source 圖會用 `pdftoppm -png -r 300 -cropbox -singlefile` 渲染，以保留高清文字與線條並減少整頁空白。若 source 圖已是 PNG/JPG，則直接複製。若某張圖轉換失敗，才手動 fallback。

由目前**對話模型**讀取主 `.tex` 與其 `\input{}` / `\include{}` 引用的正文檔，直接產出：

```bash
$OUTPUT_DIR/$PDF_NAME.md
```

若檔名包含不適合作為路徑的字元，可替換為安全字元，但最終必須回報保存路徑。

Markdown 結構要求：

- `#` 使用自然繁體中文論文題名，不保留英文題名或中英並列。
- 標題下保留英文原題與作者/機構資訊。
- `摘要` 可寫成 `## Abstract` 下一行 `## 摘要`，不強制編號。
- 從 `Introduction` 起，章節與小節必須編號，並同時保留英文標題與繁中標題：
  - `\section{Introduction}` → `## 1. Introduction` 下一行 `## 1. 引言`
  - `\subsection{Method}` → `### 3.1 Method` 下一行 `### 3.1 方法`
  - `\subsubsection{}`、`\paragraph{}` 也按層級延續編號，採英文標題一行、中文標題一行。
- 正文採段落級雙語格式：英文原文自然段在前，對應繁中翻譯緊跟在後；不要做成整章 Original + 整章 Translation。
- 若 LaTeX source 將同一自然段拆成多行，先合併成同一英文段落，再放對應翻譯。
- 列表轉成 Markdown 列表。
- 表格若簡單則轉成 Markdown 表格；複雜表格可保留為 fenced code block 或簡潔文字說明。
- 每個表格 caption 必須中英成對：
  - `Table X: <original caption>`
  - `表 X：<中文 caption>`
- 公式保留 LaTeX；行內公式用 `$...$`，展示公式用 `$$...$$` 或原 LaTeX 環境。
- 圖片必須保存在 `$OUTPUT_DIR/${PDF_NAME}_assets/`，並用 Markdown 圖片語法嵌入：`![圖X：中文說明](相對路徑.png)`。
- 每張圖片下方必須有中英 caption，英文原文不能省略 `Figure X:` 前綴：
  - `Figure X: <original caption>`
  - `圖 X：<中文 caption>`

引用與交叉引用規則：

- citation 指令必須轉成純文字方括號 key 列表，不保留 LaTeX citation command，也不做超連結。
  - `\cite{OpenScene, maskclustering, conceptfusion}` → `[OpenScene, maskclustering, conceptfusion]`
  - `\citep{SAM}`、`\citet{CLIP}`、`\citealp{foo,bar}` → `[SAM]`、`[CLIP]`、`[foo, bar]`
- 文中交叉引用必須解析成純文字編號，不保留 LaTeX ref command，也不做超連結。
  - `Fig.~\ref{fig:pipeline}` → `Figure 2` 或 `圖 2`
  - `Sec.~\ref{subsec:method}` → `Section 3.2` 或 `第 3.2 節`
  - `Tab.~\ref{tab:main}` → `Table 1` 或 `表 1`
- 若無法可靠解析某個交叉引用，優先根據圖表/章節出現順序推斷；仍不確定時才保留原始 `\ref{...}`，並在自檢中說明。

翻譯規則：

- **翻譯範圍：** 預設只翻正文，不翻附錄；若同一檔案中出現 `\appendix`，預設只翻該命令之前的內容。使用者明確要求「翻譯全文」時才翻附錄。
- **必須翻譯：** 正文敘述、摘要、圖表標題、列表項、腳註描述文字，以及程式碼區塊中的註解。
- **必須保留原文：** 與翻譯內容對應的英文原文都必須保留，並置於翻譯之前。
- **保留不翻：** 數學環境、citation/ref key、圖片路徑、URL、程式碼本體、`.bib`、人名、機構名、模型名、資料集名。
- **專有名詞：** Transformer、Softmax、Token 等通用學術術語保留英文，不要生硬硬譯。
- **多篇處理：** 多篇論文順序處理；只有使用者明確要求平行委派時，才使用 subagent。

譯後必須自檢：

- 確認 `.md` 檔存在且非空。
- 快速檢查 Markdown 開頭包含中文標題與摘要。
- 檢查從 Introduction 起章節/小節皆有編號，且英文標題與繁中標題成對出現。
- 檢查 `Figure X:` / `圖 X：`、`Table X:` / `表 X：` 成對出現，圖片下方英文 caption 不缺 `Figure X:` 前綴。
- 檢查正文沒有未解析的 `Fig.~\ref{...}`、`Tab.~\ref{...}`、`Sec.~\ref{...}` 等引用。
- 檢查正文沒有殘留 `\cite{...}`、`\citep{...}`、`\citet{...}` 等 citation command；應已轉為 `[key1, key2]`。
- 檢查正文沒有大段未翻譯英文，除非屬於模型名、資料集名、citation key、公式、程式碼、URL、圖片路徑等保留範圍。
- 確認 Markdown 圖片相對連結指向存在的 `.png` / `.jpg`，且使用 `![...](...)` 圖片語法。

---

## 第四步：清理

```bash
python3 {SKILL_DIR}/scripts/cleanup.py "$OUTPUT_DIR"
```

多篇論文時，所有 Markdown 都完成並保存後再清理中間檔。

最後回報 Markdown 保存路徑；若有圖片資源目錄，也同時回報。

---

## 參考文件

- `references/compile-errors.md`：僅在使用者臨時要求 PDF 編譯時參考；預設 Markdown 流程不使用。
