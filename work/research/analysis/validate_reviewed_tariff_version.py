"""Mutation checks for the narrow, opt-in source-version boundary."""
from pathlib import Path
import argparse
import json
import sys
import tempfile
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'work/research/models'))
from reviewed_tariff_version import *
ap=argparse.ArgumentParser();ap.add_argument('--new-file',type=Path,required=True);args=ap.parse_args()
new=args.new_file.read_bytes();old=(ROOT/OLD_PATH).read_bytes();checks=[]
assert digest(new)==NEW_SHA and digest(old)==OLD_SHA
with tempfile.TemporaryDirectory() as directory:
    root=Path(directory)
    def put(name,body):
        p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(body)
    put(NEW_PATH,new);put(AUDIT_PATH,(ROOT/AUDIT_PATH).read_bytes())
    required={OLD_PATH:OLD_SHA}
    def rejects(label,call):
        try:call()
        except (ValueError,FileNotFoundError):checks.append(label)
        else:raise AssertionError(label)
    rejects('default_does_not_accept_reviewed_version',lambda:admit_inputs(root,required))
    replacements=admit_inputs(root,required,allow_reviewed_tariff_version=True)
    assert len(replacements)==1 and replacements[0]['admitted_sha256']==NEW_SHA
    checks.append('explicit_opt_in_emits_full_version_proof')
    for label,changed in [('tariff',new.replace(b'7:00-9:00',b'6:00-9:00')),
                          ('script',new.replace(b"$this_router='/index.php/cms/item'",b"$this_router='other'"))]:
        assert changed!=new;put(NEW_PATH,changed)
        rejects('reject_changed_'+label,lambda:admit_inputs(root,required,allow_reviewed_tariff_version=True))
    put(NEW_PATH,new)
    put(OLD_PATH,b'corrupted old file')
    rejects('corrupt_original_cannot_hide_behind_new_version',lambda:admit_inputs(root,required,allow_reviewed_tariff_version=True))
    put(OLD_PATH,old)
    assert admit_inputs(root,required)==[] and admit_inputs(root,required,allow_reviewed_tariff_version=True)==[]
    checks.append('original_exact_bytes_remain_preferred_and_default')
    (root/OLD_PATH).unlink()
    rejects('unknown_expected_original_hash',lambda:admit_inputs(root,{OLD_PATH:'0'*64},allow_reviewed_tariff_version=True))
    rejects('other_missing_source_not_exempted',lambda:admit_inputs(root,{**required,'numerical.csv':digest(b'1')},allow_reviewed_tariff_version=True))
    put('numerical.csv',b'2')
    rejects('changed_numerical_input_not_exempted',lambda:admit_inputs(root,{**required,'numerical.csv':digest(b'1')},allow_reviewed_tariff_version=True))
    audit=json.loads((root/AUDIT_PATH).read_text());audit['new_sha256']='0'*64
    put(AUDIT_PATH,json.dumps(audit).encode())
    rejects('wrong_review_pair_rejected',lambda:admit_inputs(root,required,allow_reviewed_tariff_version=True))
    rejects('nonboolean_opt_in_rejected',lambda:admit_inputs(root,required,allow_reviewed_tariff_version='yes'))
report=dict(checks=checks,number_of_checks=len(checks),scope='Provenance boundary mutation tests, not new physical validation')
(ROOT/'outputs/research/revision/reviewed_tariff_version/admission_validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
