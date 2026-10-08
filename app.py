import os
import time
import subprocess
import streamlit as st
from pathlib import Path
from google import genai
from google.genai import types
from schemas.question_schema import ExamPaper

st.set_page_config(page_title="入試解答用紙ジェネレーター", page_icon="📝", layout="centered")

st.title("📝 大学入試 解答用紙ジェネレーター")
st.write("過去問PDFをアップロードすると、AIが設問構成を解析してB4サイズの解答用紙を自動生成します。")

# サイドバー設定
with st.sidebar:
    st.header("⚙️ 設定")
    default_key = os.environ.get("GEMINI_API_KEY", "")
    input_api_key = st.text_input("Gemini API Key", value=default_key, type="password")
    
    # 利用可能な現行モデルから選択
    selected_model = st.selectbox(
        "使用モデル",
        options=["gemini-3.8-flash", "gemini-3.5-flash-lite"],
        index=0
    )
    st.caption("※片方でクォータ上限（429）が出た場合、もう一方に切り替えると通る場合があります。")

uploaded_file = st.file_uploader("過去問PDFを選択またはドラッグ＆ドロップしてください", type=["pdf"])

if uploaded_file is not None:
    st.success(f"アップロード完了: {uploaded_file.name}")
    
    if st.button("🚀 解答用紙を生成する", type="primary"):
        api_key = input_api_key.strip()
        if not api_key:
            st.error("サイドバーに Gemini API キーを入力してください。")
            st.stop()

        progress_text = st.empty()
        progress_bar = st.progress(0)

        try:
            progress_text.text("1/3: PDFデータを読み込み中...")
            progress_bar.progress(20)
            pdf_bytes = uploaded_file.read()

            progress_text.text(f"2/3: AI ({selected_model}) が設問構造を解析中...")
            progress_bar.progress(50)

            client = genai.Client(api_key=api_key)
            prompt = """
あなたは大学入試の解答用紙を設計する組版の専門家です。
提供された問題PDFから、解答欄のレイアウトに必要な枠構造「のみ」を正確に抽出してください。

【最重要判定ルール】
1. 解答用紙には問題文や指示文は一切不要です（instructionは空文字にしてください）。
2. 小問番号（q_number）は「問1」「問2」「(1)」のように番号のみを抽出してください。
3. 解答欄形式（q_type）の選定：
   - table_fill: 選択肢（1〜4、A〜D、ア〜エ等）から選ぶ記号問題、空欄補充記号
   - word_fill: 本文から英単語や短いフレーズを抜き出して書く短答記述
   - char_grid: 「○字以内」「○字程度」の日本語記述（chars_limitに制限文字数を設定）
   - lined_box: 英文和訳、下線部説明、自由英作文（line_countに行数を設定。和訳は2〜3行、自由英作文は12〜15行程度）
   - reorder: 語句整序で「3番目」「7番目」などを書かせる場合（targetsに設定）
"""

            max_retries = 3
            response = None
            for attempt in range(1, max_retries + 1):
                try:
                    response = client.models.generate_content(
                        model=selected_model,
                        contents=[
                            types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
                            prompt
                        ],
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            response_schema=ExamPaper,
                            temperature=0.1,
                        ),
                    )
                    break
                except Exception as e:
                    err_msg = str(e)
                    if "503" in err_msg or "UNAVAILABLE" in err_msg:
                        if attempt < max_retries:
                            time.sleep(attempt * 4)
                            continue
                    raise e

            exam = ExamPaper.model_validate_json(response.text)

            # 解析結果を保存（次回以降のバックアップ用）
            with open("parsed_exam.json", "w", encoding="utf-8") as f:
                f.write(exam.model_dump_json(indent=2))

            progress_text.text("3/3: B4レイアウトを組版中...")
            progress_bar.progress(80)

            lines = [
                '#import "components/components.typ": *',
                "",
                '#set page(paper: "jis-b4", flipped: true, margin: (x: 18mm, top: 14mm, bottom: 14mm))',
                '#set text(font: ("Noto Sans CJK JP", "Yu Gothic"), lang: "ja", size: 9.5pt)',
                "",
            ]

            for i, sec in enumerate(exam.sections):
                if i > 0:
                    lines.append("#pagebreak()")

                lines.extend([
                    "#grid(",
                    "  columns: (1fr, auto),",
                    "  align: (left + horizon, right + horizon),",
                    f'  text(size: 13pt, weight: "bold")[{exam.year} {exam.university} {exam.subject} 解答用紙 【{sec.big_number}】],',
                    '  table(',
                    '    columns: (55pt, 85pt),',
                    '    rows: (20pt,),',
                    '    align: center + horizon,',
                    '    stroke: 0.5pt + luma(80),',
                    '    [受験番号], []',
                    '  )',
                    ")",
                    "#v(3pt)",
                    "#line(length: 100%, stroke: 0.8pt)",
                    "#v(10pt)",
                    "",
                    "// 2段組（左右均等レイアウト）",
                    "#columns(2, gutter: 16mm)[",
                ])

                for q in sec.questions:
                    lines.append(f'  #text(weight: "bold", size: 10pt)[【{q.q_number}】]')
                    lines.append("  #v(2pt)")

                    if q.q_type == "char_grid":
                        c = q.chars_limit or 100
                        lines.append(f"  #char-grid(chars: {c})")
                    elif q.q_type in ["lined_box", "free_box"]:
                        ln = q.line_count or 12
                        lines.append(f"  #lined-box(lines: {ln})")
                    elif q.q_type == "reorder":
                        targets = q.targets or ["3番目", "7番目"]
                        arr = ", ".join([f'"{t}"' for t in targets])
                        lines.append(f"  #reorder-box(targets: ({arr},))")
                    elif q.q_type == "table_fill":
                        symbols = q.symbols or ["(1)", "(2)", "(3)", "(4)"]
                        arr = ", ".join([f'"{s}"' for s in symbols])
                        lines.append(f"  #symbol-table(symbols: ({arr},))")
                    elif q.q_type == "word_fill":
                        symbols = q.symbols or ["(1)", "(2)"]
                        arr = ", ".join([f'"{s}"' for s in symbols])
                        lines.append(f"  #word-box(symbols: ({arr},))")

                    lines.append("  #v(10pt)")

                lines.append("]")
                lines.append("")

            typst_code = "\n".join(lines)
            typ_path = "web_output.typ"
            pdf_path = "web_output.pdf"

            with open(typ_path, "w", encoding="utf-8") as f:
                f.write(typst_code)

            res = subprocess.run(
                f'typst compile "{typ_path}" "{pdf_path}"',
                shell=True,
                capture_output=True,
                encoding="utf-8",
                errors="replace"
            )

            if res.returncode != 0:
                st.error(f"Typstコンパイルエラー:\n{res.stderr}")
                st.stop()

            with open(pdf_path, "rb") as f:
                result_pdf_bytes = f.read()

            progress_bar.progress(100)
            progress_text.text("✨ 解答用紙の生成が完了しました！")
            st.balloons()

            st.download_button(
                label="📥 B4解答用紙PDFをダウンロード",
                data=result_pdf_bytes,
                file_name=f"{exam.university}_{exam.subject}_解答用紙.pdf",
                mime="application/pdf",
                type="primary"
            )

        except Exception as e:
            st.error(f"エラーが発生しました: {e}")

