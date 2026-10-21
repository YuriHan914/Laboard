<p align="center">
  <img src="../assets/LABOARD_RESULT.png" alt="Result" width="900"/>
</p>

# Result

**English** | [한국어](../ko/result.md)

The Result page opens any file under `paths.results`:

- metric files become charts and tables
- logs and json are shown as text
- images open in a zoomable viewer

You can tick several charts to compare them on one shared axis. Up to 20,000 result files are listed.

## Left sidebar

**Result files** is a folder tree. Each row shows a type tag (`TB` for TensorBoard event files,
otherwise the extension), the file name and its size.

## Header card

- **Title:** the file name and a pill with its type:

| Pill | Files |
| --- | --- |
| TensorBoard | `*tfevents*` |
| CSV / TSV / JSONL | `.csv`, `.tsv`, `.jsonl` |
| Weights & Biases | A csv / tsv / jsonl whose name contains `wandb` |
| Image | `.png`, `.jpg`, `.jpeg`, `.bmp`, `.gif`, `.webp` |
| JSON | `.json` |
| Text | Anything else |

- **Second line:** the path relative to the project root, plus what was read, such as
  `12 columns · 3,000 rows`, `8 scalar tags` or `1024×768 PNG`.
- **Smoothing** (0–0.95): an exponential moving average applied to every chart and to Compare. It only
  appears when the file has charts.

## Charts

**Which columns become charts:**

- **csv / tsv / jsonl:** every column that is numeric in at least half of the rows and isn't constant.
- **TensorBoard:** every scalar tag with more than one value. Event files are read directly; TensorFlow
  isn't needed.

**The x axis** is the first of these columns that exists: `step`, `global_step`, `_step`, `epoch`,
`iteration`, `iter`. If none of them exists, the row number is used. TensorBoard charts use the step.

**Layout:** up to 16 charts per file, three per row (fewer when the page is narrow). Long series are
thinned to about 400 points. Each card shows the series name and `last · min · max`.

| Action | Effect |
| --- | --- |
| Hover | A line snaps to the nearest point, and a tooltip shows the x value and the value |
| Ctrl+scroll | Zoom the x axis around the cursor (down to 1/50 of the range) |
| Drag (zoomed in) | Move the view sideways |
| Drag the card's bottom edge | Change the chart height (80–1000 px) |
| Drag the card's left or right edge | Change the card's width |
| Click the card | Tick it for Compare |

A plain scroll scrolls the page.

## Compare (right panel)

1. Click chart cards to tick them, up to 10 per file. A ticked card gets a green border and a check mark.
2. The **Compare** panel opens on the right. It draws every ticked series on one shared x and y axis.
3. Each series has its own colour and dash pattern, and the legend lists them with their last value.
   A series keeps its colour while you tick and untick others.
4. Smoothing applies here too.
5. Drag the bottom edge of the panel to make the chart taller.
6. The panel closes when nothing is ticked.

## Tables

Every csv / tsv / jsonl file is also shown as a table with all of its columns:

- **Rows read:** up to 20,000. A `+` after the row count means the file has more.
- **Paging:** 50 rows per page, with **Previous / Next**.
- **Column widths:** columns are sized to their contents, and the table scrolls sideways when it is wide.
- **Folding:** a big table (5 or more columns and 10 or more rows) starts folded. It shows as a
  chart-sized card with the first 6 rows and 5 columns. Click it to unfold it to the full width, and
  click again to fold it.

## Text and JSON

- Up to 256 KB is read.
- Each line is numbered.
- Lines containing `WARN` are orange, and lines containing `ERROR` or `Traceback` are red.
- The text can be selected and copied.

## Images

Images open in the same viewer as on the Data page:

| Action | Effect |
| --- | --- |
| Scroll | Zoom around the cursor |
| Shift+scroll, or drag | Pan |
| Double-click | Fit the image |
