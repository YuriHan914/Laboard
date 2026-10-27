# Result

<p align="center">
  <img src="../assets/LABOARD_RESULT.png" alt="Result" width="900"/>
</p>


The Result page opens any file under `[Path] Results`:

- metric files become charts and tables
- logs and json are shown as text
- images open in a zoomable viewer

You can tick several charts to compare them on one shared axis. Up to 20,000 result files are listed.

`[Path] Results` can be on a server, e.g. `"gcloud:~/project/Results"`. Files under 50 MB are copied at every load
([Files on a remote server](setting.md#files-on-a-remote-server)).

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
- **Reset** (under Smoothing): unticks every chart of this file. The Compare plots empty and the right panel
  closes.

## Charts

**Which columns become charts:**

- **csv / tsv / jsonl:** every column that is numeric in at least half of the rows and isn't constant.
- **TensorBoard:** every scalar tag with more than one value. Event files are read directly; TensorFlow
  isn't needed.

**The x axis** is the first of these columns that exists: `step`, `global_step`, `_step`, `epoch`,
`iteration`, `iter`. If none of them exists, the row number is used. TensorBoard charts use the step.

**Layout:** up to 60 charts per file, three per row (fewer when the page is narrow). Long series are
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

1. Click chart cards to tick them. A ticked card gets a coloured border and a check mark.
2. The **Compare** panel opens on the right. It draws the ticked series on one shared x and y axis.
   - One Compare plot holds 10 charts. The 11th opens **Compare 2** below it, the 21st **Compare 3**, and so
     on: up to 60 charts (6 plots) per file.
   - Each plot has its own border colour for the cards ticked into it, and the dot next to its title matches.

     | Plot | Charts | Border colour |
     | --- | --- | --- |
     | Compare | 1st–10th | Positive Deep `#054d28` |
     | Compare 2 | 11th–20th | Positive `#2ead4b` |
     | Compare 3 | 21st–30th | Warning `#ffd11a` |
     | Compare 4 | 31st–40th | Warning Deep `#b86700` |
     | Compare 5 | 41st–50th | Warning Content `#4a3b1c` |
     | Compare 6 | 51st–60th | Negative Darkest `#a7000d` |

   - Unticking a chart in an earlier plot frees its place, and the next chart you tick fills it first. A plot
     with nothing left in it disappears.
3. Each series has its own colour and dash pattern, and the legend lists them with their last value.
   A series keeps its colour while you tick and untick others.
4. **Drag and drop:** drag a chart card from the left onto a Compare card on the right to merge it into that plot.
   - While dragging, a see-through image of the card follows the cursor and the card itself fades. A Compare card
     you can drop on lights up its border in its colour.
   - An unticked chart joins that plot; a chart in another Compare plot moves there. When the plot already holds
     10 charts, the status bar says so and nothing changes.
   - Dragging a card's edge still resizes it, and dragging inside a zoomed chart still pans it. Compare cards only
     take drops while the panel is open, i.e. once something is ticked.
5. Smoothing applies here too.
6. Drag the bottom edge of the panel to make the chart taller.
7. The panel closes when nothing is ticked.

## Tables

Every csv / tsv / jsonl file is also shown as a table with all of its columns:

- **Rows read:** up to 20,000. A `+` after the row count means the file has more.
- **Paging:** 30 rows per page (20 / 30 / 40 / 50 / 100, picked under [Items per page](setting.md#items-per-page) in Setting).
  Under the table, a page bar: `N rows per page · change in Setting` on the left; **Previous**, the page
  numbers (first, last, the current one and its neighbours, `…` for a gap) and **Next**; and a page box with **Go**
  (or Enter) on the right. A number out of range goes to the first or last page.
- **Column widths:** columns are sized to their contents, and the table scrolls sideways when it is wide.
- **Folding:** a big table (5 or more columns and 10 or more rows) starts folded. It shows as a
  chart-sized card with the first 6 rows and 5 columns. Click it to unfold it to the full width, and
  click again to fold it.

### Sort, filter and hide columns

In an open table, a column's header opens that column's menu.

- **Sort ascending / Sort descending:** sorts by the column. A column of numbers sorts by value, any other as text
  (any case); blanks always go last. Picking the current sort again turns sorting off. One column sorts at a time.
- **Filter:** filters as you type (Enter closes the menu).
  - Text: keeps the values that hold it (any case), e.g. `abnormal`.
  - A comparison: `> 0.5`, `>= 10`, `< 3`, `<= 1e-3`, `= 2`, `!= 0`. Values that aren't numbers drop out.
  - Filters on several columns keep only the rows that pass them all. Empty the box to remove one.
- **Hide column:** hides the column. The last one shown can't be hidden.

Headers show `↑` / `↓` on the sorted column and `•` on filtered ones. The bar above the table reads like
`6 of 8 columns · 877 of 7,011 rows`, with two buttons on the right:

- **Columns:** every column with a tick; click one to hide or show it, or **Show all**.
- **Reset:** clears the sort, the filters and the hidden columns (shown only when something is set).

Sort, filters and hidden columns are kept per file and cleared when you leave the Result page. Changing them goes
back to the first page.

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
