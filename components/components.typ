// 1. 大きめの字数マス目
#let char-grid(chars: 100, cols-per-line: 20) = {
  let rows = calc.ceil(chars / cols-per-line)
  let cell-size = 7.5mm

  stack(
    spacing: 3pt,
    ..range(rows).map(r => {
      let start-idx = r * cols-per-line
      let count = calc.min(cols-per-line, chars - start-idx)
      
      grid(
        columns: range(count).map(_ => cell-size),
        rows: (cell-size,),
        stroke: 0.4pt + luma(120),
        align: center + horizon,
        ..range(count).map(_ => [])
      )
    })
  )
}

// 2. 横罫線（和訳・自由英作文用）
#let lined-box(lines: 4, height-per-line: 8.5mm) = {
  rect(
    width: 100%,
    stroke: 0.6pt + luma(80),
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

// 3. 語句整序用枠
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

// 4. 記号選択枠（1行に最大4〜5個並ぶ適度な長方形枠）
#let symbol-table(symbols: ("(1)", "(2)", "(3)", "(4)")) = {
  let count = symbols.len()
  let max-cols = calc.min(count, 4)
  table(
    columns: range(max-cols).map(_ => 1fr),
    rows: (18pt, 24pt),
    align: center + horizon,
    stroke: 0.5pt + luma(80),
    ..symbols.slice(0, max-cols).map(s => table.cell(fill: luma(245))[#text(weight: "bold", size: 8.5pt)[#s]]),
    ..range(max-cols).map(_ => []),
    ..if count > max-cols {
      let rest = symbols.slice(max-cols)
      let rest-cols = rest.len()
      (
        ..rest.map(s => table.cell(fill: luma(245))[#text(weight: "bold", size: 8.5pt)[#s]]),
        ..range(max-cols - rest-cols).map(_ => table.cell(stroke: none)[]),
        ..range(rest-cols).map(_ => []),
        ..range(max-cols - rest-cols).map(_ => table.cell(stroke: none)[])
      )
    } else { () }
  )
}

// 5. 英単語抜き出し・短答記述用枠（高さ32pt、1行に2個並ぶワイド長方形）
#let word-box(symbols: ("(1)", "(2)")) = {
  let count = symbols.len()
  let max-cols = if count == 1 { 1 } else { 2 }
  table(
    columns: range(max-cols).map(_ => 1fr),
    rows: (18pt, 32pt),
    align: center + horizon,
    stroke: 0.5pt + luma(80),
    ..symbols.slice(0, max-cols).map(s => table.cell(fill: luma(245))[#text(weight: "bold", size: 9pt)[#s]]),
    ..range(max-cols).map(_ => []),
    ..if count > max-cols {
      let rest = symbols.slice(max-cols)
      let rest-cols = rest.len()
      (
        ..rest.map(s => table.cell(fill: luma(245))[#text(weight: "bold", size: 9pt)[#s]]),
        ..range(max-cols - rest-cols).map(_ => table.cell(stroke: none)[]),
        ..range(rest-cols).map(_ => []),
        ..range(max-cols - rest-cols).map(_ => table.cell(stroke: none)[])
      )
    } else { () }
  )
}
