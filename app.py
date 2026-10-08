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

            progress_text.text("2/3: 設問構造を抽出中...")
            progress_bar.progress(50)

            client = genai.Client(api_key=api_key)

            if selected_subject == "国語":
                prompt = """
あなたは大学入試（東大・京大・難関大）の国語解答用紙を設計する最高峰の組版専門家です。
問題PDFに存在する各大問（第一問、第二問、第三問など）と、それに含まれる小問（一、二、三…）を、問題文の末尾にある「設問」から正確に抽出してください。

【超重要ルール】
1. 架空の選択肢や記号（ア・イ・ウ・エ等）を勝手に捏造することは絶対に禁止です。問題文に「選べ」と書いてある場合のみ table_fill にしてください。
2. 漢字書き取り問題（設問一など。カタカナや漢字の書き取り）:
   - q_type="word_fill"
   - symbols には問題で指定されている記号一覧（例: ["ア", "イ", "ウ", "エ", "オ"] や ["A", "B", "C", "D", "E"]）を入れてください。
3. 説明記述・現代語訳・理由説明問題（設問二、三、四など。〜を説明せよ、〜を現代語訳せよ）:
   - 「○字以内」と指定がある場合: q_type="char_grid", chars_limit に字数を設定。
   - 字数指定がない場合（東大標準）: q_type="free_box", line_count に行数（目安2行〜3行）を設定。
4. 抜き出し問題（二字、四字で抜き出せなど）:
   - q_type="word_fill", symbols に ["抜き出し"] を設定。
5. 大学名や年度がPDFに明記されていない場合は空文字にしてください（推測禁止）。
6. instructionは空文字にしてください。
"""
            elif selected_subject == "数学":
                prompt = """
問題PDFから各大問（第1問、第2問など）の番号とタイトルのみを抽出してください。
各セクションの questions には q_number="解答欄", q_type="math_box" の要素を1つだけ含めてください。
"""
            else:
                prompt = f"""
提供された問題PDFから、{selected_subject}の設問構造を一問も漏らさず正確に抽出してください。
架空の設問を捏造せず、問題に存在する設問のみを忠実に抽出してください。
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

            univ_display = exam.university if exam.university and "unknown" not in exam.university.lower() else "    大学"
            year_display = exam.year if exam.year and "unknown" not in str(exam.year).lower() else "  年度"

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
                sheet_count += 1
                if sheet_count > 1:
                    lines.append("#pagebreak()")

                if selected_subject == "国語":
                    # 国語: 1大問＝B4横1枚完結。右側に縦型ヘッダー帯、左側に全設問を右から並べる
                    lines.append("#grid(")
                    lines.append("  columns: (1fr, 32mm),")
                    lines.append("  gutter: 14mm,")
                    lines.append("  [")
                    lines.append("    #align(right)[")
                    lines.append("      #stack(")
                    lines.append("        dir: ltr,")
                    lines.append("        spacing: 9mm,")

                    # 右から左へ設問を並べる
                    for q in reversed(questions):
                        lines.append("        block(breakable: false)[")
                        lines.append(f'          #align(center)[#text(weight: "bold", size: 10pt)[【{q.q_number}】]]')
                        lines.append("          #v(6pt)")

                        if q.q_type == "char_grid":
                            c = q.chars_limit or 60
                            lines.append(f"          #vertical-grid(chars: {c})")
                        elif q.q_type == "word_fill":
                            symbols = q.symbols or ["ア", "イ", "ウ", "エ", "オ"]
                            arr = ", ".join([f'"{s}"' for s in symbols])
                            lines.append(f"          #vertical-kanji-box(symbols: ({arr},))")
                        elif q.q_type == "table_fill":
                            symbols = q.symbols or ["(1)", "(2)"]
                            arr = ", ".join([f'"{s}"' for s in symbols])
                            lines.append(f"          #vertical-symbol-box(symbols: ({arr},))")
                        else:
                            # 現代文・古文・漢文の記述枠（行数2〜3行の縦書き枠）
                            ln = q.line_count or 2
                            lines.append(f"          #vertical-free-box(columns-count: {ln})")

                        lines.append("        ],")

                    lines.append("      )")
                    lines.append("    ]")
                    lines.append("  ],")

                    # 右側ヘッダー（本番入試仕様）
                    lines.append("  [")
                    lines.append("    #rect(width: 100%, height: 100%, stroke: 0.8pt + luma(60), fill: white, inset: 0pt)[")
                    lines.append("      #stack(")
                    lines.append("        dir: ttb,")
                    lines.append("        spacing: 0pt,")
                    lines.append('        rect(width: 100%, height: 35pt, stroke: (bottom: 0.5pt), fill: luma(245))[#align(center + horizon)[#text(size: 11pt, weight: "bold")[国語 解答用紙]]],')
                    lines.append(f'        rect(width: 100%, height: 30pt, stroke: (bottom: 0.5pt), fill: white)[#align(center + horizon)[#text(size: 9.5pt, weight: "bold")[【{sec.big_number}】]]],')
                    lines.append(f'        rect(width: 100%, height: 42pt, stroke: (bottom: 0.5pt), fill: white)[#align(center + horizon)[#text(size: 8.5pt)[{year_display}\n{univ_display}]]],')
                    lines.append('        rect(width: 100%, height: 18pt, stroke: (bottom: 0.5pt), fill: luma(245))[#align(center + horizon)[#text(size: 8pt)[学部・日程]]],')
                    lines.append('        rect(width: 100%, height: 32pt, stroke: (bottom: 0.5pt), fill: white)[],')
                    lines.append('        rect(width: 100%, height: 18pt, stroke: (bottom: 0.5pt), fill: luma(245))[#align(center + horizon)[#text(size: 8pt)[受験番号]]],')
                    lines.append('        rect(width: 100%, height: 40pt, stroke: (bottom: 0.5pt), fill: white)[],')
                    lines.append('        rect(width: 100%, height: 18pt, stroke: (bottom: 0.5pt), fill: luma(245))[#align(center + horizon)[#text(size: 8pt)[氏名]]],')
                    lines.append('        rect(width: 100%, height: 50pt, stroke: (bottom: 0.5pt), fill: white)[],')
                    lines.append('        rect(width: 100%, height: 18pt, stroke: (bottom: 0.5pt), fill: luma(235))[#align(center + horizon)[#text(size: 8pt)[※得点]]],')
                    lines.append('        rect(width: 100%, height: 40pt, stroke: none, fill: white)[]')
                    lines.append("      )")
                    lines.append("    ]")
                    lines.append("  ]")
                    lines.append(")")
                    lines.append("")

                elif selected_subject == "数学":
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
