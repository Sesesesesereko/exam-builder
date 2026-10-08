import os
import sys
import json
from pathlib import Path
from google import genai
from google.genai import types
from schemas.question_schema import ExamPaper

def parse_pdf_to_exam_structure(pdf_path: str) -> ExamPaper:
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

    path_obj = Path(pdf_path).resolve()
    if not path_obj.exists():
        raise FileNotFoundError(f"ファイルが見つかりません: {path_obj}")

    print(f"1. PDFをアップロード中: {path_obj} ...")
    # ファイルオブジェクトを開いてバイナリとしてアップロード
    with open(path_obj, "rb") as f:
        uploaded_file = client.files.upload(
            file=f,
            mime_type="application/pdf"
        )

    prompt = """
あなたは大学入試の解答用紙を設計するエキスパートです。
アップロードされた入試問題PDFを詳細に分析し、受験生が実際に記述・記入するすべての解答欄の構造を抽出してください。

【抽出ルール】
1. 大学名、科目名、年度を可能な限り特定して設定してください。
2. 大問（第1問、第2問など）ごとにブロックを分割してください。
3. 各小問の解答形式を以下から正確に選択してください：
   - char_grid: 「○字以内」「○字程度」と指定された要約・説明記述（chars_limitに上限字数を数値で設定）
   - lined_box: 行数指定や一般的な和訳・記述問題（line_countに行数を設定。目安は和訳=2〜3行、短めの説明=3〜4行）
   - reorder: 語句整序問題で「○番目と○番目に入るもの」が指定されている場合（targetsに対象を文字列リストで設定。例: ["3番目", "7番目"]）
   - table_fill: 空欄補充や記号選択で、複数の記号・番号が並ぶもの（symbolsに記号リストを設定。例: ["(1)", "(2)", "(3)"]）
   - free_box: 自由英作文など、まとまった英文や計算を書く枠
4. 問題文そのものではなく、「解答欄に必要な情報（設問番号、指示、制限字数、記号一覧など）」のみを過不足なく抽出してください。
"""

    print("2. Gemini (gemini-2.5-flash) で設問構造を解析中...")
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[uploaded_file, prompt],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=ExamPaper,
            temperature=0.1,
        ),
    )

    try:
        client.files.delete(name=uploaded_file.name)
    except Exception:
        pass

    return ExamPaper.model_validate_json(response.text)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使い方: python parse_exam.py <問題PDFファイルのパス>")
        sys.exit(1)

    input_pdf = sys.argv[1]
    exam_data = parse_pdf_to_exam_structure(input_pdf)

    output_json = "parsed_exam.json"
    with open(output_json, "w", encoding="utf-8") as f:
        f.write(exam_data.model_dump_json(indent=2))

    print(f"\n3. 解析完了！ 結果を {output_json} に保存しました。")
    print(f"大学: {exam_data.university} / 科目: {exam_data.subject} / 大問数: {len(exam_data.sections)}")
