# APAAR SETU — Student Record Reconciliation Platform

> **Smart India Hackathon 2026** · **Problem Statement:** SIH26263  
> **Team:** Code Zero (Team ID: 197410)  
> **Status:** Interactive Prototype Under Development  
> **Tagline:** *Every admission accounted for. Every decision traceable.*

---

## 1. Executive Summary & Core Positioning

**APAAR SETU** is designed to reconcile post-admission institutional student records across universities and polytechnics without losing reported enrolment counts, turning uncertainty into accusations, or conflating distinct administrative questions.

Traditional deduplication systems treat student records as flat database rows, frequently merging or silently deleting records upon discovering typographical or phonetic similarities. In high-stakes regulatory and educational governance, this causes severe distortions:
- Institutions lose formally reported admission numbers.
- Legitimate students with similar names are disenfranchised.
- Binary fraud flags replace nuanced, evidence-based policy evaluations.

### The Four-Layer Truth Model
APAAR SETU decouples record reconciliation into four independent questions:
1. **Layer 1: Reported Truth** — What did the institution actually report? (Committed to an append-only reporting ledger; findings never erase reported admissions).
2. **Layer 2: Identity Confidence** — Which records may refer to the same person? (Probabilistic candidate generation with reversible human determinations).
3. **Layer 3: Policy Determination** — Does available evidence establish a regulatory conflict? (Contextual evaluation against versioned rule ASTs; missing data yields `INSUFFICIENT EVIDENCE`, never an automatic fraud accusation).
4. **Layer 4: Evidence Completeness** — Can an authorized reviewer defend the conclusion? (Immutable dependency graph with SHA-256 provenance hashes).

> **Foundational Invariant:**  
> *An admission can remain counted while its identity is uncertain and its policy status remains unresolved.*

---

## 2. Core Technical Innovations

### 1. The Reconciliation Proof Chain
Every finding is linked to an immutable, versioned reconciliation run containing:
- Source submission payloads and evidence hashes.
- Candidate similarity vectors and reviewer determinations.
- Active statutory handbook clauses at intake.
- Full replayability and impact preview before commit.

### 2. Transactional Reporting Integrity
- **Deterministic Idempotency:** Client-generated idempotency tokens prevent double-counting across network retries.
- **ACID Ledger:** Relational constraints ensure concurrent admission submissions across regional portals remain committed.
- **Transactional Outbox:** Background reconciliation tasks resume deterministically without losing events.

### 3. Reversible Identity Discipline
- Candidate generation across exact, phonetic, and trigram passes.
- Two strict safeguards:
  1. *Similar names alone do not establish identity.*
  2. *Identity matching never automatically changes reported enrolment counts.*

---

## 3. Technology Stack

### Current Web Entry Point (Landing & Interactive Model)
- **Framework:** Vite 5 + React 18 + TypeScript 5
- **Styling:** Modular Vanilla CSS with semantic HSL/HEX tokens
- **Typography:** Inter (text) + JetBrains Mono (proof chain hashes & audit logs)
- **Icons:** Lucide React

### Proposed Production Backend Architecture
- **Frontend:** Next.js 14, TypeScript, TanStack Table
- **API Service:** FastAPI & Pydantic v2
- **Database:** PostgreSQL 16 (Serializable isolation & append-only journal)
- **Persistence & Migrations:** SQLAlchemy 2.0 & Alembic
- **Background Worker:** Durable Transactional Outbox processor
- **Testing:** pytest with real PostgreSQL integration test containers

---

## 4. Local Development & Build

### Prerequisites
- Node.js (v18.0.0 or later, v24 recommended)
- npm (v9.0.0 or later)

### Installation
```bash
# Clone the repository
git clone <repository-url>
cd 26263

# Install dependencies
npm install
```

### Run Locally (Dev Server)
```bash
npm run dev
# The application will start at http://localhost:3000/
```

### Production Build
```bash
npm run build
# Compiles TypeScript and builds optimized static assets into the /dist directory
```

### Preview Production Build
```bash
npm run preview
```

---

## 5. Deployment Guide (Vercel & Static Hosts)

The project is zero-configuration ready for deployment on **Vercel**, **Netlify**, or **Cloudflare Pages**:

### Deploying to Vercel
1. Push this repository to GitHub or GitLab.
2. In the Vercel Dashboard, select **Add New Project** and import the repository.
3. Configure the build settings:
   - **Framework Preset:** Vite
   - **Build Command:** `npm run build`
   - **Output Directory:** `dist`
   - **Install Command:** `npm install`
4. Click **Deploy**.

---

## 6. Important Claim Boundaries & Ethics Notice

- **Prototype Status:** This website represents the permanent public entry point and interactive model for a Smart India Hackathon 2026 project currently under development.
- **Synthetic Data:** All institutional names, student profiles, admission numbers, and APAAR keys presented in simulations are purely synthetic and illustrative.
- **No Live Endorsements:** The system does not claim live integration with production APAAR, ABC, DigiLocker, or AICTE APIs, nor does it present fabricated endorsements or user statistics.

---

## 7. Project Metadata

- **Hackathon:** Smart India Hackathon 2026
- **Problem Statement:** SIH26263
- **Category:** Post-admission student-record reconciliation and verification
- **Team Name:** Code Zero
- **Team ID:** 197410
