import streamlit as st
from dotenv import load_dotenv
import os
import fitz  # PyMuPDF

# .envからAPIキー読み込み
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

st.set_page_config(page_title="DDレポート生成", layout="centered")
st.title("📊 DDレポート自動生成アプリ")

# --- 企業情報入力 ---
st.subheader("① 企業情報の入力")
company_name = st.text_input("企業名を入力")
uploaded_pdf = st.file_uploader("またはIR資料（PDF）をアップロード", type=["pdf"])

# --- オプションを横並び ---
st.subheader("② オプション設定")
col1, col2 = st.columns([1, 2])
with col1:
    include_financials = st.checkbox("財務情報も含める", value=True)
with col2:
    custom_topic = st.text_input("追加観点（AI活用、ESGなど）")

# --- PDFテキスト抽出関数 ---
def extract_text_from_pdf(uploaded_file):
    with fitz.open(stream=uploaded_file.read(), filetype="pdf") as doc:
        text = ""
        for page in doc:
            text += page.get_text()
    return text

# --- レポート生成ボタン ---
st.subheader("③ レポート生成")
if st.button("要約を開始"):
    if uploaded_pdf:
        extracted_text = extract_text_from_pdf(uploaded_pdf)
        st.success(f"✅ {uploaded_pdf.name} を読み取りました")
        st.text_area("抽出テキスト（冒頭1000文字）", extracted_text[:1000], height=300)
    elif company_name:
        st.warning("⚠️ 現時点では企業名からのIR取得は未対応です。PDFをアップロードしてください。")
    else:
        st.error("❌ PDFまたは企業名を入力してください。")