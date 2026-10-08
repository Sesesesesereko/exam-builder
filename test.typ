#import "components/components.typ": *

#set page(paper: "jis-b4", flipped: true, margin: 15mm)
#set text(font: "Yu Gothic", size: 10pt)

= 解答用紙 部品テスト

== 1. 和訳問題（3行罫線）
#lined-box(lines: 3)

== 2. 要約・内容説明（80字マス目）
#char-grid(chars: 80)

== 3. 語句整序（3番目と6番目）
#reorder-box(targets: ("3番目", "6番目"))

== 4. 記号選択・空欄補充
#symbol-table(symbols: ("(ア)", "(イ)", "(ウ)", "(エ)"))
