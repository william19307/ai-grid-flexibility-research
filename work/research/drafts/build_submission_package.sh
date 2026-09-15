#!/bin/zsh
# Build Word files for the submission package (English manuscript with embedded figures, SI, Chinese draft, cover letter).
set -e
cd "$(dirname "$0")/../../.."
P=work/figure-env/bin/python; M=outputs/research/manuscript; F=outputs/research/figures/submission
EN=$(ls $M/core_paper_en_v1.*.md | sort -V | tail -1); ZH=$(ls $M/论文工作稿_v1.*.md | sort -V | tail -1); SI=$(ls $M/supplementary_information_v1.*.md | sort -V | tail -1)
$P - "$EN" "$F" <<'PY'
import sys;from pathlib import Path
en,F=sys.argv[1],sys.argv[2];s=open(en,encoding='utf-8').read()
for n,f in [('Fig. 1 |','fig1_constraints_and_power.png'),('Fig. 2 |','fig2_cost_by_scenario.png'),('Fig. 3 |','fig3_realised_share.png'),('Fig. 4 |','fig4_robustness.png')]:
    k=s.find(f'**{n}');
    if k>=0:s=s[:k]+f'![]({F}/{f})\n\n'+s[k:]
open('outputs/research/manuscript/_build_en.md','w',encoding='utf-8').write(s)
PY
mkdir -p $M/docx
pandoc $M/_build_en.md -o $M/docx/$(basename ${EN%.md}).docx --resource-path=. && rm -f $M/_build_en.md
pandoc "$SI" -o $M/docx/$(basename ${SI%.md}).docx
pandoc "$ZH" -o $M/docx/$(basename ${ZH%.md}).docx --resource-path=$M
[ -f $M/cover_letter_nature_energy.md ] && pandoc $M/cover_letter_nature_energy.md -o $M/docx/cover_letter_nature_energy.docx
ls -la $M/docx/; echo PACKAGE_DONE
