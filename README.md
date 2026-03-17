# 🌿 GreenGate — AI + Blockchain CBAM Carbon Compliance Platform

**For Indian MSME Exporters**

GreenGate helps Indian MSMEs exporting to the European Union comply with the **Carbon Border Adjustment Mechanism (CBAM)** regulation. It calculates carbon emissions, generates AI-powered reduction recommendations, and stores immutable certificates on the Polygon blockchain.

---

## 🛠 Tech Stack

| Layer            | Technology                                        |
|-----------------|---------------------------------------------------|
| **Frontend**     | React + Vite + TailwindCSS + ethers.js            |
| **Backend**      | Python FastAPI + SQLAlchemy + web3.py + OpenAI SDK |
| **Database**     | SQLite                                            |
| **Blockchain**   | Polygon Amoy Testnet (EVM-compatible)              |
| **Smart Contract** | Solidity 0.8.x (Hardhat)                       |
| **AI Engine**    | Rule-based IPCC calculator + Cerebras/Ollama fallback stack |

---

## 🚀 Quick Start

### Prerequisites

- **Node.js** ≥ 18
- **Python** ≥ 3.10
- **MetaMask** browser extension
- (Optional) **OpenAI API Key** for AI recommendations

### 1. Blockchain Setup (do this FIRST)

```bash
cd blockchain
npm install
npx hardhat compile
```

To deploy to Polygon Amoy testnet:

1. Get a wallet private key and add test MATIC from <https://faucet.polygon.technology>
2. Update `blockchain/.env` with your `DEPLOYER_PRIVATE_KEY`
3. Run:

```bash
npx hardhat run scripts/deploy.js --network amoy
```

1. Copy the printed `CONTRACT_ADDRESS` to `backend/.env` and `frontend/.env`

### 2. Backend Setup

```bash
cd backend
pip install -r requirements.txt
```

Edit `backend/.env`:

- Set `OPENAI_API_KEY` (optional — fallback recommendations will be used if not set)
- Set `SIGNER_PRIVATE_KEY` (your backend wallet private key for blockchain submissions)
- Set `CONTRACT_ADDRESS` (from Step 1)

Start the server:

```bash
uvicorn main:app --reload --port 8000
```

### 3. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The app will be available at **<http://localhost:5173>**

### 4. MetaMask Setup

1. Install **MetaMask** browser extension
2. The app will automatically prompt you to add **Polygon Amoy** network
3. Get free test MATIC from: <https://faucet.polygon.technology>

---

## 📋 Features

- **🔬 AI Carbon Calculator** — Uses IPCC/CEA emission factors for accurate Scope 1 & 2 calculations
- **🤖 AI Recommendations** — Cerebras-first with local fallback and deterministic backup recommendations
- **🔗 Blockchain Certification** — Immutable report hashes on Polygon for trustless verification
- **✅ Public Verification** — EU importers can verify certificates without any login
- **📊 CBAM Reports** — Downloadable reports in EU-compatible format
- **📈 Sector Benchmarks** — Compare your emissions against industry standards
- **🏭 Product Supply Chain Discovery** — LLM-planned company/supplier verification queries + graph-based traceability
- **🧪 Factory Intelligence + Optimization** — Per-factory emissions analysis and supplier replacement simulation
- **📎 Evidence Upload Workflow** — Support low-confidence reports with PDF evidence before certification

---

## 🧭 Architecture Flow

```mermaid
flowchart LR
        %% -------- Users & Frontend --------
        U[MSME User]
        VU[EU Importer / Public Verifier]
        FE[Frontend Dashboard<br/>React + Vite]
        U --> FE
        VU --> FE

        %% -------- API Layer --------
        subgraph API[FastAPI Layer]
            direction TB
            AUTH[/Auth Router<br/>register/login/me/]
            CALC[/Calculator Router<br/>company-intelligence/calculate/simulate-reduction/]
            PROD[/Products Router<br/>discover/confirm/analyze/aggregate/optimize/]
            REP[/Reports Router<br/>list/get/upload-evidence/certify/download/]
            VER[/Verify Router<br/>public hash verification/]
        end

        FE -->|1. JWT auth| AUTH
        FE -->|2. Emission submission| CALC
        FE -->|3. Product graph workflow| PROD
        FE -->|4. Reports + evidence + certify| REP
        FE -->|5. Public verification| VER

        %% -------- Service Layer --------
        subgraph CORE[Core Services]
            direction LR
            ENG[Emission + Verification Engines<br/>IPCC/CBAM/benchmark/confidence]
            AI[AI Recommendation Service<br/>Cerebras primary → Ollama fallback → deterministic fallback]
            DISC[Supply Chain Discovery Service<br/>LLM plans company-first then supplier verification queries]
            FACT[Factory Intelligence Service<br/>machinery extraction + per-node emissions]
            AGG[Product Aggregation Service<br/>product footprint + CBAM risk]
            OPT[Supply Chain Optimizer<br/>replacement simulation + savings]
            CHAIN[Blockchain Service<br/>web3.py signing + tx submit]
        end

        CALC --> ENG
        CALC --> AI

        PROD --> DISC --> FACT --> AGG --> OPT
        DISC --> AI
        FACT --> AI

        REP --> CHAIN

        %% -------- Persistence --------
        PERSIST[(Application Persistence)]
        DB[(SQLite<br/>users / reports / products / nodes / factory_profiles)]
        AUTH --> PERSIST
        CALC --> PERSIST
        PROD --> PERSIST
        REP --> PERSIST
        VER --> PERSIST
        PERSIST --> DB

        %% -------- External Integrations --------
        subgraph EXT[External Integrations]
            direction TB
            SEARCH[Web Intelligence Stack]
            CEREBRAS[(Cerebras API)]
            OLLAMA[(Local Ollama)]
            EXA[(Exa Search)]
            TAVILY[(Tavily Search)]
            FIRE[(Firecrawl)]
            SC[(Polygon Amoy<br/>CarbonReportRegistry)]
        end

        AI --> CEREBRAS
        AI --> OLLAMA

        DISC --> SEARCH
        FACT --> SEARCH
        SEARCH --> EXA
        SEARCH --> TAVILY
        SEARCH --> FIRE

        CHAIN --> SC
        VER --> SC

        %% -------- Styling --------
        classDef user fill:#dcfce7,stroke:#16a34a,color:#14532d,stroke-width:1.5px;
        classDef frontend fill:#dbeafe,stroke:#2563eb,color:#1e3a8a,stroke-width:1.5px;
        classDef api fill:#f3e8ff,stroke:#7e22ce,color:#581c87,stroke-width:1.2px;
        classDef core fill:#ecfeff,stroke:#0891b2,color:#164e63,stroke-width:1.2px;
        classDef store fill:#fff7ed,stroke:#ea580c,color:#7c2d12,stroke-width:1.2px;
        classDef ext fill:#f5f3ff,stroke:#6d28d9,color:#4c1d95,stroke-width:1.2px;

        class U,VU user;
        class FE frontend;
        class AUTH,CALC,PROD,REP,VER api;
        class ENG,AI,DISC,FACT,AGG,OPT,CHAIN core;
        class PERSIST,DB store;
        class SEARCH,CEREBRAS,OLLAMA,EXA,TAVILY,FIRE,SC ext;
```

---

## 🌐 API Endpoints

| Method | Endpoint                          | Auth     | Description                      |
|--------|-----------------------------------|----------|----------------------------------|
| POST   | `/auth/register`                  | No       | Register MSME user               |
| POST   | `/auth/login`                     | No       | Login and get JWT token          |
| GET    | `/auth/me`                        | JWT      | Get user profile                 |
| POST   | `/api/company-intelligence`       | JWT      | Discover company profile hints   |
| POST   | `/api/calculate`                  | JWT      | Calculate carbon emissions       |
| POST   | `/api/simulate-reduction`         | JWT      | Simulate reduction actions       |
| GET    | `/api/reports`                    | JWT      | List user's reports              |
| GET    | `/api/reports/{id}`               | JWT      | Get full report details          |
| POST   | `/api/reports/{id}/upload-evidence` | JWT    | Upload evidence PDFs             |
| POST   | `/api/reports/{id}/certify`       | JWT      | Certify report on blockchain     |
| GET    | `/api/reports/{id}/download`      | JWT      | Download CBAM report as JSON     |
| POST   | `/api/products/discover`          | JWT      | Discover product supply chain    |
| POST   | `/api/products/{id}/confirm-supply-chain` | JWT | Confirm/edit discovered graph |
| GET    | `/api/products/{id}`              | JWT      | Get product detail + graph       |
| POST   | `/api/products/{id}/analyze-factories` | JWT  | Run per-factory intelligence     |
| POST   | `/api/products/{id}/aggregate-carbon` | JWT   | Aggregate product-level carbon   |
| POST   | `/api/products/{id}/optimize`     | JWT      | Simulate supplier replacement    |
| GET    | `/api/verify/{hash}`              | **No**   | Public certificate verification  |
| GET    | `/api/health`                     | No       | Health check                     |

---

## 📁 Project Structure

```
greengate/
├── frontend/              # React + Vite
│   ├── src/
│   │   ├── pages/         # Home, Dashboard, Calculator, Report, Verify, Product*
│   │   ├── components/    # Navbar, EmissionForm, ResultCard, etc.
│   │   ├── hooks/         # useWeb3 (MetaMask)
│   │   └── utils/         # API client
│   └── ...
├── backend/               # FastAPI
│   ├── routers/           # auth, calculator, reports, verify, products
│   ├── services/          # emissions, verification, intelligence, optimization, blockchain
│   ├── data/              # emission factors, benchmarks, verified factories, etc.
│   └── ...
└── blockchain/            # Hardhat + Solidity
    ├── contracts/         # CarbonReportRegistry.sol
    └── scripts/           # deploy.js
```

---

## 📄 License

MIT License — Built for the GreenGate Hackathon 2026.
