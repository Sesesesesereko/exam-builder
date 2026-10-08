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
    options=["国語", "英語", "数学", "地歴・社会", "理科"],
    horizontal=True
)

uploaded_file = st.file_uploader("問題PDFをアップロード", type=["pdf"])

def get_q_width_mm(q):
    """大枠(rect)のパディングを含めた物理幅(mm)を算出し、はみ出しを防ぐ"""
    base_gap = 14.0 # 枠組みと余白分
    if q.q_type == "char_grid":
        chars = q.chars_limit or 60
        lines = (chars + 19) // 20
        w = lines * 8.7
    elif q.q_type == "word_fill":
        sym_count = len(q.symbols) if q.symbols else 5
        cols = (sym_count + 4) // 5  # 5個で折り返し
        w = cols * 17.0
    elif q.q_type == "table_fill":
        sym_count = len(q.symbols) if q.symbols else 5
        cols = (sym_count + 5) // 6  # 6個で折り返し
        w = cols * 14.0
    elif q.q_type in ["lined_box", "free_box"]:
        lines = q.line_count or 2
        w = lines * 11.5
    else:
        w = 20.0
    return max(w, 15.0) + base_gap

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
            progress_text.text("1/3: PDFデータを読み込み中...")
            progress_bar.progress(20)
            pdf_bytes = uploaded_file.read()

            progress_text.text(f"2/3: {selected_subject}専用エンジンで設問解析中...")
            progress_bar.progress(50)

            client = genai.Client(api_key=api_key)

            if selected_subject == "国語":
                prompt = """
You are a highly precise typesetter for Japanese university entrance exams.
Extract the EXACT question structure from the PDF.

[CRITICAL RULES]
1. ZERO HALLUCINATION: NEVER create fake choices, symbols, or questions.
2. If a question is a descriptive text (e.g. "説明せよ"), DO NOT output `table_fill`. Use `free_box` (no limit) or `char_grid` (if "○字以内").
3. Mentally solve descriptive questions to estimate the `line_count` (usually 2, 3, or 4 lines).
4. For Kanji/Vocab extraction: use `word_fill` and set `symbols`.
5. DO NOT GUESS `university` or `year`. If not clearly printed, leave them as empty strings ("").
6. Set `instruction` to "".
"""
            elif selected_subject == "数学":
                prompt = """
Extract ONLY the main question numbers (e.g., 第1問, 第2問) from the Math exam PDF.
DO NOT extract sub-questions. Output ONE question per section with `q_number="解答欄"`, `q_type="math_box"`.
Do not guess university or year.
"""
            else:
                prompt = f"""
Extract the precise question structure for the {selected_subject} exam.
Mentally solve questions to estimate `line_count` or `chars_limit`.
Never invent questions. Do not guess university or year if missing.
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

            raw_u = (exam.university or "").replace("大学", "").replace("大学名", "").strip()
            has_univ = bool(raw_u and raw_u.lower() not in ["unknown", "none", "未定"])
            univ_display = f"{raw_u}大学" if has_univ else ""

            raw_y = (str(exam.year) if exam.year else "").replace("年度", "").strip()
            has_year = bool(raw_y and raw_y.lower() not in ["unknown", "none", "未定"])
            year_display = f"{raw_y}年度" if has_year else ""

            lines = [
                '#import "components/components.typ": *',
                "",
                '#set page(',
                '  paper: "jis-b4",',
                '  flipped: true,',
                '  margin: (x: 14mm, top: 12mm, bottom: 12mm)',
                ')',
                '#set text(font: ("Noto Serif CJK JP", "Noto Sans CJK JP", "IPAexGothic", "IPAGothic", "Yu Gothic"), lang: "ja", size: 9.5pt)',
                "",
            ]

            sheet_count = 0

            for sec in exam.sections:
                questions = sec.questions

                if selected_subject == "国語":
                    chunks = []
                    current_chunk = []
                    current_width = 0.0
                    MAX_WIDTH = 230.0

                    for q in questions:
                        w = get_q_width_mm(q)
                        if current_width + w > MAX_WIDTH and current_chunk:
                            chunks.append(current_chunk)
                            current_chunk = [q]
                            current_width = w
                        else:
                            current_chunk.append(q)
                            current_width += w
                    
                    if current_chunk:
                        chunks.append(current_chunk)

                    for c_idx, chunk in enumerate(chunks):
                        sheet_count += 1
                        if sheet_count > 1:
                            lines.append("#pagebreak()")

                        page_label = f"({c_idx + 1}/{len(chunks)})" if len(chunks) > 1 else ""

                        lines.append("#grid(")
                        lines.append("  columns: (1fr, 36mm),")
                        lines.append("  gutter: 14mm,")
                        lines.append("  [")
                        lines.append("    #align(right)[")
                        lines.append("      #stack(")
                        lines.append("        dir: ltr,")
                        lines.append("        spacing: 9mm,")

                        for q in reversed(chunk):
                            # ★ ここにあった `#rect` の `#` を削除しました（文法エラー解消）
                            lines.append("        rect(")
                            lines.append("          stroke: 0.8pt + luma(80),")
                            lines.append("          inset: 12pt,")
                            lines.append("          radius: 4pt,")
                            lines.append("          fill: white,")
                            lines.append("          block(breakable: false)[")
                            lines.append(f'            #align(center)[#text(weight: "bold", size: 10pt)[【{q.q_number}】]]')
                            lines.append("            #v(8pt)")

                            if q.q_type == "char_grid":
                                c = q.chars_limit or 60
                                lines.append(f"            #vertical-grid(chars: {c})")
                            elif q.q_type == "word_fill":
                                symbols = q.symbols or ["ア", "イ", "ウ", "エ", "オ"]
                                arr = ", ".join([f'"{s}"' for s in symbols])
                                lines.append(f"            #vertical-kanji-box(symbols: ({arr},))")
                            elif q.q_type == "table_fill":
                                symbols = q.symbols or ["(1)", "(2)"]
                                arr = ", ".join([f'"{s}"' for s in symbols])
                                lines.append(f"            #vertical-symbol-box(symbols: ({arr},))")
                            else:
                                ln = q.line_count or 2
                                lines.append(f"            #vertical-free-box(columns-count: {ln})")

                            lines.append("          ]")
                            lines.append("        ),")

                        lines.append("      )")
                        lines.append("    ]")
                        lines.append("  ],")

                        lines.extend([
                            "  [",
                            "    #rect(width: 100%, height: 100%, stroke: 0.8pt + luma(60), fill: white, inset: 0pt)[",
                            "      #grid(",
                            "        columns: (100%,),",
                            "        rows: (35pt, 28pt, 55pt, 55pt, 22pt, 65pt, 22pt, 75pt, 22pt, 1fr),",
                            '        rect(width: 100%, height: 100%, stroke: (bottom: 0.5pt), fill: luma(245))[#align(center + horizon)[#text(size: 11pt, weight: "bold")[国語 解答用紙]]],',
                            f'        rect(width: 100%, height: 100%, stroke: (bottom: 0.5pt), fill: white)[#align(center + horizon)[#text(size: 9.5pt, weight: "bold")[【{sec.big_number}】{page_label}]]],',
                            f'        rect(width: 100%, height: 100%, stroke: (bottom: 0.5pt), fill: white)[',
                            '          #align(left + top)[',
                            '            #v(4pt)#h(4pt)#text(size: 8pt)[大学名:]',
                            '            #v(10pt)',
                            f'            #align(center)[#text(size: 10pt, weight: "bold")[{univ_display}] #if "{univ_display}" == "" [#box(width: 75%, stroke: (bottom: 0.5pt))[] #text(size: 8pt)[大学]]]',
                            '          ]',
                            '        ],',
                            f'        rect(width: 100%, height: 100%, stroke: (bottom: 0.5pt), fill: white)[',
                            '          #align(left + top)[',
                            '            #v(4pt)#h(4pt)#text(size: 8pt)[年度・学部:]',
                            '            #v(10pt)',
                            f'            #align(center)[#text(size: 10pt, weight: "bold")[{year_display}] #if "{year_display}" == "" [#box(width: 85%, stroke: (bottom: 0.5pt))[]]]',
                            '          ]',
                            '        ],',
                            '        rect(width: 100%, height: 100%, stroke: (bottom: 0.5pt), fill: luma(245))[#align(center + horizon)[#text(size: 9pt)[受験番号]]],',
                            '        rect(width: 100%, height: 100%, stroke: (bottom: 0.5pt), fill: white)[],',
                            '        rect(width: 100%, height: 100%, stroke: (bottom: 0.5pt), fill: luma(245))[#align(center + horizon)[#text(size: 9pt)[氏名]]],',
                            '        rect(width: 100%, height: 100%, stroke: (bottom: 0.5pt), fill: white)[],',
                            '        rect(width: 100%, height: 100%, stroke: (bottom: 0.5pt), fill: luma(235))[#align(center + horizon)[#text(size: 9pt)[※得点]]],',
                            '        rect(width: 100%, height: 100%, stroke: none, fill: white)[]',
                            "      )",
                            "    ]",
                            "  ]",
                            ")",
                            ""
                        ])

                elif selected_subject == "数学":
                    sheet_count += 1
                    if sheet_count > 1:
                        lines.append("#pagebreak()")
                    lines.extend([
                        "#grid(",
                        "  columns: (1fr, auto),",
                        "  gutter: 12pt,",
                        "  align: (left + top, right + top),",
                        f'  text(size: 13pt, weight: "bold")[{year_display} {univ_display} 数学 解答用紙 【{sec.big_number}】],',
                        '  table(columns: (45pt, 70pt, 35pt, 90pt, 45pt), rows: (16pt, 24pt), align: center + horizon, stroke: 0.5pt, table.cell(fill: luma(245))[受験番号], table.cell(rowspan: 2, fill: white)[], table.cell(fill: luma(245))[氏名], table.cell(rowspan: 2, fill: white)[], table.cell(fill: luma(235))[※得点], table.cell(fill: white)[])',
                        ")",
                        "#v(5pt)",
                        "#line(length: 100%, stroke: 1.2pt)",
                        "#v(10pt)",
                        "#math-calc-box(height-pt: 480pt, divided: true)",
                        ""
                    ])

                else:
                    sheet_count += 1
                    if sheet_count > 1:
                        lines.append("#pagebreak()")
                    lines.extend([
                        "#grid(",
                        "  columns: (1fr, auto),",
                        "  gutter: 12pt,",
                        "  align: (left + top, right + top),",
                        f'  text(size: 13pt, weight: "bold")[{year_display} {univ_display} {exam.subject} 解答用紙 【{sec.big_number}】],',
                        '  table(columns: (45pt, 70pt, 35pt, 90pt, 45pt), rows: (16pt, 24pt), align: center + horizon, stroke: 0.5pt, table.cell(fill: luma(245))[受験番号], table.cell(rowspan: 2, fill: white)[], table.cell(fill: luma(245))[氏名], table.cell(rowspan: 2, fill: white)[], table.cell(fill: luma(235))[※得点], table.cell(fill: white)[])',
                        ")",
                        "#v(5pt)",
                        "#line(length: 100%, stroke: 1.2pt)",
                        "#v(10pt)",
                        "#columns(2, gutter: 16mm)[",
                    ])
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
