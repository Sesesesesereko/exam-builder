import os
import time
import subprocess
import streamlit as st
from google import genai
from google.genai import types
from schemas.question_schema import ExamPaper

# GoogleフォームのURL
GOOGLE_FORM_URL = "https://forms.gle/"

st.set_page_config(
    page_title="入試解答用紙ジェネレーター",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# モダンUIスタイル
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

# 1. 教科選択
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
            progress_text.text("1/3: PDFデータを解析準備中...")
            progress_bar.progress(20)
            pdf_bytes = uploaded_file.read()

            progress_text.text("2/3: 設問構造の解析中...")
            progress_bar.progress(50)

            client = genai.Client(api_key=api_key)

            # 科目ごとの最適化プロンプト
            if selected_subject == "数学":
                prompt = """
あなたは大学入試の解答用紙を設計する組版専門家です。
問題PDFから、各大問（第1問、第2問、大問1など）の番号とタイトルのみを抽出してください。
小問（(1), (2)など）の枠は不要です。各セクションの questions には、q_number="解答欄", q_type="math_box" の要素を1つだけ含めてください。
"""
            elif selected_subject == "国語":
                prompt = """
あなたは大学入試の解答用紙を設計する組版専門家です。
問題PDFから国語の設問構造を抽出してください。
【ルール】
1. 小問・枝問（イ・ロ、A〜Eなど）は独立したQuestion要素として分割してください。
2. 「○字以内」「○字程度」の論述は q_type="char_grid", chars_limit に字数を設定。
3. 漢字書き取り、語句短答は q_type="word_fill", symbols に記号リスト（["A","B"]等）を設定。
4. 字数指定のない説明・現代語訳は q_type="lined_box", line_count に行数（2〜3）を設定。
5. 選択肢問題は q_type="table_fill" としてください。
6. instructionは空文字にしてください。
"""
            else:
                prompt = f"""
あなたは大学入試の解答用紙を設計する組版専門家です。
提供された問題PDFから、{selected_subject}の解答欄に必要な枠構造を抽出してください。
【ルール】
1. 小問・枝問は分割してください。
2. 字数制限のある記述は q_type="char_grid", chars_limit に数値を設定。
3. 語句整序は q_type="reorder", targets に指定位置を設定。
4. 選択肢記号問題は q_type="table_fill", symbols に記号を設定。
5. 単語短答は q_type="word_fill"。
6. 記述・論述・和訳・英作文は q_type="lined_box"。模範解答を想定し余裕を持った line_count を設定。
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
                    temperature=0.1,
                ),
            )

            exam = ExamPaper.model_validate_json(response.text)
            exam.subject = selected_subject

            progress_text.text("3/3: B4本番用紙を組版中...")
            progress_bar.progress(80)

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

                # 本番仕様ヘッダー
                lines.extend([
                    "// 本番入試仕様ヘッダー",
                    "#grid(",
                    "  columns: (1fr, auto),",
                    "  gutter: 12pt,",
                    "  align: (left + top, right + top),",
                    "  [",
                    f'    #text(size: 13pt, weight: "bold")[{exam.year} {exam.university} {exam.subject} 解答用紙 【{sec.big_number}】]',
                    "    #v(3pt)",
                    '    #text(size: 7.5pt, fill: luma(90))[※受験番号および氏名を正確に記入し、※印欄には何も記入してはならない。]',
                    "  ],",
                    "  [",
                    "    #table(",
                    "      columns: (45pt, 65pt, 35pt, 75pt, 45pt),",
                    "      rows: (18pt, 22pt),",
                    "      stroke: 0.5pt + luma(80),",
                    "      align: center + horizon,",
                    '      fill: (col, row) => if row == 0 { luma(245) } else { none },',
                    '      [受験番号], table.cell(rowspan: 2)[], [氏名], table.cell(rowspan: 2)[], table.cell(fill: luma(235))[※得点],',
                    '      [], [], table.cell(stroke: (top: 0.5pt + luma(80)))[]',
                    "    )",
                    "  ]",
                    ")",
                    "#v(2pt)",
                    "#line(length: 100%, stroke: 1.2pt)",
                    "#v(10pt)",
                    "",
                ])

                if selected_subject == "国語":
                    # 国語: 1大問＝1枚に集約し、右から左へ並べる
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
                        elif q.q_type in ["lined_box", "free_box"]:
                            ln = q.line_count or 3
                            lines.append(f"      #vertical-free-box(columns-count: {ln})")
                        elif q.q_type == "word_fill":
                            symbols = q.symbols or ["A", "B", "C", "D", "E"]
                            arr = ", ".join([f'"{s}"' for s in symbols])
                            lines.append(f"      #vertical-kanji-box(symbols: ({arr},))")
                        elif q.q_type == "table_fill":
                            symbols = q.symbols or ["(1)", "(2)", "(3)"]
                            arr = ", ".join([f'"{s}"' for s in symbols])
                            lines.append(f"      #symbol-table(symbols: ({arr},))")

                        lines.append("    ],")

                    lines.append("  )")
                    lines.append("]")
                    lines.append("")

                elif selected_subject == "数学":
                    # 数学: 1大問につき広大な計算・論述余白枠を1枚配置
                    lines.append("  #math-calc-box(height-pt: 480pt, divided: true)")
                    lines.append("")

                else:
                    # 英語・社会・理科: 2段組
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
                st.error("組版処理中にエラーが発生しました。設問形式をご確認ください。")
                st.stop()

            with open(pdf_path, "rb") as f:
                result_pdf_bytes = f.read()

            progress_bar.progress(100)
            progress_text.text("✨ 本番仕様の解答用紙が完成しました！")
            st.balloons()

            file_display_name = f"{exam.university}_{exam.subject}_解答用紙.pdf".replace(" ", "_")
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
            st.error("処理中にエラーが発生しました。PDFの形式をご確認の上、もう一度お試しください。")
