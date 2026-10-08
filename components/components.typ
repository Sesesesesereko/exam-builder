// ==================== 英語・共通コンポーネント ====================

// 1. 横書き字数マス目（英語用）
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

// 2. 横罫線（英作文・和訳用）
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

// 4. 記号選択枠
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

// 5. 短答・語句記述枠（横）
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

// ==================== 国語専用コンポーネント ====================

// 6. 本番仕様: 縦書き原稿マス目（1行20マス、右から左へ並ぶ）
#let vertical-grid(chars: 60) = {
  let lines-count = calc.ceil(chars / 20)
  let cell-w = 8.0mm
  let cell-h = 8.5mm

  // 右から左（右端が1行目）に配置
  align(right)[
    #stack(
      dir: ltr,
      spacing: 3.5mm,
      ..range(lines-count).rev().map(line-idx => {
        let start-num = line-idx * 20
        let current-line-chars = calc.min(20, chars - start-num)
        
        stack(
          dir: ttb,
          spacing: 0pt,
          ..range(20).map(c => {
            let is-active = (c < current-line-chars)
            let is-tenth = (c == 9 or c == 19)
            let stroke-color = if is-active { 0.5pt + luma(90) } else { 0.2pt + luma(200) }
            let bottom-stroke = if is-tenth and is-active { 1.2pt + luma(60) } else { stroke-color }
            
            rect(
              width: cell-w,
              height: cell-h,
              stroke: (
                top: stroke-color,
                bottom: bottom-stroke,
                left: stroke-color,
                right: stroke-color,
              ),
              fill: if is-active { none } else { luma(250) }
            )[]
          })
        )
      })
    )
  ]
}

// 7. 漢字書き取り枠（漢字1文字用の正方形マス）
#let kanji-box(symbols: ("A", "B", "C", "D", "E")) = {
  let count = symbols.len()
  table(
    columns: range(count).map(_ => 30pt),
    rows: (16pt, 30pt),
    align: center + horizon,
    stroke: 0.5pt + luma(80),
    ..symbols.map(s => table.cell(fill: luma(245))[#text(weight: "bold", size: 8.5pt)[#s]]),
    ..range(count).map(_ => [])
  )
}
