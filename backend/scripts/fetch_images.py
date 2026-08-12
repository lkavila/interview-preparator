"""Download illustrative diagrams/images from Wikimedia Commons for lesson topics.

Strategy per topic: first fetch curated, known-good Commons files by exact title;
if none resolve, fall back to a keyword-filtered search. Throttled + retry on 429
per Wikimedia bot policy. Saves to frontend/public/images/lessons/<topic>/ and
writes attribution to backend/seeds/images_manifest.json.
"""

import json
import re
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]
IMAGES_DIR = ROOT / "frontend" / "public" / "images" / "lessons"
MANIFEST_PATH = ROOT / "backend" / "seeds" / "images_manifest.json"

API = "https://commons.wikimedia.org/w/api.php"
# Wikimedia requires a descriptive User-Agent with contact info (https://w.wiki/4wJS)
HEADERS = {
    "User-Agent": "InterviewPreparatorBot/1.0 (educational desktop app; contact: usuario.dev@outlook.com) python-httpx/0.27"
}
THROTTLE_SECONDS = 1.5

# topic -> curated exact Commons file titles (classic, well-known diagrams)
CURATED: dict[str, list[str]] = {
    "big-o": ["File:Comparison computational complexity.svg"],
    "binary-tree": ["File:Binary search tree.svg", "File:AVL Tree Example.gif"],
    "linked-list": ["File:Singly-linked-list.svg", "File:Doubly-linked-list.svg"],
    "hash-table": ["File:Hash table 3 1 1 0 1 0 0 SP.svg", "File:Hash table 5 0 1 1 1 1 1 LL.svg"],
    "sorting": ["File:Merge sort algorithm diagram.svg", "File:Quicksort-diagram.svg"],
    "stack-heap": ["File:ProgramCallStack2 en.svg", "File:Lifo stack.svg"],
    "b-tree": ["File:B-tree.svg", "File:B tree insertion example.png"],
    "sql-joins": ["File:SQL Joins.svg"],
    "cap-theorem": ["File:CAP Theorem Venn Diagram khazaei.png"],
    "tcp-handshake": ["File:Tcp state diagram fixed new.svg", "File:TCP CLOSE.svg"],
    "osi-model": ["File:OSI Model v1.svg", "File:OSI-model-Communication.svg"],
    "dns": ["File:DNS Architecture.svg", "File:Domain name space.svg"],
    "tls": ["File:Full TLS 1.2 Handshake.svg", "File:Tls handshake.png"],
    "http": ["File:HTTP cookie exchange.svg", "File:Internet1.svg"],
    "websocket": ["File:Websocket connection.png", "File:WebSockets-Protocol.png"],
    "load-balancer": ["File:Elastic Load Balancing.png", "File:Load Balancing Cluster (NAT).png"],
    "multithreading": ["File:Multithreaded process.svg", "File:Concepts- Program vs. Process vs. Thread.jpg"],
    "concurrency": ["File:Parallel-concurrent.png", "File:Amdahlslaw.svg"],
    "event-loop": ["File:Event loop.svg", "File:Node.js Event Loop.png"],
    "microservices": ["File:Microservices Architektur.png", "File:Microservice Architecture.png"],
    "api-gateway": ["File:Wso2-esb-overview.png", "File:API-Gateway-Muster.png"],
    "message-queue": ["File:Message Queue Diagram.png", "File:Message queue.svg"],
    "kafka": ["File:Overview of Apache Kafka.svg", "File:Apache kafka wordtype.svg"],
    "publish-subscribe": ["File:Publish subscribe.svg"],
    "kubernetes": ["File:Kubernetes.png", "File:Kubernetes logo without workmark.svg"],
    "containers": ["File:Docker-containerized-and-vm-transparent-bg.png", "File:Docker (container engine) logo.svg"],
    "aws-cloud": ["File:Cloud computing.svg", "File:AWS Simple Icons AWS Cloud.svg"],
    "caching": ["File:Cache,basic.svg", "File:Cache hierarchy example.png"],
    "redis": ["File:Redis Logo.svg", "File:Redis-logo.svg"],
    "database-replication": ["File:Active replication.png", "File:Replicare pasiva.png"],
    "distributed-systems": ["File:Distributed-parallel.svg", "File:NetworkTopologies.svg"],
    "react": ["File:React-icon.svg", "File:React Developer Tools screenshot.png"],
    "nodejs": ["File:Node.js logo.svg", "File:Unofficial JavaScript logo 2.svg"],
    "typescript": ["File:Typescript logo 2020.svg"],
    "monitoring": ["File:Grafana dashboard.png", "File:Prometheus software logo.svg"],
}

# fallback search queries + relevance keywords (title must contain one)
SEARCH: dict[str, tuple[str, list[str]]] = {
    "api-gateway": ("API gateway diagram", ["gateway", "api"]),
    "load-balancer": ("load balancing diagram", ["load", "balanc"]),
    "microservices": ("microservices architecture", ["microservice"]),
    "multithreading": ("thread process diagram", ["thread", "process"]),
    "concurrency": ("concurrency parallel diagram", ["concurren", "parallel"]),
    "event-loop": ("event loop diagram", ["event loop", "event-loop"]),
    "hash-table": ("hash table diagram", ["hash"]),
    "linked-list": ("linked list diagram", ["linked"]),
    "binary-tree": ("binary search tree diagram", ["binary", "tree"]),
    "big-o": ("computational complexity comparison", ["complexity", "big o", "big-o"]),
    "sorting": ("sorting algorithm diagram", ["sort"]),
    "stack-heap": ("call stack diagram", ["stack"]),
    "b-tree": ("B-tree diagram", ["b-tree", "b tree", "btree"]),
    "sql-joins": ("SQL joins diagram", ["join", "sql"]),
    "database-replication": ("database replication diagram", ["replic"]),
    "cap-theorem": ("CAP theorem", ["cap"]),
    "message-queue": ("message queue diagram", ["queue", "message"]),
    "kafka": ("Apache Kafka diagram", ["kafka"]),
    "publish-subscribe": ("publish subscribe pattern", ["publish", "subscrib", "pub"]),
    "kubernetes": ("Kubernetes architecture", ["kubernetes", "k8s"]),
    "containers": ("Docker container virtualization", ["docker", "container"]),
    "aws-cloud": ("cloud computing diagram", ["cloud", "aws"]),
    "tcp-handshake": ("TCP handshake diagram", ["tcp", "handshake"]),
    "osi-model": ("OSI model diagram", ["osi"]),
    "dns": ("DNS hierarchy diagram", ["dns", "domain name"]),
    "tls": ("TLS handshake diagram", ["tls", "ssl", "handshake"]),
    "http": ("HTTP request diagram", ["http"]),
    "websocket": ("WebSocket diagram", ["websocket", "web socket"]),
    "caching": ("CPU cache diagram", ["cache", "caching"]),
    "redis": ("Redis logo", ["redis"]),
    "react": ("React JavaScript library", ["react"]),
    "nodejs": ("Node.js logo", ["node"]),
    "typescript": ("TypeScript logo", ["typescript"]),
    "monitoring": ("Grafana Prometheus dashboard", ["grafana", "prometheus", "dashboard", "monitor"]),
    "distributed-systems": ("distributed computing diagram", ["distribut"]),
}

EXT_OK = {"png", "jpg", "jpeg", "svg", "gif", "webp"}


def slugify(name: str) -> str:
    name = re.sub(r"[^a-zA-Z0-9._-]+", "-", name)
    return name.strip("-")[:80]


def clean_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text or "").strip()


def api_get(client: httpx.Client, params: dict) -> dict | None:
    for attempt in range(3):
        time.sleep(THROTTLE_SECONDS)
        try:
            r = client.get(API, params=params)
            if r.status_code == 429:
                time.sleep(15 * (attempt + 1))
                continue
            r.raise_for_status()
            return r.json()
        except httpx.HTTPError as e:
            print(f"  api error: {e}")
            time.sleep(5)
    return None


def download(client: httpx.Client, url: str, dest: Path) -> bool:
    for attempt in range(3):
        time.sleep(THROTTLE_SECONDS)
        try:
            r = client.get(url)
            if r.status_code == 429:
                time.sleep(15 * (attempt + 1))
                continue
            r.raise_for_status()
            dest.write_bytes(r.content)
            return True
        except httpx.HTTPError as e:
            print(f"  download error: {e}")
    return False


def entries_from_pages(pages: dict, relevance: list[str] | None = None, limit: int = 3) -> list[dict]:
    results = []
    for page in sorted(pages.values(), key=lambda p: p.get("index", 99)):
        title = page.get("title", "")
        if page.get("missing") is not None or "imageinfo" not in page:
            continue
        if relevance and not any(k.lower() in title.lower() for k in relevance):
            continue
        info = page["imageinfo"][0]
        url = info.get("thumburl") or info.get("url")
        if not url:
            continue
        ext = url.split("?")[0].rsplit(".", 1)[-1].lower()
        if ext not in EXT_OK:
            continue
        meta = info.get("extmetadata") or {}
        license_short = clean_html((meta.get("LicenseShortName") or {}).get("value", ""))
        if license_short and re.search(r"copyright|non-free", license_short, re.I):
            continue
        results.append(
            {
                "title": title.replace("File:", ""),
                "url": url,
                "author": clean_html((meta.get("Artist") or {}).get("value", ""))[:120],
                "license": license_short or "See source",
                "source_url": info.get("descriptionurl") or "",
            }
        )
        if len(results) >= limit:
            break
    return results


IIPROPS = {"prop": "imageinfo", "iiprop": "url|extmetadata|mime", "iiurlwidth": 1200}


def fetch_curated(client: httpx.Client, titles: list[str]) -> list[dict]:
    data = api_get(
        client,
        {"action": "query", "format": "json", "titles": "|".join(titles), **IIPROPS},
    )
    pages = ((data or {}).get("query") or {}).get("pages") or {}
    return entries_from_pages(pages, relevance=None, limit=3)


def fetch_search(client: httpx.Client, query: str, relevance: list[str]) -> list[dict]:
    data = api_get(
        client,
        {
            "action": "query",
            "format": "json",
            "generator": "search",
            "gsrsearch": f"filetype:bitmap|drawing {query}",
            "gsrlimit": 10,
            "gsrnamespace": 6,
            **IIPROPS,
        },
    )
    pages = ((data or {}).get("query") or {}).get("pages") or {}
    return entries_from_pages(pages, relevance=relevance, limit=2)


def main() -> None:
    refresh = "--refresh" in sys.argv
    manifest: dict[str, list[dict]] = {}
    if MANIFEST_PATH.exists() and not refresh:
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    topics = list(SEARCH.keys())
    with httpx.Client(headers=HEADERS, timeout=60, follow_redirects=True) as client:
        for topic in topics:
            if manifest.get(topic) and not refresh:
                print(f"skip {topic} ({len(manifest[topic])} already)")
                continue
            found = fetch_curated(client, CURATED.get(topic, [])) if CURATED.get(topic) else []
            if not found:
                query, relevance = SEARCH[topic]
                found = fetch_search(client, query, relevance)

            entries = []
            topic_dir = IMAGES_DIR / topic
            topic_dir.mkdir(parents=True, exist_ok=True)
            for item in found:
                ext = item["url"].split("?")[0].rsplit(".", 1)[-1].lower()
                fname = slugify(item["title"])
                if not fname.lower().endswith(f".{ext}"):
                    fname = f"{fname}.{ext}"
                dest = topic_dir / fname
                if download(client, item["url"], dest):
                    entries.append(
                        {
                            "src": f"/images/lessons/{topic}/{fname}",
                            "title": item["title"],
                            "author": item["author"],
                            "license": item["license"],
                            "source_url": item["source_url"],
                        }
                    )
            manifest[topic] = entries
            print(f"{topic}: {len(entries)} images")

    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    total = sum(len(v) for v in manifest.values())
    with_images = sum(1 for v in manifest.values() if v)
    print(f"manifest written: {total} images across {with_images}/{len(manifest)} topics")


if __name__ == "__main__":
    main()
