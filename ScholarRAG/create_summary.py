from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, PageBreak
from reportlab.lib.enums import TA_LEFT, TA_CENTER

OUTPUT = "ScholarRAG_Session_Summary.pdf"

doc = SimpleDocTemplate(
    OUTPUT,
    pagesize=letter,
    leftMargin=0.9*inch,
    rightMargin=0.9*inch,
    topMargin=0.9*inch,
    bottomMargin=0.9*inch,
)

styles = getSampleStyleSheet()

title_style = ParagraphStyle("Title2", parent=styles["Title"], fontSize=22, textColor=colors.HexColor("#4F46E5"), spaceAfter=6)
h1 = ParagraphStyle("H1", parent=styles["Heading1"], fontSize=14, textColor=colors.HexColor("#1E293B"), spaceBefore=14, spaceAfter=4)
h2 = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=11, textColor=colors.HexColor("#4F46E5"), spaceBefore=10, spaceAfter=3)
body = ParagraphStyle("Body", parent=styles["Normal"], fontSize=9.5, leading=14, spaceAfter=5)
code = ParagraphStyle("Code", parent=styles["Code"], fontSize=8, backColor=colors.HexColor("#F1F5F9"), leftIndent=12, rightIndent=12, spaceBefore=4, spaceAfter=4)
bullet = ParagraphStyle("Bullet", parent=styles["Normal"], fontSize=9.5, leading=14, leftIndent=16, spaceAfter=3)

def B(text): return f"<b>{text}</b>"
def C(text): return f'<font color="#4F46E5">{text}</font>'

story = []

# ── Title ──────────────────────────────────────────────────────────────────
story.append(Paragraph("ScholarRAG", title_style))
story.append(Paragraph("Research Paper + Code Recommendation System", ParagraphStyle("sub", parent=styles["Normal"], fontSize=13, textColor=colors.HexColor("#64748B"), spaceAfter=4)))
story.append(Paragraph("Session Summary — June 15, 2026", ParagraphStyle("date", parent=styles["Normal"], fontSize=9, textColor=colors.gray, spaceAfter=8)))
story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#4F46E5"), spaceAfter=14))

# ── 1. What is ScholarRAG ─────────────────────────────────────────────────
story.append(Paragraph("1. What is ScholarRAG?", h1))
story.append(Paragraph(
    "ScholarRAG is a Retrieval-Augmented Generation (RAG) system. A student types a plain-English query like "
    "<i>lane detection for Raspberry Pi</i> and the system finds the most relevant research papers, checks if their "
    "GitHub repos are alive and usable, and returns a concrete implementation plan — not a list of links.", body))
story.append(Paragraph(B("Without RAG:") + " you → LLM → answer from memory (possibly hallucinated)", bullet))
story.append(Paragraph(B("With RAG:") + " you → fetch relevant docs → stuff into LLM prompt → answer grounded in real data", bullet))

# ── 2. Session Progress ───────────────────────────────────────────────────
story.append(Paragraph("2. What We Built This Session", h1))

done_data = [
    [B("Task"), B("Status"), B("Notes")],
    ["Fetch 6000 papers from ArXiv", "✅ Done", "12 fields × 500 papers"],
    ["Embed with sentence-transformers", "✅ Done", "all-mpnet-base-v2, 768-dim"],
    ["Run embeddings on EC2 (t2.large)", "✅ Done", "~92 min CPU, 6000 uploaded"],
    ["Copy qdrant_local/ back to local", "✅ Done", "scp from EC2"],
    ["FastAPI backend with Claude", "✅ Done", "cache_control added"],
    ["React frontend (chat + sources)", "✅ Done", "ChatGPT-style layout"],
    ["Semantic Scholar enrichment script", "⚙️ In Progress", "Rate limit issue — need API key"],
    ["Papers With Code integration", "⏳ Next", "Step 2 of enrichment"],
    ["PostgreSQL for reranking metadata", "⏳ Next", "After enrichment done"],
    ["Fix 2 — score threshold + live fetch", "⏳ Next", "Week 2"],
    ["Docker + Kubernetes", "⏳ Next", "Week 2"],
]

t = Table(done_data, colWidths=[2.8*inch, 1.2*inch, 2.5*inch])
t.setStyle(TableStyle([
    ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#4F46E5")),
    ("TEXTCOLOR", (0,0), (-1,0), colors.white),
    ("FONTSIZE", (0,0), (-1,-1), 8.5),
    ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.HexColor("#F8FAFC"), colors.white]),
    ("GRID", (0,0), (-1,-1), 0.4, colors.HexColor("#CBD5E1")),
    ("PADDING", (0,0), (-1,-1), 5),
    ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
]))
story.append(t)

# ── 3. Architecture ───────────────────────────────────────────────────────
story.append(Paragraph("3. Full Query Flow", h1))
flow_data = [
    [B("Step"), B("What Happens"), B("Tool")],
    ["1. User types query", "Plain English input", "React frontend"],
    ["2. FastAPI receives", "POST /query endpoint", "FastAPI + uvicorn"],
    ["3. Embed query", "Text → 768-dim vector", "sentence-transformers"],
    ["4. Search Qdrant", "Top-20 papers by cosine similarity", "Qdrant (local)"],
    ["5. Score check", "Best score >= 0.4? YES→continue, NO→Fix 2", "Python logic"],
    ["6. Fix 2 (if triggered)", "Fetch 20 live papers from ArXiv", "arxiv + Qdrant"],
    ["7. Rerank top 5", "similarity×0.5 + citations×0.3 + stars×0.1 + recency×0.1", "PostgreSQL + Python"],
    ["8. Claude synthesis", "Top-5 abstracts + metadata → answer", "Anthropic SDK"],
    ["9. Return answer", "Answer + sources to frontend", "FastAPI JSON"],
]
t2 = Table(flow_data, colWidths=[1.5*inch, 3.0*inch, 2.0*inch])
t2.setStyle(TableStyle([
    ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#1E293B")),
    ("TEXTCOLOR", (0,0), (-1,0), colors.white),
    ("FONTSIZE", (0,0), (-1,-1), 8.5),
    ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.HexColor("#F8FAFC"), colors.white]),
    ("GRID", (0,0), (-1,-1), 0.4, colors.HexColor("#CBD5E1")),
    ("PADDING", (0,0), (-1,-1), 5),
    ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
]))
story.append(t2)

# ── 4. Data Architecture ──────────────────────────────────────────────────
story.append(Paragraph("4. Where Every Piece of Data Lives", h1))
data_data = [
    [B("Data"), B("Where"), B("Why")],
    ["Paper vectors (768 numbers)", "Qdrant (local / EC2)", "Similarity search"],
    ["Citations, stars, dates, license", "PostgreSQL (EC2)", "Reranking formula"],
    ["Raw paper JSON", "AWS S3", "Disaster recovery backup"],
    ["GitHub repos + stars", "PostgreSQL (from Papers With Code + GitHub API)", "Reranking"],
    ["Author affiliations, country", "PostgreSQL (from Semantic Scholar)", "Author/institute filter"],
    ["API keys + config", "K8s Secret + .env", "Never baked into images"],
]
t3 = Table(data_data, colWidths=[2.0*inch, 2.3*inch, 2.2*inch])
t3.setStyle(TableStyle([
    ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#0F172A")),
    ("TEXTCOLOR", (0,0), (-1,0), colors.white),
    ("FONTSIZE", (0,0), (-1,-1), 8.5),
    ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.HexColor("#F8FAFC"), colors.white]),
    ("GRID", (0,0), (-1,-1), 0.4, colors.HexColor("#CBD5E1")),
    ("PADDING", (0,0), (-1,-1), 5),
    ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
]))
story.append(t3)

# ── 5. Enriched JSON Format ───────────────────────────────────────────────
story.append(Paragraph("5. New Enriched papers.json Format (Target)", h1))
story.append(Paragraph("After running Semantic Scholar + Papers With Code enrichment, each paper entry will have:", body))
story.append(Paragraph("""
{
  "id": "2606.13621",
  "title": "...",
  "authors": ["name1", "name2"],
  "summary": "...",
  "published": "2026-06-15",
  "pdf_url": "...",
  "category": "cs.LG",

  // From Semantic Scholar
  "citations": 42,
  "journal": "NeurIPS 2024",
  "doi": "10.xxx",
  "fields_of_study": ["Computer Science"],
  "authors_enriched": [
    { "name": "Yi Zhaohua", "affiliations": ["Peking University"] }
  ],

  // From Papers With Code + GitHub API
  "github_repos": [
    { "url": "https://github.com/...", "stars": 1200, "framework": "PyTorch" }
  ],
  "has_code": true,
  "sota_tasks": ["Image Classification"]
}
""", code))

# ── 6. Reranking Formula ──────────────────────────────────────────────────
story.append(Paragraph("6. Reranking Formula", h1))
story.append(Paragraph("Qdrant returns top-20 by semantic similarity. Reranking adds quality signals:", body))
story.append(Paragraph("""
score = (semantic_similarity × 0.5)
      + (normalized_citations  × 0.3)
      + (normalized_repo_stars × 0.1)
      + (recency_score         × 0.1)
""", code))
rank_data = [
    [B("Factor"), B("Weight"), B("Source"), B("Why")],
    ["Semantic similarity", "50%", "Qdrant score", "Is the paper about the topic?"],
    ["Citations", "30%", "Semantic Scholar → PostgreSQL", "Peer-validated quality"],
    ["Repo stars", "10%", "GitHub API → PostgreSQL", "Community adoption"],
    ["Recency", "10%", "Published date → PostgreSQL", "Newer = active maintenance"],
]
t4 = Table(rank_data, colWidths=[1.5*inch, 0.7*inch, 2.3*inch, 2.0*inch])
t4.setStyle(TableStyle([
    ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#4F46E5")),
    ("TEXTCOLOR", (0,0), (-1,0), colors.white),
    ("FONTSIZE", (0,0), (-1,-1), 8.5),
    ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.HexColor("#F8FAFC"), colors.white]),
    ("GRID", (0,0), (-1,-1), 0.4, colors.HexColor("#CBD5E1")),
    ("PADDING", (0,0), (-1,-1), 5),
]))
story.append(t4)

# ── 7. EC2 Setup Done ─────────────────────────────────────────────────────
story.append(PageBreak())
story.append(Paragraph("7. EC2 Setup (Completed This Session)", h1))
story.append(Paragraph(B("Instance:") + " Ubuntu on t2.large — 2 vCPU, 8GB RAM, 30GB disk", bullet))
story.append(Paragraph(B("Public IP:") + " ec2-18-234-203-252.compute-1.amazonaws.com", bullet))
story.append(Paragraph(B("Key file:") + " C:\\Users\\hp\\Desktop\\Rccar part\\schlor.pem", bullet))
story.append(Paragraph(B("Username:") + " ubuntu", bullet))
story.append(Paragraph(B("What ran on EC2:") + " ingestembed.py — embedded 6000 papers in ~92 minutes on CPU", bullet))
story.append(Paragraph(B("Disk fix:") + " Extended volume from 8GB → 30GB via AWS Console + resize2fs", bullet))

story.append(Paragraph("SSH command:", h2))
story.append(Paragraph('ssh -i "C:\\Users\\hp\\Desktop\\Rccar part\\schlor.pem" ubuntu@ec2-18-234-203-252.compute-1.amazonaws.com', code))

# ── 8. Current File Structure ─────────────────────────────────────────────
story.append(Paragraph("8. Current File Structure", h1))
story.append(Paragraph("""
ScholarRAG/
├── backend/
│   ├── main.py              ← FastAPI app (lifespan startup)
│   ├── rag.py               ← Retrieval + Claude with cache_control
│   ├── requirements.txt
│   └── .env                 ← ANTHROPIC_API_KEY (gitignored)
├── frontend/
│   └── src/
│       ├── App.jsx           ← Chat layout, state management
│       └── components/
│           ├── ChatInput.jsx  ← Calls POST /query
│           ├── SourcesPanel.jsx ← Shows papers + PDF links
│           └── Sidebar.jsx
├── ingestion/
│   ├── papers.json           ← 6000 ArXiv papers
│   ├── papers_enriched.json  ← (in progress)
│   ├── enrich_papers.py      ← Semantic Scholar enrichment
│   ├── fetch_papers.py       ← ArXiv fetcher
│   ├── fetch_github_docs.py  ← GitHub README fetcher
│   ├── github_config.py      ← 36 repos list
│   └── github_docs/          ← 34 README files
├── qdrant_local/             ← Vector DB (gitignored)
├── ingestembed.py            ← Embedding script (runs on EC2)
└── .gitignore
""", code))

# ── 9. Immediate Next Steps ───────────────────────────────────────────────
story.append(Paragraph("9. Immediate Next Steps", h1))
steps = [
    ("Step 1", "Get Semantic Scholar API key", "semanticscholar.org/product/api → free, instant signup"),
    ("Step 2", "Run enrich_papers.py --test", "Verify 5 papers get affiliations + citations"),
    ("Step 3", "Run enrich_papers.py (full)", "~2.5 hrs for 6000 papers, resumable"),
    ("Step 4", "Add Papers With Code to enrich script", "Get GitHub repos per paper"),
    ("Step 5", "Re-embed on EC2 with enriched data", "Copy papers_enriched.json → EC2, re-run ingestembed.py"),
    ("Step 6", "Set up PostgreSQL", "Store citations, stars, affiliations for reranking"),
    ("Step 7", "Implement reranking in backend", "Replace current top-5 with scored results"),
    ("Step 8", "Implement Fix 2", "Score threshold 0.4 + live ArXiv fetch on cache miss"),
    ("Step 9", "Docker + Kubernetes", "Week 2 deployment"),
]
for step, title, desc in steps:
    story.append(Paragraph(f"<b>{step} — {title}:</b> {desc}", bullet))

# ── 10. Key Decisions ─────────────────────────────────────────────────────
story.append(Paragraph("10. Key Decisions Made", h1))
dec_data = [
    [B("Decision"), B("Choice"), B("Reason")],
    ["Vector DB", "Qdrant", "Simple K8s setup, right scale for 6k papers"],
    ["API framework", "FastAPI", "Async, one file, auto docs"],
    ["LLM", "Claude Sonnet 4.6", "Speed + cost balance. Only used at final step"],
    ["Embeddings", "sentence-transformers all-mpnet-base-v2", "768-dim, good semantic accuracy"],
    ["Prompt caching", "cache_control: ephemeral on system prompt", "50-90% input cost reduction"],
    ["Paper count", "6000 (12 fields × 500)", "Broader coverage than original 1200 plan"],
    ["LangChain", "Removed — plain Python", "Fix 2 is custom logic, plain Python is cleaner"],
    ["EC2 for embedding", "t2.large (CPU)", "GPU not needed for one-time batch job"],
]
t5 = Table(dec_data, colWidths=[1.6*inch, 2.2*inch, 2.7*inch])
t5.setStyle(TableStyle([
    ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#1E293B")),
    ("TEXTCOLOR", (0,0), (-1,0), colors.white),
    ("FONTSIZE", (0,0), (-1,-1), 8.5),
    ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.HexColor("#F8FAFC"), colors.white]),
    ("GRID", (0,0), (-1,-1), 0.4, colors.HexColor("#CBD5E1")),
    ("PADDING", (0,0), (-1,-1), 5),
    ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
]))
story.append(t5)

# ── 11. Git State ─────────────────────────────────────────────────────────
story.append(Paragraph("11. Git State", h1))
story.append(Paragraph(B("Repo:") + " https://github.com/Akriti-236/ScholarRAG", bullet))
story.append(Paragraph(B("Current branch:") + " oum (your working branch)", bullet))
story.append(Paragraph(B("Main branch:") + " main (merged PRs from oum)", bullet))
story.append(Paragraph(B("gitignored:") + " qdrant_local/ (too large), backend/.env (secrets)", bullet))
story.append(Paragraph(B("To sync oum with main:") + " git pull origin main", bullet))

# ── Footer ────────────────────────────────────────────────────────────────
story.append(Spacer(1, 20))
story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#CBD5E1")))
story.append(Paragraph(
    "ScholarRAG Session Summary — Generated June 15, 2026 — Branch: oum — GuptaOum",
    ParagraphStyle("footer", parent=styles["Normal"], fontSize=8, textColor=colors.gray, alignment=TA_CENTER, spaceBefore=6)
))

doc.build(story)
print(f"PDF saved: {OUTPUT}")
