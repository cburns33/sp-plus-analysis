# SP+ Week 7 cloud capture

This public repo holds a small, frozen 2026 Week 7 large-underdog cohort and a hosted capture workflow. The full historical backtest and source workbooks remain in the local project.

The [fixed game list](cloud/week7_frozen.csv) contains 13 DraftKings opening-line large underdogs. Three were selected by the saved SP+ comparison. The original underdog spreads and displayed American prices were captured October 11, 2026. Scheduled GitHub Actions runs collect later DraftKings quotes around kickoff, then grade final scores on Sunday. Results are saved in `cloud/runs`; raw web responses are retained as workflow artifacts. Each observation records its retrieval time, source, and whether it arrived before kickoff.

Run a manual check with **Actions > SP+ Week 7 capture > Run workflow**. The scheduled entries are limited in code to October 15, 17, and 18, 2026. GitHub scheduled jobs may start late, so a quote's recorded retrieval time determines whether it was pregame.

Scheduled checks, Central time:

| Date | Time | Games |
| --- | --- | --- |
| Thu Oct 15 | 6:31 p.m. | Colorado State |
| Sat Oct 17 | 11:31 a.m. | Charlotte |
| Sat Oct 17 | 2:02 p.m. | Arizona State, Auburn |
| Sat Oct 17 | 4:31 p.m. | Washington State |
| Sat Oct 17 | 5:31 p.m. | Florida State, Kent State, Nevada, Syracuse, UL Monroe |
| Sat Oct 17 | 8:31 p.m. | Sacramento State, Colorado, Hawai'i |
| Sun Oct 18 | 12:02 p.m. | Final-score check and grading |

The Sunday comparison uses the frozen 13-game baseline and the three SP+ selected games. A later quote counts as near kickoff only when retrieved within two hours before the scheduled start.

The quote source is the public DraftKings Network betting-splits page, with SportsLine's embedded DraftKings records for games absent there. Sunday scores use ESPN's public event summary with the same game IDs. These are source observations, not verified executable wagers. The cloud workflow does not use or store `CFBD_API_KEY`.
