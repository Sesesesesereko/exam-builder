#import "components/components.typ": *

#set page(paper: "jis-b4", flipped: true, margin: (x: 18mm, top: 14mm, bottom: 14mm))
#set text(font: "Yu Gothic", size: 9.5pt)

#grid(
  columns: (1fr, auto),
  align: (left + horizon, right + horizon),
  text(size: 13pt, weight: "bold")[2021 北海道大学 英語 解答用紙 【第1問】],
  table(
    columns: (55pt, 85pt),
    rows: (20pt,),
    align: center + horizon,
    stroke: 0.5pt + luma(80),
    [受験番号], []
  )
)
#v(3pt)
#line(length: 100%, stroke: 0.8pt)
#v(10pt)

// 2段組（左右均等レイアウト）
#columns(2, gutter: 16mm)[
  #text(weight: "bold", size: 10pt)[【1】]
  #v(2pt)
  #char-grid(chars: 100)
  #v(10pt)
  #text(weight: "bold", size: 10pt)[【2】]
  #v(2pt)
  #lined-box(lines: 3)
  #v(10pt)
  #text(weight: "bold", size: 10pt)[【3】]
  #v(2pt)
  #symbol-table(symbols: ("(A)", "(B)", "(C)",))
  #v(10pt)
  #text(weight: "bold", size: 10pt)[【4】]
  #v(2pt)
  #symbol-table(symbols: ("(あ)", "(い)", "(う)",))
  #v(10pt)
]

#pagebreak()
#grid(
  columns: (1fr, auto),
  align: (left + horizon, right + horizon),
  text(size: 13pt, weight: "bold")[2021 北海道大学 英語 解答用紙 【第2問】],
  table(
    columns: (55pt, 85pt),
    rows: (20pt,),
    align: center + horizon,
    stroke: 0.5pt + luma(80),
    [受験番号], []
  )
)
#v(3pt)
#line(length: 100%, stroke: 0.8pt)
#v(10pt)

// 2段組（左右均等レイアウト）
#columns(2, gutter: 16mm)[
  #text(weight: "bold", size: 10pt)[【1】]
  #v(2pt)
  #symbol-table(symbols: ("(1)", "(2)", "(3)", "(4)",))
  #v(10pt)
  #text(weight: "bold", size: 10pt)[【2】]
  #v(2pt)
  #char-grid(chars: 80)
  #v(10pt)
  #text(weight: "bold", size: 10pt)[【3】]
  #v(2pt)
  #symbol-table(symbols: ("(あ)", "(い)", "(う)", "(え)",))
  #v(10pt)
  #text(weight: "bold", size: 10pt)[【4】]
  #v(2pt)
  #reorder-box(targets: ("2番目", "5番目",))
  #v(10pt)
  #text(weight: "bold", size: 10pt)[【5】]
  #v(2pt)
  #symbol-table(symbols: ("(1)", "(2)", "(3)", "(4)",))
  #v(10pt)
  #text(weight: "bold", size: 10pt)[【6】]
  #v(2pt)
  #word-box(symbols: ("(1)", "(2)",))
  #v(10pt)
  #text(weight: "bold", size: 10pt)[【7】]
  #v(2pt)
  #symbol-table(symbols: ("(1)", "(2)", "(3)", "(4)",))
  #v(10pt)
  #text(weight: "bold", size: 10pt)[【8】]
  #v(2pt)
  #symbol-table(symbols: ("(1)", "(2)", "(3)", "(4)",))
  #v(10pt)
]

#pagebreak()
#grid(
  columns: (1fr, auto),
  align: (left + horizon, right + horizon),
  text(size: 13pt, weight: "bold")[2021 北海道大学 英語 解答用紙 【第3問】],
  table(
    columns: (55pt, 85pt),
    rows: (20pt,),
    align: center + horizon,
    stroke: 0.5pt + luma(80),
    [受験番号], []
  )
)
#v(3pt)
#line(length: 100%, stroke: 0.8pt)
#v(10pt)

// 2段組（左右均等レイアウト）
#columns(2, gutter: 16mm)[
  #text(weight: "bold", size: 10pt)[【設問】]
  #v(2pt)
  #lined-box(lines: 12)
  #v(10pt)
]
