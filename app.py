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

# OpenAI client
client = OpenAI()

# セッション状態初期化
if "step" not in st.session_state:
    st.session_state.step = "menu"
if "pdf_bytes" not in st.session_state:
    st.session_state.pdf_bytes = None
if "extracted_text" not in st.session_state:
    st.session_state.extracted_text = ""
if "pdf_urls" not in st.session_state:
    st.session_state.pdf_urls = []

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
    doc = fitz.open(stream=pdf_file, filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    return text

# 要約プロンプト作成関数
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
    prompt += "\n\n### IR資料本文：\n" + text

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "あなたはプロのアナリストです。"},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3
    )
    return response.choices[0].message.content.strip()

def summarize_financial_section(text):
    prompt = """
以下の企業IR資料から、財務情報に関する要点を箇条書きで抽出してください。
・売上・利益などの数値（可能な限り具体的に）
・セグメント構成
・成長率・その要因
・特筆すべき財務トピック（減益／黒字化／構造改革など）
・誤情報を避け、判断できない情報は「不明」と記載してください

### IR資料本文：
""" + text

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "あなたは財務アナリストです。"},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3
    )
    return response.choices[0].message.content.strip()

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


# --- UI構成 ---
st.set_page_config(page_title="DDレポート生成", layout="centered")
st.title("📊 DDレポート自動生成アプリ")

# --- メニュー切り替え ---
st.subheader("ステップを選んでください")
col1, col2 = st.tabs(["🔍 企業名から検索", "📤 PDFアップロード"])
with col1:
    if st.button("企業名から検索"):
        st.session_state.step = "input"
with col2:
    if st.button("PDFをアップロード"):
        st.session_state.step = "upload"
        
LOG_FILE = "log_reports.txt"
with st.sidebar:
    # --- セッション状態の初期化 ---
    if "log_reports" not in st.session_state:
        st.session_state.log_reports = []

        # ログファイルが存在すれば読み込み
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                logs = f.read().split("\n===END===\n")
                st.session_state.log_reports = [log for log in logs if log.strip()]
                
    with st.sidebar:
        st.markdown("### 🕒 レポートログ")

        if "expanded_log_index" not in st.session_state:
            st.session_state.expanded_log_index = None

        for i, log in enumerate(st.session_state.log_reports):
            st.markdown(f"**{i+1}. レポート抜粋**")

            # ログが展開表示されているかどうか
            if st.session_state.expanded_log_index == i:
                st.markdown(log)  # 全文表示
                if st.button("🔙 閉じる", key=f"close_{i}"):
                    st.session_state.expanded_log_index = None
            else:
                st.markdown(log[:50] + "...")
                if st.button("🔍 全文を見る", key=f"open_{i}"):
                    st.session_state.expanded_log_index = i

# --- 入力ステップ：企業名から検索 ---
if st.session_state.step == "input":
    company_name = st.text_input("企業名を入力", key="company_name_input")
    if st.button("IR資料を検索"):
        with st.spinner("PDFを検索中..."):
            st.session_state.pdf_urls = find_ir_pdfs(company_name)
            st.session_state.company_name = company_name  # セッションに保存
            st.session_state.step = "select"

# --- PDF選択 ---
if st.session_state.step == "select" and st.session_state.pdf_urls:
    selected_url = st.selectbox("PDFを選んでください", st.session_state.pdf_urls)
    if st.button("このPDFを使う"):
        pdf_bytes = download_pdf_content(selected_url)
        if pdf_bytes:
            st.session_state.pdf_bytes = pdf_bytes
            st.session_state.extracted_text = extract_text_from_pdf(pdf_bytes)
            st.session_state.step = "summary"
            st.success("✅ PDFを読み込みました")
        else:
            st.error("❌ PDFの取得に失敗")

# --- PDFアップロード ---
if st.session_state.step == "upload":
    uploaded_pdf = st.file_uploader("PDFをアップロード", type=["pdf"])
    if uploaded_pdf:
        st.session_state.pdf_bytes = uploaded_pdf
        st.session_state.extracted_text = extract_text_from_pdf(uploaded_pdf)
        st.session_state.company_name = "アップロード資料"  # 名前が未入力の場合の仮名
        st.session_state.step = "summary"
        st.success(f"✅ {uploaded_pdf.name} を読み取りました")

# --- レポート生成 ---
if st.session_state.step == "summary" and st.session_state.extracted_text:
    st.subheader("② オプション設定")
    col1, col2 = st.columns([1, 2])
    with col1:
        include_financials = st.checkbox("財務情報も含める", value=True)
    with col2:
        custom_topics_raw = st.text_input("追加観点（カンマ区切り）")
        custom_topics = [t.strip() for t in custom_topics_raw.split(",") if t.strip()]

    if st.button("要約を開始"):
        text = st.session_state.extracted_text
        print("抽出テキスト（冒頭1000文字）", text)

        with st.spinner("GPTで事業要約中..."):
            business_summary = summarize_business_section(text)
            st.subheader("📝 事業要約")
            st.markdown(business_summary)

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

        financial_summary = None
        if include_financials:
            with st.spinner("GPTで財務要約中..."):
                financial_summary = summarize_financial_section(text)
                st.subheader("💰 財務要約")
                st.markdown(financial_summary)

        report_md = generate_report_md(
            st.session_state.get("company_name", "企業名未入力"),
            business_summary,
            financial_summary,
            custom_summaries
        )

        # 保存処理
        st.session_state.final_report = report_md
        if report_md:
            if len(st.session_state.log_reports) == 0 or st.session_state.log_reports[-1] != report_md:
                # ログをセッションに追加
                st.session_state.log_reports.append(report_md)

        # テキストファイルに追記保存
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(report_md.strip() + "\n===END===\n")

        # 出力処理
        st.subheader("📄 生成レポート")
        st.code(report_md, language="markdown")
        st.download_button("📥 レポートをダウンロード", report_md, file_name=f"{st.session_state.get('company_name', 'report')}.md", mime="text/markdown")