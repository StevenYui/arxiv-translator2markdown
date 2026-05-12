# arXiv Translator Skill

這是一個給 Codex / Agent 使用的 arXiv 論文翻譯 Skill。它會從 arXiv LaTeX source 產生**雙語 Markdown**：英文原文在前、繁體中文翻譯在後，並將論文圖片整理成可直接嵌入 Markdown 的高品質資源。

目前預設**不產生 PDF**。重點是讓論文內容方便閱讀、搜尋、摘錄與後續筆記整理。

## 功能

你可以直接給 Agent arXiv ID、arXiv URL 或論文標題，例如：

```text
翻譯 2411.16253 成 md 檔
```

或：

```text
我想讀 RoboRefer 的中文版，整理成 Markdown
```

Skill 會引導 Agent 完成：

1. 下載 arXiv e-print source。
2. 找出主 `.tex` 與正文引用檔。
3. 依 LaTeX `\includegraphics` 出現順序產生圖片資源。
4. 將正文整理成英文原文 + 繁體中文翻譯的段落級雙語 Markdown。
5. 清理中間下載目錄。

## 圖片處理方式

圖片優先從 LaTeX source 中的原始圖檔處理。若 source 圖是 PDF，會使用：

```bash
pdftoppm -png -r 300 -cropbox -singlefile
```

這個設定的目的：

- `-png`：保留圖中文字與細線，不使用有損壓縮。
- `-r 300`：使用 300 DPI，避免圖片解析度過低。
- `-cropbox`：尊重 PDF 的 CropBox，減少整頁畫布造成的多餘空白。
- `-singlefile`：每張 figure 輸出單一圖片檔。

輸出檔會命名為：

```text
fig01.png
fig02.png
fig03.png
...
```

若 source 圖本身已是 PNG/JPG，則直接複製到 assets 目錄。

## Markdown 規則

輸出的 Markdown 會採用段落級雙語格式：

```markdown
English paragraph.

繁體中文翻譯段落。
```

章節標題會保留英文與繁中標題：

```markdown
## 1. Introduction
## 1. 引言
```

圖片與表格 caption 也會中英成對：

```markdown
Figure 1: Original caption.

圖 1：繁體中文 caption。
```

## Citation 規則

LaTeX citation command 會轉成純文字方括號 key 列表，不保留 `\cite{}`，也不做超連結。

例如：

```latex
\cite{OpenScene, maskclustering, conceptfusion}
```

會輸出為：

```text
[OpenScene, maskclustering, conceptfusion]
```

其他常見 citation command 也採同樣規則：

```latex
\citep{SAM}
\citet{CLIP}
```

會輸出為：

```text
[SAM]
[CLIP]
```

## 安裝方式

1. Clone 本倉庫：

   ```bash
   git clone https://github.com/Leey21/arxiv-translator
   ```

2. 在 Codex 或支援 Agent Skills 的環境中，請 Agent 安裝本 repo 內的 skill 目錄：

   ```text
   路徑 `<path>/arxiv-translator` 中定義了一個 Skill，請閱讀並安裝到你的 skills 目錄。
   ```

   請將 `<path>` 換成你 clone 後的實際路徑。

## 需要的本機工具

基本需求：

- Python 3
- `pdftoppm`（通常由 poppler-utils 提供）

可檢查：

```bash
python3 --version
which pdftoppm
```

若缺少 `pdftoppm`，PDF figure 仍可能無法轉成高品質 PNG。

## 倉庫結構

```text
arxiv-translator/
├── SKILL.md
├── scripts/
│   ├── download.py          # 下載 arXiv e-print、解壓並找主 tex
│   ├── render_figures.py    # 依 includegraphics 順序產生高品質圖片
│   ├── inspect_tex.py       # 輔助掃描 tex 中可能未處理的英文
│   ├── compile.py           # 保留給臨時 PDF 編譯需求，預設流程不用
│   └── cleanup.py           # 清理 .tmp_arxiv 與 inspect 暫存檔
└── references/
    └── compile-errors.md    # 僅在臨時 PDF 編譯失敗時參考
```

## 限制

- 只適用於 arXiv 提供 LaTeX source 的論文。
- 若 arXiv 只有 PDF，無法使用完整 source-based Markdown 流程。
- 預設只翻正文，不翻附錄；若需要附錄，請明確要求「翻譯全文，包含附錄」。
- citation 會保留 key，不會自動展開成完整 bibliography 條目。

## 設計取向

這個 Skill 的目標不是做一次性的逐頁 PDF 翻譯，而是利用 LaTeX source 的結構資訊，產出更容易閱讀與二次整理的 Markdown。公式、圖表、citation key、模型名與資料集名會盡量保留原貌，正文則以繁體中文補在英文原文之後，方便對照閱讀。
