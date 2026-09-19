"""Automated Verification Master Test Runner for Unified Clinical Diagnosis & CDSS Engine.

Deliverables:
- Multi-modular Clinical Diagnostic Synthesis (Prakriti, Vikriti, Ashtavidha, Ama-Agni, Srotas, Dhatu Sarata)
- Dual-Coding Interoperability (NAMASTE National Codes + WHO ICD-11 Traditional Medicine Module 2)
- Shat Kriya Kala Pathogenesis Staging & Rogi Bala Grading
- Comprehensive Treatment Formulation (Shamana, Gated Shodhana, Pathya/Apathya, Swasthavritta)
- Multi-tiered Clinical Safety Firewalls (Severe Anemia, Hemodynamic Shock, Pregnancy, HDI)
- Statutory Human-in-the-Loop NCISM Physician Digital Counter-Signature Lifecycle
- Full RESTful API for Evaluation, Counter-Signing, Patient History, and Morbidity Catalog
- Persistence in Table 73 (clinical_diagnosis_episodes) with Immutable SHA-256 Audit Trail
"""
import sys
from pathlib import Path

# Explicitly ensure project root is on sys.path
root_dir = Path(__file__).parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import pytest


def main() -> int:
    """Execute all Clinical Diagnosis automated test suites and report status."""
    print("=" * 80)
    print("AYURVEDA_AGENT :: CLINICAL DIAGNOSTIC ORCHESTRATOR & CDSS TEST RUNNER")
    print("Scope: End-to-End Ayurvedic Diagnosis, Dual-Coding, and Treatment Decision Support")
    print("=" * 80)

    test_args = [
        "-v",
        "-s",
        str(Path(__file__).parent / "test_diagnosis_orchestrator.py"),
        str(Path(__file__).parent / "test_diagnosis_api.py"),
    ]

    exit_code = pytest.main(test_args)

    print("\n" + "=" * 80)
    if exit_code == 0:
        print(">>> CLINICAL DIAGNOSIS VERIFICATION SUCCESSFUL: 100% TESTS PASSED (EXIT CODE 0) <<<")
    else:
        print(f">>> CLINICAL DIAGNOSIS VERIFICATION FAILED WITH EXIT CODE: {exit_code} <<<")
    print("=" * 80)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
