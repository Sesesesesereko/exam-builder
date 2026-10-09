import os
import io
import time
import base64
import subprocess
import streamlit as st
from pypdf import PdfWriter, PdfReader
from google import genai
from google.genai import types
from schemas.question_schema import ExamPaper

GOOGLE_FORM_URL = "https://forms.gle/x7isU1uRdGtiT5ZPA"

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

include_questions = st.checkbox("📄 問題用紙もまとめて1つのPDFにする（問題 ＋ 解答用紙）", value=False)

def get_q_width_mm(q):
    base_gap = 14.0
    if q.q_type == "char_grid":
        chars = q.chars_limit or 60
        lines = (chars + 19) // 20
        w = lines * 8.7
    elif q.q_type == "word_fill":
        sym_count = len(q.symbols) if q.symbols else 1
        cols = (sym_count + 4) // 5
        w = cols * 17.0
    elif q.q_type == "exact_word_fill":
        chars = q.chars_limit or 4
        w = chars * 8.5
    elif q.q_type == "table_fill":
        sym_count = len(q.symbols) if q.symbols else 1
        cols = (sym_count + 5) // 6
        w = cols * 14.0
    elif q.q_type in ["lined_box", "free_box"]:
        lines = q.line_count or 2
        w = lines * 11.5
    else:
        w = 20.0
    return max(w, 15.0) + base_gap

if uploaded_file is not None:
    st.success(f"📎 読み込み完了: {uploaded_file.name}")
    pdf_bytes = uploaded_file.read()

    with st.expander("👁️ アップロードした問題PDFをプレビューする", expanded=False):
        b64_pdf = base64.b64encode(pdf_bytes).decode("utf-8")
        pdf_display = f'<iframe src="data:application/pdf;base64,{b64_pdf}" width="100%" height="600" type="application/pdf" style="border: 1px solid #cbd5e1; border-radius: 8px;"></iframe>'
        st.markdown(pdf_display, unsafe_allow_html=True)

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

            progress_text.text(f"2/3: 【{selected_subject}】専用エンジンで設問解析中...")
            progress_bar.progress(50)

            client = genai.Client(api_key=api_key)

            # ==========================================
            # 教科別 完全分離プロンプト（国語・英語は凍結維持）
            # ==========================================
            if selected_subject == "国語":
                prompt = """
You are a highly precise typesetter for Japanese entrance exams. Read ONLY the "設問" (Questions) section.
Mentally solve the question first to determine the box type and size.
ZERO HALLUCINATION: NEVER invent questions or options (like ア, イ) not explicitly written.

1. EXACT CHAR COUNT (e.g., "二字で抜き出せ", "四字で答えよ"):
   Use `q_type="exact_word_fill"`, set `chars_limit` to the exact number (e.g., 2, 4), and `symbols` to labels (e.g., ["A", "B"]).
2. KANJI/KANA:
   Use `q_type="word_fill"`, set `symbols` to exact labels (e.g., ["ア", "イ", "ウ"]).
3. DESCRIPTION (e.g., "説明せよ"):
   If "○字以内", use `q_type="char_grid"`, set `chars_limit`.
   If no limit, use `q_type="free_box"`, estimate `line_count` (2 to 4).
4. MULTIPLE CHOICE: Use `q_type="table_fill"`, set `symbols`.
5. DO NOT guess `university` or `year`. Set `instruction`="".
"""
            elif selected_subject == "英語":
                prompt = """
You are an expert English entrance exam typesetter. Mentally solve questions to estimate required space.
ZERO HALLUCINATION: Do not invent questions.

1. MULTIPLE CHOICE (e.g., Q1-Q5): Use `q_type="table_fill"`, set `symbols`.
2. WORD ORDERING (並び替え): Use `q_type="reorder"`, set `targets` (e.g., ["3rd", "5th"]).
3. SHORT ANSWER/FILL-IN-BLANK: Use `q_type="word_fill"`, set `symbols`.
4. TRANSLATION/EXPLANATION (和訳・説明):
   If character limit exists, use `q_type="char_grid"`.
   If no limit, use `q_type="lined_box"` and estimate `line_count` (3 to 6).
5. FREE ESSAY (自由英作文): Use `q_type="lined_box"`, estimate `line_count` (8 to 12).
6. DO NOT guess `university` or `year`. Set `instruction`="".
"""
            elif selected_subject == "数学":
                prompt = """
You are a Math exam typesetter.
Extract ONLY the main question numbers (e.g., 第1問, 第2問).
DO NOT extract sub-questions like (1), (2).
For each main section, output exactly ONE question with `q_number="解答欄"`, `q_type="math_box"`.
DO NOT guess `university` or `year`. Set `instruction`="".
"""
            elif selected_subject == "地歴・社会":
                prompt = """
You are a History/Geography exam typesetter. Mentally solve questions to estimate space.
ZERO HALLUCINATION.

1. SHORT TERMS/BLANKS: Use `q_type="word_fill"`, set `symbols`.
2. MULTIPLE CHOICE: Use `q_type="table_fill"`, set `symbols`.
3. ESSAY/DESCRIPTION (論述):
   If character limit exists (e.g., "400字"), use `q_type="char_grid"`, set `chars_limit`.
   If no limit (short description), use `q_type="lined_box"`, estimate `line_count` (2 to 4).
4. DO NOT guess `university` or `year`. Set `instruction`="".
"""
            elif selected_subject == "理科":
                prompt = """
You are an expert typesetter for Science university entrance exams.
Read the exam questions carefully and extract the EXACT question structure.

[CRITICAL RULES FOR SCIENCE]
1. SINGLE ANSWER MULTIPLE CHOICE (組合せ・単一番号選択):
   - When a question asks to choose ONE combination or number (e.g., "空欄ア・イに当てはまる語の組合せとして最も適当なものを、1～6のうちから一つ選び、番号で答えよ"):
     The answer is just a SINGLE number (e.g. 3).
     DO NOT output labels ["ア", "イ"]! Output a single question with `symbols=None` and `q_type="word_fill"`.
   - Any question saying "一つ選び、番号で答えよ" or "記号で答えよ" takes EXACTLY ONE answer box.

2. MULTIPLE SUB-QUESTIONS WITHIN ONE QUESTION:
   - ONLY when separate answers are explicitly required for each blank (e.g., "空欄エ・オに当てはまる語をそれぞれ答えよ"):
     Set `symbols=["エ", "オ"]` and `q_type="word_fill"`.

3. DESCRIPTIONS / LIMITS / FORMULAS:
   - Character limit (e.g. "15字以内で答えよ"): `q_type="char_grid"`, set `chars_limit=15`.
   - Reaction equations (化学反応式): `q_type="lined_box"`, `line_count=2`.
   - Structural formula (構造式): `q_type="lined_box"`, `line_count=3`.

4. SELECTIVE SECTIONS (選択問題):
   - You MUST generate BOTH selective sections (e.g., Section 4 and Section 5) so students can select either on paper.

5. Set `instruction` to "". Do NOT guess university or year.
"""
            else:
                prompt = "Extract questions. Mentally solve them. Set instruction to empty string."

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
                            elif q.q_type == "exact_word_fill":
                                symbols = q.symbols or [""]
                                arr = ", ".join([f'"{s}"' for s in symbols])
                                c = q.chars_limit or 4
                                lines.append(f"            #exact-char-box(symbols: ({arr},), chars: {c})")
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

                elif selected_subject == "理科":
                    # ★理科専用：紙面を最大限に有効活用する横並びフローレイアウト
                    sheet_count += 1
                    if sheet_count > 1:
                        lines.append("#pagebreak()")
                    lines.extend([
                        "#grid(",
                        "  columns: (1fr, auto),",
                        "  gutter: 12pt,",
                        "  align: (left + top, right + top),",
                        f'  text(size: 13pt, weight: "bold")[{year_display} {univ_display} 理科 解答用紙 【{sec.big_number}】],',
                        '  table(columns: (45pt, 70pt, 35pt, 90pt, 45pt), rows: (16pt, 24pt), align: center + horizon, stroke: 0.5pt, table.cell(fill: luma(245))[受験番号], table.cell(rowspan: 2, fill: white)[], table.cell(fill: luma(245))[氏名], table.cell(rowspan: 2, fill: white)[], table.cell(fill: luma(235))[※得点], table.cell(fill: white)[])',
                        ")",
                        "#v(5pt)",
                        "#line(length: 100%, stroke: 1.2pt)",
                        "#v(8pt)",
                    ])

                    # 設問群を横並びで配置可能なコンパクト枠とワイド枠に分類して組版
                    lines.append("#grid(")
                    lines.append("  columns: (1fr, 1fr),")
                    lines.append("  column-gutter: 16mm,")
                    lines.append("  row-gutter: 12pt,")

                    for q in questions:
                        if q.q_type in ["lined_box", "free_box"]:
                            ln = q.line_count or 2
                            lines.append(f'  grid.cell(colspan: 2)[')
                            lines.append(f'    #text(weight: "bold", size: 9pt)[【{q.q_number}】]')
                            lines.append(f'    #v(2pt)')
                            lines.append(f'    #lined-box(lines: {ln})')
                            lines.append(f'  ],')
                        elif q.q_type == "char_grid":
                            c = q.chars_limit or 50
                            lines.append(f'  grid.cell(colspan: 2)[')
                            lines.append(f'    #text(weight: "bold", size: 9pt)[【{q.q_number}】]')
                            lines.append(f'    #v(2pt)')
                            lines.append(f'    #char-grid(chars: {c})')
                            lines.append(f'  ],')
                        elif q.q_type == "math_box":
                            lines.append(f'  grid.cell(colspan: 2)[')
                            lines.append(f'    #text(weight: "bold", size: 9pt)[【{q.q_number}】]')
                            lines.append(f'    #v(2pt)')
                            lines.append(f'    #science-calc-box(height-pt: 100pt)')
                            lines.append(f'  ],')
                        else:
                            # 短答・記号・数値：問1、問2を横にテンポよく並べる
                            if q.symbols and len(q.symbols) > 1:
                                syms = ", ".join([f'"{s}"' for s in q.symbols])
                                lines.append(f'  [')
                                lines.append(f'    #text(weight: "bold", size: 9pt)[【{q.q_number}】]')
                                lines.append(f'    #v(2pt)')
                                lines.append(f'    #symbol-table(symbols: ({syms},))')
                                lines.append(f'  ],')
                            else:
                                lines.append(f'  [')
                                lines.append(f'    #text(weight: "bold", size: 9pt)[【{q.q_number}】]')
                                lines.append(f'    #v(2pt)')
                                lines.append(f'    #table(columns: (1fr,), rows: (26pt,), align: center + horizon, stroke: 0.5pt, fill: white)[]')
                                lines.append(f'  ],')

                    lines.append(")")
                    lines.append("")

                else:
                    # 英語・地歴
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
                        elif q.q_type == "exact_word_fill":
                            symbols = q.symbols or [""]
                            arr = ", ".join([f'"{s}"' for s in symbols])
                            c = q.chars_limit or 4
                            lines.append(f"    #exact-char-box(symbols: ({arr},), chars: {c})")
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
                answer_sheet_bytes = f.read()

            if include_questions:
                merger = PdfWriter()
                q_pdf_reader = PdfReader(io.BytesIO(pdf_bytes))
                for page in q_pdf_reader.pages:
                    merger.add_page(page)
                
                a_pdf_reader = PdfReader(io.BytesIO(answer_sheet_bytes))
                for page in a_pdf_reader.pages:
                    merger.add_page(page)
                
                merged_output = io.BytesIO()
                merger.write(merged_output)
                final_pdf_bytes = merged_output.getvalue()
                button_label = "📥 問題＋解答用紙PDFをダウンロード"
                file_display_name = f"{exam.subject}_問題および解答用紙.pdf"
            else:
                final_pdf_bytes = answer_sheet_bytes
                button_label = "📥 B4解答用紙PDFをダウンロード"
                file_display_name = f"{exam.subject}_解答用紙.pdf"

            progress_bar.progress(100)
            progress_text.text("✨ PDFの作成が完了しました！")
            st.balloons()

            st.download_button(
                label=button_label,
                data=final_pdf_bytes,
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
