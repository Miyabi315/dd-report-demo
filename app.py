# app.py - Step 1: UI base

import streamlit as st
from dotenv import load_dotenv
import os

# .envからAPIキー読み込み（まだ未使用）
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

st.set_page_config(page_title="DDレポート生成", layout="centered")
st.title("📊 DDレポート自動生成アプリ（ベータ版）")

# 入力セクション
st.subheader("① 企業情報の入力")

company_name = st.text_input("企業名を入力（例：ソニー株式会社）")
uploaded_pdf = st.file_uploader("またはIR資料（PDF）をアップロード", type=["pdf"])

# オプション
st.subheader("② オプション設定")
include_financials = st.checkbox("財務情報も含める（上場企業のみ）", value=True)
custom_topic = st.text_input("追加の観点（例：AI活用、ESG、海外展開）")

# 実行ボタン
st.subheader("③ レポート生成")
if st.button("要約を開始"):
    st.info("📝 この時点では要約処理は未実装です。次ステップで追加します。")
    st.write("企業名：", company_name)
    st.write("財務情報含む？：", include_financials)
    st.write("追加観点：", custom_topic)
    if uploaded_pdf:
        st.success(f"PDFファイル {uploaded_pdf.name} がアップロードされました。")