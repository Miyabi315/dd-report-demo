import streamlit as st
from dotenv import load_dotenv
import os
import fitz  # PyMuPDF
import openai
from openai import OpenAI

# .envからAPIキー読み込み
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


from openai import OpenAI

def summarize_business_section(text, custom_topic=None):
    prompt = f"""
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

    client = OpenAI()
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "あなたはプロのアナリストです。"},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3
    )

    return response.choices[0].message.content.strip()

def generate_report_md(company_name, business_summary, financial_summary=None, custom_topic=None):
    lines = []
    lines.append(f"# DDレポート：{company_name if company_name else '企業名未入力'}\n")

    lines.append("## 事業要約")
    lines.append(business_summary.strip() + "\n")

    if financial_summary:
        lines.append("## 財務要約")
        lines.append(financial_summary.strip() + "\n")

    if custom_topic:
        lines.append(f"## 観点：{custom_topic}")
        lines.append("*（この観点で要約を追加しました）*\n")

    return "\n".join(lines)

def summarize_financial_section(text):
    prompt = f"""
以下の企業IR資料から、財務情報に関する要点を箇条書きで抽出してください。
・売上・利益などの数値（可能な限り具体的に）
・セグメント構成
・成長率・その要因
・特筆すべき財務トピック（減益／黒字化／構造改革など）
・誤情報を避け、判断できない情報は「不明」と記載してください

### IR資料本文：
{text[:3000]}
"""

    client = OpenAI()
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "あなたは財務アナリストです。"},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3
    )

    return response.choices[0].message.content.strip()


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
        # 1. テキスト抽出
        extracted_text = extract_text_from_pdf(uploaded_pdf)
        st.success(f"✅ {uploaded_pdf.name} を読み取りました")
        st.text_area("抽出テキスト（冒頭1000文字）", extracted_text[:1000], height=300)

        # 2. GPT 事業要約
        with st.spinner("GPTで事業要約中..."):
            summary = summarize_business_section(
                text=extracted_text,
                custom_topic=custom_topic if custom_topic else None
            )
            st.subheader("📝 事業要約")
            st.markdown(summary)

        # 3. GPT 財務要約（任意）
        fin_summary = None
        if include_financials:
            with st.spinner("GPTで財務要約中..."):
                fin_summary = summarize_financial_section(extracted_text)
                st.subheader("💰 財務要約")
                st.markdown(fin_summary)

        # 4. Markdownレポート生成
        report_md = generate_report_md(
            company_name=company_name,
            business_summary=summary,
            financial_summary=fin_summary,
            custom_topic=custom_topic
        )

        st.subheader("📄 生成レポート（Markdown）")
        st.code(report_md, language="markdown")

        # 5. ダウンロードボタン
        st.download_button(
            label="📥 Markdownレポートをダウンロード",
            data=report_md,
            file_name=f"{company_name or 'dd-report'}.md",
            mime="text/markdown"
        )

    elif company_name:
        st.warning("⚠️ 現時点では企業名からのIR取得は未対応です。PDFをアップロードしてください。")
    else:
        st.error("❌ PDFまたは企業名を入力してください。")