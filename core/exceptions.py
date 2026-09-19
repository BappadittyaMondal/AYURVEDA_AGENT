"""Domain-specific clinical governance, safety, and security exceptions."""


class ClinicalGovernanceException(Exception):
    """Base exception for all AYURVEDA_AGENT clinical and safety violations."""
    def __init__(self, message: str, error_code: str = "CLINICAL_GOVERNANCE_ERROR"):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)


class AuthenticationFailedException(ClinicalGovernanceException):
    """Raised when authentication credentials or token signatures are invalid."""
    def __init__(self, message: str = "Authentication failed or token expired"):
        super().__init__(message=message, error_code="AUTHENTICATION_FAILED")


class AuthorizationDeniedException(ClinicalGovernanceException):
    """Raised when an actor attempts an action outside their granted role permissions."""
    def __init__(self, message: str = "Access denied: insufficient permissions"):
        super().__init__(message=message, error_code="PERMISSION_DENIED")


class TenantIsolationViolationException(ClinicalGovernanceException):
    """Raised when cross-hospital data access is detected without multi-tenant clearance."""
    def __init__(self, message: str = "Cross-tenant access prohibited"):
        super().__init__(message=message, error_code="TENANT_ISOLATION_VIOLATION")


class HerbDrugInteractionViolation(ClinicalGovernanceException):
    """Raised when a prescription matches a lethal or severe HDI firewall rule."""
    def __init__(self, herb: str, drug: str, clinical_risk: str):
        message = f"LETHAL INTERACTION INTERCEPTED: {herb} + {drug}. Risk: {clinical_risk}"
        super().__init__(message=message, error_code="REJECTED_LETHAL_INTERACTION")


class ScheduleE1ShodhanaMissingException(ClinicalGovernanceException):
    """Raised when a Schedule E(1) poisonous substance is prescribed without documented Shodhana."""
    def __init__(self, substance: str):
        message = f"Schedule E(1) substance '{substance}' requires certified Shodhana verification"
        super().__init__(message=message, error_code="SCHEDULE_E1_SHODHANA_MISSING")


class HeavyMetalExposureExceededException(ClinicalGovernanceException):
    """Raised when cumulative heavy metal exposure exceeds statutory API/USP limits."""
    def __init__(self, metal: str, current_load_mg: float, limit_mg: float):
        message = f"Cumulative {metal} exposure ({current_load_mg:.2f}mg) exceeds lifetime limit ({limit_mg:.2f}mg)"
        super().__init__(message=message, error_code="HEAVY_METAL_LIMIT_EXCEEDED")


class AmaGatingException(ClinicalGovernanceException):
    """Raised when panchakarma shodhana or brimhana is attempted during high Ama state."""
    def __init__(self, agi_score: float):
        message = f"AGI score {agi_score:.2f} >= 1.80 (Sama Avastha). Deepana-Pachana mandatory prior to Shodhana."
        super().__init__(message=message, error_code="AMA_GATING_VIOLATION")


class RecordNotFoundException(ClinicalGovernanceException):
    """Raised when an expected clinical record, patient, or inventory item is missing."""
    def __init__(self, entity: str, identifier: str):
        super().__init__(
            message=f"{entity} with ID '{identifier}' not found",
            error_code="RECORD_NOT_FOUND"
        )
