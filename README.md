# SP+ Week 7 cloud capture

This public repo holds a small, frozen 2026 Week 7 large-underdog cohort and a hosted capture workflow. The full historical backtest and source workbooks remain in the local project.

The [fixed game list](cloud/week7_frozen.csv) contains 13 DraftKings opening-line large underdogs. Three were selected by the saved SP+ comparison. The original underdog spreads and displayed American prices were captured October 11, 2026. The October 18 [hosted result](cloud/runs/sunday-results.json) grades all 13 games at those quotes. Raw web responses are retained as workflow artifacts. Each observation records its retrieval time, source, and whether it arrived before kickoff.

The seven scheduled 2026 runs completed. The expired cron entries have been removed from the workflow; manual dispatch remains available for an audit check. GitHub started the quote runs after their intended pregame windows, so a quote's recorded retrieval time determines whether it was pregame.

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

The Sunday comparison uses the frozen 13-game baseline and the three SP+ selected games. SP+ went **2-1** at the October 11 spreads and displayed prices for an indicative **+$78.58** on three $100 stakes. All 13 large underdogs went **8-5** for **+$218.91** on 13 $100 stakes. The remaining ten went 6-4. The local project reconciled every ESPN final score and grade with CFBD by game ID.

A later quote counts as near kickoff only when retrieved within two hours before the scheduled start. None of the scheduled quote checks retrieved a price before kickoff. Five saved post-kickoff observations; the Saturday late run started after the local date changed and skipped capture. The near-kickoff group has zero games. The Week 7 result uses only the fixed October 11 quotes.

The quote source is the public DraftKings Network betting-splits page, with SportsLine's embedded DraftKings records for games absent there. Sunday scores use ESPN's public event summary with the same game IDs. These are source observations, not verified executable wagers. The cloud workflow does not use or store `CFBD_API_KEY`.

An [October 12 manual hosted run](https://github.com/cburns33/sp-plus-analysis/actions/runs/38273355130) saved an [early quote in Git history](https://github.com/cburns33/sp-plus-analysis/blob/ab1b7e923f3524fd5e182b1095ed196d9039986a/cloud/runs/thursday.json) and raw page snapshots as an Actions artifact. It verified capture and repository write access. The early quote falls outside the two-hour near-kickoff window. Dry runs verified the other quote sources and the ESPN score lookup. The prior local Codex scheduled runs are paused.
