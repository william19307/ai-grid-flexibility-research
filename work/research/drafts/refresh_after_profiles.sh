#!/bin/zsh
# Re-run multi-weather grid on refreshed profiles, regenerate summaries, figures and v0.8/EN v0.7 documents.
set -e
cd "$(dirname "$0")/../../.."
P=work/figure-env/bin/python
$P work/research/analysis/run_2030_multiweather.py 2>&1 | grep -E "MW_DONE|Traceback|fail|timeout" || true
$P work/research/drafts/update_manuscript_v08.py
$P - <<'PY'
from pathlib import Path
M=Path('outputs/research/manuscript');s=open(M/'core_paper_en_v0.6.md',encoding='utf-8').read().replace('**Working English draft v0.6 (2026-09-15).','**Working English draft v0.7 (2026-09-15).')
old=open(M/'core_paper_en_v0.7.md',encoding='utf-8').read();i=old.index('## Figure legends (draft)');j=old.index('## Methods');caps=old[i:j]
k=s.index('## Methods');s=s[:k]+caps+s[k:]
for a,b in [('`[Fig. 2: incremental system cost and emissions per AI MWh under S0/S0b/S1/S2 for three calibrated provinces, 2030 main scenario, multiple weather years.]`','(Fig. 2)'),('`[Fig. 3: gap decomposition.]`','(Fig. 3)'),('`[Fig. 4: commitment–compensation frontier.]`','(Fig. 3, S3 bars)'),('`[Fig. 5: multi-weather years.]`','(Fig. 4)')]:s=s.replace(a,b)
open(M/'core_paper_en_v0.7.md','w',encoding='utf-8').write(s);print('EN v0.7 refreshed')
PY
$P work/research/analysis/plot_submission_figures.py
echo REFRESH_DONE
