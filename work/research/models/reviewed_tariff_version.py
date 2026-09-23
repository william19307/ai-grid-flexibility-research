"""One explicitly reviewed public HTML version; strict originals remain default.

This is a provenance substitution, not original-byte restoration. No HTML or
JavaScript is executed and no numerical input or schedule is modified.
"""
from pathlib import Path
import hashlib
import json
import re

OLD_PATH = 'work/research/sources/tariffs/gansu_2020_12_interpretation_gsei.html'
NEW_PATH = 'work/research/sources/tariffs/gansu_reviewed_20260923.html'
OLD_SHA = '63be4112ff3cb2324369e3e3305aacbae6bacbd9cb8947f67bb49a0190ffef17'
NEW_SHA = 'eede38f8e89ab6c7f9e10818687c432127331e7c4f58b8f00ad62e030b7207f8'
OLD_SCRIPT_SHA = 'e064303ad99a3d66023bdefefebdde78745d2c80a5e532f24bf6060a3c5f3f80'
NEW_SCRIPT_SHA = '1130a74faa0d516f98bfbc68c6ca0569176c498787f663f690b666b4191725f6'
REMAINDER_SHA = 'f4e92296d9841b91fbff356eea80367727cfbdb6d770b952c789057cde084e2f'
SOURCE_URL = 'https://manage.gsei.com.cn/index.php/cms/item-view-id-303607-page-1'
AUDIT_PATH = 'outputs/research/revision/reviewed_tariff_version/source_audit.json'


def digest(body):
    return hashlib.sha256(body).hexdigest()


def split_reviewed_script(body):
    blocks = [m for m in re.finditer(rb'<script\b[^>]*>.*?</script>', body, re.S | re.I)
              if b'P8CONFIG.RESOURCE=' in m.group()]
    if len(blocks) != 1:
        raise ValueError('Expected exactly one reviewed routing script')
    block = blocks[0]
    return block.group(), body[:block.start()]+body[block.end():]


def admit_inputs(root, required, *, allow_reviewed_tariff_version=False):
    if not isinstance(allow_reviewed_tariff_version, bool):
        raise ValueError('Explicit boolean admission mode required')
    root = Path(root); replacements = []
    for relative, expected in required.items():
        path = root/relative
        if path.exists():
            if digest(path.read_bytes()) != expected:
                raise ValueError(f'Changed original input; no fallback permitted: {relative}')
            continue
        if not allow_reviewed_tariff_version or (relative, expected) != (OLD_PATH, OLD_SHA):
            raise ValueError(f'Missing original input: {relative}')
        alternative = root/NEW_PATH
        if not alternative.is_file():
            raise ValueError('Explicit reviewed source version is missing')
        body = alternative.read_bytes()
        if digest(body) != NEW_SHA:
            raise ValueError('Unknown reviewed-source bytes; re-review required')
        script, remainder = split_reviewed_script(body)
        if digest(script) != NEW_SCRIPT_SHA or digest(remainder) != REMAINDER_SHA or len(remainder) != 20364:
            raise ValueError('Reviewed script/remainder identity failed')
        audit_file = root/AUDIT_PATH
        audit = json.loads(audit_file.read_text())
        if (audit['old_sha256'], audit['new_sha256'], audit['identical_remainder_sha256']) != (OLD_SHA, NEW_SHA, REMAINDER_SHA):
            raise ValueError('Source review does not match registered version pair')
        replacements.append(dict(original_path=relative, original_expected_sha256=expected,
            admitted_path=NEW_PATH, admitted_sha256=NEW_SHA, source_url=SOURCE_URL,
            source_audit_path=AUDIT_PATH, source_audit_sha256=digest(audit_file.read_bytes()),
            scope='Explicit reviewed version; original HTML bytes were not restored; only one routing/domain script differs'))
    return replacements
