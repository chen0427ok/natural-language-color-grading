# Photo Coloring

上傳照片、選擇風格 preset，即時看到調色前後對比，並可下載結果。

## 功能

- 6 種風格 preset：Film、Japanese Soft、Cinematic、Moody、Light & Airy、Teal & Orange
- 原圖 / 調色後左右並排對比
- 調色結果下載（JPEG）

## 調色參數

所有風格都基於同一組參數：exposure、contrast、saturation、temperature、tint、highlights、shadows、blacks、fade、grain、vignette、clarity、split\_tone。參數定義在 `presets.json`，可直接編輯新增風格。

## 啟動方式

```bash
uv run streamlit run app.py
```

開啟瀏覽器 http://localhost:8501

## 檔案結構

```
photo-coloring/
├── app.py           # Streamlit 主程式
├── processor.py     # 圖片處理邏輯
├── presets.json     # 風格參數定義
└── pyproject.toml   # 依賴管理（uv）
```

## 依賴

- Python 3.11+
- streamlit
- Pillow
- numpy
