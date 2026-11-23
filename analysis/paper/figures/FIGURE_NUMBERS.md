# Figure numbers

Round 4 (2026-11-11): the figures are numbered in the order of their first citation, as Elsevier asks. A table's notes count where the table is first cited, which is also where the Word build places the figure: the map stands beside Table 1 (ruling AT13). Old -> new: map (unnumbered) -> 1, 1 -> 2, 2 -> 3, 3 -> 4, 4 -> 5. Folders and file names keep their old names, so `fig3/` holds Figure 4.

| Number | Folder | Title (from the caption) | First citation |
|---|---|---|---|
| Figure 1 | `fig_map/` | Study regions and coral bleaching reef sites | Table 1's note (`draft/tables/table_1.md`); Table 1 is first cited in Section 1.1 (`draft/01_introduction.md`). First citation in the running text: the opening paragraph of Section 4 (`draft/04_results.md`). |
| Figure 2 | `fig1/` | treeroute v1, from dataset package to forecast ladder (short caption in Section 2.1; full legend in `fig1/fig1_caption.md` and Supplement S7.1) | Section 2.1 (`draft/02_method.md`) |
| Figure 3 | `fig2/` | Windows, cuts and locks of the five runs | Section 2.6 (`draft/02_method.md`) |
| Figure 4 | `fig3/` | Nowcast contrast per region | Section 4.1 (`draft/04_results.md`) |
| Figure 5 | `fig4/` | Skill by lead and by test year | Section 4.2 (`draft/04_results.md`) |

The graphical abstract (`ga/`) has no number; it is uploaded on its own.

Kept as they were, on purpose:

- `paper/PAPER_OUTLINE.md` keeps the outline's own figure labels. It is a planning record, and `fig1/fig1_caption.md`, `fig1/fig1.py` and `fig2/fig2_spec.md` cite its rows by those labels.
- Review logs, snapshots and the Word build's reports keep the numbers of their day; the next build rewrites its reports.

Changed in round 5 (2026-11-11): <!-- Round 5 fixes (2026-11-12): the bullet below stood under "Kept as they were, on purpose" until 2026-11-12; it records a change, so it has its own heading line now -->

- `fig3/fig3.py` writes the label "Figure 4" into the `figure` column of `fig3/fig3_data.csv` since 2026-11-11 (round 5): the label was changed in the script (line 555) and in the data file's 427 rows, one character per row, so the file keeps its size; fig3.png and fig3.pdf were not re-drawn.
