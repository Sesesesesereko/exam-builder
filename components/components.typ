// ==================== 1. 国語 本番仕様コンポーネント ====================
#let vertical-kanji-box(symbols: ("ア", "イ", "ウ", "エ", "オ")) = {
  let cell-w = 34pt
  let label-h = 16pt
  let input-h = 75pt
  let max-per-col = 5
  let cols = calc.ceil(symbols.len() / max-per-col)
  
  block(breakable: false)[
    #stack(
      dir: ltr,
      spacing: 5mm,
      ..range(cols).rev().map(c => {
        let start = c * max-per-col
        let end = calc.min(symbols.len(), start + max-per-col)
        let col-symbols = symbols.slice(start, end)
        stack(
          dir: ttb,
          spacing: 3.5mm,
          ..col-symbols.map(s => [
            #stack(
              dir: ttb,
              spacing: 0pt,
              rect(width: cell-w, height: label-h, stroke: 0.5pt + luma(80), fill: luma(245))[#align(center + horizon)[#text(size: 8.5pt, weight: "bold")[#s]]],
              rect(width: cell-w, height: input-h, stroke: 0.6pt + luma(70), fill: white)[]
            )
          ])
        )
      })
    )
  ]
}

#let exact-char-box(symbols: ("A", "B"), chars: 4) = {
  let cell-s = 18.5pt
  let label-h = 16pt
  block(breakable: false)[
    #stack(
      dir: ltr,
      spacing: 4mm,
      ..symbols.rev().map(s => [
        #stack(
          dir: ttb,
          spacing: 0pt,
          rect(width: cell-s, height: label-h, stroke: 0.5pt + luma(80), fill: luma(245))[#align(center + horizon)[#text(size: 8.5pt, weight: "bold")[#s]]],
          ..range(chars).map(_ => rect(
            width: cell-s,
            height: cell-s,
            stroke: 0.5pt + luma(70),
            fill: white
          )[])
        )
      ])
    )
  ]
}

#let vertical-symbol-box(symbols: ("(1)", "(2)")) = {
  let cell-w = 28pt
  let label-h = 16pt
  let input-h = 32pt
  let max-per-col = 6
  let cols = calc.ceil(symbols.len() / max-per-col)
  
  block(breakable: false)[
    #stack(
      dir: ltr,
      spacing: 4mm,
      ..range(cols).rev().map(c => {
        let start = c * max-per-col
        let end = calc.min(symbols.len(), start + max-per-col)
        let col-symbols = symbols.slice(start, end)
        stack(
          dir: ttb,
          spacing: 3.5mm,
          ..col-symbols.map(s => [
            #stack(
              dir: ttb,
              spacing: 0pt,
              rect(width: cell-w, height: label-h, stroke: 0.5pt + luma(80), fill: luma(245))[#align(center + horizon)[#text(size: 8.5pt, weight: "bold")[#s]]],
              rect(width: cell-w, height: input-h, stroke: 0.6pt + luma(70), fill: white)[]
            )
          ])
        )
      })
    )
  ]
}

#let vertical-free-box(columns-count: 2) = {
  let col-w = 11.5mm
  block(breakable: false)[
    #rect(
      stroke: 0.7pt + luma(60),
      fill: white,
      inset: 0pt,
      [
        #stack(
          dir: ltr,
          spacing: 0pt,
          ..range(columns-count).map(i => [
            #rect(
              width: col-w,
              height: 155mm,
              stroke: (right: if i < columns-count - 1 { (paint: luma(180), dash: "dotted", thickness: 0.5pt) } else { none }),
              fill: none
            )[]
          ])
        )
      ]
    )
  ]
}

#let vertical-grid(chars: 60) = {
  let lines-count = calc.ceil(chars / 20)
  let cell-w = 6.5mm
  let cell-h = 7.4mm
  block(breakable: false)[
    #stack(
      dir: ltr,
      spacing: 2.5mm,
      ..range(lines-count).rev().map(line-idx => {
        let start-num = line-idx * 20
        let current-line-chars = calc.min(20, chars - start-num)
        stack(
          dir: ttb,
          spacing: 0pt,
          ..range(current-line-chars).map(_ => rect(
            width: cell-w,
            height: cell-h,
            stroke: 0.4pt + luma(90),
            fill: white
          )[])
        )
      })
    )
  ]
}

// ==================== 2. 数学コンポーネント ====================
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

// ==================== 3. 英語・共通コンポーネント ====================
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

#let symbol-table(symbols: ("(1)", "(2)", "(3)", "(4)")) = {
  let count = symbols.len()
  let cols-per-row = 4
  let rows-count = calc.ceil(count / cols-per-row)
  
  stack(
    spacing: 4pt,
    ..range(rows-count).map(r => {
      let start = r * cols-per-row
      let end = calc.min(count, start + cols-per-row)
      let sub-symbols = symbols.slice(start, end)
      let fill-count = cols-per-row - sub-symbols.len()
      
      table(
        columns: range(cols-per-row).map(_ => 1fr),
        rows: (18pt, 28pt),
        align: center + horizon,
        stroke: 0.5pt + luma(80),
        ..sub-symbols.map(s => table.cell(fill: luma(245))[#text(weight: "bold", size: 9pt)[#s]]),
        ..range(fill-count).map(_ => table.cell(stroke: none)[]),
        ..range(sub-symbols.len()).map(_ => table.cell(fill: white)[]),
        ..range(fill-count).map(_ => table.cell(stroke: none)[])
      )
    })
  )
}

#let word-box(symbols: ("(1)", "(2)")) = {
  let count = symbols.len()
  let cols-per-row = 4
  let rows-count = calc.ceil(count / cols-per-row)
  
  stack(
    spacing: 4pt,
    ..range(rows-count).map(r => {
      let start = r * cols-per-row
      let end = calc.min(count, start + cols-per-row)
      let sub-symbols = symbols.slice(start, end)
      let fill-count = cols-per-row - sub-symbols.len()
      
      table(
        columns: range(cols-per-row).map(_ => 1fr),
        rows: (18pt, 30pt),
        align: center + horizon,
        stroke: 0.5pt + luma(80),
        ..sub-symbols.map(s => table.cell(fill: luma(245))[#text(weight: "bold", size: 9pt)[#s]]),
        ..range(fill-count).map(_ => table.cell(stroke: none)[]),
        ..range(sub-symbols.len()).map(_ => table.cell(fill: white)[]),
        ..range(fill-count).map(_ => table.cell(stroke: none)[])
      )
    })
  )
}

// ==================== 4. 理科模試仕様テーブルコンポーネント ====================
// 横並びでコンパクトに問1、問2、問3と詰めて配置するセル
#let science-cell(label: "問1", note: "", width-scale: 1, height-pt: 30pt, body: []) = {
  let w = if width-scale == 1 { 50pt } else if width-scale == 2 { 110pt } else { 1fr }
  box(width: w, stroke: 0.5pt + luma(80))[
    #stack(
      dir: ttb,
      rect(
        width: 100%,
        height: 16pt,
        stroke: (bottom: 0.5pt + luma(80)),
        fill: luma(245),
        align(center + horizon)[#text(size: 8pt, weight: "bold")[#label #if note != "" [#text(size: 6.5pt, fill: luma(100))[（#note）]]]]
      ),
      rect(
        width: 100%,
        height: height-pt,
        stroke: none,
        fill: white,
        align(center + horizon)[#body]
      )
    )
  ]
}
