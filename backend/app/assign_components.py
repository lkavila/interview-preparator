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
    "database-selection": "b-tree",
    "golang": "concurrency",
    # behavioral-interview has no meaningful image topic — left out on purpose.
}

# Hand-authored mermaid diagrams keyed by lesson slug substring (first match wins).
# Order matters: longer, more specific needles must come BEFORE shorter ones, or a
# generic needle swallows a specific lesson (e.g. "explain-analyze" would also match
# "reading-explain-analyze-step-by-step").
DIAGRAMS: list[tuple[str, dict]] = [
    (
        "goroutines-and-the-scheduler",
        {
            "kind": "mermaid",
            "code": (
                "flowchart TD\n"
                '  subgraph P1["P (processor) - one per GOMAXPROCS"]\n'
                '    Q1["local run queue: G G G"]\n'
                "  end\n"
                '  subgraph P2["P (processor)"]\n'
                '    Q2["local run queue: G"]\n'
                "  end\n"
                '  GQ["global run queue"]\n'
                '  M1["M - OS thread"] --> P1\n'
                '  M2["M - OS thread"] --> P2\n'
                "  GQ --> P1\n"
                "  GQ --> P2\n"
                '  P2 -.->|"work stealing when its queue is empty"| P1\n'
                '  P1 --> RUN["G running on M1"]\n'
                '  RUN -->|"blocks on channel or network read"| PARK["parked; M1 picks up the next G"]\n'
                '  PARK -.->|"ready again"| Q1'
            ),
            "caption": {
                "en": "The M:N scheduler: many goroutines multiplexed onto few OS threads. A blocked goroutine is parked so its thread runs another — which is why Go needs no async/await.",
                "es": "El scheduler M:N: muchas goroutines multiplexadas sobre pocos hilos del SO. Una goroutine bloqueada se estaciona para que su hilo corra otra — por eso Go no necesita async/await.",
            },
        },
    ),
    (
        "channels-and-select",
        {
            "kind": "mermaid",
            "code": (
                "flowchart LR\n"
                '  S["Sender goroutine"] -->|"ch <- v"| C{"Channel"}\n'
                '  C -->|"unbuffered: blocks until a receiver is ready"| R["Receiver goroutine"]\n'
                '  C -->|"buffered: blocks only when full"| R\n'
                '  R --> SEL{"select"}\n'
                '  SEL -->|"case v := <-work"| W["process the value"]\n'
                '  SEL -->|"case <-ctx.Done()"| X["return ctx.Err()"]\n'
                '  SEL -->|"case <-time.After(1s)"| T["timeout"]\n'
                '  SEL -->|"default"| N["non-blocking: run immediately"]\n'
                '  SEL -.->|"several ready: one is chosen at random"| SEL'
            ),
            "caption": {
                "en": "An unbuffered channel is a rendezvous, not a queue. select waits on several operations at once, and picks randomly among ready cases so none can starve.",
                "es": "Un canal sin buffer es una cita, no una cola. select espera varias operaciones a la vez, y elige al azar entre los casos listos para que ninguno quede hambriento.",
            },
        },
    ),
    (
        "context-and-where-async-await",
        {
            "kind": "mermaid",
            "code": (
                "flowchart TD\n"
                '  subgraph JS["JavaScript / Python"]\n'
                '    A1["async function"] --> A2["await io()"]\n'
                '    A2 --> A3["every caller must also be async"]\n'
                '    A3 --> A4["function colouring spreads through the call graph"]\n'
                "  end\n"
                '  subgraph GO["Go"]\n'
                '    B1["plain function"] --> B2["resp, err := http.Get(url)"]\n'
                '    B2 --> B3["goroutine parks; the OS thread runs another"]\n'
                '    B3 --> B4["no async keyword, so no colouring"]\n'
                "  end\n"
                '  B4 --> C1["but a goroutine cannot be killed from outside"]\n'
                '  C1 --> C2["ctx, cancel := context.WithTimeout(...)"]\n'
                '  C2 --> C3["select on ctx.Done() to return early"]\n'
                '  C3 --> C4["cancelling a parent cancels every derived context"]'
            ),
            "caption": {
                "en": "Go replaces async/await with cheap blocking, and replaces the promise's cancellation story with context.Context — needed because a goroutine must return on its own.",
                "es": "Go reemplaza async/await con bloqueo barato, y reemplaza la cancelación de las promesas con context.Context — necesario porque una goroutine debe retornar por su cuenta.",
            },
        },
    ),
    (
        "is-go-object-oriented",
        {
            "kind": "mermaid",
            "code": (
                "flowchart TD\n"
                '  OOP["Classical OOP"] --> I1["Encapsulation"]\n'
                '  OOP --> I2["Polymorphism"]\n'
                '  OOP --> I3["Inheritance"]\n'
                '  I1 --> G1["Go: yes, but per package - Name is exported, name is not"]\n'
                '  I2 --> G2["Go: yes, via interfaces satisfied implicitly and structurally"]\n'
                '  I3 --> G3["Go: no. Embedding delegates but gives no virtual dispatch"]\n'
                '  G2 --> C1["The consumer declares the interface, so tiny interfaces like io.Reader compose"]\n'
                '  G3 --> C2["Pass behaviour in as a field or small interface instead of overriding"]'
            ),
            "caption": {
                "en": "Go keeps encapsulation and polymorphism and deliberately drops inheritance. Embedding looks like inheritance but is delegation — a method defined on the outer type never overrides one the inner type calls on itself.",
                "es": "Go conserva la encapsulación y el polimorfismo y descarta la herencia a propósito. El embedding parece herencia pero es delegación — un método definido en el tipo externo nunca sobrescribe a uno que el tipo interno se llama a sí mismo.",
            },
        },
    ),
    (
        "reading-explain-analyze",
        {
            "kind": "mermaid",
            "code": (
                "flowchart TD\n"
                '  A["Limit (cost=0.4..8.5 rows=10)"] --> B["Sort (actual rows=48000 loops=1)"]\n'
                '  B --> C["Hash Join (cost=812..1904)"]\n'
                '  C --> D["Seq Scan on orders (est 60000 / actual 60000)"]\n'
                '  C --> E["Hash"]\n'
                '  E --> F["Index Scan on customers (est 20 / actual 4800)"]\n'
                '  F -.->|"estimate 240x too low, so the join above picked wrong"| C'
            ),
            "caption": {
                "en": "Read a plan bottom-up: leaf scans run first, and a bad row estimate at a leaf poisons every node above it.",
                "es": "Lee un plan de abajo hacia arriba: los scans de las hojas corren primero, y una mala estimación de filas en una hoja envenena todos los nodos de arriba.",
            },
        },
    ),
    (
        "seq-scan-vs-index-scan",
        {
            "kind": "mermaid",
            "code": (
                "flowchart LR\n"
                '  Q["WHERE user_id = 4242"] --> P{"What fraction of rows match?"}\n'
                '  P -->|"0.02% - selective"| I["Index Scan"]\n'
                '  P -->|"100% - everything matches"| S["Seq Scan"]\n'
                '  I --> I1["descend B-tree root to leaf"]\n'
                '  I1 --> I2["random heap fetch per match"]\n'
                '  I2 --> I3["cost = random_page_cost x matches"]\n'
                '  S --> S1["read every page in order"]\n'
                '  S1 --> S2["cost = seq_page_cost x pages"]\n'
                '  I3 --> R["cheapest plan wins"]\n'
                "  S2 --> R"
            ),
            "caption": {
                "en": "Postgres does not prefer indexes — it prefers the cheaper plan. Random I/O per matching row is what makes an index lose on a non-selective filter.",
                "es": "Postgres no prefiere índices — prefiere el plan más barato. La E/S aleatoria por cada fila que coincide es lo que hace perder al índice en un filtro poco selectivo.",
            },
        },
    ),
    (
        "join-algorithms",
        {
            "kind": "mermaid",
            "code": (
                "flowchart TD\n"
                '  J{"Join orders x customers"}\n'
                '  J --> NL["Nested Loop"]\n'
                '  J --> HJ["Hash Join"]\n'
                '  J --> MJ["Merge Join"]\n'
                '  NL --> NL1["for each outer row, probe the inner index"]\n'
                '  NL1 --> NL2["wins when the outer side is tiny"]\n'
                '  NL2 --> NL3["degrades: outer estimate too low, millions of loops"]\n'
                '  HJ --> HJ1["build a hash table from the smaller side"]\n'
                '  HJ1 --> HJ2["scan the larger side once and probe"]\n'
                '  HJ2 --> HJ3["degrades: hash spills to disk past work_mem"]\n'
                '  MJ --> MJ1["both inputs sorted on the join key"]\n'
                '  MJ1 --> MJ2["walk both in lockstep"]\n'
                '  MJ2 --> MJ3["degrades: pays for a Sort unless an index gives order"]'
            ),
            "caption": {
                "en": "Three algorithms, three failure modes: loop count, work_mem, and the cost of sorting.",
                "es": "Tres algoritmos, tres modos de fallo: el número de loops, work_mem y el costo de ordenar.",
            },
        },
    ),
    (
        "choosing-where-state-lives",
        {
            "kind": "mermaid",
            "code": (
                "flowchart TD\n"
                '  S["A new piece of state"] --> A{"Does it come from a server?"}\n'
                '  A -->|yes| SC["Server-cache state: React Query / RTK Query"]\n'
                '  A -->|no| B{"Must it survive a reload or be shareable by link?"}\n'
                '  B -->|yes| URL["URL state: search params / route"]\n'
                '  B -->|no| C{"Does the UI need to re-render when it changes?"}\n'
                '  C -->|no| REF["useRef: timers, scroll offsets, latest-value refs"]\n'
                '  C -->|yes| D{"Who reads it?"}\n'
                '  D -->|"one component"| L["useState, or useReducer if fields move together"]\n'
                '  D -->|"a parent and its children"| LIFT["Lift to the common parent, pass children"]\n'
                '  D -->|"a distant subtree"| E{"Does it change often?"}\n'
                '  E -->|rarely| CTX["Context: theme, locale, current user"]\n'
                '  E -->|often| STORE["External store with selectors: Redux / Zustand"]'
            ),
            "caption": {
                "en": "Most 'we need Redux' problems are really server-cache state or a missing composition.",
                "es": "La mayoría de los problemas de 'necesitamos Redux' son en realidad estado de caché del servidor o una composición que falta.",
            },
        },
    ),
    (
        "how-the-planner-chooses",
        {
            "kind": "mermaid",
            "code": (
                "flowchart LR\n"
                '  ST["pg_stats: n_distinct, MCVs, histogram, correlation"] --> SEL["Selectivity estimate"]\n'
                '  SEL --> ROWS["Estimated rows per node"]\n'
                '  ROWS --> COST["Cost = seq_page_cost x pages + random_page_cost x fetches + cpu x rows"]\n'
                '  CFG["random_page_cost, effective_cache_size, work_mem"] --> COST\n'
                '  COST --> PICK{"Cheapest total cost"}\n'
                '  PICK --> PLAN["Chosen plan"]\n'
                '  PLAN -.->|"stale stats produce wrong rows, and wrong rows produce a wrong plan"| ST'
            ),
            "caption": {
                "en": "The planner never measures your data at plan time — it estimates from statistics. Stale statistics are the single most common cause of a bad plan.",
                "es": "El planner nunca mide tus datos al planificar — estima a partir de estadísticas. Las estadísticas desactualizadas son la causa más común de un mal plan.",
            },
        },
    ),
    (
        "window-frames",
        {
            "kind": "mermaid",
            "code": (
                "flowchart TD\n"
                '  R["Rows after WHERE and GROUP BY"] --> P["PARTITION BY region: independent windows"]\n'
                '  P --> O["ORDER BY month: order inside each window"]\n'
                '  O --> F["Frame: ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW"]\n'
                '  F --> V["Running total per region"]\n'
                '  O --> LG["LAG(amount): previous row in the same partition"]\n'
                '  LG --> D["Month-over-month delta"]'
            ),
            "caption": {
                "en": "PARTITION BY splits the rows, ORDER BY orders them inside each split, and the frame decides which of them the function actually sees.",
                "es": "PARTITION BY divide las filas, ORDER BY las ordena dentro de cada división, y el frame decide cuáles de ellas ve realmente la función.",
            },
        },
    ),
    (
        "relational-vs-document",
        {
            "kind": "mermaid",
            "code": (
                "flowchart TD\n"
                '  A["New service, choosing a database"] --> B{"Are the access patterns known and stable?"}\n'
                '  B -->|no, queries will change| REL["Relational: Postgres / SQL Server"]\n'
                '  B -->|yes, few and fixed| C{"Do you need multi-entity transactions?"}\n'
                '  C -->|yes| REL\n'
                '  C -->|no| D{"Predictable single-digit ms at any scale?"}\n'
                '  D -->|yes, and you accept the modelling cost| DDB["DynamoDB: single-table design"]\n'
                '  D -->|no, want flexible documents| MDB["MongoDB: flexible schema, rich queries"]\n'
                '  REL --> E["JOINs, constraints, ad-hoc SQL, mature tooling"]\n'
                '  DDB --> F["No planner, no JOINs, capacity is the cost model"]\n'
                '  MDB --> G["Aggregation pipeline, needs index discipline"]'
            ),
            "caption": {
                "en": "The real question is not SQL vs NoSQL — it is whether your access patterns are known in advance.",
                "es": "La pregunta real no es SQL vs NoSQL — es si tus patrones de acceso se conocen de antemano.",
            },
        },
    ),
    (
        "the-star-method",
        {
            "kind": "mermaid",
            "code": (
                "flowchart LR\n"
                '  S["Situation: one sentence of context"] --> T["Task: what you owned"]\n'
                '  T --> A["Action: what YOU did, decisions and trade-offs"]\n'
                '  A --> R["Result: a number, plus what you changed after"]\n'
                '  A -.->|"spend about 60% of your time here"| A'
            ),
            "caption": {
                "en": "Interviewers score the Action. Keep Situation and Task to one sentence each, and never end without a measurable Result.",
                "es": "El entrevistador califica la Acción. Deja Situación y Tarea en una frase cada una, y nunca termines sin un Resultado medible.",
            },
        },
    ),
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


# --------------------------------------------------------------------------
# SQL playgrounds: a real Postgres (PGlite/wasm) the learner types into. The
# session persists across runs, so CREATE INDEX in one query changes the plan of
# the next — that is the whole point. `schema_sql` is split on a "-- @split"
# line by the frontend, because VACUUM cannot run inside the implicit
# transaction PGlite wraps a multi-statement batch in.
# --------------------------------------------------------------------------

_SCAN_KIND_FN = """CREATE OR REPLACE FUNCTION scan_kind(q text) RETURNS text AS $$
DECLARE p jsonb; s text;
BEGIN
  EXECUTE 'EXPLAIN (FORMAT JSON) ' || q INTO p;
  s := p::text;
  IF s LIKE '%Index Only Scan%' THEN RETURN 'index-only';
  ELSIF s LIKE '%Index Scan%' OR s LIKE '%Bitmap%' THEN RETURN 'index';
  ELSE RETURN 'seq'; END IF;
END $$ LANGUAGE plpgsql;"""

_EVENTS_SCHEMA = f"""CREATE TABLE events (
  id SERIAL PRIMARY KEY,
  user_id INT NOT NULL,
  kind TEXT NOT NULL,
  amount NUMERIC(10,2) NOT NULL
);
INSERT INTO events (user_id, kind, amount)
SELECT (g % 5000) + 1,
       (ARRAY['click','view','purchase'])[1 + (g % 3)],
       (g % 500)::numeric(10,2)
FROM generate_series(1, 30000) g;
ANALYZE events;
{_SCAN_KIND_FN}
-- @split
VACUUM events;"""

_SALES_SCHEMA = """CREATE TABLE sales (
  id SERIAL PRIMARY KEY,
  region TEXT NOT NULL,
  month INT NOT NULL,
  amount NUMERIC(10,2) NOT NULL
);
INSERT INTO sales (region, month, amount) VALUES
  ('north', 1, 100), ('north', 2, 140), ('north', 3, 90),  ('north', 4, 200),
  ('south', 1, 250), ('south', 2, 180), ('south', 3, 300), ('south', 4, 220),
  ('east',  1, 120), ('east',  2, 120), ('east',  3, 160), ('east',  4, 140);
ANALYZE sales;"""

_JOIN_SCHEMA = """CREATE TABLE customers (id SERIAL PRIMARY KEY, country TEXT NOT NULL);
INSERT INTO customers (country)
SELECT CASE WHEN g % 1000 = 0 THEN 'AD' ELSE 'US' END FROM generate_series(1, 20000) g;
CREATE TABLE orders (id SERIAL PRIMARY KEY, customer_id INT NOT NULL, amount INT NOT NULL);
INSERT INTO orders (customer_id, amount)
SELECT (g % 20000) + 1, (g % 500) FROM generate_series(1, 60000) g;
ANALYZE customers;
ANALYZE orders;
CREATE OR REPLACE FUNCTION join_kind(q text) RETURNS text AS $$
DECLARE p jsonb; s text;
BEGIN
  EXECUTE 'EXPLAIN (FORMAT JSON) ' || q INTO p;
  s := p::text;
  IF s LIKE '%Hash Join%' THEN RETURN 'hash';
  ELSIF s LIKE '%Merge Join%' THEN RETURN 'merge';
  ELSIF s LIKE '%Nested Loop%' THEN RETURN 'nested-loop';
  ELSE RETURN 'other'; END IF;
END $$ LANGUAGE plpgsql;"""

_SCAN_PLAYGROUND = {
    "schema_sql": _EVENTS_SCHEMA,
    "title": {"en": "Watch the plan change", "es": "Mira cómo cambia el plan"},
    "intro": {
        "en": "`events` has 30 000 rows and no index on `user_id` yet. Run the queries in order and watch the node type flip.",
        "es": "`events` tiene 30 000 filas y todavía no tiene índice en `user_id`. Ejecuta las consultas en orden y observa cómo cambia el tipo de nodo.",
    },
    "initial_query": "EXPLAIN ANALYZE SELECT * FROM events WHERE user_id = 4242;",
    "samples": [
        {
            "label": {"en": "1. Plan without index", "es": "1. Plan sin índice"},
            "sql": "EXPLAIN ANALYZE SELECT * FROM events WHERE user_id = 4242;",
        },
        {
            "label": {"en": "2. Create the index", "es": "2. Crear el índice"},
            "sql": "CREATE INDEX idx_events_user ON events (user_id);\nANALYZE events;",
        },
        {
            "label": {"en": "3. Plan with index", "es": "3. Plan con índice"},
            "sql": "EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM events WHERE user_id = 4242;",
        },
        {
            "label": {"en": "4. A filter that matches a third of the table", "es": "4. Un filtro que toca un tercio de la tabla"},
            "sql": "EXPLAIN ANALYZE SELECT * FROM events WHERE kind = 'click';",
        },
        {
            "label": {"en": "5. Force the seq scan off", "es": "5. Apagar el seq scan"},
            "sql": "SET enable_seqscan = off;\nEXPLAIN ANALYZE SELECT * FROM events WHERE kind = 'click';",
        },
        {
            "label": {"en": "6. Ask the helper", "es": "6. Preguntar al helper"},
            "sql": "SELECT scan_kind('SELECT * FROM events WHERE user_id = 4242') AS by_user,\n       scan_kind('SELECT * FROM events WHERE kind = ''click''') AS by_kind;",
        },
    ],
}

_PLANNER_PLAYGROUND = {
    "schema_sql": _EVENTS_SCHEMA,
    "title": {"en": "Inspect the planner's inputs", "es": "Inspecciona las entradas del planner"},
    "intro": {
        "en": "The planner never looks at your rows — it estimates from `pg_stats` and the cost settings. Read them here.",
        "es": "El planner nunca mira tus filas — estima desde `pg_stats` y los parámetros de costo. Míralos aquí.",
    },
    "initial_query": "SELECT attname, n_distinct, correlation FROM pg_stats WHERE tablename = 'events';",
    "samples": [
        {
            "label": {"en": "Statistics of the table", "es": "Estadísticas de la tabla"},
            "sql": "SELECT attname, n_distinct, correlation, most_common_vals\nFROM pg_stats WHERE tablename = 'events';",
        },
        {
            "label": {"en": "Cost settings", "es": "Parámetros de costo"},
            "sql": "SELECT name, setting, unit FROM pg_settings\nWHERE name IN ('seq_page_cost','random_page_cost','cpu_tuple_cost','effective_cache_size','work_mem');",
        },
        {
            "label": {"en": "Estimate vs reality", "es": "Estimación vs realidad"},
            "sql": "EXPLAIN ANALYZE SELECT * FROM events WHERE kind = 'purchase';",
        },
        {
            "label": {"en": "Make random I/O look cheap", "es": "Hacer barata la E/S aleatoria"},
            "sql": "CREATE INDEX IF NOT EXISTS idx_events_kind ON events (kind);\nANALYZE events;\nSET random_page_cost = 1.0;\nEXPLAIN SELECT * FROM events WHERE kind = 'purchase';",
        },
        {
            "label": {"en": "Now make it expensive", "es": "Ahora hacerla cara"},
            "sql": "SET random_page_cost = 20;\nEXPLAIN SELECT * FROM events WHERE kind = 'purchase';",
        },
    ],
}

_EXPLAIN_PLAYGROUND = {
    "schema_sql": _JOIN_SCHEMA,
    "title": {"en": "Read a real plan", "es": "Lee un plan real"},
    "intro": {
        "en": "60 000 orders joined to 20 000 customers. Compare `cost` against `actual time`, and estimated `rows` against the real ones.",
        "es": "60 000 órdenes unidas a 20 000 clientes. Compara `cost` contra `actual time`, y las `rows` estimadas contra las reales.",
    },
    "initial_query": "EXPLAIN ANALYZE\nSELECT c.country, count(*), sum(o.amount)\nFROM orders o JOIN customers c ON c.id = o.customer_id\nGROUP BY c.country;",
    "samples": [
        {
            "label": {"en": "Plain EXPLAIN (estimates only)", "es": "EXPLAIN simple (solo estimaciones)"},
            "sql": "EXPLAIN\nSELECT c.country, count(*) FROM orders o\nJOIN customers c ON c.id = o.customer_id GROUP BY c.country;",
        },
        {
            "label": {"en": "EXPLAIN ANALYZE (real timings)", "es": "EXPLAIN ANALYZE (tiempos reales)"},
            "sql": "EXPLAIN ANALYZE\nSELECT c.country, count(*) FROM orders o\nJOIN customers c ON c.id = o.customer_id GROUP BY c.country;",
        },
        {
            "label": {"en": "Add BUFFERS (hit vs read)", "es": "Agregar BUFFERS (hit vs read)"},
            "sql": "EXPLAIN (ANALYZE, BUFFERS)\nSELECT c.country, count(*) FROM orders o\nJOIN customers c ON c.id = o.customer_id GROUP BY c.country;",
        },
        {
            "label": {"en": "See the loops multiply", "es": "Ver cómo se multiplican los loops"},
            "sql": "CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders (customer_id);\nANALYZE orders;\nEXPLAIN ANALYZE\nSELECT o.id FROM orders o JOIN customers c ON c.id = o.customer_id\nWHERE c.country = 'AD';",
        },
        {
            "label": {"en": "Plan as JSON", "es": "Plan en JSON"},
            "sql": "EXPLAIN (FORMAT JSON)\nSELECT count(*) FROM orders WHERE amount > 400;",
        },
    ],
}

_JOIN_PLAYGROUND = {
    "schema_sql": _JOIN_SCHEMA,
    "title": {"en": "Make the planner switch join algorithm", "es": "Haz que el planner cambie de algoritmo de join"},
    "intro": {
        "en": "Same two tables, three algorithms. Turn them off one at a time and compare the cost the planner reports.",
        "es": "Las mismas dos tablas, tres algoritmos. Apágalos de a uno y compara el costo que reporta el planner.",
    },
    "initial_query": "EXPLAIN ANALYZE\nSELECT o.id FROM orders o JOIN customers c ON c.id = o.customer_id;",
    "samples": [
        {
            "label": {"en": "Broad join (all rows)", "es": "Join amplio (todas las filas)"},
            "sql": "EXPLAIN ANALYZE\nSELECT o.id FROM orders o JOIN customers c ON c.id = o.customer_id;",
        },
        {
            "label": {"en": "Selective join (~20 customers)", "es": "Join selectivo (~20 clientes)"},
            "sql": "EXPLAIN ANALYZE\nSELECT o.id FROM orders o JOIN customers c ON c.id = o.customer_id\nWHERE c.country = 'AD';",
        },
        {
            "label": {"en": "Index the FK, then re-run the selective join", "es": "Indexar la FK y repetir el join selectivo"},
            "sql": "CREATE INDEX idx_orders_customer ON orders (customer_id);\nANALYZE orders;\nEXPLAIN ANALYZE\nSELECT o.id FROM orders o JOIN customers c ON c.id = o.customer_id\nWHERE c.country = 'AD';",
        },
        {
            "label": {"en": "Ban the hash join", "es": "Prohibir el hash join"},
            "sql": "SET enable_hashjoin = off;\nEXPLAIN ANALYZE\nSELECT o.id FROM orders o JOIN customers c ON c.id = o.customer_id;",
        },
        {
            "label": {"en": "Ban hash and merge (nested loop only)", "es": "Prohibir hash y merge (solo nested loop)"},
            "sql": "SET enable_hashjoin = off;\nSET enable_mergejoin = off;\nEXPLAIN ANALYZE\nSELECT o.id FROM orders o JOIN customers c ON c.id = o.customer_id;",
        },
        {
            "label": {"en": "Reset the switches", "es": "Restaurar los interruptores"},
            "sql": "RESET enable_hashjoin;\nRESET enable_mergejoin;\nSELECT join_kind('SELECT o.id FROM orders o JOIN customers c ON c.id = o.customer_id') AS algo;",
        },
    ],
}

_WINDOW_PLAYGROUND = {
    "schema_sql": _SALES_SCHEMA,
    "title": {"en": "Window function sandbox", "es": "Laboratorio de window functions"},
    "intro": {
        "en": "Twelve rows: 3 regions x 4 months, with a deliberate tie in `east`. Small enough to check every result by eye.",
        "es": "Doce filas: 3 regiones x 4 meses, con un empate a propósito en `east`. Suficientemente pequeño para verificar cada resultado a ojo.",
    },
    "initial_query": "SELECT region, month, amount,\n       ROW_NUMBER() OVER (PARTITION BY region ORDER BY amount DESC) AS rn\nFROM sales ORDER BY region, amount DESC;",
    "samples": [
        {
            "label": {"en": "ROW_NUMBER vs RANK vs DENSE_RANK", "es": "ROW_NUMBER vs RANK vs DENSE_RANK"},
            "sql": "SELECT region, month, amount,\n       ROW_NUMBER()  OVER (PARTITION BY region ORDER BY amount DESC) AS rn,\n       RANK()        OVER (PARTITION BY region ORDER BY amount DESC) AS rk,\n       DENSE_RANK()  OVER (PARTITION BY region ORDER BY amount DESC) AS dr\nFROM sales ORDER BY region, amount DESC;",
        },
        {
            "label": {"en": "Window vs GROUP BY", "es": "Window vs GROUP BY"},
            "sql": "SELECT region, month, amount,\n       SUM(amount) OVER (PARTITION BY region) AS region_total,\n       amount / SUM(amount) OVER (PARTITION BY region) AS share\nFROM sales ORDER BY region, month;",
        },
        {
            "label": {"en": "Running total (frame)", "es": "Total acumulado (frame)"},
            "sql": "SELECT region, month, amount,\n       SUM(amount) OVER (PARTITION BY region ORDER BY month\n                         ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS running\nFROM sales ORDER BY region, month;",
        },
        {
            "label": {"en": "Month-over-month with LAG", "es": "Mes contra mes con LAG"},
            "sql": "SELECT region, month, amount,\n       LAG(amount) OVER (PARTITION BY region ORDER BY month) AS prev,\n       amount - LAG(amount) OVER (PARTITION BY region ORDER BY month) AS delta\nFROM sales ORDER BY region, month;",
        },
        {
            "label": {"en": "ROWS vs RANGE on a tie", "es": "ROWS vs RANGE con un empate"},
            "sql": "SELECT region, month, amount,\n       SUM(amount) OVER (PARTITION BY region ORDER BY amount\n                         ROWS  BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS by_rows,\n       SUM(amount) OVER (PARTITION BY region ORDER BY amount\n                         RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS by_range\nFROM sales WHERE region = 'east' ORDER BY amount;",
        },
        {
            "label": {"en": "Top 1 per region", "es": "Top 1 por región"},
            "sql": "SELECT region, month, amount FROM (\n  SELECT *, ROW_NUMBER() OVER (PARTITION BY region ORDER BY amount DESC) AS rn\n  FROM sales\n) t WHERE rn = 1 ORDER BY region;",
        },
    ],
}

PLAYGROUNDS: list[tuple[str, dict]] = [
    ("reading-explain-analyze", _EXPLAIN_PLAYGROUND),
    ("seq-scan-vs-index-scan", _SCAN_PLAYGROUND),
    ("how-the-planner-chooses", _PLANNER_PLAYGROUND),
    ("join-algorithms", _JOIN_PLAYGROUND),
    ("window-functions-basics", _WINDOW_PLAYGROUND),
    ("window-frames", _WINDOW_PLAYGROUND),
    ("debugging-slow-queries-in-postgres", _SCAN_PLAYGROUND),
    ("finding-slow-queries", _PLANNER_PLAYGROUND),
    ("index-types-in-postgres", _SCAN_PLAYGROUND),
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


def playground_for(lesson_slug: str) -> dict | None:
    for needle, config in PLAYGROUNDS:
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
    playgrounds = 0
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

            playground = playground_for(lesson.slug)
            if playground:
                rows.append(
                    LessonComponent(
                        lesson_id=lesson.id,
                        component_type="sql_playground",
                        order_index=7,
                        config=playground,
                    )
                )
                playgrounds += 1

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
          f"({galleries} galleries, {diagrams} diagrams, {playgrounds} playgrounds).")


if __name__ == "__main__":
    main()
