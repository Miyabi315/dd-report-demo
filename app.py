import streamlit as st
from dotenv import load_dotenv
import os
import fitz  # PyMuPDF
import openai
from openai import OpenAI
from googlesearch import search
import requests
from io import BytesIO

# .envからAPIキー読み込み
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI()

# セッション状態初期化
if "pdf_bytes" not in st.session_state:
    st.session_state.pdf_bytes = None
if "extracted_text" not in st.session_state:
    st.session_state.extracted_text = ""

# PDF検索関数
def find_ir_pdfs(company_name, max_results=5):
    query = f"{company_name} IR PDF site:.co.jp"
    urls = []
    for url in search(query, num_results=10):
        if url.lower().endswith(".pdf"):
            urls.append(url)
        if len(urls) >= max_results:
            break
    return urls

# PDFダウンロード関数
def download_pdf_content(url):
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return BytesIO(response.content)
    except Exception:
        return None

# PDFテキスト抽出関数
def extract_text_from_pdf(pdf_file):
    text = ""
    with fitz.open(stream=pdf_file, filetype="pdf") as doc:
        for page in doc:
            text += page.get_text()
    return text

# 要約関数（事業要約）
def summarize_business_section(text, custom_topic=None):
    prompt = """
以下の企業IR資料から、事業の要点を以下の観点で箇条書きで抽出してください。
・主力サービス／製品
・提供先（顧客層）
・ビジネスモデル
・競合他社
・その他特徴的な点
"""
    if custom_topic:
        prompt += f"\n・追加観点（{custom_topic}）も含めてください"
    prompt += "\n\n### IR資料本文：\n" + text[:3000]

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "あなたはプロのアナリストです。"},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3
    )
    return response.choices[0].message.content.strip()

# 要約関数（財務要約）
def summarize_financial_section(text):
    prompt = """
以下の企業IR資料から、財務情報に関する要点を箇条書きで抽出してください。
・売上・利益などの数値（可能な限り具体的に）
・セグメント構成
・成長率・その要因
・特筆すべき財務トピック（減益／黒字化／構造改革など）
・誤情報を避け、判断できない情報は「不明」と記載してください

### IR資料本文：
""" + text[:3000]

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "あなたは財務アナリストです。"},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3
    )
    return response.choices[0].message.content.strip()

# Markdownレポート生成関数
def generate_report_md(company_name, business_summary, financial_summary=None, custom_summaries=None):
    lines = [f"# DDレポート：{company_name}\n"]
    lines.append("## 事業要約")
    lines.append(business_summary + "\n")
    if financial_summary:
        lines.append("## 財務要約")
        lines.append(financial_summary + "\n")
    if custom_summaries:
        for topic, summary in custom_summaries.items():
            lines.append(f"## 観点：{topic}")
            lines.append(summary + "\n")
    return "\n".join(lines)

# --- Streamlit UI ---
st.set_page_config(page_title="DDレポート生成", layout="centered")
st.title("📊 DDレポート自動生成アプリ")

# ① 企業情報の入力
st.subheader("① 企業情報の入力")
company_name = st.text_input("企業名を入力")

if company_name and st.button("IR資料を検索して読み込む"):
    with st.spinner("PDFを検索中..."):
        pdf_urls = find_ir_pdfs(company_name)

    if pdf_urls:
        selected_url = pdf_urls[0]  # 最初のPDFを自動選択
        pdf_bytes = download_pdf_content(selected_url)
        if pdf_bytes:
            try:
                extracted_text = extract_text_from_pdf(pdf_bytes)
                st.session_state.pdf_bytes = pdf_bytes
                st.session_state.extracted_text = extracted_text
                st.session_state.selected_url = selected_url
                st.success(f"✅ PDFを読み込みました：{selected_url}")
                st.text_area("抽出テキスト（冒頭1000文字）", extracted_text[:1000], height=300)
            except Exception as e:
                st.error(f"❌ テキスト抽出中にエラーが発生しました：{e}")
        else:
            st.error("❌ PDFのダウンロードに失敗しました")
    else:
        st.warning("⚠️ PDFが見つかりませんでした")

# またはPDFアップロード
uploaded_pdf = st.file_uploader("またはPDFをアップロード", type=["pdf"])
if uploaded_pdf:
    st.session_state.pdf_bytes = uploaded_pdf
    st.session_state.extracted_text = extract_text_from_pdf(uploaded_pdf)
    st.success(f"✅ {uploaded_pdf.name} を読み取りました")

# ② オプション設定
st.subheader("② オプション設定")
col1, col2 = st.columns([1, 2])
with col1:
    include_financials = st.checkbox("財務情報も含める", value=True)
with col2:
    custom_topics_raw = st.text_input("追加観点（カンマ区切り）")
    custom_topics = [t.strip() for t in custom_topics_raw.split(",") if t.strip()]

# ③ レポート生成
st.subheader("③ レポート生成")
if st.button("要約を開始"):
    if st.session_state.extracted_text:
        text = st.session_state.extracted_text
        st.text_area("抽出テキスト（冒頭1000文字）", text[:1000], height=300)

        # 事業要約
        with st.spinner("GPTで事業要約中..."):
            business_summary = summarize_business_section(text)
            st.subheader("📝 事業要約")
            st.markdown(business_summary)

        # カスタム観点の要約
        custom_summaries = {}
        for topic in custom_topics:
            with st.spinner(f"GPTで「{topic}」観点の要約中..."):
                try:
                    result = summarize_business_section(text, custom_topic=topic)
                    custom_summaries[topic] = result
                except Exception as e:
                    custom_summaries[topic] = f"（エラー：{e}）"

        for topic, content in custom_summaries.items():
            st.subheader(f"🔍 観点：{topic}")
            st.markdown(content)

        # 財務要約
        financial_summary = None
        if include_financials:
            with st.spinner("GPTで財務要約中..."):
                financial_summary = summarize_financial_section(text)
                st.subheader("💰 財務要約")
                st.markdown(financial_summary)

        # レポート出力
        report_md = generate_report_md(company_name, business_summary, financial_summary, custom_summaries)
        st.subheader("📄 生成レポート")
        st.code(report_md, language="markdown")
        st.download_button("📥 レポートをダウンロード", report_md, file_name=f"{company_name}.md", mime="text/markdown")
    else:
        st.error("PDFの読み取りに失敗しました。ファイルをアップロードまたは選択してください。")
