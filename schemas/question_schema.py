from typing import List, Optional
from pydantic import BaseModel, Field

class Question(BaseModel):
    q_number: str = Field(description="設問番号 (例: 問1, [1], ア, A)")
    q_type: str = Field(
        description="解答欄のタイプ: 'mark_sheet', 'table_fill', 'word_fill', 'exact_word_fill', 'char_grid', 'lined_box', 'free_box', 'math_box', 'graph_box', 'reorder'"
    )
    symbols: Optional[List[str]] = Field(default=None, description="小問記号やマークの選択肢ラベル (例: ['1','2','3','4'] や ['ア','イ'])")
    chars_limit: Optional[int] = Field(default=None, description="字数制限")
    line_count: Optional[int] = Field(default=None, description="行数")
    targets: Optional[List[str]] = Field(default=None, description="並び替え対象")

class Section(BaseModel):
    big_number: str = Field(description="大問番号 (例: 第1問, I)")
    instruction: Optional[str] = Field(default="", description="大問の指示")
    questions: List[Question] = Field(default_factory=list, description="設問リスト")

class ExamPaper(BaseModel):
    subject: str = Field(description="科目名")
    university: Optional[str] = Field(default="", description="大学名")
    year: Optional[str] = Field(default="", description="年度")
    sections: List[Section] = Field(default_factory=list, description="大問リスト")
