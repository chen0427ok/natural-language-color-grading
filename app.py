import io
import json

import streamlit as st
from PIL import Image

from parser import parse_prompt, merge_preset_with_delta
from processor import (
    process_image,
    crop_to_ratio,
    apply_manual_crop,
    apply_straighten,
    suggest_crop,
)

st.set_page_config(page_title="Photo Coloring", layout="wide", page_icon="🎨")


@st.cache_data
def load_presets():
    with open("presets.json", "r", encoding="utf-8") as f:
        return json.load(f)


presets = load_presets()

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🎨 Photo Coloring")
    st.markdown("---")

    uploaded_file = st.file_uploader("上傳照片", type=["jpg", "jpeg", "png"])

    st.markdown("### 選擇風格")
    selected = st.radio(
        "風格",
        options=list(presets.keys()),
        label_visibility="collapsed",
    )
    if selected:
        st.caption(presets[selected]["description"])

    st.markdown("---")
    st.markdown("### 自然語言微調")
    prompt_text = st.text_area(
        "描述你想要的風格",
        placeholder="例如：微暖偏綠、黃色偏橘、主體提亮、降低藍綠飽和",
        height=100,
        label_visibility="collapsed",
    )
    if prompt_text.strip():
        parsed = parse_prompt(prompt_text)
        if parsed.style_tags:
            st.caption(f"偵測到風格：{', '.join(parsed.style_tags)}")
        if parsed.crop_suggestion_hint:
            st.caption(f"構圖建議：{parsed.crop_suggestion_hint}")
    else:
        parsed = None

    st.markdown("---")
    st.markdown("### 構圖與裁切")

    crop_mode = st.radio(
        "裁切模式",
        ["不裁切", "比例裁切", "手動裁切", "拉直"],
        label_visibility="collapsed",
    )

    crop_ratio = None
    manual_crop = None
    straighten_angle = 0.0
    show_thirds = False

    if crop_mode == "比例裁切":
        crop_ratio = st.selectbox("選擇比例", ["1:1", "4:5", "3:4", "16:9"])
        show_thirds = st.checkbox("顯示三分線")
        if uploaded_file is not None:
            img_tmp = Image.open(uploaded_file)
            suggestion = suggest_crop(img_tmp, crop_ratio)
            st.caption(
                f"建議裁切：從 ({suggestion['x']}, {suggestion['y']}) "
                f"裁 {suggestion['width']}×{suggestion['height']} px"
            )

    elif crop_mode == "手動裁切":
        if uploaded_file is not None:
            img_tmp = Image.open(uploaded_file)
            iw, ih = img_tmp.size
            st.caption(f"原圖尺寸：{iw} × {ih} px")
            cx = st.number_input("左邊起點 X", 0, iw - 1, 0)
            cy = st.number_input("上邊起點 Y", 0, ih - 1, 0)
            cw = st.number_input("寬度", 1, iw - int(cx), iw - int(cx))
            ch = st.number_input("高度", 1, ih - int(cy), ih - int(cy))
            manual_crop = (int(cx), int(cy), int(cw), int(ch))
        show_thirds = st.checkbox("顯示三分線")

    elif crop_mode == "拉直":
        straighten_angle = st.slider("旋轉角度", -15.0, 15.0, 0.0, 0.1)

# ── Main area ────────────────────────────────────────────────────────────────
if uploaded_file is None:
    st.markdown("## 請先在左側上傳照片 👈")
else:
    original = Image.open(uploaded_file)

    # Build effective params
    base_params = dict(presets[selected])
    if parsed is not None:
        effective_params = merge_preset_with_delta(base_params, parsed)
    else:
        effective_params = base_params

    processed = process_image(original, effective_params)

    # Apply crop / straighten
    if crop_mode == "比例裁切" and crop_ratio:
        processed = crop_to_ratio(processed, crop_ratio)
        original_display = crop_to_ratio(original, crop_ratio)
    elif crop_mode == "手動裁切" and manual_crop:
        x, y, w, h = manual_crop
        processed = apply_manual_crop(processed, x, y, w, h)
        original_display = apply_manual_crop(original, x, y, w, h)
    elif crop_mode == "拉直" and straighten_angle != 0:
        processed = apply_straighten(processed, straighten_angle)
        original_display = apply_straighten(original, straighten_angle)
    else:
        original_display = original

    # ── Preview ──
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**原圖**")
        st.image(original_display, use_container_width=True)
        if show_thirds:
            st.caption("─ 三分線（左側為原圖參考）")
    with col2:
        label = selected
        if parsed and parsed.style_tags:
            label += f" + {', '.join(parsed.style_tags)}"
        st.markdown(f"**{label}**")
        st.image(processed, use_container_width=True)
        if show_thirds:
            w, h = processed.size
            st.caption(f"三分點：({w//3}, {h//3})、({w*2//3}, {h//3})、({w//3}, {h*2//3})、({w*2//3}, {h*2//3})")

    # ── Download ──
    buf = io.BytesIO()
    processed.save(buf, format="JPEG", quality=95)
    buf.seek(0)
    fname = f"{selected.lower().replace(' ', '_')}"
    if parsed and parsed.style_tags:
        fname += "_" + "_".join(parsed.style_tags)
    st.download_button(
        label="⬇️ 下載調色後照片",
        data=buf,
        file_name=f"{fname}.jpg",
        mime="image/jpeg",
    )

    # ── Info panel ──
    with st.expander("查看套用的參數"):
        display_params = {k: v for k, v in effective_params.items() if v not in (None, 0, [], {})}
        st.json(display_params)
