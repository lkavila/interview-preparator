"""Populate the lesson_components table: which interactive components each lesson
shows, controlled from PostgreSQL (not hardcoded in the frontend).

Every lesson gets the LLM-driven components (quiz_card, interview_question_card,
fun_fact_carousel). Lessons whose slug matches an image topic also get an
image_gallery (from images_manifest.json), and hand-picked lessons get a
concept_diagram (mermaid). Idempotent: re-running replaces each lesson's rows.

Run:  python -m app.assign_components
"""

import json
from pathlib import Path

from app.database import SessionLocal
from app.models import Course, Lesson, LessonComponent

MANIFEST_PATH = Path(__file__).resolve().parents[1] / "seeds" / "images_manifest.json"

# Ordered rules: first substring match of the lesson slug wins the image topic.
TOPIC_RULES: list[tuple[str, str]] = [
    ("btree", "b-tree"),
    ("b-tree", "b-tree"),
    ("index", "b-tree"),
    ("hash", "hash-table"),
    ("linked-list", "linked-list"),
    ("array", "linked-list"),
    ("binary", "binary-tree"),
    ("tree", "binary-tree"),
    ("big-o", "big-o"),
    ("complexity", "big-o"),
    ("sort", "sorting"),
    ("stack", "stack-heap"),
    ("heap", "stack-heap"),
    ("join", "sql-joins"),
    ("aggregation", "sql-joins"),
    ("replica", "database-replication"),
    ("cap-theorem", "cap-theorem"),
    ("consistency", "cap-theorem"),
    ("gateway", "api-gateway"),
    ("load-balanc", "load-balancer"),
    ("microservice", "microservices"),
    ("thread", "multithreading"),
    ("gil", "multithreading"),
    ("concurren", "concurrency"),
    ("parallel", "concurrency"),
    ("event-loop", "event-loop"),
    ("asyncio", "event-loop"),
    ("kafka", "kafka"),
    ("partition", "kafka"),
    ("queue", "message-queue"),
    ("broker", "message-queue"),
    ("consumer", "message-queue"),
    ("publish", "publish-subscribe"),
    ("event", "publish-subscribe"),
    ("kubernetes", "kubernetes"),
    ("pod", "kubernetes"),
    ("k8s", "kubernetes"),
    ("container", "containers"),
    ("docker", "containers"),
    ("aws", "aws-cloud"),
    ("cloud", "aws-cloud"),
    ("s3", "aws-cloud"),
    ("lambda", "aws-cloud"),
    ("tcp", "tcp-handshake"),
    ("osi", "osi-model"),
    ("dns", "dns"),
    ("tls", "tls"),
    ("https", "tls"),
    ("http", "http"),
    ("websocket", "websocket"),
    ("cach", "caching"),
    ("redis", "redis"),
    ("react", "react"),
    ("hook", "react"),
    ("node", "nodejs"),
    ("typescript", "typescript"),
    ("monitor", "monitoring"),
    ("observab", "monitoring"),
    ("metric", "monitoring"),
    ("distributed", "distributed-systems"),
    ("scaling", "distributed-systems"),
]

# Course-level fallback topic when no slug rule matches.
COURSE_TOPIC: dict[str, str] = {
    "cs-fundamentals": "big-o",
    "backend-architecture": "microservices",
    "distributed-systems": "distributed-systems",
    "high-throughput": "load-balancer",
    "postgresql": "b-tree",
    "redis-caching": "redis",
    "message-brokers": "kafka",
    "kubernetes": "kubernetes",
    "aws": "aws-cloud",
    "python-django": "multithreading",
    "networking": "osi-model",
    "observability": "monitoring",
    "react": "react",
    "node": "nodejs",
    "typescript": "typescript",
}

# Hand-authored mermaid diagrams keyed by lesson slug substring (first match wins).
DIAGRAMS: list[tuple[str, dict]] = [
    (
        "api-gateway",
        {
            "kind": "mermaid",
            "code": "flowchart LR\n  C[Client] --> G[API Gateway]\n  G -->|auth + rate limit| A[Auth Service]\n  G --> S1[Users Service]\n  G --> S2[Orders Service]\n  G --> S3[Payments Service]\n  S2 --> DB[(PostgreSQL)]\n  S3 --> Q[[Message Broker]]",
            "caption": {
                "en": "A single entry point routes, authenticates and rate-limits traffic to internal services.",
                "es": "Un único punto de entrada enruta, autentica y limita el tráfico hacia los servicios internos.",
            },
        },
    ),
    (
        "cache-aside",
        {
            "kind": "mermaid",
            "code": "sequenceDiagram\n  participant App\n  participant Cache as Redis\n  participant DB as PostgreSQL\n  App->>Cache: GET user:42\n  Cache-->>App: MISS\n  App->>DB: SELECT * FROM users WHERE id=42\n  DB-->>App: row\n  App->>Cache: SET user:42 (TTL 300s)\n  App->>Cache: GET user:42\n  Cache-->>App: HIT",
            "caption": {
                "en": "Cache-aside: read from cache, fall back to the database, then populate the cache.",
                "es": "Cache-aside: lee de la caché, si falla ve a la base de datos y luego llena la caché.",
            },
        },
    ),
    (
        "circuit-breaker",
        {
            "kind": "mermaid",
            "code": "stateDiagram-v2\n  [*] --> Closed\n  Closed --> Open: failures exceed threshold\n  Open --> HalfOpen: cooldown timer expires\n  HalfOpen --> Closed: probe succeeds\n  HalfOpen --> Open: probe fails",
            "caption": {
                "en": "Circuit breaker states: closed (normal), open (fail fast), half-open (probing).",
                "es": "Estados del circuit breaker: cerrado (normal), abierto (falla rápido), semiabierto (sondeo).",
            },
        },
    ),
    (
        "tcp-three-way",
        {
            "kind": "mermaid",
            "code": "sequenceDiagram\n  participant C as Client\n  participant S as Server\n  C->>S: SYN (seq=x)\n  S->>C: SYN-ACK (seq=y, ack=x+1)\n  C->>S: ACK (ack=y+1)\n  Note over C,S: Connection established\n  C->>S: HTTP request",
            "caption": {
                "en": "The TCP three-way handshake establishes a reliable connection before any data flows.",
                "es": "El handshake de tres vías de TCP establece una conexión confiable antes de enviar datos.",
            },
        },
    ),
    (
        "url-to-page",
        {
            "kind": "mermaid",
            "code": "flowchart LR\n  U[URL typed] --> D[DNS resolution]\n  D --> T[TCP handshake]\n  T --> H[TLS handshake]\n  H --> R[HTTP request]\n  R --> P[Server response]\n  P --> X[Parse + render]",
            "caption": {
                "en": "End-to-end journey from typing a URL to a rendered page.",
                "es": "Recorrido completo desde escribir una URL hasta la página renderizada.",
            },
        },
    ),
    (
        "cap-theorem",
        {
            "kind": "mermaid",
            "code": "flowchart TD\n  CAP{CAP theorem}\n  CAP --> C[Consistency]\n  CAP --> A[Availability]\n  CAP --> P[Partition tolerance]\n  C -. CP: e.g. etcd, ZooKeeper .- P\n  A -. AP: e.g. Cassandra, DynamoDB .- P\n  C -. CA: impossible under partitions .- A",
            "caption": {
                "en": "Under a network partition you must choose between consistency and availability.",
                "es": "Ante una partición de red debes elegir entre consistencia y disponibilidad.",
            },
        },
    ),
    (
        "kafka-partitions",
        {
            "kind": "mermaid",
            "code": "flowchart LR\n  P1[Producer] -->|key=user42| T\n  subgraph T[Topic: orders]\n    A[Partition 0]\n    B[Partition 1]\n    C[Partition 2]\n  end\n  A --> C1[Consumer 1]\n  B --> C2[Consumer 2]\n  C --> C2",
            "caption": {
                "en": "Messages with the same key land in the same partition, preserving per-key order.",
                "es": "Los mensajes con la misma clave caen en la misma partición, preservando el orden por clave.",
            },
        },
    ),
    (
        "rolling-updates",
        {
            "kind": "mermaid",
            "code": "flowchart LR\n  D[Deployment v2] --> S1[Start new Pod v2]\n  S1 --> R[Readiness probe passes]\n  R --> T[Traffic shifts to v2]\n  T --> K[Terminate one Pod v1]\n  K -->|repeat until done| S1",
            "caption": {
                "en": "Rolling update: new pods must become ready before old ones are terminated.",
                "es": "Rolling update: los pods nuevos deben estar listos antes de terminar los antiguos.",
            },
        },
    ),
    (
        "layered-architecture",
        {
            "kind": "mermaid",
            "code": "flowchart TD\n  C[Controller / API layer] --> S[Service layer]\n  S --> R[Repository layer]\n  R --> DB[(Database)]\n  C -.->|DTOs| S\n  S -.->|domain objects| R",
            "caption": {
                "en": "Each layer only talks to the one below it, keeping responsibilities separate.",
                "es": "Cada capa solo habla con la de abajo, manteniendo responsabilidades separadas.",
            },
        },
    ),
    (
        "retries-and-backoff",
        {
            "kind": "mermaid",
            "code": "flowchart LR\n  A[Request] --> F{Failed?}\n  F -->|no| OK[Done]\n  F -->|yes| W1[Wait 1s + jitter]\n  W1 --> R1[Retry 1]\n  R1 --> F2{Failed?}\n  F2 -->|no| OK\n  F2 -->|yes| W2[Wait 2s + jitter]\n  W2 --> R2[Retry 2]\n  R2 --> F3{Failed?}\n  F3 -->|yes| DLQ[Give up / DLQ]\n  F3 -->|no| OK",
            "caption": {
                "en": "Exponential backoff with jitter prevents retry storms against a struggling service.",
                "es": "El backoff exponencial con jitter evita tormentas de reintentos contra un servicio degradado.",
            },
        },
    ),
    (
        "websocket",
        {
            "kind": "mermaid",
            "code": "sequenceDiagram\n  participant B as Browser\n  participant S as Server\n  B->>S: HTTP GET + Upgrade: websocket\n  S->>B: 101 Switching Protocols\n  Note over B,S: Persistent bidirectional channel\n  S->>B: push event\n  B->>S: message\n  S->>B: push event",
            "caption": {
                "en": "One HTTP upgrade handshake, then full-duplex messaging over a single TCP connection.",
                "es": "Un handshake de upgrade HTTP y luego mensajería full-duplex sobre una sola conexión TCP.",
            },
        },
    ),
    (
        "event-loop",
        {
            "kind": "mermaid",
            "code": "flowchart TD\n  Q[Callback queue] --> L{Event loop}\n  L -->|stack empty?| S[Call stack]\n  S --> API[async APIs: timers, I/O]\n  API --> Q\n  L -->|microtasks first| M[Promise queue]\n  M --> S",
            "caption": {
                "en": "The event loop moves callbacks to the stack only when it is empty; microtasks run first.",
                "es": "El event loop mueve callbacks a la pila solo cuando está vacía; las microtareas van primero.",
            },
        },
    ),
    (
        "idempotency",
        {
            "kind": "mermaid",
            "code": "sequenceDiagram\n  participant C as Client\n  participant S as Payment API\n  C->>S: POST /charge (Idempotency-Key: abc)\n  S-->>C: 200 charged $10\n  Note over C: timeout, client retries\n  C->>S: POST /charge (Idempotency-Key: abc)\n  S-->>C: 200 (cached result, no double charge)",
            "caption": {
                "en": "The same idempotency key returns the stored result instead of repeating the side effect.",
                "es": "La misma clave de idempotencia devuelve el resultado guardado en vez de repetir el efecto.",
            },
        },
    ),
    (
        "load-balancing",
        {
            "kind": "mermaid",
            "code": "flowchart LR\n  C1[Clients] --> LB{Load balancer}\n  LB -->|round robin / least conn| S1[Server 1]\n  LB --> S2[Server 2]\n  LB --> S3[Server 3]\n  LB -.->|health checks| S1 & S2 & S3",
            "caption": {
                "en": "The balancer spreads traffic and stops routing to instances that fail health checks.",
                "es": "El balanceador reparte tráfico y deja de enrutar a instancias que fallan los health checks.",
            },
        },
    ),
    (
        "reconciliation",
        {
            "kind": "mermaid",
            "code": "flowchart TD\n  S[setState] --> V2[New virtual DOM]\n  V1[Previous virtual DOM] --> D{Diff}\n  V2 --> D\n  D --> P[Minimal patch set]\n  P --> DOM[Real DOM updates]",
            "caption": {
                "en": "React diffs virtual DOM trees and applies only the minimal set of real DOM changes.",
                "es": "React compara árboles de virtual DOM y aplica solo el mínimo de cambios reales al DOM.",
            },
        },
    ),
]


def image_topic_for(lesson_slug: str, course_slug: str) -> str | None:
    for needle, topic in TOPIC_RULES:
        if needle in lesson_slug:
            return topic
    return COURSE_TOPIC.get(course_slug)


def diagram_for(lesson_slug: str) -> dict | None:
    for needle, config in DIAGRAMS:
        if needle in lesson_slug:
            return config
    return None


def main() -> None:
    manifest: dict[str, list[dict]] = {}
    if MANIFEST_PATH.exists():
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    db = SessionLocal()
    created = 0
    galleries = 0
    diagrams = 0
    try:
        lessons = db.query(Lesson).join(Course).all()
        for lesson in lessons:
            db.query(LessonComponent).filter(LessonComponent.lesson_id == lesson.id).delete()

            topic = image_topic_for(lesson.slug, lesson.course.slug)
            images = manifest.get(topic or "", [])

            rows = [
                LessonComponent(
                    lesson_id=lesson.id,
                    component_type="fun_fact_carousel",
                    order_index=10,
                    config={"images": images[:1]} if images else {},
                ),
                LessonComponent(
                    lesson_id=lesson.id, component_type="interview_question_card", order_index=20, config={}
                ),
                LessonComponent(
                    lesson_id=lesson.id, component_type="quiz_card", order_index=30, config={}
                ),
            ]

            diagram = diagram_for(lesson.slug)
            if diagram:
                rows.append(
                    LessonComponent(
                        lesson_id=lesson.id,
                        component_type="concept_diagram",
                        order_index=5,
                        config=diagram,
                    )
                )
                diagrams += 1

            if images:
                rows.append(
                    LessonComponent(
                        lesson_id=lesson.id,
                        component_type="image_gallery",
                        order_index=40,
                        config={"images": images[:4]},
                    )
                )
                galleries += 1

            db.add_all(rows)
            created += len(rows)
        db.commit()
    finally:
        db.close()

    print(f"Assigned {created} components to {len(lessons)} lessons "
          f"({galleries} galleries, {diagrams} diagrams).")


if __name__ == "__main__":
    main()
