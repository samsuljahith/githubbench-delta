#!/usr/bin/env python3
"""Create six multi-language fixture repositories for GitHubBench-Delta v1."""

from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "datasets" / "fixtures"


def run(cmd: list[str], cwd: Path) -> None:
    subprocess.run(cmd, cwd=cwd, check=True, capture_output=True)


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def init_repo(repo: Path, commits: list[tuple[str, dict[str, str]]]) -> None:
    if repo.exists():
        # Recreate cleanly
        import shutil

        shutil.rmtree(repo)
    repo.mkdir(parents=True)
    run(["git", "init"], repo)
    run(["git", "config", "user.email", "bench@local"], repo)
    run(["git", "config", "user.name", "GitHubBench"], repo)
    for message, files in commits:
        for rel, content in files.items():
            write(repo / rel, content)
        run(["git", "add", "-A"], repo)
        run(["git", "-c", "commit.gpgsign=false", "commit", "-m", message], repo)


def build_py_cli() -> None:
    init_repo(
        FIXTURES / "py_cli",
        [
            (
                "Initial CLI scaffold",
                {
                    "README.md": "# WidgetCLI\n\nCommand-line tool for managing widgets.\n\n## Usage\n\n```bash\npython -m widgetcli list\n```\n",
                    "widgetcli/__init__.py": '__version__ = "0.1.0"\n',
                    "widgetcli/__main__.py": "from widgetcli.cli import main\n\nif __name__ == '__main__':\n    raise SystemExit(main())\n",
                    "widgetcli/cli.py": (
                        "import argparse\n\n"
                        "from widgetcli.store import WidgetStore\n\n\n"
                        "def main(argv=None):\n"
                        "    parser = argparse.ArgumentParser(prog='widgetcli')\n"
                        "    sub = parser.add_subparsers(dest='command', required=True)\n"
                        "    sub.add_parser('list', help='List widgets')\n"
                        "    add = sub.add_parser('add', help='Add a widget')\n"
                        "    add.add_argument('name')\n"
                        "    args = parser.parse_args(argv)\n"
                        "    store = WidgetStore()\n"
                        "    if args.command == 'list':\n"
                        "        for name in store.list_names():\n"
                        "            print(name)\n"
                        "        return 0\n"
                        "    if args.command == 'add':\n"
                        "        store.add(args.name)\n"
                        "        print(f'added {args.name}')\n"
                        "        return 0\n"
                        "    return 1\n"
                    ),
                    "widgetcli/store.py": (
                        "class WidgetStore:\n"
                        "    def __init__(self):\n"
                        "        self._items = ['alpha', 'beta']\n\n"
                        "    def list_names(self):\n"
                        "        return list(self._items)\n\n"
                        "    def add(self, name: str) -> None:\n"
                        "        if name in self._items:\n"
                        "            return\n"
                        "        self._items.append(name)\n\n"
                        "    def legacy_dump(self):\n"
                        "        # leftover debug helper\n"
                        "        return ','.join(self._items)\n"
                    ),
                    "ISSUES.md": "# Issues\n\n## #1 list command prints nothing on empty store\nOpened by maintainers.\n\n## #2 add should reject blank names\n",
                    "docs/architecture.md": "# Architecture\n\n`cli.py` parses args and delegates to `WidgetStore` in `store.py`.\n",
                },
            ),
            (
                "Reject blank widget names",
                {
                    "widgetcli/store.py": (
                        "class WidgetStore:\n"
                        "    def __init__(self):\n"
                        "        self._items = ['alpha', 'beta']\n\n"
                        "    def list_names(self):\n"
                        "        return list(self._items)\n\n"
                        "    def add(self, name: str) -> None:\n"
                        "        if not name or not name.strip():\n"
                        "            raise ValueError('name must be non-empty')\n"
                        "        if name in self._items:\n"
                        "            return\n"
                        "        self._items.append(name)\n\n"
                        "    def legacy_dump(self):\n"
                        "        return ','.join(self._items)\n"
                    ),
                },
            ),
            (
                "Document store module",
                {
                    "docs/store.md": "# WidgetStore\n\nIn-memory store used by the CLI. Not durable across processes.\n",
                },
            ),
        ],
    )


def build_py_rag() -> None:
    init_repo(
        FIXTURES / "py_rag",
        [
            (
                "Initial RAG service scaffold",
                {
                    "README.md": "# DocSearch RAG\n\nMinimal retrieval-augmented question answering service.\n",
                    "ragapp/__init__.py": "",
                    "ragapp/ingest.py": (
                        "from pathlib import Path\n\n\n"
                        "def chunk_text(text: str, size: int = 200) -> list[str]:\n"
                        "    return [text[i:i+size] for i in range(0, len(text), size) if text[i:i+size].strip()]\n\n\n"
                        "def load_documents(root: Path) -> list[str]:\n"
                        "    docs = []\n"
                        "    for path in root.glob('**/*.md'):\n"
                        "        docs.extend(chunk_text(path.read_text(encoding='utf-8')))\n"
                        "    return docs\n"
                    ),
                    "ragapp/retriever.py": (
                        "def score(query: str, chunk: str) -> int:\n"
                        "    q = set(query.lower().split())\n"
                        "    c = set(chunk.lower().split())\n"
                        "    return len(q & c)\n\n\n"
                        "def retrieve(query: str, corpus: list[str], k: int = 3) -> list[str]:\n"
                        "    ranked = sorted(corpus, key=lambda ch: score(query, ch), reverse=True)\n"
                        "    return ranked[:k]\n"
                    ),
                    "ragapp/answer.py": (
                        "from ragapp.retriever import retrieve\n\n\n"
                        "def answer_question(query: str, corpus: list[str]) -> str:\n"
                        "    hits = retrieve(query, corpus, k=2)\n"
                        "    if not hits:\n"
                        "        return 'No relevant context found.'\n"
                        "    return 'Based on docs: ' + ' | '.join(hits)\n"
                    ),
                    "ragapp/unused_embed.py": (
                        "def fake_embed(text: str) -> list[float]:\n"
                        "    # dead code left from prototype\n"
                        "    return [float(len(text))]\n"
                    ),
                    "ISSUES.md": "# Issues\n\n## #3 Retriever ignores punctuation\n## #4 Ingest should skip node_modules-like dirs\n",
                    "docs/overview.md": "# Overview\n\nIngest chunks markdown, retriever ranks by token overlap, answer joins top chunks.\n",
                },
            ),
            (
                "Skip hidden directories during ingest",
                {
                    "ragapp/ingest.py": (
                        "from pathlib import Path\n\n\n"
                        "def chunk_text(text: str, size: int = 200) -> list[str]:\n"
                        "    return [text[i:i+size] for i in range(0, len(text), size) if text[i:i+size].strip()]\n\n\n"
                        "def load_documents(root: Path) -> list[str]:\n"
                        "    docs = []\n"
                        "    for path in root.glob('**/*.md'):\n"
                        "        if any(part.startswith('.') for part in path.parts):\n"
                        "            continue\n"
                        "        docs.extend(chunk_text(path.read_text(encoding='utf-8')))\n"
                        "    return docs\n"
                    ),
                },
            ),
            (
                "Add API entrypoint stub",
                {
                    "ragapp/api.py": (
                        "from ragapp.answer import answer_question\n"
                        "from ragapp.ingest import load_documents\n"
                        "from pathlib import Path\n\n\n"
                        "def handle(query: str, docs_root: str = 'docs') -> dict:\n"
                        "    corpus = load_documents(Path(docs_root))\n"
                        "    return {'answer': answer_question(query, corpus)}\n"
                    ),
                },
            ),
        ],
    )


def build_ts_frontend() -> None:
    init_repo(
        FIXTURES / "ts_frontend",
        [
            (
                "Initial frontend scaffold",
                {
                    "README.md": "# PulseBoard\n\nTypeScript frontend for displaying service health cards.\n",
                    "package.json": '{\n  "name": "pulseboard",\n  "version": "0.1.0",\n  "private": true\n}\n',
                    "src/api/client.ts": (
                        "export type Health = { service: string; status: 'up' | 'down' };\n\n"
                        "export async function fetchHealth(baseUrl: string): Promise<Health[]> {\n"
                        "  const res = await fetch(`${baseUrl}/health`);\n"
                        "  if (!res.ok) throw new Error('health fetch failed');\n"
                        "  return res.json();\n"
                        "}\n"
                    ),
                    "src/components/HealthCard.tsx": (
                        "import type { Health } from '../api/client';\n\n"
                        "export function HealthCard({ item }: { item: Health }) {\n"
                        "  return (\n"
                        "    <div className=\"card\">\n"
                        "      <h3>{item.service}</h3>\n"
                        "      <p>{item.status}</p>\n"
                        "    </div>\n"
                        "  );\n"
                        "}\n"
                    ),
                    "src/App.tsx": (
                        "import { useEffect, useState } from 'react';\n"
                        "import { fetchHealth, type Health } from './api/client';\n"
                        "import { HealthCard } from './components/HealthCard';\n\n"
                        "export function App() {\n"
                        "  const [items, setItems] = useState<Health[]>([]);\n"
                        "  useEffect(() => {\n"
                        "    fetchHealth('/api').then(setItems).catch(console.error);\n"
                        "  }, []);\n"
                        "  return (\n"
                        "    <main>\n"
                        "      {items.map((item) => (\n"
                        "        <HealthCard key={item.service} item={item} />\n"
                        "      ))}\n"
                        "    </main>\n"
                        "  );\n"
                        "}\n"
                    ),
                    "src/legacy/format.ts": "export function unusedFormat(n: number): string {\n  return String(n);\n}\n",
                    "ISSUES.md": "# Issues\n\n## #1 HealthCard should show degraded state\n## #2 fetchHealth needs timeout\n",
                    "docs/components.md": "# Components\n\n`HealthCard` renders a single service health row.\n",
                },
            ),
            (
                "Add degraded status type",
                {
                    "src/api/client.ts": (
                        "export type Health = { service: string; status: 'up' | 'down' | 'degraded' };\n\n"
                        "export async function fetchHealth(baseUrl: string): Promise<Health[]> {\n"
                        "  const res = await fetch(`${baseUrl}/health`);\n"
                        "  if (!res.ok) throw new Error('health fetch failed');\n"
                        "  return res.json();\n"
                        "}\n"
                    ),
                },
            ),
            (
                "Document API client",
                {
                    "docs/api-client.md": "# API client\n\n`fetchHealth` loads `/health` from the configured base URL.\n",
                },
            ),
        ],
    )


def build_go_rest_api() -> None:
    init_repo(
        FIXTURES / "go_rest_api",
        [
            (
                "Initial Go REST API",
                {
                    "README.md": "# Inventory API\n\nGo HTTP API for inventory items.\n",
                    "go.mod": "module github.com/example/inventoryapi\n\ngo 1.22\n",
                    "cmd/server/main.go": (
                        "package main\n\n"
                        "import (\n"
                        "\t\"log\"\n"
                        "\t\"net/http\"\n\n"
                        "\t\"github.com/example/inventoryapi/internal/httpapi\"\n"
                        ")\n\n"
                        "func main() {\n"
                        "\tmux := httpapi.NewMux()\n"
                        "\tlog.Fatal(http.ListenAndServe(\":8080\", mux))\n"
                        "}\n"
                    ),
                    "internal/httpapi/handlers.go": (
                        "package httpapi\n\n"
                        "import (\n"
                        "\t\"encoding/json\"\n"
                        "\t\"net/http\"\n\n"
                        "\t\"github.com/example/inventoryapi/internal/store\"\n"
                        ")\n\n"
                        "func NewMux() *http.ServeMux {\n"
                        "\tmux := http.NewServeMux()\n"
                        "\ts := store.New()\n"
                        "\tmux.HandleFunc(\"/items\", func(w http.ResponseWriter, r *http.Request) {\n"
                        "\t\tif r.Method != http.MethodGet {\n"
                        "\t\t\tw.WriteHeader(http.StatusMethodNotAllowed)\n"
                        "\t\t\treturn\n"
                        "\t\t}\n"
                        "\t\t_ = json.NewEncoder(w).Encode(s.List())\n"
                        "\t})\n"
                        "\treturn mux\n"
                        "}\n"
                    ),
                    "internal/store/store.go": (
                        "package store\n\n"
                        "type Item struct {\n"
                        "\tSKU  string `json:\"sku\"`\n"
                        "\tName string `json:\"name\"`\n"
                        "}\n\n"
                        "type Store struct {\n"
                        "\titems []Item\n"
                        "}\n\n"
                        "func New() *Store {\n"
                        "\treturn &Store{items: []Item{{SKU: \"A1\", Name: \"Bolt\"}}}\n"
                        "}\n\n"
                        "func (s *Store) List() []Item { return s.items }\n\n"
                        "func (s *Store) DeadDebug() string { return \"debug\" }\n"
                    ),
                    "ISSUES.md": "# Issues\n\n## #2 POST /items not implemented\n## #5 Auth middleware missing\n",
                    "docs/api.md": "# API\n\n`GET /items` returns inventory rows as JSON.\n",
                },
            ),
            (
                "Add health endpoint",
                {
                    "internal/httpapi/handlers.go": (
                        "package httpapi\n\n"
                        "import (\n"
                        "\t\"encoding/json\"\n"
                        "\t\"net/http\"\n\n"
                        "\t\"github.com/example/inventoryapi/internal/store\"\n"
                        ")\n\n"
                        "func NewMux() *http.ServeMux {\n"
                        "\tmux := http.NewServeMux()\n"
                        "\ts := store.New()\n"
                        "\tmux.HandleFunc(\"/health\", func(w http.ResponseWriter, r *http.Request) {\n"
                        "\t\t_ = json.NewEncoder(w).Encode(map[string]string{\"status\": \"ok\"})\n"
                        "\t})\n"
                        "\tmux.HandleFunc(\"/items\", func(w http.ResponseWriter, r *http.Request) {\n"
                        "\t\tif r.Method != http.MethodGet {\n"
                        "\t\t\tw.WriteHeader(http.StatusMethodNotAllowed)\n"
                        "\t\t\treturn\n"
                        "\t\t}\n"
                        "\t\t_ = json.NewEncoder(w).Encode(s.List())\n"
                        "\t})\n"
                        "\treturn mux\n"
                        "}\n"
                    ),
                },
            ),
            (
                "Document store package",
                {
                    "docs/store.md": "# Store\n\nIn-memory inventory store used by HTTP handlers.\n",
                },
            ),
        ],
    )


def build_rust_service() -> None:
    init_repo(
        FIXTURES / "rust_service",
        [
            (
                "Initial Rust notifier service",
                {
                    "README.md": "# NotifyRS\n\nSmall Rust service that formats notification payloads.\n",
                    "Cargo.toml": (
                        '[package]\nname = "notifyrs"\nversion = "0.1.0"\nedition = "2021"\n'
                    ),
                    "src/main.rs": (
                        "mod format;\nmod unused;\n\n"
                        "fn main() {\n"
                        "    let msg = format::render(\"deploy\", \"ok\");\n"
                        "    println!(\"{msg}\");\n"
                        "}\n"
                    ),
                    "src/format.rs": (
                        "pub fn render(kind: &str, status: &str) -> String {\n"
                        "    format!(\"{kind}:{status}\")\n"
                        "}\n\n"
                        "pub fn render_json(kind: &str, status: &str) -> String {\n"
                        "    format!(r#\"{{\"kind\":\"{kind}\",\"status\":\"{status}\"}}\"#)\n"
                        "}\n"
                    ),
                    "src/unused.rs": "pub fn leftover() -> i32 { 7 }\n",
                    "ISSUES.md": "# Issues\n\n## #1 Add structured logging\n## #2 JSON renderer should escape quotes\n",
                    "docs/design.md": "# Design\n\n`format::render` builds human-readable lines; `render_json` builds JSON strings.\n",
                },
            ),
            (
                "Escape quotes in JSON renderer",
                {
                    "src/format.rs": (
                        "pub fn render(kind: &str, status: &str) -> String {\n"
                        "    format!(\"{kind}:{status}\")\n"
                        "}\n\n"
                        "pub fn render_json(kind: &str, status: &str) -> String {\n"
                        "    let kind = kind.replace('\"', \"\\\\\\\"\");\n"
                        "    let status = status.replace('\"', \"\\\\\\\"\");\n"
                        "    format!(r#\"{{\"kind\":\"{kind}\",\"status\":\"{status}\"}}\"#)\n"
                        "}\n"
                    ),
                },
            ),
            (
                "Document format module",
                {
                    "docs/format.md": "# format module\n\nPublic helpers for notification string rendering.\n",
                },
            ),
        ],
    )


def build_java_backend() -> None:
    init_repo(
        FIXTURES / "java_backend",
        [
            (
                "Initial Java billing backend",
                {
                    "README.md": "# BillingBackend\n\nMulti-package Java backend for invoice listing.\n",
                    "src/main/java/com/example/billing/App.java": (
                        "package com.example.billing;\n\n"
                        "import com.example.billing.api.InvoiceController;\n"
                        "import com.example.billing.service.InvoiceService;\n\n"
                        "public class App {\n"
                        "  public static void main(String[] args) {\n"
                        "    InvoiceController controller = new InvoiceController(new InvoiceService());\n"
                        "    System.out.println(controller.listJson());\n"
                        "  }\n"
                        "}\n"
                    ),
                    "src/main/java/com/example/billing/api/InvoiceController.java": (
                        "package com.example.billing.api;\n\n"
                        "import com.example.billing.service.InvoiceService;\n\n"
                        "public class InvoiceController {\n"
                        "  private final InvoiceService service;\n\n"
                        "  public InvoiceController(InvoiceService service) {\n"
                        "    this.service = service;\n"
                        "  }\n\n"
                        "  public String listJson() {\n"
                        "    return service.listAsJson();\n"
                        "  }\n"
                        "}\n"
                    ),
                    "src/main/java/com/example/billing/service/InvoiceService.java": (
                        "package com.example.billing.service;\n\n"
                        "import java.util.List;\n\n"
                        "public class InvoiceService {\n"
                        "  public List<String> listIds() {\n"
                        "    return List.of(\"INV-1\", \"INV-2\");\n"
                        "  }\n\n"
                        "  public String listAsJson() {\n"
                        "    return \"[\\\"INV-1\\\",\\\"INV-2\\\"]\";\n"
                        "  }\n\n"
                        "  public String legacyFormat() {\n"
                        "    return String.join(\",\", listIds());\n"
                        "  }\n"
                        "}\n"
                    ),
                    "ISSUES.md": "# Issues\n\n## #8 Add pagination to invoice list\n## #9 Remove legacyFormat\n",
                    "docs/modules.md": "# Modules\n\n`api` exposes controllers; `service` owns business logic.\n",
                },
            ),
            (
                "Return empty list when no invoices",
                {
                    "src/main/java/com/example/billing/service/InvoiceService.java": (
                        "package com.example.billing.service;\n\n"
                        "import java.util.ArrayList;\n"
                        "import java.util.List;\n\n"
                        "public class InvoiceService {\n"
                        "  private final List<String> ids = new ArrayList<>(List.of(\"INV-1\", \"INV-2\"));\n\n"
                        "  public List<String> listIds() {\n"
                        "    return List.copyOf(ids);\n"
                        "  }\n\n"
                        "  public String listAsJson() {\n"
                        "    if (ids.isEmpty()) {\n"
                        "      return \"[]\";\n"
                        "    }\n"
                        "    return \"[\\\"INV-1\\\",\\\"INV-2\\\"]\";\n"
                        "  }\n\n"
                        "  public String legacyFormat() {\n"
                        "    return String.join(\",\", listIds());\n"
                        "  }\n"
                        "}\n"
                    ),
                },
            ),
            (
                "Document service layer",
                {
                    "docs/service.md": "# InvoiceService\n\nProvides invoice identifiers and JSON serialization helpers.\n",
                },
            ),
        ],
    )


def main() -> None:
    FIXTURES.mkdir(parents=True, exist_ok=True)
    build_py_cli()
    build_py_rag()
    build_ts_frontend()
    build_go_rest_api()
    build_rust_service()
    build_java_backend()
    print("Built fixtures:", ", ".join(sorted(p.name for p in FIXTURES.iterdir() if p.is_dir())))


if __name__ == "__main__":
    main()
