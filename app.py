import os
import time
import subprocess
import streamlit as st
from google import genai
from google.genai import types
from schemas.question_schema import ExamPaper

st.set_page_config(page_title="入試解答用紙ジェネレーター", page_icon="📝", layout="centered")

st.title("📝 大学入試 解答用紙ジェネレーター")
st.write("過去問PDFから本番さながらの解答用紙（英語・国語）を自動生成します。")

with st.sidebar:
    st.header("⚙️ 設定")
    default_key = os.environ.get("GEMINI_API_KEY", "")
    input_api_key = st.text_input("Gemini API Key", value=default_key, type="password")
    selected_model = st.selectbox(
        "使用モデル",
        options=["gemini-2.5-flash", "gemini-2.0-flash"],
        index=0
    )
    st.caption("※2026年現在の高精度安定版モデルを使用しています。")

uploaded_file = st.file_uploader("過去問PDFをアップロードしてください", type=["pdf"])

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
            progress_text.text("1/3: PDFデータを解析準備中...")
            progress_bar.progress(20)
            pdf_bytes = uploaded_file.read()

            progress_text.text(f"2/3: AI ({selected_model}) が設問構成を精密分析中...")
            progress_bar.progress(50)

            client = genai.Client(api_key=api_key)
            prompt = """
あなたは大学入試の解答用紙を設計する組版の専門家です。
問題PDFから科目（英語/国語）を特定し、解答欄のレイアウトに必要な枠構造「のみ」を漏れなく正確に抽出してください。

【重要指示】
1. 科目（subject）: "英語" または "国語"
2. 小問・枝問の完全分離:
   - 1つの問いの中に複数の解答欄がある場合（例: 問い二に「イ」「ロ」がある、問い一に「A〜Eの漢字」がある等）、必ず独立したQuestion要素として分割してください。
   - q_number の表記: 「問一」「問二 (イ)」「問二 (ロ)」「問三」のように統一。
3. 国語の解答欄タイプの厳密判定:
   - 「○字以内」「○字程度」とある論述問題: q_type="char_grid", chars_limit に数値を設定（例: 30, 50, 60, 100）。
   - 漢字書き取り、語句の抜き出し・短答: q_type="word_fill", symbols に ["A", "B", "C", "D", "E"] や ["ア", "イ"] などの記号リストを設定。
   - 字数指定のない説明・現代語訳・心情説明: q_type="lined_box", line_count に行数（2〜4）を設定。
4. instruction（指示文）は解答用紙には不要なため、すべて空文字（""）にしてください。
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

            progress_text.text("3/3: 洗練されたB4解答用紙を組版中...")
            progress_bar.progress(80)

            is_kokugo = ("国語" in exam.subject)

            lines = [
                '#import "components/components.typ": *',
                "",
                '#set page(',
                '  paper: "jis-b4",',
                '  flipped: true,',
                '  margin: (x: 16mm, top: 12mm, bottom: 12mm),',
                '  header: locate(loc => {',
                '    let page-num = counter(page).at(loc).first()',
                '    align(right)[#text(size: 8.5pt, fill: luma(100))[その #page-num]]',
                '  })',
                ')',
                '#set text(font: ("Noto Serif CJK JP", "Noto Sans CJK JP", "IPAexGothic", "IPAGothic", "Yu Gothic"), lang: "ja", size: 9.5pt)',
                "",
            ]

            for i, sec in enumerate(exam.sections):
                if i > 0:
                    lines.append("#pagebreak()")

                lines.extend([
                    "// ヘッダー情報",
                    "#grid(",
                    "  columns: (1fr, auto),",
                    "  align: (left + horizon, right + horizon),",
                    f'  text(size: 14pt, weight: "bold")[{exam.year} {exam.university} {exam.subject} 解答用紙 【{sec.big_number}】],',
                    '  table(',
                    '    columns: (60pt, 90pt),',
                    '    rows: (22pt,),',
                    '    align: center + horizon,',
                    '    stroke: 0.6pt + luma(80),',
                    '    [受験番号], []',
                    '  )',
                    ")",
                    "#v(4pt)",
                    "#line(length: 100%, stroke: 1.2pt)",
                    "#v(14pt)",
                    "",
                ])

                if is_kokugo:
                    # 国語: 右から左へ流れる本番仕様の水平スタック配置
                    lines.append("#align(right)[")
                    lines.append("  #stack(")
                    lines.append("    dir: ltr,")
                    lines.append("    spacing: 12mm,")

                    # 右から問一、問二と並べるため逆順でスタックに投入
                    for q in reversed(sec.questions):
                        lines.append("    block(breakable: false)[")
                        lines.append(f'      #align(center)[#text(weight: "bold", size: 10.5pt)[【{q.q_number}】]]')
                        lines.append("      #v(6pt)")

                        if q.q_type == "char_grid":
                            c = q.chars_limit or 60
                            lines.append(f"      #vertical-grid(chars: {c})")

                        elif q.q_type in ["lined_box", "free_box"]:
                            ln = q.line_count or 3
                            lines.append(f"      #vertical-free-box(columns-count: {ln})")

                        elif q.q_type == "word_fill":
                            symbols = q.symbols or ["A", "B", "C", "D", "E"]
                            arr = ", ".join([f'"{s}"' for s in symbols])
                            lines.append(f"      #kanji-box(symbols: ({arr},))")

                        elif q.q_type == "table_fill":
                            symbols = q.symbols or ["(1)", "(2)", "(3)"]
                            arr = ", ".join([f'"{s}"' for s in symbols])
                            lines.append(f"      #symbol-table(symbols: ({arr},))")

                        lines.append("    ],")

                    lines.append("  )")
                    lines.append("]")

                else:
                    # 英語: 見やすい2段組レイアウト
                    lines.append("#columns(2, gutter: 16mm)[")
                    for q in sec.questions:
                        lines.append("  #block(breakable: false)[")
                        lines.append(f'    #text(weight: "bold", size: 10pt)[【{q.q_number}】]')
                        lines.append("    #v(3pt)")

                        if q.q_type == "char_grid":
                            c = q.chars_limit or 100
                            lines.append(f"    #char-grid(chars: {c})")
                        elif q.q_type in ["lined_box", "free_box"]:
                            ln = q.line_count or 10
                            lines.append(f"    #lined-box(lines: {ln})")
                        elif q.q_type == "reorder":
                            targets = q.targets or ["3番目", "7番目"]
                            arr = ", ".join([f'"{t}"' for t in targets])
                            lines.append(f"    #reorder-box(targets: ({arr},))")
                        elif q.q_type == "table_fill":
                            symbols = q.symbols or ["(1)", "(2)", "(3)", "(4)"]
                            arr = ", ".join([f'"{s}"' for s in symbols])
                            lines.append(f"    #symbol-table(symbols: ({arr},))")
                        elif q.q_type == "word_fill":
                            symbols = q.symbols or ["(1)", "(2)"]
                            arr = ", ".join([f'"{s}"' for s in symbols])
                            lines.append(f"    #word-box(symbols: ({arr},))")

                        lines.append("    #v(14pt)")
                        lines.append("  ]")
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
            progress_text.text("✨ 本番仕様の解答用紙が完成しました！")
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
