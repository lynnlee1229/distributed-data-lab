#!/usr/bin/env python3
"""Allowlisted, bilingual static export. Never copies a runtime directory."""
import hashlib, html, json, shutil, zipfile
from pathlib import Path
import markdown

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "build/site/distributed-data-lab"
BASE = "/distributed-data-lab/"
DOMAIN = "https://lynnlee1229.github.io"
REPO = "https://github.com/lynnlee1229/distributed-data-lab"
CHAPTERS = [
    (
        "01-foundations",
        "Names, bytes & authority",
        "名称、字节与元数据权威",
        "reading",
        "—",
    ),
    ("02-parquet", "Parquet physical layout", "Parquet 物理布局", "executed", "01"),
    ("03-hdfs", "HDFS blocks & recovery", "HDFS 块与故障恢复", "executed", "01–02"),
    (
        "04-storage-engine",
        "WAL, LSM, MVCC & indexes",
        "WAL、LSM、MVCC 与索引",
        "reading",
        "01–03",
    ),
    (
        "05-transactions",
        "Cross-range transactions",
        "跨范围分布式事务",
        "executed",
        "04",
    ),
    (
        "06-lakehouse",
        "Snapshots & evolution",
        "表快照与分区演进",
        "executed",
        "02, 04–05",
    ),
]
SOURCE_FILES = (
    [
        "lab.py",
        "requirements.txt",
        "requirements-iceberg.txt",
        "data/resources.json",
        "README.md",
        "README.zh-CN.md",
        "LICENSE",
        "VALIDATION.md",
        "runtime-lock.json",
        ".gitignore",
        ".github/workflows/ci.yml",
    ]
    + sorted(
        str(p.relative_to(ROOT))
        for folder, ext in [
            ("scripts", "*.py"),
            ("experiments", "*.py"),
            ("tests", "*.py"),
            ("tests", "*.mjs"),
            ("docs", "*.md"),
            ("site", "*.mjs"),
            ("site", "*.css"),
        ]
        for p in (ROOT / folder).glob(ext)
    )
    + [
        "results/parquet.json",
        "results/hdfs.json",
        "results/database.json",
        "results/iceberg.json",
        "results/index.json",
    ]
)
if OUT.exists():
    shutil.rmtree(OUT)
OUT.mkdir(parents=True)


def t(lang, en, zh):
    return zh if lang == "zh" else en


def href(lang, name=""):
    return BASE + lang + "/" + name


def page(lang, name, title, body, kind=""):
    other = "en" if lang == "zh" else "zh"
    path = href(lang, name)
    target = OUT / lang / name / "index.html" if name else OUT / lang / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    nav = [
        ("", t(lang, "Course", "课程")),
        ("inspector", t(lang, "Parquet inspector", "Parquet 检查器")),
        ("evidence", t(lang, "Evidence", "实测证据")),
        ("resources", t(lang, "Readings", "课程资源")),
        ("reproduce", t(lang, "Run locally", "本地复现")),
    ]
    navhtml = "".join(
        f'<a href="{href(lang,n)}"'
        + (' aria-current="page"' if n == name else "")
        + ">"
        + label
        + "</a>"
        for n, label in nav
    )
    content = f"""<!doctype html><html lang="{lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{html.escape(title)} · Distributed Data Systems Lab</title><meta name="description" content="{html.escape(t(lang,'Learn storage layout, replication and transactions through original guides and four real reproducible experiments.','用原创课程与四类真实可复现实验，理解数据布局、副本与分布式事务。'))}"><meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'self'; connect-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; object-src 'none'; base-uri 'none'; form-action 'none'"><link rel="stylesheet" href="{BASE}assets/site.css"><link rel="canonical" href="{DOMAIN+path}{'/' if name else ''}"><link rel="alternate" hreflang="{other}" href="{DOMAIN+href(other,name)}{'/' if name else ''}"><link rel="alternate" hreflang="{lang}" href="{DOMAIN+path}{'/' if name else ''}"><script type="module" src="{BASE}assets/site.mjs"></script></head><body><a class="skip" href="#main">{t(lang,'Skip to content','跳到正文')}</a><header><div class="top"><a class="brand" href="{href(lang)}">Distributed Data Systems Lab<small>Lynn Lee / Engineering notebook</small></a><nav aria-label="{t(lang,'Main navigation','主导航')}">{navhtml}<a href="{href(other,name)}">{t(lang,'中文','English')}</a></nav></div></header><main id="main" class="wrap {kind}">{body}</main><footer>{t(lang,'Original teaching material · Synthetic data · v2 / 2026-11-14. Single-host observations, no production capacity claims.','原创课程 · 合成数据 · v2 / 2026-11-14。仅单机观察，不作生产容量结论。')}<br><a href="{REPO}">{t(lang,'Audited companion source','经审计的实验配套源码')}</a> · <a href="{BASE}downloads/distributed-data-lab.zip">ZIP</a> · <a href="{BASE}public-files.json">{t(lang,'Export checksums','导出校验和')}</a> · <a href="/{'zh/' if lang=='zh' else ''}websites/">{t(lang,'All learning labs','全部学习 Lab')}</a></footer></body></html>"""
    target.write_text(content)


def home(lang):
    cards = ""
    for slug, en, zh, status, prereq in CHAPTERS:
        label = (
            t(lang, "Executed profile", "真实实操")
            if status == "executed"
            else t(lang, "Reading + reasoning", "阅读与推理")
        )
        cards += f'<article class="card"><span class="badge {"read" if status=="reading" else ""}">{label}</span><h3><a href="{href(lang,slug)}/">{slug[:2]} / {t(lang,en,zh)}</a></h3><p>{t(lang,"Prerequisites","前置")} {prereq}</p></article>'
    return f"""<section class="hero"><div><p class="eyebrow">Storage / Layout / Commit / Read</p><h1>{t(lang,'Where bytes live.<br>How changes commit.','数据如何存放，<br>变更如何提交。')}</h1><p class="lede">{t(lang,'A foundation-first course in distributed databases and storage. Inspect Parquet, stop a real DataNode, and observe a transaction conflict across real database nodes.','从基础出发的分布式数据库与存储课程：检查 Parquet 布局，停止真实 DataNode，观察真正跨节点数据库的事务冲突。')}</p><div class="actions"><a class="button" href="{href(lang,'01-foundations')}/">{t(lang,'Start chapter 01 →','从第 01 章开始 →')}</a><a class="button secondary" href="{href(lang,'inspector')}/">{t(lang,'Inspect a Parquet file','检查 Parquet 文件')}</a></div></div><div class="architecture"><h3>{t(lang,'Two routes · distinct responsibilities','两条路线 · 不同职责')}</h3><div class="route"><strong>{t(lang,'Analytical files','分析型文件')}</strong><span class="layer">SQL engine</span><span class="layer">Iceberg (optional)</span><span class="layer">Parquet</span><span class="layer">Files / HDFS / Objects</span></div><div class="route"><strong>{t(lang,'Transactional key ranges','事务型键范围')}</strong><span class="layer">SQL gateway</span><span class="layer">Transactions / MVCC</span><span class="layer">Replicated ranges</span><span class="layer">LSM engine</span></div><p>{t(lang,'Compatible roles, not one mandatory HDFS → Parquet → Iceberg → database pipeline.','按职责理解组合关系，不存在所有系统都走 HDFS → Parquet → Iceberg → 数据库的通用链路。')}</p></div></section><div class="stats"><div class="stat"><strong>06</strong><span>{t(lang,'Bilingual chapters','双语课程章节')}</span></div><div class="stat"><strong>04</strong><span>{t(lang,'Real executable profiles','真实可执行 Profile')}</span></div><div class="stat"><strong>0</strong><span>{t(lang,'File uploads in inspector','检查器文件上传')}</span></div></div><div class="note">{t(lang,'Coverage: chapters 02 / 03 / 05 / 06 have executed profiles. 01 / 04 remain reading and reasoning. Iceberg uses a local SQLite catalog, not a distributed/cloud catalog. All cluster nodes share one laptop.','覆盖范围：02 / 03 / 05 / 06 有真实实操，01 / 04 为阅读推理。Iceberg 使用本地 SQLite catalog，不是分布式或云目录。所有集群节点共用一台笔记本。')}</div><h2>{t(lang,'Follow the concept dependencies','沿概念依赖学习')}</h2><div class="cards">{cards}</div><h2>{t(lang,'Four experiments, inspectable evidence','四个实验，可检查的证据')}</h2><div class="cards"><article class="card"><span class="eyebrow">01 / PARQUET</span><h3>{t(lang,'Equal rows. Different requests.','结果相同，读取请求不同。')}</h3><p>{t(lang,'Five layouts, 45 measured queries. Separate footer candidates from real engine requests and timing.','五种布局、45 次正式查询。区分 Footer 候选范围与引擎实际请求、耗时。')}</p><a href="{href(lang,'evidence')}/?profile=parquet">{t(lang,'Inspect layout evidence →','检查布局证据 →')}</a></article><article class="card"><span class="eyebrow">02 / HDFS</span><h3>{t(lang,'Readable and fully replicated?','可读，也恢复副本了吗？')}</h3><p>{t(lang,'Four DataNodes, RF=3, thirteen blocks. Stop one node, verify reads, then prove repair on surviving targets.','四个 DataNode、RF=3、十三块。停一节点、验证读取，再检查幸存目标上的补副本。')}</p><a href="{href(lang,'evidence')}/?profile=hdfs">{t(lang,'Inspect recovery evidence →','检查恢复证据 →')}</a></article><article class="card"><span class="eyebrow">03 / DATABASE</span><h3>{t(lang,'One rule. Two stale decisions.','一条规则，两次过期决策。')}</h3><p>{t(lang,'Three actual nodes and distinct range leaseholders. Commit a transfer, then observe a real 40001 conflict.','三个真实节点，不同范围租约持有者。先提交转账，再观察真实 40001 冲突。')}</p><a href="{href(lang,'evidence')}/?profile=database">{t(lang,'Inspect transaction evidence →','检查事务证据 →')}</a></article><article class="card"><span class="eyebrow">04 / ICEBERG</span><h3>{t(lang,'A file is not a committed table.','文件不等于已提交的表。')}</h3><p>{t(lang,'Read real 3/5/6-row snapshots, preserve field identity, mix partition specs and exclude a valid uncommitted file.','读取真实 3/5/6 行快照，保留字段身份，混合分区规范，排除合法但未提交的文件。')}</p><a href="{href(lang,'evidence')}/?profile=iceberg">{t(lang,'Inspect snapshot evidence →','检查快照证据 →')}</a></article></div><div class="actions"><a class="button secondary" href="{href(lang,'resources')}/">{t(lang,'Study with verified CMU / MIT readings →','结合已核验的 CMU / MIT 课程学习 →')}</a></div><div class="note">{t(lang,'Scope boundary: Streaming Lab follows data changes; Distributed Compute Lab studies execution. This course focuses on storage layout, commit, placement and reading.','课程边界：Streaming Lab 关注数据变更链路，Distributed Compute Lab 关注分布式执行；本课程聚焦布局、提交、存放与读取。')}</div>"""


def inspector(lang):
    return f"""<p class="eyebrow">Browser-local / Footer only</p><h1>{t(lang,'Read the layout.<br>Keep your file local.','检查物理布局，<br>文件留在本地。')}</h1><p class="lede">{t(lang,'Inspect schema, row groups, encodings, codecs and min/max. Only header/footer slices are read; no file is uploaded. No external scripts, analytics or WASM download.','查看 Schema、Row Group、编码、压缩与 min/max。只读取 Header/Footer 切片，不上传文件；无外部脚本、统计或 WASM 下载。')}</p><div class="note warning">{t(lang,'This is metadata inspection, not SQL execution. The integer range selector marks candidate groups from raw physical INT32/INT64 bounds. It cannot measure actual engine scans. Standard unencrypted PAR1 files only; footer ≤16 MiB, bounded parser complexity. Decimals/timestamps need logical interpretation; unsupported types stay candidates.','这是元数据检查，不执行 SQL。整数范围选择器根据原始物理 INT32/INT64 界限标记候选组，不测量引擎实际扫描。只支持标准未加密 PAR1 文件，Footer ≤16 MiB，解析复杂度有上限。小数与时间需结合逻辑类型解释；不支持的类型保留为候选。')}</div><div class="controls"><label>{t(lang,'Choose a local .parquet file','选择本地 .parquet 文件')}<input id="file" type="file" accept=".parquet,.pq"></label><button id="sample-sorted">{t(lang,'Sorted synthetic sample','有序合成样本')}</button><button id="sample-shuffled">{t(lang,'Shuffled synthetic sample','打乱合成样本')}</button></div><p id="filename" class="muted">{t(lang,'Choose your file or a synthetic sample to begin.','选择文件或合成样本开始。')}</p><div class="controls"><label>{t(lang,'Filter column','过滤列')}<select id="column"><option>id</option></select></label><label>{t(lang,'Lower bound (inclusive)','下界（含）')}<input id="lower" type="number" value="32000" step="1"></label><label>{t(lang,'Upper bound (inclusive)','上界（含）')}<input id="upper" type="number" value="33023" step="1"></label><button id="apply">{t(lang,'Estimate candidates','估算候选组')}</button><button id="export" disabled>{t(lang,'Export local report','导出本地报告')}</button></div><p id="status" role="status" aria-live="polite" class="status"></p><p id="file-info" class="muted"></p><div id="groups" class="groups" aria-label="Row group candidates"></div><div id="metadata"></div><div id="raw"></div><p class="source"><a href="{href(lang,'02-parquet')}/">{t(lang,'Learn how to interpret these numbers →','学习如何解释这些数字 →')}</a></p>"""


def resource_page(lang):
    inventory = json.loads((ROOT / "data/resources.json").read_text())
    course_cards = ""
    for c in inventory["courses"]:
        course_cards += f'<article class="card"><span class="badge">{html.escape(c["school"])}</span><h3><a href="{c["homepage"]}">{html.escape(c["course_number"]+" / "+c["course_name"])}</a></h3><p>{c["term"]} · {c["status"]}</p><p>{html.escape(c["prerequisites"][lang])}</p><p>{html.escape(c["access"][lang])}</p><details><summary>{t(lang,"Reading and solution policy","阅读与解答政策")}</summary><p>{html.escape(c["solution_policy"][lang])}</p><a href="{c["prerequisite_source"]}">{t(lang,"Official prerequisites / policy","官方先修与政策")}</a></details></article>'
    mapping = ""
    by_id = {r["id"]: r for r in inventory["resources"]}
    for u in inventory["unit_mappings"]:
        links = " · ".join(
            f'<a href="{by_id[i]["url"]}">{html.escape(by_id[i]["locator"]+" / "+by_id[i]["title"])}</a>'
            for i in u["resources"]
        )
        mapping += f'<details><summary>{u["unit"]} / {t(lang,"Read → predict → run → explain","阅读 → 预测 → 运行 → 解释")}</summary><p>{links}</p><p>{html.escape(u["task"][lang])}</p><pre>{html.escape(chr(10).join(u["exercise_commands"]))}</pre><p>{html.escape(u["check"][lang])}</p><a href="{href(lang,u["slug"])}/">{t(lang,"Open the complete unit →","打开完整单元 →")}</a></details>'
    course_options = "".join(
        f'<option value="{c["id"]}">{html.escape(c["school"]+" "+c["course_number"])}</option>'
        for c in inventory["courses"]
    )
    unit_options = "".join(
        f'<option value="{i:02}">{i:02}</option>' for i in range(1, 7)
    )
    return f'<p class="eyebrow">Primary sources / Verified 2026-11-14</p><h1>{t(lang,"Read with purpose.<br>Test the claims.","带着问题阅读，<br>用实验检验。")}</h1><p class="lede">{t(lang,"Two real university courses, specific lectures and original runnable exercises mapped to all six units. Use this as a study route, not a course enrollment or assignment-solution service.","两门真实大学课程、具体讲义与原创可运行练习，对应六个学习单元。这里提供学习路线，不提供课程注册或官方作业解答。")}</p><div class="note">{html.escape(inventory["policy"][lang])}</div><div class="grid2">{course_cards}</div><h2>{t(lang,"Six learning loops","六个学习闭环")}</h2>{mapping}<h2>{t(lang,"Search the source inventory","检索结构化资源清单")}</h2><div class="controls"><label>{t(lang,"Search course, topic or lecture","搜索课程、主题或讲义")}<input id="resource-search" type="search" placeholder="Parquet / MVCC / 快照 / 6.5830"></label><label>{t(lang,"Course / source","课程 / 来源")}<select id="resource-course"><option value="">{t(lang,"All sources","全部来源")}</option>{course_options}<option value="official">{t(lang,"Official tutorials / papers","官方教程 / 论文")}</option></select></label><label>{t(lang,"Learning unit","学习单元")}<select id="resource-unit"><option value="">{t(lang,"All units","全部单元")}</option>{unit_options}<option value="AI-extension">{t(lang,"AI reading extension","AI 阅读拓展")}</option></select></label></div><p id="resource-status" role="status" aria-live="polite"></p><div id="resource-results" class="grid2"></div><p><a href="{BASE}resources.json">{t(lang,"Download the structured inventory JSON","下载结构化清单 JSON")}</a></p><h2>{t(lang,"2026: dataset lineage for retrieval","2026：检索的数据版本血缘")}</h2><p>{html.escape(inventory["ai_extension"]["connection"][lang])}</p><p><a href="https://dsg.csail.mit.edu/6.5830/lectures/lec17.pdf">MIT Spring 2026 / Lecture 17 / Embeddings, RAG, and Vector DBs</a></p><div class="note">{t(lang,"The GFS paper is a 2003 classic. MIT 2026 selected lectures are published PDFs, verified readable; no planned or speculative release is presented as completed. Tutorials may evolve; executed compatibility is recorded separately.","GFS 是 2003 年经典文献。所选 MIT 2026 讲义已有公开 PDF 并已核验可读，没有把计划或推测当成完成资料。教程可能更新，实际兼容版本另有记录。")}</div>'


for lang in ["en", "zh"]:
    page(lang, "", t(lang, "Course", "课程"), home(lang))
    page(
        lang,
        "inspector",
        t(lang, "Parquet inspector", "Parquet 检查器"),
        inspector(lang),
    )
    ev = (
        f'<p class="eyebrow">Recorded / Synthetic / Reproducible</p><h1>{t(lang,"Inspect the evidence.","检查真实证据。")}</h1><p class="lede">{t(lang,"These are saved local runs, not live services or illustrative simulations. Read full results, code and limitations before comparing timings.","这里是保存的本地实测，不是在线运行的服务或原理模拟。比较耗时前，先检查完整结果、代码与边界。")}</p><div class="note">{t(lang,"Versioned baseline: PyArrow 20.0.0 / HDFS 3.4.2 + JDK 11 / CockroachDB 24.1.24 / PyIceberg 0.10.0. All data is synthetic; all nodes share one host.","固定基线：PyArrow 20.0.0 / HDFS 3.4.2 + JDK 11 / CockroachDB 24.1.24 / PyIceberg 0.10.0。全部为合成数据，节点共用宿主机。")}</div><div class="tabs" aria-label="Experiment"><button data-report="parquet" aria-pressed="true">Parquet</button><button data-report="hdfs" aria-pressed="false">HDFS</button><button data-report="database" aria-pressed="false">{t(lang,"Distributed database","分布式数据库")}</button><button data-report="iceberg" aria-pressed="false">Iceberg</button></div><div id="evidence-output" aria-live="polite"><p>{t(lang,"Loading recorded results… JSON files remain available below if JavaScript is disabled.","加载保存的结果… 若关闭 JavaScript，可直接读取下方 JSON。")}</p></div><p>'
        + " · ".join(
            f'<a href="{BASE}results/{n}.json">{n}.json</a>'
            for n in ["parquet", "hdfs", "database", "iceberg"]
        )
        + f'</p><p><a href="{href(lang,"source")}/">{t(lang,"Browse the executable code →","浏览可执行代码 →")}</a></p>'
    )
    page(lang, "evidence", t(lang, "Evidence", "实测证据"), ev)
    page(
        lang,
        "resources",
        t(lang, "Readings and exercises", "课程资源与练习"),
        resource_page(lang),
    )
    for i, (slug, en, zh, status, pre) in enumerate(CHAPTERS):
        sidebar = (
            '<aside class="sidebar" aria-label="Chapters">'
            + "".join(
                f'<a href="{href(lang,s)}/"'
                + (' aria-current="page"' if s == slug else "")
                + f">{s[:2]} {t(lang,e,z)}</a>"
                for s, e, z, _, _ in CHAPTERS
            )
            + "</aside>"
        )
        body = markdown.markdown(
            (ROOT / f"docs/{slug}.{lang}.md").read_text(),
            extensions=["tables", "fenced_code"],
        )
        pager = (
            '<div class="pager">'
            + (
                f'<a href="{href(lang,CHAPTERS[i-1][0])}/">← {t(lang,"Previous","上一章")}</a>'
                if i
                else "<span></span>"
            )
            + (
                f'<a href="{href(lang,CHAPTERS[i+1][0])}/">{t(lang,"Next","下一章")} →</a>'
                if i < 5
                else f'<a href="{href(lang,"reproduce")}/">{t(lang,"Run locally","本地复现")} →</a>'
            )
            + "</div>"
        )
        page(
            lang,
            slug,
            t(lang, en, zh),
            f'<div class="chapter-layout">{sidebar}<article class="prose"><p class="eyebrow">{t(lang,"Executed profile" if status=="executed" else "Reading / reasoning","真实实操" if status=="executed" else "阅读 / 推理")}</p>{body}{pager}</article></div>',
        )
    page(
        lang,
        "reproduce",
        t(lang, "Reproduce from zero", "从零复现"),
        '<article class="prose">'
        + markdown.markdown(
            (ROOT / f"docs/reproduce.{lang}.md").read_text(),
            extensions=["tables", "fenced_code"],
        )
        + "</article>",
    )
    listing = ""
    for file in SOURCE_FILES:
        if file.startswith(("experiments/", "scripts/")) or file == "lab.py":
            name = file.replace("/", "--")
            listing += f'<li><a href="{href(lang,"source-"+name)}/">{html.escape(file)}</a></li>'
            page(
                lang,
                "source-" + name,
                file,
                f'<p class="eyebrow">Executable companion source</p><h1>{html.escape(file)}</h1><p><a href="{href(lang,"source")}/">← {t(lang,"Source index","代码目录")}</a></p><pre>{html.escape((ROOT/file).read_text())}</pre>',
            )
    page(
        lang,
        "source",
        t(lang, "Executable source", "可执行源码"),
        f'<h1>{t(lang,"Read, change, reproduce.","阅读、修改、复现。")}</h1><p>{t(lang,"Audited companion only. Runtime binaries, local environments and raw logs are excluded.","只包含经审计的配套代码，不包含运行时二进制、本地环境或原始日志。")}</p><ul>{listing}</ul><a class="button" href="{BASE}downloads/distributed-data-lab.zip">{t(lang,"Download companion ZIP","下载实验配套 ZIP")}</a>',
    )
(OUT / "assets").mkdir()
for file in ["site.css", "site.mjs", "parquet.mjs", "study.mjs"]:
    shutil.copy2(ROOT / "site" / file, OUT / "assets" / file)
(OUT / "samples").mkdir()
for order in ["sorted", "shuffled"]:
    shutil.copy2(
        ROOT / f"build/parquet/{order}-4096-zstd.parquet",
        OUT / f"samples/{order}.parquet",
    )
(OUT / "results").mkdir()
for name in ["parquet", "hdfs", "database", "iceberg", "index"]:
    shutil.copy2(ROOT / f"results/{name}.json", OUT / f"results/{name}.json")
shutil.copy2(ROOT / "data/resources.json", OUT / "resources.json")
(OUT / "downloads").mkdir()
with zipfile.ZipFile(
    OUT / "downloads/distributed-data-lab.zip", "w", zipfile.ZIP_DEFLATED
) as z:
    for file in SOURCE_FILES:
        if not (ROOT / file).is_file():
            raise SystemExit("Missing allowlisted file " + file)
        z.write(ROOT / file, "distributed-data-lab/" + file)
(OUT / "index.html").write_text(
    '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta http-equiv="refresh" content="0; url=en/"><title>Distributed Data Systems Lab</title></head><body><a href="en/">English</a> · <a href="zh/">中文</a></body></html>'
)
urls = [
    DOMAIN + BASE + str(p.relative_to(OUT)).replace("index.html", "")
    for p in OUT.rglob("index.html")
]
(OUT / "sitemap.xml").write_text(
    '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    + "".join("<url><loc>" + html.escape(u) + "</loc></url>" for u in urls)
    + "</urlset>"
)
files = {
    str(p.relative_to(OUT)): {
        "bytes": p.stat().st_size,
        "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
    }
    for p in sorted(OUT.rglob("*"))
    if p.is_file()
}
(OUT / "public-files.json").write_text(
    json.dumps(
        {
            "scope": "allowlisted original companion, synthetic samples and sanitized measurements only",
            "files": files,
        },
        indent=2,
    )
)
print("Exported", len(files) + 1, "files to", OUT)
