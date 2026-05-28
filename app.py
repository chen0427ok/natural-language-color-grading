import io
import json

import streamlit as st
from PIL import Image

from processor import process_image

st.set_page_config(page_title="Photo Coloring", layout="wide", page_icon="🎨")


@st.cache_data
def load_presets():
    with open("presets.json", "r", encoding="utf-8") as f:
        return json.load(f)


presets = load_presets()

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

if uploaded_file is None:
    st.markdown("## 請先在左側上傳照片 👈")
else:
    original = Image.open(uploaded_file)
    processed = process_image(original, presets[selected])

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**原圖**")
        st.image(original, use_container_width=True)
    with col2:
        st.markdown(f"**{selected}**")
        st.image(processed, use_container_width=True)

    buf = io.BytesIO()
    processed.save(buf, format="JPEG", quality=95)
    buf.seek(0)

    st.download_button(
        label="⬇️ 下載調色後照片",
        data=buf,
        file_name=f"{selected.lower().replace(' ', '_')}.jpg",
        mime="image/jpeg",
    )
