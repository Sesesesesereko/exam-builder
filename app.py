import os
import time
import subprocess
import streamlit as st
from google import genai
from google.genai import types
from schemas.question_schema import ExamPaper

# GoogleフォームのURL（必要に応じて差し替え可能）
GOOGLE_FORM_URL = "https://forms.gle/"

st.set_page_config(
    page_title="入試解答用紙ジェネレーター",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# モダンなデザインスタイル
st.markdown("""
<style>
    .block-container { padding-top: 2rem; padding-bottom: 2rem; max-width: 850px; }
    .header-box { text-align: center; margin-bottom: 2rem; }
    .header-title { font-size: 2rem; font-weight: 800; color: #1e293b; margin-bottom: 0.5rem; }
    .header-sub { font-size: 1rem; color: #64748b; }
    div[data-testid="stFileUploader"] { margin-bottom: 1.5rem; border: 2px dashed #cbd5e1; border-radius: 12px; padding: 10px; }
    .stButton>button { width: 100%; border-radius: 10px; height: 3.4rem; font-weight: bold; font-size: 1.15rem; background: linear-gradient(135deg, #2563eb, #1d4ed8); color: white; border: none; }
    .feedback-box { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 1.2rem; margin-top: 2rem; text-align: center; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="header-box">
    <div class="header-title">📝 入試解答用紙ジェネレーター</div>
    <div class="header-sub">問題PDFをアップロードするだけで、本番仕様のB4解答用紙を自動組版します。</div>
</div>
""", unsafe_allow_html=True)

uploaded_file = st.file_uploader("過去問PDFを選択してください（英語・国語・数学・社会・理科）", type=["pdf"])

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

            progress_text.text("2/3: 設問構造の解析と解答スペースの自動算出中...")
            progress_bar.progress(50)

            client = genai.Client(api_key=api_key)
            prompt = """
あなたは大学入試の解答用紙を設計する最高峰の組版専門家です。
提供された問題PDFを詳しく精査し、解答用紙のレイアウトに必要な枠構造「のみ」を漏れなく正確に抽出してください。

【思考と枠サイズの算出ルール】
1. 科目（subject）を "国語", "英語", "数学", "社会", "理科" のいずれかで特定してください。
2. 字数制限が明記されていない記述・説明・和訳問題について:
   - あなた自身が頭の中で一度その設問を実際に解いて模範解答を作成してください。
   - その模範解答の文字数・行数を計測し、受験生が余裕をもって書けるように「1.3〜1.5倍のゆとり」を持たせた行数（line_count）を決定してください。
3. 設問の完全分離:
   - 1つの問に枝問（イ・ロ、(1)(2)など）がある場合は独立した小問として分割してください。
4. 解答欄タイプの選定:
   - char_grid: 「○字以内」の指定がある論述・要約（chars_limitにその字数を設定）。
   - vertical_grid: 国語の字数指定（自動で判別）。
   - word_fill: 漢字書き取り、用語穴埋め、英単語短答。
   - lined_box: 英文和訳、自由英作文、説明記述。
   - math_box: 数学・物理・化学などの計算記述・導出過程枠。
   - table_fill: 選択肢記号問題。
5. 解答用紙には問題文・指示文は不要です（instructionは空文字にしてください）。
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

            progress_text.text("3/3: B4本番用紙を組版中...")
            progress_bar.progress(80)

            is_kokugo = ("国語" in exam.subject)

            lines = [
                '#import "components/components.typ": *',
                "",
                '#set page(',
                '  paper: "jis-b4",',
                '  flipped: true,',
                '  margin: (x: 16mm, top: 12mm, bottom: 12mm)',
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
                    "// ヘッダー部",
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
                    "#line(length: 100%, stroke: 1pt)",
                    "#v(10pt)",
                    "",
                ])

                if is_kokugo:
                    # 国語: 1大問を原則1枚に集約し、右から左へ並べる
                    lines.append("#align(right)[")
                    lines.append("  #stack(")
                    lines.append("    dir: ltr,",
                    "    spacing: 8mm,")

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

                elif "数学" in exam.subject:
                    # 数学: ゆったりとした計算・論述余白枠
                    lines.append("#columns(2, gutter: 16mm)[")
                    for q in questions:
                        lines.append("  #block(breakable: false)[")
                        lines.append(f'    #text(weight: "bold", size: 10pt)[【{q.q_number}】]')
                        lines.append("    #v(3pt)")
                        # 推定行数や大問規模に合わせて高さを決定（デフォルト180pt）
                        lines.append("    #math-calc-box(height-pt: 190pt, divided: false)")
                        lines.append("    #v(10pt)")
                        lines.append("  ]")
                    lines.append("]")
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
                st.error(f"Typstコンパイルエラー:\n{res.stderr}")
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

            # フィードバック案内
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


