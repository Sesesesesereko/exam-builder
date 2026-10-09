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
TOSHIN_URL = "https://www.toshin-kakomon.com/"

st.set_page_config(
    page_title="大学入試解答用紙ジェネレーター",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Noto Sans JP', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    .block-container {
        padding-top: 2.5rem;
        padding-bottom: 3rem;
        max-width: 820px;
    }
    .header-box {
        border-bottom: 2px solid var(--text-color, #0f172a);
        padding-bottom: 1rem;
        margin-bottom: 2rem;
    }
    .header-title {
        font-size: 1.8rem;
        font-weight: 700;
        letter-spacing: -0.02em;
        margin-bottom: 0.3rem;
    }
    .header-sub {
        font-size: 0.9rem;
        opacity: 0.8;
    }
    div[data-testid="stFileUploader"] {
        border: 1px solid rgba(150, 150, 150, 0.3);
        border-radius: 6px;
        padding: 12px;
        margin-bottom: 0.5rem;
    }
    .notice-box {
        font-size: 0.82rem;
        color: #64748b;
        margin-bottom: 1.2rem;
        line-height: 1.5;
    }
    .notice-box a {
        color: #0284c7;
        text-decoration: underline;
    }
    .stButton>button {
        width: 100%;
        border-radius: 6px;
        height: 3.2rem;
        font-weight: 700;
        font-size: 1.05rem;
        background-color: #2563eb;
        color: #ffffff !important;
        border: none;
        transition: all 0.2s ease;
    }
    .stButton>button:hover {
        background-color: #1d4ed8;
    }
    .footer-container {
        margin-top: 3.5rem;
        padding-top: 1.5rem;
        border-top: 1px solid rgba(150, 150, 150, 0.2);
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 1rem;
    }
    .footer-text {
        font-size: 0.82rem;
        opacity: 0.75;
    }
    .footer-link {
        font-size: 0.85rem;
        font-weight: 500;
        color: #38bdf8;
        text-decoration: none;
    }
    .footer-link:hover {
        text-decoration: underline;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="header-box">
    <div class="header-title">大学入試解答用紙ジェネレーター</div>
    <div class="header-sub">入試過去問PDFから本番準拠のB4判解答用紙を自動組版・生成します。</div>
</div>
""", unsafe_allow_html=True)

selected_subject = st.radio(
    "科目を選択してください",
    options=["国語", "英語", "数学", "地歴・社会", "理科"],
    horizontal=True
)

uploaded_file = st.file_uploader("問題PDFをアップロード", type=["pdf"])

# 規約・著作権に配慮した安全な外部リンク案内
st.markdown(f"""
<div class="notice-box">
    ※ 過去問PDFをお持ちでない場合は、各大学の公式サイトや <a href="{TOSHIN_URL}" target="_blank" rel="noopener noreferrer">東進 過去問データベース</a> などの公式ポータル等から各自ご用意ください。
</div>
""", unsafe_allow_html=True)

include_questions = st.checkbox("問題用紙もまとめて1つのPDFにする（問題 ＋ 解答用紙）", value=False)

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
    st.success(f"読み込み完了: {uploaded_file.name}")
    pdf_bytes = uploaded_file.read()

    with st.expander("問題PDFの確認", expanded=False):
        b64_pdf = base64.b64encode(pdf_bytes).decode("utf-8")
        pdf_display = f'<iframe src="data:application/pdf;base64,{b64_pdf}" width="100%" height="600" type="application/pdf" style="border: 1px solid rgba(150,150,150,0.3); border-radius: 4px;"></iframe>'
        st.markdown(pdf_display, unsafe_allow_html=True)

    if st.button("解答用紙を作成する"):
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            st.error("システムエラー: APIキーが設定されていません。管理者に連絡してください。")
            st.stop()

        progress_text = st.empty()
        progress_bar = st.progress(0)

        try:
            progress_text.text("1/3: PDFデータを解析中...")
            progress_bar.progress(20)

            progress_text.text(f"2/3: {selected_subject}の設問構成を抽出中...")
            progress_bar.progress(50)

            client = genai.Client(api_key=api_key)

            # ==========================================
            # 教科別 完全分離プロンプト（国語・英語は完全固定）
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
1. NUMERICAL & SIGNIFICANT FIGURES ARE SINGLE GENERAL BOXES (数値計算・有効数字):
   - Questions saying "有効数字2桁で答えよ", "有効数字3桁で", "整数で答えよ", or "数値を求めよ":
     NEVER use `exact_word_fill`! Numerical answers need decimal points and powers (e.g., 0.42, 3.6x10^-2).
     You MUST use `q_type="word_fill"` with `symbols=None` (a single open box).

2. ONLY TEXT EXTRACTION USES EXACT CHARACTER BOXES:
   - ONLY when it explicitly asks for exact Japanese characters (e.g., "漢字2文字で答えよ", "3文字で抜き出せ"):
     Use `q_type="exact_word_fill"`, set `chars_limit` to that number.

3. SINGLE ANSWER MULTIPLE CHOICE (組合せ・単一番号選択):
   - "一つ選び、番号で答えよ" or "記号で答えよ":
     Output EXACTLY ONE answer box with `q_type="table_fill"`. Do NOT create boxes for individual choices!

4. MULTIPLE SUB-QUESTIONS IN ONE QUESTION:
   - When multiple blanks are explicitly required (e.g., "空欄エ・オに当てはまる語"):
     Set `symbols=["エ", "オ"]` and `q_type="word_fill"`.

5. DESCRIPTIONS & FORMULAS:
   - "○字以内で説明せよ": `q_type="char_grid"`, set `chars_limit`.
   - Chemical formula or reaction: `q_type="lined_box"`, `line_count=2`.
   - Calculation process: `q_type="math_box"`.

6. SELECTIVE SECTIONS:
   - Generate BOTH selective sections (e.g., Section 4 and Section 5).

7. Set `instruction` to "". Do NOT guess university or year.
"""
            else:
                prompt = "Extract questions. Mentally solve them. Set instruction to empty string."

            max_retries = 3
            response = None
            for attempt in range(1, max_retries + 1):
                try:
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
                    break
                except Exception as api_err:
                    err_str = str(api_err)
                    if ("503" in err_str or "UNAVAILABLE" in err_str) and attempt < max_retries:
                        time.sleep(attempt * 3)
                        continue
                    raise api_err

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
                '#set text(font: ("Noto Serif CJK JP", "Noto Sans CJK JP", "IPAexGothic", "IPAGothic"), lang: "ja", size: 9.5pt)',
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

                    lines.append("#grid(")
                    lines.append("  columns: (1fr, 1fr),")
                    lines.append("  column-gutter: 16mm,")
                    lines.append("  row-gutter: 12pt,")

                    col_index = 0
                    for q in questions:
                        is_wide = q.q_type in ["lined_box", "free_box", "char_grid", "math_box"]
                        
                        if is_wide:
                            if col_index % 2 == 1:
                                lines.append("  [],")
                                col_index += 1
                            
                            lines.append("  grid.cell(colspan: 2)[")
                            lines.append(f'    #text(weight: "bold", size: 9pt)[【{q.q_number}】]')
                            lines.append("    #v(2pt)")
                            if q.q_type == "char_grid":
                                c = q.chars_limit or 50
                                lines.append(f"    #char-grid(chars: {c})")
                            elif q.q_type == "math_box":
                                lines.append("    #science-calc-box(height-pt: 100pt)")
                            else:
                                ln = q.line_count or 2
                                lines.append(f"    #lined-box(lines: {ln})")
                            lines.append("  ],")
                            col_index += 2
                        elif q.q_type == "exact_word_fill":
                            lines.append("  [")
                            lines.append(f'    #text(weight: "bold", size: 9pt)[【{q.q_number}】]')
                            lines.append("    #v(2pt)")
                            symbols = q.symbols or [""]
                            arr = ", ".join([f'"{s}"' for s in symbols])
                            c = q.chars_limit or 4
                            lines.append(f"    #exact-char-box(symbols: ({arr},), chars: {c})")
                            lines.append("  ],")
                            col_index += 1
                        else:
                            lines.append("  [")
                            lines.append(f'    #text(weight: "bold", size: 9pt)[【{q.q_number}】]')
                            lines.append("    #v(2pt)")
                            if q.symbols and len(q.symbols) > 1:
                                syms = ", ".join([f'"{s}"' for s in q.symbols])
                                lines.append(f"    #symbol-table(symbols: ({syms},))")
                            else:
                                label = q.symbols[0] if (q.symbols and len(q.symbols) == 1) else ""
                                if label:
                                    lines.append(f'    #word-box(symbols: ("{label}",))')
                                else:
                                    lines.append("    #table(columns: (1fr,), rows: (26pt,), align: center + horizon, stroke: 0.5pt, fill: white)[]")
                            lines.append("  ],")
                            col_index += 1

                    lines.append(")")
                    lines.append("")

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
                button_label = "問題＋解答用紙PDFをダウンロード"
                file_display_name = f"{exam.subject}_問題および解答用紙.pdf"
            else:
                final_pdf_bytes = answer_sheet_bytes
                button_label = "B4解答用紙PDFをダウンロード"
                file_display_name = f"{exam.subject}_解答用紙.pdf"

            progress_bar.progress(100)
            progress_text.text("組版が完了しました。")

            st.download_button(
                label=button_label,
                data=final_pdf_bytes,
                file_name=file_display_name,
                mime="application/pdf",
                type="primary"
            )

        except Exception as e:
            st.error(f"エラー詳細: {str(e)}")

st.markdown(f"""
<div class="footer-container">
    <div class="footer-text">
        大学入試解答用紙ジェネレーター &mdash; 実務・学習用ツール
    </div>
    <div>
        <a href="{GOOGLE_FORM_URL}" target="_blank" class="footer-link">
            不具合報告・レイアウト改善要望はこちら
        </a>
    </div>
</div>
""", unsafe_allow_html=True)
