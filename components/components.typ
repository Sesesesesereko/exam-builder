// ==================== 英語・共通コンポーネント ====================
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

#let symbol-table(symbols: ("(1)", "(2)", "(3)", "(4)")) = {
  let count = symbols.len()
  table(
    columns: range(count).map(_ => 1fr),
    rows: (18pt, 24pt),
    align: center + horizon,
    stroke: 0.5pt + luma(80),
    ..symbols.map(s => table.cell(fill: luma(245))[#text(weight: "bold", size: 8.5pt)[#s]]),
    ..range(count).map(_ => [])
  )
}

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

// ==================== 国語専用コンポーネント（実寸本番仕様） ====================

// 1行20マス・右から左へ並ぶ本番原稿用紙（1マス 5.8mm × 6.8mm）
#let vertical-grid(chars: 60) = {
  let lines-count = calc.ceil(chars / 20)
  let cell-w = 5.8mm
  let cell-h = 6.8mm

  block(breakable: false)[
    #stack(
      dir: ltr,
      spacing: 1.8mm,
      // 右端が1行目（逆順に並べる）
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

// 漢字書き取り・短答用（縦に並ぶ正方形マス）
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
