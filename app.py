import os
import io
import time
import base64
import subprocess
import streamlit as st
import streamlit.components.v1 as components
from pypdf import PdfWriter, PdfReader
from google import genai
from google.genai import types
from schemas.question_schema import ExamPaper, Question

GOOGLE_FORM_URL = "https://forms.gle/x7isU1uRdGtiT5ZPA"
TOSHIN_URL = "https://www.toshin-kakomon.com/"
AI_STUDIO_URL = "https://aistudio.google.com/app/apikey"

st.set_page_config(
    page_title="大学入試解答用紙ジェネレーター",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;700&display=swap');
    html, body, [class*="css"] { font-family: 'Noto Sans JP', -apple-system, BlinkMacSystemFont, sans-serif; }
    .block-container { padding-top: 2rem; padding-bottom: 3rem; max-width: 840px; }
    
    .header-box { 
        border-bottom: 1px solid #e2e8f0; 
        padding-bottom: 1.2rem; 
        margin-bottom: 1.5rem; 
    }
    .header-title { 
        font-size: 1.6rem; 
        font-weight: 700; 
        color: #0f172a; 
        letter-spacing: -0.01em; 
        margin-bottom: 0.3rem; 
    }
    .header-sub { 
        font-size: 0.88rem; 
        color: #64748b; 
        line-height: 1.5; 
    }
    
    .auth-panel {
        background-color: #f8fafc;
        border: 1px solid #cbd5e1;
        border-radius: 8px;
        padding: 16px 20px;
        margin-bottom: 1.5rem;
    }
    .auth-title {
        font-size: 0.95rem;
        font-weight: 700;
        color: #1e293b;
        margin-bottom: 6px;
    }
    .auth-desc {
        font-size: 0.82rem;
        color: #475569;
        margin-bottom: 12px;
        line-height: 1.5;
    }
    .step-list {
        margin: 0;
        padding-left: 1.2rem;
        font-size: 0.83rem;
        color: #334155;
        line-height: 1.7;
    }
    .step-list a {
        color: #2563eb;
        text-decoration: underline;
        font-weight: 600;
    }
    
    div[data-testid="stFileUploader"] { 
        border: 1px solid #cbd5e1; 
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
        color: #2563eb; 
        text-decoration: underline; 
    }
    
    .stButton>button { 
        width: 100%; 
        border-radius: 6px; 
        height: 3.2rem; 
        font-weight: 700; 
        font-size: 1rem; 
        background-color: #0f172a; 
        color: #ffffff !important; 
        border: none; 
        transition: background-color 0.2s ease; 
    }
    .stButton>button:hover { 
        background-color: #1e293b; 
    }

    .batch-file-card {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 6px;
        padding: 12px 16px;
        margin-bottom: 10px;
    }
    
    .footer-container { 
        margin-top: 3.5rem; 
        padding-top: 1.5rem; 
        border-top: 1px solid #e2e8f0; 
        display: flex; 
        justify-content: space-between; 
        align-items: center; 
        flex-wrap: wrap; 
        gap: 1rem; 
    }
    .footer-text { 
        font-size: 0.82rem; 
        color: #64748b; 
    }
    .footer-link { 
        font-size: 0.85rem; 
        font-weight: 500; 
        color: #2563eb; 
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
    <div class="header-sub">入試過去問PDFから本番準拠のB4判解答用紙・マークシートを自動組版・生成します。</div>
</div>
""", unsafe_allow_html=True)

# ----------------- ブラウザローカル保存スクリプト -----------------
js_storage_bridge = """
<script>
    const savedKey = localStorage.getItem("user_gemini_api_key") || "";
    const parentDoc = window.parent.document;
    const inputField = parentDoc.querySelector('input[data-testid="stTextInputRootElement_apiKeyInput"]');
    
    if (inputField && !inputField.value && savedKey) {
        inputField.value = savedKey;
        inputField.dispatchEvent(new Event('input', { bubbles: true }));
        inputField.dispatchEvent(new Event('change', { bubbles: true }));
    }
</script>
"""
components.html(js_storage_bridge, height=0, width=0)

if "saved_api_key" not in st.session_state:
    st.session_state["saved_api_key"] = ""

url_key = st.query_params.get("key", "")
default_input_val = st.session_state["saved_api_key"] or url_key

st.markdown(f"""
<div class="auth-panel">
    <div class="auth-title">Gemini APIキーの設定（無料）</div>
    <div class="auth-desc">
        問題構造の解析に利用するGoogle Gemini APIキーを設定します。キーはブラウザに自動保存されるため、次回以降の入力は不要です。
    </div>
    <ol class="step-list">
        <li><a href="{AI_STUDIO_URL}" target="_blank" rel="noopener noreferrer">Google AI Studio（APIキー管理画面）</a> にアクセスする</li>
        <li>画面右上の「<strong>API キーを作成</strong>」をクリックする</li>
        <li>ポップアップ内の「<strong>キーを作成</strong>」をクリックする</li>
        <li>生成されたキーの「<strong>コピー</strong>」をクリックし、下の入力欄に貼り付ける</li>
    </ol>
</div>
""", unsafe_allow_html=True)

user_api_key = st.text_input(
    "Gemini APIキー",
    value=default_input_val,
    type="password",
    placeholder="AIzaSy...",
    key="apiKeyInput",
    help="Google AI Studioで取得したAPIキーを入力してください。"
).strip()

if user_api_key:
    st.session_state["saved_api_key"] = user_api_key
    save_js = f"""
    <script>
        localStorage.setItem("user_gemini_api_key", "{user_api_key}");
    </script>
    """
    components.html(save_js, height=0, width=0)
    st.caption("APIキーを保存しました。この端末では次回以降もそのままご利用いただけます。")
    if "key" in st.query_params:
        del st.query_params["key"]

# ----------------- 共通処理・関数 -----------------
SUBJECT_OPTIONS = ["国語", "英語", "数学", "地歴・社会", "理科"]
FORMAT_OPTIONS = ["記述・論述式", "マークシート式（共通テスト・私大マーク型）"]

TYPE_LABEL_MAP = {
    "table_fill": "記号選択（a〜e・①〜④）",
    "lined_box": "横罫線（和訳・英作文・短論述）",
    "char_grid": "原稿用紙マス（○字以内）",
    "math_box": "計算・立式枠（数学・物理）",
    "graph_box": "作図・グラフ枠",
    "word_fill": "単語・空所補充",
    "exact_word_fill": "抜き出し指定マス（○字）",
    "free_box": "白紙枠（短答・計算）",
    "reorder": "整序・並べ替え（矢印）"
}
LABEL_TO_TYPE_MAP = {v: k for k, v in TYPE_LABEL_MAP.items()}

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
    elif q.q_type == "graph_box":
        w = 120.0
    else:
        w = 20.0
    return max(w, 15.0) + base_gap

def build_typst_code(exam, exam_format, selected_subject, science_layout=""):
    raw_u = (exam.university or "").replace("大学", "").replace("大学名", "").strip()
    has_univ = bool(raw_u and raw_u.lower() not in ["unknown", "none", "未定"])
    univ_display = f"{raw_u}大学" if has_univ else ""

    raw_y = (str(exam.year) if exam.year else "").replace("年度", "").strip()
    has_year = bool(raw_y and raw_y.lower() not in ["unknown", "none", "未定"])
    year_display = f"{raw_y}年度" if has_year else ""

    # 受験番号の改行崩れを防ぐ共通ヘッダー（54pt幅 + 8.5pt文字）
    header_table_code = 'table(columns: (54pt, 68pt, 36pt, 88pt, 45pt), rows: (16pt, 24pt), align: center + horizon, stroke: 0.6pt + luma(40), table.cell(fill: white)[#text(size: 8.5pt)[受験番号]], table.cell(rowspan: 2, fill: white)[], table.cell(fill: white)[氏名], table.cell(rowspan: 2, fill: white)[], table.cell(fill: white)[※得点], table.cell(fill: white)[])'

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

    if exam_format == "マークシート式（共通テスト・私大マーク型）":
        lines.extend([
            "#grid(",
            "  columns: (1fr, auto),",
            "  gutter: 12pt,",
            "  align: (left + top, right + top),",
            f'  text(size: 14pt, weight: "bold")[{year_display} {univ_display} {exam.subject} マーク式解答用紙],',
            '  table(columns: (55pt, 120pt), rows: (26pt,), align: center + horizon, stroke: 0.6pt + luma(40), table.cell(fill: white)[氏名], table.cell(fill: white)[])',
            ")",
            "#v(4pt)",
            "#line(length: 100%, stroke: 1.2pt + luma(40))",
            "#v(6pt)",
            "#grid(",
            "  columns: (auto, 1fr),",
            "  gutter: 20pt,",
            "  align: (left + top, left + top),",
            "  [",
            "    #exam-id-mark-box(digits: 6)",
            "    #v(10pt)",
            "    #rect(width: 145pt, stroke: 0.5pt + luma(60), inset: 6pt, fill: white)[",
            '      #text(size: 7.5pt, weight: "bold")[【マーク上の注意】]',
            '      #v(3pt)',
            '      #text(size: 6.5pt)[',
            "      1. HBまたはBの黒鉛筆を使用すること。\n",
            "      2. 枠からはみ出さず濃く塗りつぶすこと。\n",
            "      3. 訂正は消しゴムで跡を残さず消すこと。",
            "      ]",
            "    ]",
            "  ],",
            "  [",
            "    #columns(3, gutter: 12pt)[",
        ])

        for sec in exam.sections:
            lines.append(f'      #block(width: 100%, stroke: (bottom: 0.8pt + luma(40)), inset: (bottom: 2pt))[#text(weight: "bold", size: 9.5pt)[【{sec.big_number}】]]')
            lines.append("      #v(2pt)")
            lines.append("      #table(")
            lines.append("        columns: (32pt, 1fr),")
            lines.append("        rows: (15pt,),")
            lines.append("        align: center + horizon,")
            lines.append("        stroke: 0.4pt + luma(100),")
            for q in sec.questions:
                q_name = q.q_number
                opts = q.symbols if q.symbols else ["1", "2", "3", "4"]
                opt_str = ", ".join([f'"{o}"' for o in opts])
                lines.append(f'        mark-row("{q_name}", options: ({opt_str},)),')
            lines.append("      )")
            lines.append("      #v(8pt)")

        lines.extend([
            "    ]",
            "  ]",
            ")",
            ""
        ])

    else:
        sheet_count = 0
        for sec_idx, sec in enumerate(exam.sections):
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
                        lines.append("          stroke: 0.8pt + luma(40),")
                        lines.append("          inset: 12pt,")
                        lines.append("          radius: 0pt,")
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
                        "    #rect(width: 100%, height: 100%, stroke: 0.8pt + luma(40), fill: white, inset: 0pt)[",
                        "      #grid(",
                        "        columns: (100%,),",
                        "        rows: (35pt, 28pt, 55pt, 55pt, 22pt, 65pt, 22pt, 75pt, 22pt, 1fr),",
                        '        rect(width: 100%, height: 100%, stroke: (bottom: 0.5pt), fill: white)[#align(center + horizon)[#text(size: 11pt, weight: "bold")[国語 解答用紙]]],',
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
                        '        rect(width: 100%, height: 100%, stroke: (bottom: 0.5pt), fill: white)[#align(center + horizon)[#text(size: 8.5pt)[受験番号]]],',
                        '        rect(width: 100%, height: 100%, stroke: (bottom: 0.5pt), fill: white)[],',
                        '        rect(width: 100%, height: 100%, stroke: (bottom: 0.5pt), fill: white)[#align(center + horizon)[#text(size: 8.5pt)[氏名]]],',
                        '        rect(width: 100%, height: 100%, stroke: (bottom: 0.5pt), fill: white)[],',
                        '        rect(width: 100%, height: 100%, stroke: (bottom: 0.5pt), fill: white)[#align(center + horizon)[#text(size: 8.5pt)[※得点]]],',
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
                    f'  {header_table_code}',
                    ")",
                    "#v(5pt)",
                    "#line(length: 100%, stroke: 1.2pt + luma(40))",
                    "#v(10pt)",
                ])
                for q in questions:
                    if q.q_type == "graph_box":
                        lines.append("  #graph-box(height-pt: 200pt)")
                    else:
                        lines.append("  #math-calc-box(height-pt: 450pt, divided: true)")
                lines.append("")

            elif selected_subject == "理科":
                if "記述メイン" in science_layout:
                    sheet_count += 1
                    if sheet_count > 1:
                        lines.append("#pagebreak()")
                    lines.extend([
                        "#grid(",
                        "  columns: (1fr, auto),",
                        "  gutter: 12pt,",
                        "  align: (left + top, right + top),",
                        f'  text(size: 13pt, weight: "bold")[{year_display} {univ_display} 理科 解答用紙 【{sec.big_number}】],',
                        f'  {header_table_code}',
                        ")",
                        "#v(5pt)",
                        "#line(length: 100%, stroke: 1.2pt + luma(40))",
                        "#v(10pt)",
                    ])

                    lines.append("#grid(")
                    lines.append("  columns: (1fr, 1fr),")
                    lines.append("  gutter: 16pt,")
                    lines.append("  align: left + top,")

                    col_index = 0
                    for q in questions:
                        q_name = q.q_number
                        body_code = "none"
                        note_str = ""

                        if q.q_type == "math_box":
                            span = 1
                            estimated_lines = q.line_count or 6
                            dynamic_h = max(140, min(280, estimated_lines * 26))
                            h = f"{dynamic_h}pt"
                            body_code = "[#align(top + left)[#v(4pt)#h(4pt)#text(size: 8pt, fill: luma(80))[【計算過程・理由等】]]]"
                        elif q.q_type == "graph_box":
                            span = 1
                            h = "220pt"
                            body_code = "[#graph-box(height-pt: 190pt)]"
                        elif q.q_type == "char_grid":
                            span = 2
                            h = "auto"
                            c = q.chars_limit or 50
                            note_str = f"{c}字"
                            body_code = f"[#v(6pt)#char-grid(chars: {c}, cols-per-line: 35)#v(6pt)]"
                        elif q.q_type in ["lined_box", "free_box"]:
                            span = 2
                            ln = q.line_count or 4
                            h = "auto"
                            body_code = f"[#lined-box(lines: {ln})]"
                        else:
                            span = 1
                            h = "100pt"

                        if col_index % 2 + span > 2:
                            lines.append("  [],")
                            col_index += 1

                        lines.append(f'  grid.cell(colspan: {span})[')
                        lines.append(f'    #science-cell(label: "{q_name}", note: "{note_str}", height-pt: {h}, body: {body_code})')
                        lines.append("  ],")
                        col_index += span

                    if col_index % 2 != 0:
                        lines.append("  [],")

                    lines.append(")")
                    lines.append("")

                else:
                    if sec_idx % 2 == 0:
                        sheet_count += 1
                        if sheet_count > 1:
                            lines.append("#pagebreak()")
                        lines.extend([
                            "#grid(",
                            "  columns: (1fr, auto),",
                            "  gutter: 12pt,",
                            "  align: (left + top, right + top),",
                            f'  text(size: 13pt, weight: "bold")[{year_display} {univ_display} 理科 解答用紙],',
                            f'  {header_table_code}',
                            ")",
                            "#v(4pt)",
                            "#line(length: 100%, stroke: 1.2pt + luma(40))",
                            "#v(6pt)",
                        ])
                    else:
                        lines.append("#v(14pt)")

                    sec_title = f"【{sec.big_number}】"
                    lines.append(f'#rect(width: 100%, fill: white, stroke: 0.8pt + luma(40), inset: 6pt)[#text(weight: "bold", size: 11pt)[#h(4pt){sec_title}]]')
                    lines.append("#v(10pt)")

                    lines.append("#grid(")
                    lines.append("  columns: (1fr, 1fr, 1fr, 1fr),")
                    lines.append("  gutter: 14pt,")
                    lines.append("  align: left + top,")

                    col_index = 0
                    for q in questions:
                        q_name = q.q_number
                        body_code = "none"
                        note_str = ""

                        if q.q_type == "math_box":
                            span = 4
                            ln = q.line_count or 4
                            h = f"{max(120, ln * 24)}pt"
                            body_code = "[#align(top + left)[#v(4pt)#h(4pt)#text(size: 8pt, fill: luma(80))[【計算過程・理由等】]]]"
                        elif q.q_type == "graph_box":
                            span = 2
                            h = "140pt"
                            body_code = "[#graph-box(height-pt: 120pt)]"
                        elif q.q_type == "char_grid":
                            span = 4
                            h = "auto"
                            c = q.chars_limit or 50
                            note_str = f"{c}字"
                            body_code = f"[#v(6pt)#char-grid(chars: {c}, cols-per-line: 35)#v(6pt)]"
                        elif q.q_type in ["lined_box", "free_box"]:
                            span = 4
                            ln = q.line_count or 3
                            h = "auto"
                            body_code = f"[#lined-box(lines: {ln})]"
                        elif q.q_type == "table_fill":
                            span = 1
                            h = "35pt"
                        elif q.q_type == "exact_word_fill":
                            span = 2
                            h = "auto"
                            c = q.chars_limit or 4
                            note_str = f"{c}字"
                            body_code = f"[#v(6pt)#char-grid(chars: {c}, cols-per-line: {c})#v(6pt)]"
                        else:
                            if q.symbols and len(q.symbols) > 1:
                                span = 2
                                h = "auto"
                                syms = ", ".join([f'"{s}"' for s in q.symbols])
                                body_code = f"[#v(6pt)#symbol-table(symbols: ({syms},))#v(6pt)]"
                            else:
                                span = 2
                                h = "50pt"

                        if col_index % 4 + span > 4:
                            rem = 4 - (col_index % 4)
                            for _ in range(rem):
                                lines.append("  [],")
                                col_index += 1

                        lines.append(f'  grid.cell(colspan: {span})[')
                        lines.append(f'    #science-cell(label: "{q_name}", note: "{note_str}", height-pt: {h}, body: {body_code})')
                        lines.append("  ],")
                        col_index += span

                    if col_index % 4 != 0:
                        rem = 4 - (col_index % 4)
                        for _ in range(rem):
                            lines.append("  [],")

                    lines.append(")")
                    lines.append("")

            # 英語・地歴社会
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
                    f'  {header_table_code}',
                    ")",
                    "#v(5pt)",
                    "#line(length: 100%, stroke: 1.2pt + luma(40))",
                    "#v(10pt)",
                ])

                grouped_items = []
                current_choice_group = []

                for q in questions:
                    if q.q_type == "table_fill" and (not q.symbols or len(q.symbols) <= 1):
                        current_choice_group.append(q.q_number)
                    else:
                        if current_choice_group:
                            grouped_items.append(("choice_group", current_choice_group))
                            current_choice_group = []
                        grouped_items.append(("single", q))
                if current_choice_group:
                    grouped_items.append(("choice_group", current_choice_group))

                lines.append("#columns(2, gutter: 16mm)[")
                for item in grouped_items:
                    if item[0] == "choice_group":
                        group_labels = item[1]
                        arr_str = ", ".join([f'"{lbl}"' for lbl in group_labels])
                        lines.append("  #block(breakable: false)[")
                        lines.append(f'    #compact-symbol-grid(items: ({arr_str},))')
                        lines.append("    #v(10pt)")
                        lines.append("  ]")
                    else:
                        q = item[1]
                        lines.append("  #block(breakable: false)[")
                        lines.append(f'    #text(weight: "bold", size: 10pt)[【{q.q_number}】]')
                        lines.append("    #v(3pt)")
                        if q.q_type == "char_grid":
                            c = q.chars_limit or 100
                            lines.append(f"    #char-grid(chars: {c})")
                        elif q.q_type == "graph_box":
                            lines.append("    #graph-box(height-pt: 160pt)")
                        elif q.q_type == "exact_word_fill":
                            symbols = q.symbols or [""]
                            arr = ", ".join([f'"{s}"' for s in symbols])
                            c = q.chars_limit or 4
                            lines.append(f"    #exact-char-box(symbols: ({arr},), chars: {c})")
                        elif q.q_type in ["lined_box", "free_box"]:
                            ln = q.line_count or 4
                            lines.append(f"    #lined-box(lines: {ln})")
                        elif q.q_type == "reorder":
                            lines.append("    #reorder-box()")
                        elif q.q_type == "table_fill":
                            opts = q.symbols if q.symbols else ["(1)", "(2)", "(3)", "(4)"]
                            arr = ", ".join([f'"{s}"' for s in opts])
                            lines.append(f"    #compact-symbol-grid(items: ({arr},))")
                        elif q.q_type == "word_fill":
                            symbols = q.symbols or ["(1)", "(2)"]
                            arr = ", ".join([f'"{s}"' for s in symbols])
                            lines.append(f"    #word-box(symbols: ({arr},))")
                        lines.append("    #v(12pt)")
                        lines.append("  ]")
                lines.append("]")
                lines.append("")

    return "\n".join(lines)

def compile_typst_to_pdf(typst_code, filename_prefix="output"):
    typ_path = f"{filename_prefix}.typ"
    pdf_path = f"{filename_prefix}.pdf"

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
        raise RuntimeError(f"Typstコンパイルエラー:\n{res.stderr}")

    with open(pdf_path, "rb") as f:
        return f.read()

def get_ai_prompt(selected_subject, exam_format, science_layout=""):
    if exam_format == "マークシート式（共通テスト・私大マーク型）":
        return """
You are an expert typesetter for Multiple-Choice Mark Sheet (OMR) Entrance Exams (like Japanese Common Test / 共通テスト).
Read the exam questions carefully and extract EVERY multiple-choice question and sub-question.
ZERO HALLUCINATION: Extract only questions that exist in the text.

RULES FOR MARK SHEET:
1. For each question or mark target (e.g., 問1, 問2, [1], [ア], [イ], [アイ]):
   - Set `q_type="mark_sheet"`.
   - Set `q_number` to the question or blank identifier (e.g., "問1", "ア", "[12]").
   - In `symbols`, list the options available to mark:
     - For standard 4-choice: `symbols=["1", "2", "3", "4"]`
     - For 5-choice: `symbols=["1", "2", "3", "4", "5"]`
     - For numbers 0-9: `symbols=["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"]`
     - For signs or letters: list them (e.g., `["-", "±"]` or `["A", "B", "C", "D"]`).
2. Do NOT skip any question.
3. Set `instruction` to "".
"""
    elif selected_subject == "国語":
        return """
You are a highly precise typesetter for Japanese entrance exams. Read ONLY the "設問" (Questions) section.
Mentally solve the question first to determine the box type and size. ZERO HALLUCINATION.

1. EXACT CHAR COUNT: Use `q_type="exact_word_fill"`, set `chars_limit`, and `symbols` to labels (e.g., ["A", "B"]).
2. KANJI/KANA: Use `q_type="word_fill"`, set `symbols`.
3. DESCRIPTION: If "○字以内", use `q_type="char_grid"`, set `chars_limit`. If no limit, use `q_type="free_box"`, estimate `line_count` (2 to 4).
4. MULTIPLE CHOICE: Use `q_type="table_fill"`, set `symbols`.
"""
    elif selected_subject == "英語":
        return """
You are an expert English entrance exam typesetter. Mentally solve questions to estimate required space. ZERO HALLUCINATION.

1. MULTIPLE CHOICE & LISTENING (記号選択・リスニング):
   - For single-answer multiple choice questions (e.g. Q7-Q21 listening, Q22-Q26 error correction):
     Set `q_type="table_fill"`. Do NOT put the options (a, b, c, d, e) inside symbols! Just set `symbols=None`.
   - CRITICAL: If a question has multiple blanks (e.g. "空所(1)〜(5)に当てはまる文を選べ"):
     Set `q_type="table_fill"`, and set `symbols=["(1)", "(2)", "(3)", "(4)", "(5)"]` so all blanks have distinct answer boxes!
2. WORD ORDERING (並べ替え): Use `q_type="reorder"`.
3. SHORT ANSWER: Use `q_type="word_fill"`, set `symbols`.
4. TRANSLATION/EXPLANATION: If character limit exists, use `q_type="char_grid"`. If no limit, use `q_type="lined_box"` and estimate `line_count` (3 to 6).
5. FREE ESSAY: Use `q_type="lined_box"`, estimate `line_count` (8 to 12).
"""
    elif selected_subject == "数学":
        return """
You are a Math exam typesetter.
Extract ONLY the main question numbers (e.g., 第1問, 第2問).
For questions asking to draw a graph or figure, use `q_type="graph_box"`.
Otherwise, output exactly ONE question per section with `q_number="解答欄"`, `q_type="math_box"`.
"""
    elif selected_subject == "地歴・社会":
        return """
You are an expert typesetter for University Entrance Exams in History, Geography, and Civics.
Mentally solve and construct the standard model answer for each question first to estimate space accurately. ZERO HALLUCINATION.

1. ESSAYS & DESCRIPTIONS: If character limit exists, use `q_type="char_grid"`, set `chars_limit`. If no limit, use `q_type="lined_box"`, estimate `line_count` (2 to 8 lines).
2. SHORT TERMS & IDENTIFICATION: Use `q_type="word_fill"`, set `symbols`.
3. MULTIPLE CHOICE: Use `q_type="table_fill"`, set `symbols`.
4. DRAWING / MAP ANNOTATION: Use `q_type="graph_box"`.
"""
    elif selected_subject == "理科":
        prompt_base = """You are an expert typesetter for Science university entrance exams.
Read the exam questions carefully and extract the EXACT question structure. ZERO OMISSION:
- You MUST extract EVERY explicitly numbered question and sub-question (問1, 問2, (1), (2), (a), (b)).
"""
        if "記述メイン" in science_layout:
            return prompt_base + """
[DESCRIPTIVE EXAM RULES: MENTALLY SOLVE FIRST]
1. MATH & DERIVATION BOXES (`q_type="math_box"`): Solve mentally, estimate lines (`line_count`: 4 to 12).
2. TEXT DESCRIPTIONS: "○字以内で": `q_type="char_grid"`, set `chars_limit`. Without limit: `q_type="lined_box"`, `line_count` (2 to 5).
3. DRAWING & GRAPHS: Use `q_type="graph_box"`.
4. SHORT ANSWERS: Use `q_type="free_box"`.
5. SELECTIVE SECTIONS: Generate BOTH selective sections.
"""
        else:
            return prompt_base + """
[MOCK EXAM RULES: MENTALLY SOLVE FIRST]
1. SINGLE ANSWER MULTIPLE CHOICE: Output EXACTLY ONE answer box with `q_type="table_fill"`.
2. NUMERICAL QUESTIONS: Use `q_type="word_fill"` with `symbols=None`.
3. MULTIPLE BLANKS: `symbols=["エ", "オ"]`, `q_type="word_fill"`.
4. DRAWING & GRAPHS: Use `q_type="graph_box"`.
5. TEXT DESCRIPTIONS: "○字以内で": `q_type="char_grid"`. Formula: `q_type="lined_box"`.
"""
    return "Extract questions. Set instruction to empty string."

def parse_exam_with_gemini(client, pdf_bytes, prompt):
    max_retries = 3
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
            return ExamPaper.model_validate_json(response.text)
        except Exception as api_err:
            err_str = str(api_err)
            if ("503" in err_str or "UNAVAILABLE" in err_str) and attempt < max_retries:
                time.sleep(attempt * 3)
                continue
            raise api_err

# ----------------- タブUI -----------------
tab_single, tab_batch = st.tabs(["1教科ずつ作成", "複数教科まとめて作成"])

# =========================================================
# タブ1: 1教科ずつ作成
# =========================================================
with tab_single:
    selected_subject = st.radio(
        "科目を選択してください",
        options=SUBJECT_OPTIONS,
        horizontal=True,
        key="single_subj"
    )

    exam_format = st.radio(
        "形式を選択してください",
        options=FORMAT_OPTIONS,
        horizontal=True,
        key="single_fmt"
    )

    science_layout = ""
    if selected_subject == "理科" and exam_format == "記述・論述式":
        science_layout = st.radio(
            "理科のレイアウト設定",
            options=["記述メイン（国公立・難関大風）", "記号・短答メイン（模試風）"],
            horizontal=True,
            key="single_sci"
        )

    uploaded_file = st.file_uploader("問題PDFをアップロード", type=["pdf"], key="single_uploader")

    st.markdown(f"""
    <div class="notice-box">
        ※ 過去問PDFをお持ちでない場合は、各大学の公式サイトや <a href="{TOSHIN_URL}" target="_blank" rel="noopener noreferrer">東進 過去問データベース</a> などの公式ポータル等から各自ご用意ください。
    </div>
    """, unsafe_allow_html=True)

    include_questions = st.checkbox("問題用紙もまとめて1つのPDFにする（問題 ＋ 解答用紙）", value=False, key="single_inc_q")

    if uploaded_file is not None:
        st.caption(f"読み込みファイル: {uploaded_file.name}")
        pdf_bytes = uploaded_file.read()

        with st.expander("問題PDFプレビュー", expanded=False):
            b64_pdf = base64.b64encode(pdf_bytes).decode("utf-8")
            pdf_display = f'<iframe src="data:application/pdf;base64,{b64_pdf}" width="100%" height="600" type="application/pdf" style="border: 1px solid #cbd5e1; border-radius: 4px;"></iframe>'
            st.markdown(pdf_display, unsafe_allow_html=True)

        if st.button("解答用紙を作成する", key="single_gen_btn"):
            active_api_key = user_api_key or os.environ.get("GEMINI_API_KEY")
            if not active_api_key:
                st.error("Gemini APIキーが設定されていません。ページ上部の手順に従ってAPIキーを入力してください。")
                st.stop()

            progress_text = st.empty()
            progress_bar = st.progress(0)

            try:
                progress_text.text("1/3: PDFデータを解析中...")
                progress_bar.progress(20)

                progress_text.text(f"2/3: {selected_subject}の設問構成を抽出中...")
                progress_bar.progress(50)

                client = genai.Client(api_key=active_api_key)
                prompt = get_ai_prompt(selected_subject, exam_format, science_layout)
                exam = parse_exam_with_gemini(client, pdf_bytes, prompt)
                exam.subject = selected_subject

                st.session_state["cached_exam"] = exam
                st.session_state["cached_pdf_bytes"] = pdf_bytes
                st.session_state["is_modified"] = False

                progress_text.text("3/3: B4本番用紙を組版中...")
                progress_bar.progress(80)

                typst_code = build_typst_code(exam, exam_format, selected_subject, science_layout)
                answer_sheet_bytes = compile_typst_to_pdf(typst_code, "web_output_single")

                raw_u = (exam.university or "").replace("大学", "").replace("大学名", "").strip()
                has_univ = bool(raw_u and raw_u.lower() not in ["unknown", "none", "未定"])
                raw_y = (str(exam.year) if exam.year else "").replace("年度", "").strip()
                has_year = bool(raw_y and raw_y.lower() not in ["unknown", "none", "未定"])

                name_parts = []
                if has_univ:
                    name_parts.append(f"{raw_u}大学")
                if has_year:
                    name_parts.append(f"{raw_y}年度")
                if exam.subject:
                    name_parts.append(exam.subject)

                doc_type = "問題および解答用紙" if include_questions else "解答用紙"
                name_parts.append(doc_type)
                file_display_name = f"{'_'.join(name_parts)}.pdf"

                if include_questions:
                    merger = PdfWriter()
                    for p in PdfReader(io.BytesIO(pdf_bytes)).pages:
                        merger.add_page(p)
                    for p in PdfReader(io.BytesIO(answer_sheet_bytes)).pages:
                        merger.add_page(p)
                    out = io.BytesIO()
                    merger.write(out)
                    final_pdf_bytes = out.getvalue()
                else:
                    final_pdf_bytes = answer_sheet_bytes

                st.session_state["final_pdf_bytes"] = final_pdf_bytes
                st.session_state["file_display_name"] = file_display_name

                progress_bar.progress(100)
                progress_text.text("組版が完了しました。")

            except Exception as e:
                st.error(f"エラー詳細: {str(e)}")

        if "final_pdf_bytes" in st.session_state and "file_display_name" in st.session_state:
            button_label = f"{st.session_state['file_display_name']} をダウンロード"
            if st.session_state.get("is_modified", False):
                button_label = f"{st.session_state['file_display_name']}（修正版）をダウンロード"

            st.download_button(
                label=button_label,
                data=st.session_state["final_pdf_bytes"],
                file_name=st.session_state["file_display_name"],
                mime="application/pdf",
                type="primary",
                key="single_dl_btn"
            )

            with st.expander("設問・解答欄のレイアウト微調整（任意）", expanded=False):
                st.caption("AIが自動判定した枠の種類や行数を手動で変更し、PDFを再生成できます。")
                cached_exam = st.session_state.get("cached_exam")
                if cached_exam:
                    japanese_type_options = list(TYPE_LABEL_MAP.values())
                    for sec_i, sec in enumerate(cached_exam.sections):
                        st.markdown(f"**【{sec.big_number}】**")
                        for q_i, q in enumerate(sec.questions):
                            cols = st.columns([2, 4, 3])
                            with cols[0]:
                                q.q_number = st.text_input("設問番号", value=q.q_number, key=f"qnum_{sec_i}_{q_i}")
                            with cols[1]:
                                cur_jp = TYPE_LABEL_MAP.get(q.q_type, "横罫線（和訳・英作文・短論述）")
                                new_jp = st.selectbox("枠の種類", options=japanese_type_options, index=japanese_type_options.index(cur_jp), key=f"qtype_{sec_i}_{q_i}")
                                q.q_type = LABEL_TO_TYPE_MAP[new_jp]
                            with cols[2]:
                                if q.q_type in ["lined_box", "free_box", "math_box"]:
                                    q.line_count = st.number_input("枠の高さ・行数", min_value=1, max_value=20, value=q.line_count or 4, key=f"qln_{sec_i}_{q_i}")
                                elif q.q_type == "char_grid":
                                    q.chars_limit = st.number_input("字数制限（マス数）", min_value=10, max_value=600, step=10, value=q.chars_limit or 100, key=f"qch_{sec_i}_{q_i}")
                                elif q.q_type == "exact_word_fill":
                                    q.chars_limit = st.number_input("抜き出し文字数", min_value=1, max_value=20, value=q.chars_limit or 4, key=f"qex_{sec_i}_{q_i}")
                                elif q.q_type == "table_fill":
                                    cnt = len(q.symbols) if q.symbols else 1
                                    new_cnt = st.number_input("小問・マークの個数", min_value=1, max_value=15, value=cnt, key=f"qcnt_{sec_i}_{q_i}")
                                    q.symbols = [f"({i+1})" for i in range(new_cnt)] if new_cnt > 1 else None

                    if st.button("設定を反映して再生成する", type="secondary", key="single_re_gen"):
                        new_typ = build_typst_code(cached_exam, exam_format, selected_subject, science_layout)
                        new_a_bytes = compile_typst_to_pdf(new_typ, "web_output_single")
                        if include_questions:
                            merger = PdfWriter()
                            for p in PdfReader(io.BytesIO(st.session_state["cached_pdf_bytes"])).pages:
                                merger.add_page(p)
                            for p in PdfReader(io.BytesIO(new_a_bytes)).pages:
                                merger.add_page(p)
                            out = io.BytesIO()
                            merger.write(out)
                            st.session_state["final_pdf_bytes"] = out.getvalue()
                        else:
                            st.session_state["final_pdf_bytes"] = new_a_bytes
                        st.session_state["is_modified"] = True
                        st.rerun()

# =========================================================
# タブ2: 複数教科まとめて作成（パターンA ＆ 並び順①）
# =========================================================
with tab_batch:
    batch_files = st.file_uploader(
        "複数の過去問PDFを一括アップロード",
        type=["pdf"],
        accept_multiple_files=True,
        key="batch_uploader"
    )

    if batch_files:
        st.markdown("##### 各ファイルの教科・形式を設定")
        
        batch_configs = []
        for idx, f in enumerate(batch_files):
            st.markdown(f'<div class="batch-file-card">📄 <strong>{f.name}</strong></div>', unsafe_allow_html=True)
            cols = st.columns([3, 4, 3])
            
            # ファイル名から科目を簡易推測
            default_subj_idx = 0
            fname_lower = f.name.lower()
            if "英" in fname_lower or "eng" in fname_lower:
                default_subj_idx = 1
            elif "数" in fname_lower or "math" in fname_lower:
                default_subj_idx = 2
            elif "歴" in fname_lower or "社" in fname_lower or "世" in fname_lower or "日" in fname_lower or "地" in fname_lower:
                default_subj_idx = 3
            elif "理" in fname_lower or "物" in fname_lower or "化" in fname_lower or "生" in fname_lower:
                default_subj_idx = 4
            
            with cols[0]:
                b_subj = st.selectbox("科目", options=SUBJECT_OPTIONS, index=default_subj_idx, key=f"b_subj_{idx}")
            with cols[1]:
                b_fmt = st.selectbox("形式", options=FORMAT_OPTIONS, key=f"b_fmt_{idx}")
            with cols[2]:
                b_sci = ""
                if b_subj == "理科" and b_fmt == "記述・論述式":
                    b_sci = st.selectbox("理科設定", options=["記述メイン（国公立・難関大風）", "記号・短答メイン（模試風）"], key=f"b_sci_{idx}")
                else:
                    st.write("")

            batch_configs.append({
                "file": f,
                "subject": b_subj,
                "format": b_fmt,
                "sci_layout": b_sci
            })

        if st.button("まとめて解答用紙を作成する", key="batch_gen_btn"):
            active_api_key = user_api_key or os.environ.get("GEMINI_API_KEY")
            if not active_api_key:
                st.error("Gemini APIキーが設定されていません。ページ上部の手順に従ってAPIキーを入力してください。")
                st.stop()

            total_count = len(batch_configs)
            progress_text = st.empty()
            progress_bar = st.progress(0)

            client = genai.Client(api_key=active_api_key)

            results_list = [] # 各教科の (q_bytes, a_bytes, univ, year, subj)

            try:
                for idx, item in enumerate(batch_configs):
                    f = item["file"]
                    f_subj = item["subject"]
                    f_fmt = item["format"]
                    f_sci = item["sci_layout"]

                    f.seek(0)
                    cur_q_bytes = f.read()

                    progress_text.text(f"[{idx+1}/{total_count}] {f_subj}（{f.name}）を解析中...")
                    progress_bar.progress(int((idx / total_count) * 100))

                    prompt = get_ai_prompt(f_subj, f_fmt, f_sci)
                    exam = parse_exam_with_gemini(client, cur_q_bytes, prompt)
                    exam.subject = f_subj

                    typ_code = build_typst_code(exam, f_fmt, f_subj, f_sci)
                    cur_a_bytes = compile_typst_to_pdf(typ_code, f"web_output_batch_{idx}")

                    results_list.append({
                        "q_bytes": cur_q_bytes,
                        "a_bytes": cur_a_bytes,
                        "univ": exam.university,
                        "year": exam.year,
                        "subject": f_subj
                    })

                progress_bar.progress(100)
                progress_text.text("全科目の組版が完了しました。")

                # 3種類のPDFを事前生成
                # 1. 解答用紙のみ
                merger_a = PdfWriter()
                for r in results_list:
                    for p in PdfReader(io.BytesIO(r["a_bytes"])).pages:
                        merger_a.add_page(p)
                out_a = io.BytesIO()
                merger_a.write(out_a)

                # 2. 問題用紙のみ
                merger_q = PdfWriter()
                for r in results_list:
                    for p in PdfReader(io.BytesIO(r["q_bytes"])).pages:
                        merger_q.add_page(p)
                out_q = io.BytesIO()
                merger_q.write(out_q)

                # 3. 問題 ＋ 解答（並び順①: 科目ごとに 問題 -> 解答）
                merger_qa = PdfWriter()
                for r in results_list:
                    for p in PdfReader(io.BytesIO(r["q_bytes"])).pages:
                        merger_qa.add_page(p)
                    for p in PdfReader(io.BytesIO(r["a_bytes"])).pages:
                        merger_qa.add_page(p)
                out_qa = io.BytesIO()
                merger_qa.write(out_qa)

                # 代表大学名・年度
                first_r = results_list[0]
                raw_u = (first_r["univ"] or "").replace("大学", "").replace("大学名", "").strip()
                u_str = f"{raw_u}大学" if (raw_u and raw_u.lower() not in ["unknown", "none", "未定"]) else ""
                raw_y = (str(first_r["year"]) if first_r["year"] else "").replace("年度", "").strip()
                y_str = f"{raw_y}年度" if (raw_y and raw_y.lower() not in ["unknown", "none", "未定"]) else ""

                base_prefix = "_".join([part for part in [u_str, y_str, "全科目"] if part]) or "入試過去問"

                st.session_state["batch_pdf_answers"] = out_a.getvalue()
                st.session_state["batch_pdf_questions"] = out_q.getvalue()
                st.session_state["batch_pdf_merged"] = out_qa.getvalue()
                st.session_state["batch_base_name"] = base_prefix

            except Exception as e:
                st.error(f"エラー詳細: {str(e)}")

        if "batch_pdf_answers" in st.session_state:
            st.markdown("---")
            download_choice = st.radio(
                "出力するPDFの種類を選択",
                options=["解答用紙のみ", "問題用紙のみ", "問題 ＋ 解答"],
                horizontal=True,
                key="batch_dl_choice"
            )

            base_name = st.session_state["batch_base_name"]

            if download_choice == "解答用紙のみ":
                dl_data = st.session_state["batch_pdf_answers"]
                dl_filename = f"{base_name}_解答用紙一式.pdf"
            elif download_choice == "問題用紙のみ":
                dl_data = st.session_state["batch_pdf_questions"]
                dl_filename = f"{base_name}_問題用紙一式.pdf"
            else:
                dl_data = st.session_state["batch_pdf_merged"]
                dl_filename = f"{base_name}_問題および解答用紙一式.pdf"

            st.download_button(
                label=f"📥 {dl_filename} をダウンロード",
                data=dl_data,
                file_name=dl_filename,
                mime="application/pdf",
                type="primary",
                key="batch_dl_btn"
            )

# ----------------- フッター -----------------
st.markdown(f"""
<div class="footer-container">
    <div class="footer-text">
        大学入試解答用紙ジェネレーター &mdash; 実務・学習用ツール
    </div>
    <div>
        <a href="{GOOGLE_FORM_URL}" target="_blank" class="footer-link">
            不具合報告・レイアウト改善要望
        </a>
    </div>
</div>
""", unsafe_allow_html=True)
