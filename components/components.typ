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
              rect(width: cell-w, height: label-h, stroke: 0.6pt + luma(40), fill: white)[#align(center + horizon)[#text(size: 8.5pt, weight: "bold")[#s]]],
              rect(width: cell-w, height: input-h, stroke: 0.6pt + luma(40), fill: white)[]
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
          rect(width: cell-s, height: label-h, stroke: 0.6pt + luma(40), fill: white)[#align(center + horizon)[#text(size: 8.5pt, weight: "bold")[#s]]],
          ..range(chars).map(_ => rect(
            width: cell-s,
            height: cell-s,
            stroke: 0.5pt + luma(40),
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
              rect(width: cell-w, height: label-h, stroke: 0.6pt + luma(40), fill: white)[#align(center + horizon)[#text(size: 8.5pt, weight: "bold")[#s]]],
              rect(width: cell-w, height: input-h, stroke: 0.6pt + luma(40), fill: white)[]
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
      stroke: 0.7pt + luma(40),
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
              stroke: (right: if i < columns-count - 1 { (paint: luma(160), dash: "dotted", thickness: 0.5pt) } else { none }),
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
            stroke: 0.5pt + luma(40),
            fill: white
          )[])
        )
      })
    )
  ]
}

// ==================== 2. 数学・理科・共通コンポーネント ====================
#let math-calc-box(height-pt: 480pt, divided: true) = {
  rect(
    width: 100%,
    height: height-pt,
    stroke: 0.7pt + luma(40),
    fill: white,
    inset: 0pt,
    [
      #if divided [
        #line(start: (50%, 0%), end: (50%, 100%), stroke: (paint: luma(160), dash: "dashed", thickness: 0.5pt))
      ]
    ]
  )
}

#let science-calc-box(height-pt: 120pt) = {
  rect(
    width: 100%,
    height: height-pt,
    stroke: 0.7pt + luma(40),
    fill: white,
    inset: 5pt,
    [
      #align(top + left)[#text(size: 8pt, fill: luma(80))[【計算過程・理由等】]]
    ]
  )
}

#let graph-box(height-pt: 180pt) = {
  rect(
    width: 100%,
    height: height-pt,
    stroke: 0.7pt + luma(40),
    fill: white,
    inset: 5pt,
    [
      #align(top + left)[#text(size: 8pt, fill: luma(80))[【作図・グラフ・図示】]]
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
        stroke: 0.5pt + luma(40),
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
    stroke: 0.7pt + luma(40),
    fill: white,
    inset: 0pt,
    [
      #stack(
        ..range(lines - 1).map(_ => [
          #v(height-per-line)
          #line(length: 100%, stroke: (paint: luma(160), dash: "dotted", thickness: 0.5pt))
        ]),
        v(height-per-line)
      )
    ]
  )
}

#let reorder-box(targets: (), count: 6) = {
  let total = calc.max(count, 6)
  let cells = ()
  for i in range(total) {
    cells.push(
      rect(
        width: 22pt,
        height: 24pt,
        stroke: 0.6pt + luma(40),
        fill: white
      )[]
    )
    if i < total - 1 {
      cells.push(
        align(center + horizon)[#text(size: 10pt, fill: luma(40))[→]]
      )
    }
  }
  stack(
    dir: ltr,
    spacing: 4pt,
    ..cells
  )
}

// ★コンパクトな記号記入枠（リスニング・単一記号選択用）
#let compact-symbol-grid(items: ()) = {
  let count = items.len()
  let cols-per-row = calc.min(count, 6)
  if cols-per-row == 0 { cols-per-row = 1 }
  let rows-count = calc.ceil(count / cols-per-row)
  
  stack(
    spacing: 4pt,
    ..range(rows-count).map(r => {
      let start = r * cols-per-row
      let end = calc.min(count, start + cols-per-row)
      let sub-items = items.slice(start, end)
      let fill-count = cols-per-row - sub-items.len()
      
      table(
        columns: range(cols-per-row).map(_ => 1fr),
        rows: (18pt, 24pt),
        align: center + horizon,
        stroke: 0.5pt + luma(60),
        ..sub-items.map(it => table.cell(fill: white)[#text(weight: "bold", size: 8.5pt)[#it]]),
        ..range(fill-count).map(_ => table.cell(stroke: none)[]),
        ..range(sub-items.len()).map(_ => table.cell(fill: white)[]),
        ..range(fill-count).map(_ => table.cell(stroke: none)[])
      )
    })
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
        stroke: 0.6pt + luma(40),
        ..sub-symbols.map(s => table.cell(fill: white)[#text(weight: "bold", size: 9pt)[#s]]),
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
        stroke: 0.6pt + luma(40),
        ..sub-symbols.map(s => table.cell(fill: white)[#text(weight: "bold", size: 9pt)[#s]]),
        ..range(fill-count).map(_ => table.cell(stroke: none)[]),
        ..range(sub-symbols.len()).map(_ => table.cell(fill: white)[]),
        ..range(fill-count).map(_ => table.cell(stroke: none)[])
      )
    })
  )
}

// ==================== 4. 理科・本番仕様セル ====================
#let science-cell(label: "問1", note: "", height-pt: 45pt, body: none) = {
  rect(
    width: 100%,
    stroke: 0.7pt + luma(40),
    inset: 0pt,
    fill: white,
    [
      #grid(
        columns: (100%),
        rows: (18pt, auto),
        rect(width: 100%, height: 100%, fill: white, stroke: (bottom: 0.6pt + luma(40)), inset: 0pt)[
          #align(center + horizon)[#text(size: 8.5pt, weight: "bold")[#label #if note != "" [#text(size: 7pt, fill: luma(80))[（#note）]]]]
        ],
        block(width: 100%, height: height-pt, inset: 4pt)[
          #if body != none { align(center + horizon)[#body] } else { [] }
        ]
      )
    ]
  )
}

// ==================== 5. マークシート仕様コンポーネント ====================
#let mark-bubble(label) = {
  box(
    width: 13.5pt,
    height: 9pt,
    radius: 4.5pt,
    stroke: 0.5pt + luma(40),
    fill: white,
    align(center + horizon)[#text(size: 6.5pt, weight: "medium")[#label]]
  )
}

#let mark-row(q-label, options: ("1", "2", "3", "4")) = {
  table.cell(stroke: 0.4pt + luma(100), fill: white)[#text(weight: "bold", size: 8pt)[#q-label]]
  table.cell(stroke: 0.4pt + luma(100), fill: white)[
    #stack(
      dir: ltr,
      spacing: 3.5pt,
      ..options.map(opt => mark-bubble(opt))
    )
  ]
}

#let exam-id-mark-box(digits: 6) = {
  table(
    columns: (32pt, ..range(digits).map(_ => 16pt)),
    rows: (14pt, 16pt, ..range(10).map(_ => 13pt)),
    align: center + horizon,
    stroke: 0.4pt + luma(80),
    table.cell(rowspan: 2, fill: white)[#text(size: 7.5pt, weight: "bold")[受験番号]],
    ..range(digits).map(i => table.cell(fill: white)[#text(size: 7pt)[#(i+1)]]),
    ..range(digits).map(_ => table.cell(fill: white)[]),
    ..range(10).map(d => (
      table.cell(fill: white)[#text(size: 7pt, weight: "bold")[#d]],
      ..range(digits).map(_ => table.cell(fill: white)[#mark-bubble(str(d))])
    )).flatten()
  )
}
