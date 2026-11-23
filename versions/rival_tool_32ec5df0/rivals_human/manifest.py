"""Product manifests for products that were on disk before the plan (SPEC_HUMAN.txt 1.8).

`manifest --product <id>` hashes every file of a product the product registry (registry/_products.yaml) names by a
folder (or one file) and writes <out_root>/_products/<id>/product_manifest.json: file list, size, sha256, mtime,
licence text, source note. Never written into the product folder. Downloads (D1-D6) already carry their own
product_manifest.json (fetch_products.py); for those this command only re-checks the listed sha256 (--verify).
Resumable: a progress file keeps the files already hashed (same size and mtime are not hashed again).
"""
# Provenance: SPEC_HUMAN.txt 1.8, 8 (O4-O6, O15); D:/treeroute/human_products/*/product_manifest.json (format of a
# download manifest: files {name: {bytes, sha256}}).

import os
import time
from pathlib import Path
from typing import Any, Dict, List

from rivals_human import config as C
from rivals_human import index as IX
from rivals_human.common import HumanCommand, load, refuse, tool_code_sha

PROGRESS = "progress.json"


def _list_files(root: Path, patterns: List[str]) -> List[Path]:
    if root.is_file():
        return [root]
    if not root.is_dir():
        refuse("product folder %s does not exist" % root)
    out = set()
    for pat in patterns or ["**/*"]:
        for p in root.glob(pat):
            if p.is_file():
                out.add(p)
    return sorted(out)


def manifest(product_id: str, config: Any = None, verify: bool = False) -> Path:
    cfg = C.load_config(config)
    LY, H = load(cfg)
    products = C.load_products(cfg)
    if product_id not in products:
        refuse("product %r is not in the product registry %s" % (product_id, cfg["on_disk_products"]))
    rec = products[product_id]
    if rec.get("manifest"):
        mp = Path(str(rec["manifest"]))
        if not verify:
            refuse("product %s is a download with its own manifest %s; nothing to write (pass --verify to re-check "
                   "its sha256)" % (product_id, mp))
        with HumanCommand("manifest", C.product_out_manifest(cfg, product_id).parent, cfg) as ctx:
            m = IX.product_manifest(cfg, products, product_id)
            root = IX.product_root(cfg, products, product_id)
            for name, e in sorted(m["files"].items()):
                IX.verify_product_file(root / name, str(e["sha256"]))
            ctx.log("manifest", product_id, message="%d files re-checked against %s" % (len(m["files"]), mp))
            return mp
    target = C.product_out_manifest(cfg, product_id)
    root = Path(str(rec["path"]))
    with HumanCommand("manifest", target.parent, cfg) as ctx:
        ctx.mkdir(target.parent)
        files = _list_files(root, list(rec.get("patterns") or []))
        if not files:
            refuse("product %s: no file under %s matches %s" % (product_id, root, rec.get("patterns")))
        prog_p = target.parent / PROGRESS
        prog: Dict[str, Any] = C.read_json(prog_p) if prog_p.is_file() else {}
        out: Dict[str, Any] = {}
        t0 = time.time()
        total = 0
        base = root if root.is_dir() else root.parent
        for i, p in enumerate(files):
            name = p.relative_to(base).as_posix()
            st = os.stat(str(p))
            old = prog.get(name)
            if old and old["bytes"] == int(st.st_size) and old["mtime_ns"] == int(st.st_mtime_ns):
                out[name] = old
            else:
                out[name] = {"bytes": int(st.st_size), "mtime_ns": int(st.st_mtime_ns), "sha256": H.sha256_file(p)}
                prog[name] = out[name]
                if (i + 1) % 20 == 0:
                    ctx.replace_json(prog_p, prog)
                    ctx.log("manifest", product_id, "%d/%d" % (i + 1, len(files)), time.time() - t0)
            total += int(st.st_size)
        doc = {"format": C.FORMAT_PRODUCT_MANIFEST, "product": product_id, "path": str(root).replace("\\", "/"),
               "patterns": list(rec.get("patterns") or []), "files": out, "total_bytes": total,
               "licence": rec.get("licence"), "source": rec.get("source"), "label": rec.get("label"),
               "created": H.utc_now(), "tool_code_sha256": tool_code_sha(), "complete": True}
        if target.is_file():
            old = C.read_json(target)
            same = old.get("files") == out
            if same:
                ctx.log("manifest", product_id, message="manifest exists with the same files; nothing written")
                return target
            changed = sorted(n for n, e in (old.get("files") or {}).items()
                             if n not in out or out[n]["sha256"] != e["sha256"])
            if not rec.get("staged") or changed:
                refuse("%s exists with other files or hashes (changed or gone: %s): the product changed after it "
                       "was hashed" % (target, changed[:5]),
                       fix="OWNER ITEM: a changed product needs a new Part; move the old manifest aside by hand")
            # a staged product (a prep before and after the lock) only ADDS files: the old manifest is moved aside
            doc["previous_manifest_sha256"] = H.sha256_file(target)
            ctx.move_aside(target)
        ctx.write_once_json(target, doc)
        ctx.replace_json(prog_p, prog)
        ctx.log("manifest", product_id, seconds=time.time() - t0,
                message="%d files, %.3f GB hashed into %s" % (len(out), total / 1e9, target))
        return target
