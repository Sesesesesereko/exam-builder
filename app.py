import os
import time
import subprocess
import streamlit as st
from google import genai
from google.genai import types
from schemas.question_schema import ExamPaper

GOOGLE_FORM_URL = "https://forms.gle/"

st.set_page_config(
    page_title="入試解答用紙ジェネレーター",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    .block-container { padding-top: 2rem; padding-bottom: 2rem; max-width: 860px; }
    .header-box { text-align: center; margin-bottom: 1.8rem; }
    .header-title { font-size: 2.1rem; font-weight: 800; color: #1e293b; margin-bottom: 0.4rem; }
    .header-sub { font-size: 1rem; color: #64748b; }
    div[data-testid="stFileUploader"] { margin-bottom: 1.2rem; border: 2px dashed #cbd5e1; border-radius: 12px; padding: 10px; }
    .stButton>button { width: 100%; border-radius: 10px; height: 3.4rem; font-weight: bold; font-size: 1.15rem; background: linear-gradient(135deg, #2563eb, #1d4ed8); color: white; border: none; }
    .feedback-box { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 1.2rem; margin-top: 2rem; text-align: center; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="header-box">
    <div class="header-title">📝 入試解答用紙ジェネレーター</div>
    <div class="header-sub">問題PDFから入試本番仕様のB4解答用紙を自動組版します。</div>
</div>
""", unsafe_allow_html=True)

selected_subject = st.radio(
    "科目を選択してください",
    options=["英語", "国語", "数学", "地歴・社会", "理科"],
    horizontal=True
)

uploaded_file = st.file_uploader("問題PDFをアップロード", type=["pdf"])

if uploaded_file is not None:
    st.success(f"📎 読み込み完了: {uploaded_file.name}")
    
    if st.button("🚀 解答用紙を生成する"):
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            st.error("システムエラー: APIキーが設定されていません。管理者に連絡してください。")
            st.stop()

        progress_text = st.empty()
        progress_bar = st.progress(0)

        try:
            progress_text.text("1/3: PDFデータを解析中...")
            progress_bar.progress(20)
            pdf_bytes = uploaded_file.read()

            progress_text.text("2/3: 設問構造を抽出中...")
            progress_bar.progress(50)

            client = genai.Client(api_key=api_key)

            if selected_subject == "数学":
                prompt = """
あなたは大学入試の解答用紙を設計する組版専門家です。
問題PDFから、各大問（第1問、第2問など）の番号とタイトルのみを抽出してください。
PDFの表紙や問題文に明記されていない場合、universityは空文字、yearは空文字にしてください。推測で補完してはいけません。
各セクションの questions には、q_number="解答欄", q_type="math_box" の要素を1つだけ含めてください。
"""
            elif selected_subject == "国語":
                prompt = """
あなたは大学入試の国語解答用紙を設計する専門家です。
問題PDFに存在する各大問・各小問を、問題の掲載順通りに一問も漏らさず正確に抽出してください。
PDFに大学名や年度が明記されていない場合、universityは空文字、yearは空文字にしてください。勝手に推測してはいけません。

【厳格ルール】
1. 小問の完全網羅: 問一、問二、問三…を絶対に省略・合算しないでください。
2. 小問内に複数の解答箇所がある場合:
   - 記号選択なら symbols に ["(1)", "(2)", "(3)"] などを設定。
   - 漢字書き取りなら symbols に ["A", "B", "C", "D", "E"] や ["ア", "イ"] などを設定。
3. 解答タイプの選定:
   - 「○字以内」「○字程度」の記述: q_type="char_grid", chars_limit に字数を設定。
   - 漢字書き取り: q_type="word_fill", symbols に記号一覧。
   - 記号選択: q_type="table_fill", symbols に記号一覧。
   - 字数指定のない説明・現代語訳・心情説明: q_type="free_box", line_count に行数（2〜3行）を設定。
4. instructionは空文字にしてください。
"""
            else:
                prompt = f"""
あなたは大学入試の解答用紙を設計する専門家です。
提供された問題PDFから、{selected_subject}の設問構造を一問も漏らさず正確に抽出してください。
PDFに大学名や年度が明記されていない場合、universityは空文字、yearは空文字にしてください。推測で補完してはいけません。
【ルール】
1. 小問・枝問は省略せず抽出してください。
2. 字数制限のある記述は q_type="char_grid", chars_limit に数値を設定。
3. 語句整序は q_type="reorder", targets に指定位置を設定。
4. 選択肢記号問題は q_type="table_fill", symbols に小問記号を設定。
5. 単語短答は q_type="word_fill", symbols に小問記号を設定。
6. 説明・和訳・英作文は q_type="lined_box", line_count に行数を設定。
7. instructionは空文字にしてください。
"""

            response = client.models.generate_content(
                model="gemini-3.5-flash-lite",
                contents=[
                    types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
                    prompt
                ],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ExamPaper,
                    temperature=0.0,
                ),
            )

            exam = ExamPaper.model_validate_json(response.text)
            exam.subject = selected_subject

            progress_text.text("3/3: B4本番用紙を組版中...")
            progress_bar.progress(80)

            # 大学名・年度の厳密な判定（曖昧・推測・不明な場合は「  大学」「  年度」にする）
            raw_univ = (exam.university or "").strip()
            if not raw_univ or any(k in raw_univ.lower() for k in ["unknown", "令和", "大学", "未定", "none"]):
                # 正確な大学名が入っていない場合は手書き用スペース
                univ_display = "     大学"
            else:
                univ_display = f"{raw_univ}大学" if not raw_univ.endswith("大学") else raw_univ

            raw_year = (str(exam.year) if exam.year else "").strip()
            if not raw_year or any(k in raw_year.lower() for k in ["unknown", "none", "未定"]):
                year_display = "  年度"
            else:
                year_display = f"{raw_year}年度" if not raw_year.endswith("年度") else raw_year

            lines = [
                '#import "components/components.typ": *',
                "",
                '#set page(',
                '  paper: "jis-b4",',
                '  flipped: true,',
                '  margin: (x: 16mm, top: 10mm, bottom: 12mm)',
                ')',
                '#set text(font: ("Noto Serif CJK JP", "Noto Sans CJK JP", "IPAexGothic", "IPAGothic", "Yu Gothic"), lang: "ja", size: 9.5pt)',
                "",
            ]

            total_sheet_count = 0

            for sec in exam.sections:
                questions = sec.questions
                total_sheet_count += 1
                if total_sheet_count > 1:
                    lines.append("#pagebreak()")

                lines.extend([
                    "// 本番入試仕様ヘッダー",
                    "#grid(",
                    "  columns: (1fr, auto),",
                    "  gutter: 12pt,",
                    "  align: (left + top, right + top),",
                    "  [",
                    f'    #text(size: 13pt, weight: "bold")[{year_display} {univ_display} {exam.subject} 解答用紙 【{sec.big_number}】]',
                    "    #v(3pt)",
                    '    #text(size: 8pt)[学部：#box(width: 80pt, stroke: (bottom: 0.5pt + luma(80)))[] 日程：#box(width: 60pt, stroke: (bottom: 0.5pt + luma(80)))[] #text(size: 7.5pt, fill: luma(90))[（※印欄には何も記入してはならない。）]]',
                    "  ],",
                    "  [",
                    "    #table(",
                    "      columns: (45pt, 70pt, 35pt, 90pt, 45pt, 45pt),",
                    "      rows: (16pt, 26pt),",
                    "      stroke: 0.5pt + luma(80),",
                    "      align: center + horizon,",
                    '      table.cell(fill: luma(245))[受験番号], table.cell(rowspan: 2, fill: white)[],',
                    '      table.cell(fill: luma(245))[氏名], table.cell(rowspan: 2, fill: white)[],',
                    '      table.cell(fill: luma(235), colspan: 2)[※得点],',
                    '      table.cell(fill: white)[], table.cell(fill: white)[]',
                    "    )",
                    "  ]",
                    ")",
                    "#v(2pt)",
                    "#line(length: 100%, stroke: 1.2pt)",
                    "#v(10pt)",
                    "",
                ])

                if selected_subject == "国語":
                    lines.append("#align(right)[")
                    lines.append("  #stack(")
                    lines.append("    dir: ltr,")
                    lines.append("    spacing: 8.5mm,")

                    for q in reversed(questions):
                        lines.append("    block(breakable: false)[")
                        lines.append(f'      #align(center)[#text(weight: "bold", size: 9.5pt)[【{q.q_number}】]]')
                        lines.append("      #v(5pt)")

                        if q.q_type == "char_grid":
                            c = q.chars_limit or 60
                            lines.append(f"      #vertical-grid(chars: {c})")
                        elif q.q_type == "word_fill":
                            symbols = q.symbols or ["A", "B", "C", "D", "E"]
                            arr = ", ".join([f'"{s}"' for s in symbols])
                            lines.append(f"      #vertical-kanji-box(symbols: ({arr},))")
                        elif q.q_type == "table_fill":
                            symbols = q.symbols or ["(1)", "(2)", "(3)"]
                            arr = ", ".join([f'"{s}"' for s in symbols])
                            lines.append(f"      #vertical-symbol-box(symbols: ({arr},))")
                        else:
                            ln = q.line_count or 3
                            lines.append(f"      #vertical-free-box(columns-count: {ln})")

                        lines.append("    ],")

                    lines.append("  )")
                    lines.append("]")
                    lines.append("")

                elif selected_subject == "数学":
                    lines.append("  #math-calc-box(height-pt: 480pt, divided: true)")
                    lines.append("")

                else:
                    lines.append("#columns(2, gutter: 16mm)[")
                    for q in questions:
                        lines.append("  #block(breakable: false)[")
                        lines.append(f'    #text(weight: "bold", size: 10pt)[【{q.q_number}】]')
                        lines.append("    #v(3pt)")

                        if q.q_type == "char_grid":
                            c = q.chars_limit or 100
                            lines.append(f"    #char-grid(chars: {c})")
                        elif q.q_type in ["lined_box", "free_box"]:
                            ln = q.line_count or 6
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

                        lines.append("    #v(12pt)")
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

            file_display_name = f"{exam.subject}_解答用紙.pdf"
            st.download_button(
                label="📥 B4解答用紙PDFをダウンロード",
                data=result_pdf_bytes,
                file_name=file_display_name,
                mime="application/pdf",
                type="primary"
            )

            st.markdown(f"""
            <div class="feedback-box">
                <div style="font-weight: bold; margin-bottom: 0.5rem; color: #334155;">💬 ご意見・改善要望・不具合報告</div>
                <div style="font-size: 0.9rem; color: #64748b; margin-bottom: 0.8rem;">
                    「枠のサイズ感をこうしてほしい」「この大学の過去問に対応してほしい」など、<br>
                    些細なことでもお気軽に匿名でお寄せください！
                </div>
                <a href="{GOOGLE_FORM_URL}" target="_blank" style="text-decoration: none;">
                    <button style="padding: 0.5rem 1.2rem; border-radius: 6px; border: 1px solid #cbd5e1; background: white; font-weight: bold; color: #1e293b; cursor: pointer;">
                        📝 フィードバックを送る（Googleフォーム）
                    </button>
                </a>
            </div>
            """, unsafe_allow_html=True)

        except Exception as e:
            st.error(f"エラー詳細: {str(e)}")
