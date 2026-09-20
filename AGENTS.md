# AYURVEDA_AGENT :: Workspace Operational Rules & Autonomous Execution Guidelines

## 1. Autonomous Execution & Reduced Permission Invariant ("Reduce Ask Permission to Continue")
- **Autonomous End-to-End Execution**: When tasked with an objective, implementation, bug fix, verification, or multi-step workflow, execute all necessary steps, file modifications, and test verifications autonomously to completion.
- **Eliminate Trivial Permission Prompts**: DO NOT pause execution to ask routine confirmation questions such as:
  - "Shall I proceed to the next step?"
  - "May I have permission to continue?"
  - "Would you like me to run the tests now?"
  - "Should I push these changes to git?"
- **Proactive Action**: Proactively execute terminal commands, run test suites, apply code edits, and perform verifications. Present the final verified results and actionable conclusions directly.
- **Exception Boundary**: Only pause to solicit user input when:
  1. A requirement is fundamentally contradictory or critically underspecified.
  2. A destructive, irrecoverable operation outside the project scope is explicitly involved.

## 2. Zero Circular Oscillation ("No Wheel-Spinning")
- Avoid revisiting or endlessly refactoring established, validated mathematical and clinical engines (e.g., Tridosha simplex $\Delta^2$, Ama-Agni gating, 28-point HDI matrix).
- Advance sequentially with clear, evidence-based deliverables.

## 3. Strict Documentation & Code Preservation
- Strict Preservation Invariant: DO NOT delete or overwrite historical audit entries or established roadmap documentation (e.g., in `HISTORY_UPGRADE_ROADMAP_SUMMARY.md`). All updates must be strictly additive / appended.
- Maintain 100% test suite pass rate with exit code 0 repository-wide.
