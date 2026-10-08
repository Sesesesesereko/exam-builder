from pydantic import BaseModel, Field
from typing import List, Literal, Optional

class QuestionBlock(BaseModel):
    q_number: str = Field(description="小問番号。例: '問1', '(1)', '問2(a)'")
    q_type: Literal["char_grid", "lined_box", "reorder", "table_fill", "word_fill", "free_box"] = Field(
        description="解答欄のタイプ: char_grid(字数マス目), lined_box(横罫線), reorder(整序), table_fill(記号・選択), word_fill(英単語抜出・短答記述), free_box(白地枠)"
    )
    instruction: Optional[str] = Field(default="", description="設問の指示")
    chars_limit: Optional[int] = Field(default=None, description="char_gridの場合の制限字数")
    line_count: Optional[int] = Field(default=3, description="lined_boxの場合の行数")
    targets: Optional[List[str]] = Field(default=None, description="reorderの場合の指定位置")
    symbols: Optional[List[str]] = Field(default=None, description="table_fill / word_fill の小問記号リスト")

class BigQuestion(BaseModel):
    big_number: str = Field(description="大問番号。例: '第1問', '第2問'")
    title: Optional[str] = Field(default="", description="大問のタイトル")
    questions: List[QuestionBlock] = Field(description="含まれる小問のリスト")

class ExamPaper(BaseModel):
    university: str = Field(default="大学入試", description="大学名")
    subject: str = Field(default="英語", description="科目名")
    year: Optional[str] = Field(default="", description="年度")
    sections: List[BigQuestion] = Field(description="大問のリスト")
