// ==================== 1. 国語コンポーネント ====================
// 縦書き原稿用紙マス（1行20マス、右から左へ並ぶ本番仕様）
#let vertical-grid(chars: 60) = {
  let lines-count = calc.ceil(chars / 20)
  let cell-w = 5.8mm
  let cell-h = 6.8mm

  block(breakable: false)[
    #stack(
      dir: ltr,
      spacing: 1.8mm,
      ..range(lines-count).rev().map(line-idx => {
        let start-num = line-idx * 20
        let current-line-chars = calc.min(20, chars - start-num)
        
        stack(
          dir: ttb,
          spacing: 0pt,
          ..range(current-line-chars).map(c => {
            let is-tenth = (c == 9 or c == 19)
            let bottom-stroke = if is-tenth { 1.2pt + luma(30) } else { 0.4pt + luma(110) }
            rect(
              width: cell-w,
              height: cell-h,
              stroke: (
                top: 0.4pt + luma(110),
                bottom: bottom-stroke,
                left: 0.4pt + luma(110),
                right: 0.4pt + luma(110),
              ),
              fill: none
            )[]
          })
        )
      })
    )
  ]
}

// 漢字書き取り・短答欄（縦型正方形マス）
#let vertical-kanji-box(symbols: ("A", "B", "C", "D", "E")) = {
  let cell-s = 18pt
  block(breakable: false)[
    #stack(
      dir: ltr,
      spacing: 3mm,
      ..symbols.rev().map(s => [
        #stack(
          dir: ttb,
          spacing: 0pt,
          rect(width: cell-s, height: 14pt, stroke: 0.5pt + luma(80), fill: luma(245))[#align(center + horizon)[#text(size: 8pt, weight: "bold")[#s]]],
          rect(width: cell-s, height: cell-s, stroke: 0.5pt + luma(80))[]
        )
      ])
    )
  ]
}

// 縦書き自由記述（字数指定なしの現代語訳や説明枠）
#let vertical-free-box(columns-count: 3) = {
  let col-w = 8mm
  block(breakable: false)[
    #rect(
      stroke: 0.6pt + luma(70),
      inset: 0pt,
      [
        #stack(
          dir: ltr,
          spacing: 0pt,
          ..range(columns-count).map(i => [
            #rect(
              width: col-w,
              height: 140mm,
              stroke: (right: if i < columns-count - 1 { (paint: luma(180), dash: "dotted", thickness: 0.5pt) } else { none }),
              fill: none
            )[]
          ])
        )
      ]
    )
  ]
}

// ==================== 2. 英語・地歴・共通コンポーネント ====================
// 横書きマス目（英語要約、地歴論述用）
#let char-grid(chars: 100, cols-per-line: 20) = {
  let rows = calc.ceil(chars / cols-per-line)
  let cell-size = 6.5mm
  stack(
    spacing: 2.5pt,
    ..range(rows).map(r => {
      let start-idx = r * cols-per-line
      let count = calc.min(cols-per-line, chars - start-idx)
      grid(
        columns: range(count).map(_ => cell-size),
        rows: (cell-size,),
        stroke: 0.4pt + luma(100),
        align: center + horizon,
        ..range(count).map(_ => [])
      )
    })
  )
}

// 横罫線（和訳・自由英作文用）
#let lined-box(lines: 4, height-per-line: 8.5mm) = {
  rect(
    width: 100%,
    stroke: 0.6pt + luma(70),
    outset: 0pt,
    inset: 0pt,
    [
      #stack(
        ..range(lines - 1).map(_ => [
          #v(height-per-line)
          #line(length: 100%, stroke: (paint: luma(180), dash: "dotted", thickness: 0.5pt))
        ]),
        v(height-per-line)
      )
    ]
  )
}

// 語句整序枠
#let reorder-box(targets: ("3番目", "7番目")) = {
  let cols = ()
  for _ in targets {
    cols.push(1fr)
    cols.push(1.6fr)
  }
  grid(
    columns: cols,
    rows: (26pt,),
    stroke: 0.5pt + luma(80),
    align: center + horizon,
    ..targets.map(t => (
      grid.cell(fill: luma(245))[#text(weight: "bold", size: 9pt)[#t]],
      []
    )).flatten()
  )
}

// 記号選択・短答テーブル
#let symbol-table(symbols: ("(1)", "(2)", "(3)", "(4)")) = {
  let count = symbols.len()
  let max-cols = calc.min(count, 4)
  table(
    columns: range(max-cols).map(_ => 1fr),
    rows: (18pt, 24pt),
    align: center + horizon,
    stroke: 0.5pt + luma(80),
    ..symbols.slice(0, max-cols).map(s => table.cell(fill: luma(245))[#text(weight: "bold", size: 8.5pt)[#s]]),
    ..range(max-cols).map(_ => [])
  )
}

// 単語・用語記述枠
#let word-box(symbols: ("(1)", "(2)")) = {
  let count = symbols.len()
  table(
    columns: range(count).map(_ => 1fr),
    rows: (18pt, 30pt),
    align: center + horizon,
    stroke: 0.5pt + luma(80),
    ..symbols.map(s => table.cell(fill: luma(245))[#text(weight: "bold", size: 9pt)[#s]]),
    ..range(count).map(_ => [])
  )
}

// ==================== 3. 数学・理科コンポーネント ====================
// 計算・記述余白枠（高さ指定可能、中央破線で二段に分ける標準形式）
#let math-calc-box(height-pt: 180pt, divided: true) = {
  rect(
    width: 100%,
    height: height-pt,
    stroke: 0.6pt + luma(70),
    inset: 0pt,
    [
      #if divided [
        #line(start: (50%, 0%), end: (50%, 100%), stroke: (paint: luma(180), dash: "dashed", thickness: 0.5pt))
      ]
    ]
  )
}
