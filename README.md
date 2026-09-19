# AYURVEDA_AGENT (v3.1.0 Enterprise Clinical Edition)

**Autonomous Zero-Trust Ayurvedic Hospital Information System (A-HIS), Electronic Health Record (EHR), and Clinical Decision Support System (A-CDSS).**

[![Python 3.14](https://img.shields.io/badge/python-3.14-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)
[![Pydantic v2](https://img.shields.io/badge/pydantic-v2-E92063.svg)](https://docs.pydantic.dev/)
[![SQLite WAL](https://img.shields.io/badge/sqlite-WAL%20mode-003B57.svg)](https://www.sqlite.org/)
[![Tests](https://img.shields.io/badge/tests-397%20passed%20%7C%20100%25-brightgreen.svg)]()
[![Compliance](https://img.shields.io/badge/compliance-NCISM%20%7C%20NABH%20%7C%20ABDM-success.svg)]()

---

## 🏛️ Statutory Framework & Clinical Governance
- **Statutory Framework:** National Commission for Indian System of Medicine (NCISM) Act 2020.
- **Drug Safety Standards:** Drugs and Cosmetics Act 1940 & Rules 1945 (Schedule E(1) & Schedule T).
- **Hospital Accreditation:** NABH Accreditation Standards for AYUSH Hospitals (2nd Edition, 2023, COP.6/HIC/IMS).
- **Terminology & Ontologies:** NAMASTE National Portal, WHO ICD-11 Chapter 26 (Traditional Medicine 2 / TM2), SNOMED CT.
- **Cross-Practice Defense:** Enforces the Supreme Court *Poonam Verma* doctrine; Schedule H/H1/X allopathic drug prescription is strictly firewalled.
- **Human-in-the-Loop Gate:** Autonomous prescribing is prohibited. All clinical evaluations originate in `DRAFT_DECISION_SUPPORT` and mandate NCISM practitioner counter-signature with valid Ayush Registration Number (`ARN`).

---

## 🚀 Architecture & Technical Highlights
- **All 51 Phases Complete:** Covers canonical Ayurvedic diagnosis (Phases 01–34), acute safety break-glass (Phase 35), 28-point herb-drug interaction matrix (Phase 36), 12-language voice/intake (Phase 37), Tele-AYUSH (Phase 38), 500Hz IoT pulse sensor DSP (Phase 39), CIELAB computer vision diagnostics (Phase 40), patient PWA portal (Phase 41), AYUSH Grid ABDM FHIR R4 & ZKP (Phase 42), offline edge sync (Phase 43), pharmacovigilance NPvCC (Phase 44), CTRI clinical trials (Phase 45), IPD/OPD operations (Phases 46–47), GS1 pharmacy inventory (Phase 48), disaster recovery PITR (Phase 49), zero-trust security audit (Phase 50), and production certification (Phase 51).
- **Relational Persistence:** 109 fully normalized relational tables with foreign keys, indexes, and SHA-256 hash-chained audit logging in SQLite WAL mode.
- **API Routing:** 52 registered FastAPI routers aggregated under `/api/v1`.
- **Biophysical Vector Calculus:** Tridosha 2-simplex space $\Delta^2$ with Kullback-Leibler and Mahalanobis Vikriti divergence analytics.

---

## ⚡ Quick Start

### 1. Installation & Environment Setup
```bash
python -m venv .venv
source .venv/bin/activate   # On Windows: .venv\Scripts\activate
pip install -r requirements.txt # or pip install fastapi uvicorn pydantic pytest
```

### 2. Run Autonomous Clinical Diagnosis Demo
Execute the benchmark clinical cases (*Amavata*, *Prameha*, *Tamaka Shwasa*, *Gridhrasi*):
```bash
python run_diagnosis.py --demo
```

### 3. Run Interactive Diagnostic Intake Session
```bash
python run_diagnosis.py --interactive
```

### 4. Start the Live FastAPI Platform
```bash
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```
Interactive Swagger documentation is available at: `http://localhost:8000/docs`

### 5. Run the Full Test Suite
```bash
python -m pytest
```
*Current result: 397 passed in ~97s (100% pass rate).*

---

## 📜 Repository Documentation
- **Master History & Architectural Certification:** [`HISTORY_UPGRADE_ROADMAP_SUMMARY.md`](HISTORY_UPGRADE_ROADMAP_SUMMARY.md)
