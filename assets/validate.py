#!/usr/bin/env python3
"""Read-only self-check for the qodercn-cli skill package.

Run:  python assets/validate.py
Exit: 0 = all checks pass, 1 = at least one failure.

Mutates nothing: the only side effects are subprocess syntax probes
(bash -n, compile() in memory).
"""

import re
import shutil
import subprocess
import sys
from pathlib import Path

SKILL_MD_MAX_LINES = 500
ROSTER_MARKER = "QODERWORK_"
METADATA_EXAMPLE_MIN = 2
METADATA_EXAMPLE_MAX = 5
SELF_EXEMPT = {"validate.py", "VALIDATE-REPORT.txt"}
TEXT_SUFFIXES = {".md", ".sh", ".py", ".txt", ".yaml", ".yml", ".json"}

REQUIRED_KEYS = [
    "name",
    "name_en",
    "name_zh",
    "description",
    "description_en",
    "description_zh",
    "argument-hint",
    "argument-hint-en",
    "argument-hint-zh",
    "user-invocable",
    "version",
]

ASSET_REF_RE = re.compile(r"assets/[A-Za-z0-9._\-/]+")
TRAILING_JUNK = ".,;:!?)]}'\"`/"


class Report:
    def __init__(self):
        self.rows = []
        self.failures = []

    def add(self, name, ok, detail):
        self.rows.append((name, ok, detail))
        if not ok:
            self.failures.append((name, detail))


def read_text(path):
    raw = path.read_bytes()
    for enc in ("utf-8", "latin-1"):
        try:
            return raw.decode(enc), raw
        except UnicodeDecodeError:
            continue
    return raw.decode("latin-1", errors="replace"), raw


def split_frontmatter(text):
    lines = text.split("\n")
    if not lines or lines[0].lstrip("\ufeff").strip() != "---":
        return None, text
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return "\n".join(lines[1:index]), "\n".join(lines[index + 1:])
    return None, text


def parse_frontmatter(raw):
    fields = {}
    for line in raw.split("\n"):
        if not line.strip() or line.startswith((" ", "\t", "#", "-")):
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        fields[key.strip()] = value.strip()
    return fields


def check_line_count(root, skill_text, rp):
    total = len(skill_text.splitlines())
    asset_lines = 0
    for path in sorted((root / "assets").glob("*")):
        if path.is_file():
            asset_lines += len(read_text(path)[0].splitlines())
    rp.add(
        "LINE_COUNT",
        total <= SKILL_MD_MAX_LINES,
        "SKILL.md = %d lines (limit %d); assets/ aggregate %d lines informational"
        % (total, SKILL_MD_MAX_LINES, asset_lines),
    )


def check_frontmatter_keys(fields, rp):
    missing = [k for k in REQUIRED_KEYS if k not in fields]
    empty = [k for k in REQUIRED_KEYS if k in fields and not fields[k]]
    ok = not missing and not empty
    detail = "%d/%d keys present" % (len(REQUIRED_KEYS) - len(missing), len(REQUIRED_KEYS))
    if missing:
        detail += "; missing: " + ",".join(missing)
    if empty:
        detail += "; empty: " + ",".join(empty)
    rp.add("FRONTMATTER_KEYS", ok, detail)


def check_description_parity(fields, rp):
    zh = fields.get("description", "")
    en = fields.get("description_en", "")
    if not zh or not en:
        rp.add("DESC_PARITY", False, "one of description / description_en absent")
        return
    a = zh.encode("utf-8")
    b = en.encode("utf-8")
    if a == b:
        rp.add("DESC_PARITY", True, "byte-identical (%d bytes)" % len(a))
        return
    pos = next((i for i in range(min(len(a), len(b))) if a[i] != b[i]), min(len(a), len(b)))
    rp.add(
        "DESC_PARITY",
        False,
        "byte diff at offset %d (description=%d bytes, description_en=%d bytes)"
        % (pos, len(a), len(b)),
    )


def collect_asset_refs(body):
    refs = set()
    for match in ASSET_REF_RE.findall(body):
        cleaned = match.rstrip(TRAILING_JUNK)
        if cleaned.endswith("assets") or cleaned.endswith("assets/"):
            continue
        tail = cleaned.split("/", 1)[1] if "/" in cleaned else cleaned
        if not tail.strip("."):
            continue
        refs.add("assets/" + tail)
    return refs


def check_asset_references(body, root, rp):
    refs = collect_asset_refs(body)
    if not refs:
        rp.add("ASSET_REFS_EXIST", False, "no assets/ path found in body")
        return
    missing = sorted(r for r in refs if not (root / Path(*r.split("/"))).exists())
    rp.add(
        "ASSET_REFS_EXIST",
        not missing,
        "%d referenced paths, all exist" % len(refs)
        if not missing
        else "missing: " + ", ".join(missing),
    )


def check_no_orphans(refs, root, rp):
    assets_dir = root / "assets"
    present = sorted("assets/" + p.name for p in assets_dir.iterdir() if p.is_file())
    names = {Path(*p.split("/")).name: p for p in present}
    exempt = sorted(n for n in names if n in SELF_EXEMPT)
    unref = sorted(p for p in present if p not in refs and Path(p).name not in SELF_EXEMPT)
    detail = "%d files in assets/, %d must be referenced" % (len(present), len(present) - len(exempt))
    if exempt:
        detail += "; exempt self-generated: " + ", ".join(exempt)
    rp.add("ASSET_NO_ORPHANS", not unref, detail if not unref else "orphans: " + ", ".join(unref))


def scan_tabs(root, skill_text):
    hits = []
    targets = [("SKILL.md", skill_text)]
    assets_dir = root / "assets"
    for path in sorted(assets_dir.iterdir()):
        if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES:
            targets.append(("assets/" + path.name, read_text(path)[0]))
    for label, text in targets:
        for number, line in enumerate(text.split("\n"), 1):
            if "\t" in line:
                hits.append("%s:%d" % (label, number))
    return hits, len(targets)


def check_no_tabs(root, skill_text, rp):
    hits, scanned = scan_tabs(root, skill_text)
    detail = "%d text files scanned, no U+0009" % scanned
    rp.add("NO_TABS", not hits, detail if not hits else "tabs at: " + ", ".join(hits[:10]) +
           ("" if len(hits) <= 10 else " (+%d more)" % (len(hits) - 10)))


def metadata_examples_structural(text):
    blocks = re.split(r"(?m)^\s*-\s+id\s*:", text)
    blocks = [b for b in blocks[1:]]
    if not blocks:
        return 0, []
    problems = []
    for index, block in enumerate(blocks, 1):
        zh = len(re.findall(r"(?m)^\s+zh\s*:", block))
        en = len(re.findall(r"(?m)^\s+en\s*:", block))
        if zh == 0 or en == 0 or zh != en:
            problems.append("example#%d zh=%d en=%d" % (index, zh, en))
    return len(blocks), problems


def check_metadata(root, rp):
    candidates = [root / ".skill-metadata.yaml", root / "assets" / ".skill-metadata.yaml"]
    path = next((c for c in candidates if c.exists()), None)
    if path is None:
        rp.add("METADATA_EXAMPLES", False, ".skill-metadata.yaml not found")
        return
    text, _ = read_text(path)
    try:
        import yaml  # type: ignore
    except ImportError:
        count, problems = metadata_examples_structural(text)
        engine = "fallback structural parser (PyYAML unavailable)"
    else:
        try:
            data = yaml.safe_load(text)
        except Exception as exc:
            rp.add("METADATA_EXAMPLES", False, "yaml parse error: %s" % exc)
            return
        examples = data.get("examples") if isinstance(data, dict) else None
        if not isinstance(examples, list):
            rp.add("METADATA_EXAMPLES", False, "no list at top-level key 'examples'")
            return
        count = len(examples)
        problems = []
        for index, item in enumerate(examples, 1):
            if not isinstance(item, dict):
                problems.append("example#%d not a mapping" % index)
                continue
            for field in ("title", "description", "prompt"):
                value = item.get(field)
                if not isinstance(value, dict):
                    problems.append("example#%d %s missing" % (index, field))
                    continue
                for lang in ("zh", "en"):
                    if not str(value.get(lang) or "").strip():
                        problems.append("example#%d %s.%s empty" % (index, field, lang))
        engine = "PyYAML"
    range_ok = METADATA_EXAMPLE_MIN <= count <= METADATA_EXAMPLE_MAX
    ok = range_ok and not problems
    detail = "%d examples (allowed %d-%d), parser=%s" % (
        count, METADATA_EXAMPLE_MIN, METADATA_EXAMPLE_MAX, engine)
    if not ok:
        detail += "; " + ("; ".join(problems[:5]) if problems else "count out of range")
    rp.add("METADATA_EXAMPLES", ok, detail)


def find_bash():
    found = shutil.which("bash")
    if found:
        return found
    for candidate in (
        r"C:\Program Files\Git\bin\bash.exe",
        r"C:\Program Files\Git\usr\bin\bash.exe",
        "/bin/bash",
        "/usr/bin/bash",
    ):
        if Path(candidate).exists():
            return candidate
    return None


def check_bash_syntax(root, rp):
    script = root / "assets" / "qcn.sh"
    if not script.exists():
        rp.add("BASH_SYNTAX", False, "assets/qcn.sh not found")
        return
    bash = find_bash()
    if bash is None:
        rp.add("BASH_SYNTAX", False, "no bash interpreter discoverable on this host")
        return
    try:
        proc = subprocess.run(
            [bash, "-n", script.as_posix()],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except Exception as exc:
        rp.add("BASH_SYNTAX", False, "probe error: %s" % exc)
        return
    rp.add(
        "BASH_SYNTAX",
        proc.returncode == 0,
        "bash -n assets/qcn.sh rc=%d" % proc.returncode
        if proc.returncode == 0
        else (proc.stderr or proc.stdout or "rc=%d" % proc.returncode).strip()[:300],
    )


def check_python_compile(root, rp):
    files = sorted(p for p in (root / "assets").iterdir() if p.is_file() and p.suffix == ".py")
    broken = []
    for path in files:
        source, _ = read_text(path)
        try:
            compile(source, str(path), "exec")
        except SyntaxError as exc:
            broken.append("%s:%s %s" % (path.name, exc.lineno, exc.msg))
    detail = "%d .py files compiled clean" % len(files)
    rp.add("PY_COMPILE", not broken, detail if not broken else "; ".join(broken))


def check_no_roster_copy(body, rp):
    count = body.count(ROSTER_MARKER)
    rp.add(
        "NO_ROSTER_2ND_COPY",
        count == 0,
        "'%s' occurs %d time(s) in body (authoritative copy stays in assets/qcn.sh)" % (ROSTER_MARKER, count),
    )


def check_denylist_parity(root, rp):
    """sdk_bridge.py 的 POLLUTION_* 名单必须逐条出现在 qcn.sh 里（防单边漂移）。"""
    try:
        sb = read_text(root / "assets" / "sdk_bridge.py")[0]
        sh = read_text(root / "assets" / "qcn.sh")[0]
    except Exception as e:
        rp.add("DENYLIST_PARITY", False, "cannot read denylist sources: %r" % e)
        return
    def _block(src, start, end):
        i = src.find(start)
        if i < 0:
            return ""
        i += len(start)
        j = src.find(end, i)
        return src[i:j if j > 0 else len(src)]
    fam = re.findall(r'"([A-Z0-9_]+)"', _block(sb, "POLLUTION_FAMILIES = (", ")"))
    exact = re.findall(r'"([A-Z0-9_]+)"', _block(sb, "POLLUTION_EXACT = {", "}"))
    if not fam or not exact:
        rp.add("DENYLIST_PARITY", False, "could not parse POLLUTION_* from sdk_bridge.py")
        return
    missing = [n for n in fam + exact if n not in sh]
    detail = "%d families + %d exact names, all present in qcn.sh" % (len(fam), len(exact))
    rp.add("DENYLIST_PARITY", not missing, detail if not missing else "in sdk_bridge but not qcn.sh: " + ", ".join(missing))

def main():
    root = Path(__file__).resolve().parent.parent
    skill_path = root / "SKILL.md"
    rp = Report()

    print("qodercn-cli self-check")
    print("  root: %s" % root)
    print("  python: %s" % sys.version.split()[0])

    if not skill_path.exists():
        print("FAIL  01 SKILL_PRESENT         SKILL.md not found at %s" % skill_path)
        print("RESULT 1_FAILED")
        return 1

    skill_text, _ = read_text(skill_path)
    fm_raw, body = split_frontmatter(skill_text)
    if fm_raw is None:
        rp.add("FRONTMATTER_KEYS", False, "no --- frontmatter block found")
        fields = {}
        body = skill_text
    else:
        fields = parse_frontmatter(fm_raw)

    checks = [
        lambda: check_line_count(root, skill_text, rp),
        lambda: check_frontmatter_keys(fields, rp),
        lambda: check_description_parity(fields, rp),
        lambda: check_asset_references(body, root, rp),
        lambda: check_no_orphans(collect_asset_refs(body), root, rp),
        lambda: check_no_tabs(root, skill_text, rp),
        lambda: check_metadata(root, rp),
        lambda: check_bash_syntax(root, rp),
        lambda: check_python_compile(root, rp),
        lambda: check_no_roster_copy(body, rp),
        lambda: check_denylist_parity(root, rp),
    ]
    for index, run in enumerate(checks, 1):
        try:
            run()
        except Exception as exc:
            rp.add("CHECK_%02d" % index, False, "internal error: %r" % exc)

    for index, (name, ok, detail) in enumerate(rp.rows, 1):
        print("%-5s %02d %-20s %s" % ("PASS" if ok else "FAIL", index, name, detail))

    failed = len(rp.failures)
    if failed:
        print("")
        print("failed items:")
        for name, detail in rp.failures:
            print("  - %s: %s" % (name, detail))
    print("")
    print("total %d checks: %d PASS / %d FAIL" % (len(rp.rows), len(rp.rows) - failed, failed))
    print("RESULT ALL_PASS" if failed == 0 else "RESULT %d_FAILED" % failed)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
