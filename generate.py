import os
import sys
import json
import time
import subprocess
from pathlib import Path
from google import genai
from google.genai import types
from schemas.question_schema import ExamPaper

def get_target_pdf() -> Path:
    if len(sys.argv) > 1:
        p = Path(sys.argv[1]).resolve()
        if p.exists() and p.is_file():
            return p
        print(f"指定されたファイルが見つかりません: {sys.argv[1]}")

    candidates = [
        f for f in Path(".").glob("*.pdf") 
        if f.name not in ["test.pdf", "answer_sheet.pdf"]
    ]
    if candidates:
        return candidates[0].resolve()

    raise FileNotFoundError("解析対象のPDFファイルが見つかりません。")

def parse_with_gemini(pdf_path: Path) -> ExamPaper:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("環境変数 GEMINI_API_KEY が設定されていません。")

    client = genai.Client(api_key=api_key)

    print(f"\n[1/3] 対象PDFを確認中: {pdf_path.name}")
    
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    print("[2/3] Gemini (gemini-3.8-flash) にPDFを送信して設問構造を解析中...")

    prompt = """
あなたは大学入試の解答用紙を設計する組版の専門家です。
提供された問題PDFから、解答欄のレイアウトに必要な枠構造「のみ」を正確に抽出してください。

【最重要判定ルール】
1. 解答用紙には問題文や指示文は一切不要です（instructionは空文字にしてください）。
2. 小問番号（q_number）は「問1」「問2」「(1)」のように番号のみを抽出してください。
3. 解答欄形式（q_type）の選定（誤判定に厳重注意）：
   - table_fill: 【最優先】選択肢（1〜4、A〜D、ア〜エ等）から選ぶ記号問題、正誤判定（T/F）、空欄に記号を当てはめる問題はすべてこれです。マスを大きくしてはいけません。
   - word_fill: 本文から英単語や短い連語を「スペルで抜き出して書かせる」短答記述問題のみこれです。記号を選ぶ問題には絶対に割り当てないでください。
   - char_grid: 「○字以内」「○字程度」の日本語要約・説明記述（chars_limitに制限文字数を設定）。
   - lined_box: 英文和訳、下線部説明、自由英作文（line_countに行数を設定。和訳は2〜3行、自由英作文は12〜15行程度）。
   - reorder: 語句整序で「3番目」「7番目」などを書かせる場合（targetsに設定）。
"""

    max_retries = 4
    for attempt in range(1, max_retries + 1):
        try:
            response = client.models.generate_content(
                model="gemini-3.8-flash",
                contents=[
                    types.Part.from_bytes(
                        data=pdf_bytes,
                        mime_type="application/pdf",
                    ),
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
                    wait_time = attempt * 5
                    print(f"サーバー混雑中 (503)。{wait_time}秒後に再試行します... (試行 {attempt}/{max_retries})")
                    time.sleep(wait_time)
                    continue
            raise e

    exam_paper = ExamPaper.model_validate_json(response.text)
    
    with open("parsed_exam.json", "w", encoding="utf-8") as f:
        f.write(exam_paper.model_dump_json(indent=2))
        
    return exam_paper

def generate_typst_and_pdf(exam: ExamPaper):
    print("\n[3/3] 大問ごとの改ページレイアウトでPDFをコンパイル中...")
    
    lines = [
        '#import "components/components.typ": *',
        "",
        '#set page(paper: "jis-b4", flipped: true, margin: (x: 18mm, top: 14mm, bottom: 14mm))',
        '#set text(font: "Yu Gothic", size: 9.5pt)',
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
    with open("answer_sheet.typ", "w", encoding="utf-8") as f:
        f.write(typst_code)

    res = subprocess.run("typst compile answer_sheet.typ answer_sheet.pdf", shell=True, capture_output=True, encoding="utf-8", errors="replace")
    if res.returncode != 0:
        print("Typstコンパイルエラー:\n", res.stderr)
        return False

    print("\n==========================================")
    print("✨ 最適化された解答用紙PDFを生成しました！")
    print("ファイル名: answer_sheet.pdf")
    print("==========================================")
    return True

def main():
    try:
        target = get_target_pdf()
        exam_data = parse_with_gemini(target)
        success = generate_typst_and_pdf(exam_data)
        if success:
            subprocess.run("start answer_sheet.pdf", shell=True)
    except Exception as e:
        print(f"\nエラーが発生しました: {e}")

if __name__ == "__main__":
    main()
