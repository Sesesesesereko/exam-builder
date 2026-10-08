// ==================== 1. 国語コンポーネント ====================
// 縦書き原稿用紙マス（1行20マス）
#let vertical-grid(chars: 60) = {
  let lines-count = calc.ceil(chars / 20)
  let cell-w = 6.2mm
  let cell-h = 7.0mm

  block(breakable: false)[
    #stack(
      dir: ltr,
      spacing: 2.0mm,
      ..range(lines-count).rev().map(line-idx => {
        let start-num = line-idx * 20
        let current-line-chars = calc.min(20, chars - start-num)
        
        stack(
          dir: ttb,
          spacing: 0pt,
          ..range(current-line-chars).map(c => {
            rect(
              width: cell-w,
              height: cell-h,
              stroke: 0.4pt + luma(100),
              fill: white
            )[]
          })
        )
      })
    )
  ]
}

// 国語専用：縦型 記号・選択肢記入枠（しっかり書ける大きめサイズ）
#let vertical-symbol-box(symbols: ("(1)", "(2)", "(3)")) = {
  let cell-w = 26pt
  let label-h = 16pt
  let input-h = 32pt
  block(breakable: false)[
    #stack(
      dir: ltr,
      spacing: 3.5mm,
      ..symbols.rev().map(s => [
        #stack(
          dir: ttb,
          spacing: 0pt,
          rect(width: cell-w, height: label-h, stroke: 0.5pt + luma(80), fill: luma(245))[#align(center + horizon)[#text(size: 8.5pt, weight: "bold")[#s]]],
          rect(width: cell-w, height: input-h, stroke: 0.5pt + luma(80), fill: white)[]
        )
      ])
    )
  ]
}

// 漢字書き取り・短答欄（大きめの正方形マス）
#let vertical-kanji-box(symbols: ("A", "B", "C", "D", "E")) = {
  let cell-s = 26pt
  block(breakable: false)[
    #stack(
      dir: ltr,
      spacing: 3.5mm,
      ..symbols.rev().map(s => [
        #stack(
          dir: ttb,
          spacing: 0pt,
          rect(width: cell-s, height: 16pt, stroke: 0.5pt + luma(80), fill: luma(245))[#align(center + horizon)[#text(size: 8.5pt, weight: "bold")[#s]]],
          rect(width: cell-s, height: cell-s, stroke: 0.5pt + luma(80), fill: white)[]
        )
      ])
    )
  ]
}

// 縦書き自由記述（字数指定なしの現代語訳や説明枠）
#let vertical-free-box(columns-count: 3) = {
  let col-w = 9.5mm
  block(breakable: false)[
    #rect(
      stroke: 0.6pt + luma(70),
      fill: white,
      inset: 0pt,
      [
        #stack(
          dir: ltr,
          spacing: 0pt,
          ..range(columns-count).map(i => [
            #rect(
              width: col-w,
              height: 135mm,
              stroke: (right: if i < columns-count - 1 { (paint: luma(180), dash: "dotted", thickness: 0.5pt) } else { none }),
              fill: none
            )[]
          ])
        )
      ]
    )
  ]
}

// ==================== 2. 英語・共通コンポーネント ====================
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
        fill: white,
        ..range(count).map(_ => [])
      )
    })
  )
}

#let lined-box(lines: 4, height-per-line: 9mm) = {
  rect(
    width: 100%,
    stroke: 0.6pt + luma(70),
    fill: white,
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

#let reorder-box(targets: ("3番目", "7番目")) = {
  let cols = ()
  for _ in targets {
    cols.push(1fr)
    cols.push(1.6fr)
  }
  grid(
    columns: cols,
    rows: (28pt,),
    stroke: 0.5pt + luma(80),
    align: center + horizon,
    fill: white,
    ..targets.map(t => (
      grid.cell(fill: luma(245))[#text(weight: "bold", size: 9pt)[#t]],
      []
    )).flatten()
  )
}

// 横書き用の記号テーブル（十分な高さを確保）
#let symbol-table(symbols: ("(1)", "(2)", "(3)", "(4)")) = {
  let count = symbols.len()
  let max-cols = calc.min(count, 6)
  table(
    columns: range(max-cols).map(_ => 1fr),
    rows: (20pt, 30pt),
    align: center + horizon,
    stroke: 0.5pt + luma(80),
    ..symbols.slice(0, max-cols).map(s => table.cell(fill: luma(245))[#text(weight: "bold", size: 9pt)[#s]]),
    ..range(max-cols).map(_ => table.cell(fill: white)[])
  )
}

#let word-box(symbols: ("(1)", "(2)")) = {
  let count = symbols.len()
  table(
    columns: range(count).map(_ => 1fr),
    rows: (20pt, 32pt),
    align: center + horizon,
    stroke: 0.5pt + luma(80),
    ..symbols.map(s => table.cell(fill: luma(245))[#text(weight: "bold", size: 9pt)[#s]]),
    ..range(count).map(_ => table.cell(fill: white)[])
  )
}

// ==================== 3. 数学コンポーネント ====================
#let math-calc-box(height-pt: 480pt, divided: true) = {
  rect(
    width: 100%,
    height: height-pt,
    stroke: 0.6pt + luma(70),
    fill: white,
    inset: 0pt,
    [
      #if divided [
        #line(start: (50%, 0%), end: (50%, 100%), stroke: (paint: luma(180), dash: "dashed", thickness: 0.5pt))
      ]
    ]
  )
}
