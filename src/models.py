"""
Data models for healthcare claim denial analysis system.
"""
from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional, List, Dict, Any
from enum import Enum


class ClaimStatus(Enum):
    """Claim status codes from 835."""
    PROCESSED_PRIMARY = "1"
    PROCESSED_SECONDARY = "2"
    PROCESSED_TERTIARY = "3"
    DENIED = "4"
    PROCESSED_FORWARDED = "19"
    REVERSAL = "22"


class AdjustmentGroup(Enum):
    """Adjustment group codes - who is financially responsible."""
    CONTRACTUAL = "CO"  # Provider contractual obligation
    PATIENT = "PR"  # Patient responsibility
    OTHER = "OA"  # Other adjustment
    PAYER_INITIATED = "PI"  # Payer initiated
    CORRECTION = "CR"  # Correction/Reversal


class InsuranceType(Enum):
    """Types of insurance coverage."""
    MEDICARE = "Medicare"
    MEDICAID = "Medicaid"
    COMMERCIAL = "Commercial"
    UNKNOWN = "Unknown"


@dataclass
class Adjustment:
    """Represents a claim adjustment (denial reason)."""
    group: str  # CO, PR, OA, PI, CR
    reason_code: str  # CARC code
    amount: float
    quantity: Optional[float] = None


@dataclass
class ServiceLine:
    """Individual service line within a claim."""
    procedure_code: str
    modifiers: List[str]
    charged_amount: float
    paid_amount: float
    allowed_amount: Optional[float]
    service_date: Optional[date]
    adjustments: List[Adjustment]
    remark_codes: List[str]
    revenue_code: Optional[str] = None


@dataclass
class Remittance835:
    """EDI 835 - Remittance Advice (payer's response)."""
    # Claim-level fields
    claim_id: str
    claim_status: str
    claim_amount: float
    claim_paid: float
    patient_responsibility: float
    insurance_type: str
    received_date: Optional[date]
    statement_begin: Optional[date]
    statement_end: Optional[date]
    prior_auth_num: Optional[str]
    
    # Patient info
    patient_last: Optional[str]
    patient_first: Optional[str]
    
    # Provider info
    rendering_id: Optional[str]
    
    # Service lines with adjustments
    service_lines: List[ServiceLine]
    
    # Payment-level context
    payer_name: Optional[str] = None
    payer_id: Optional[str] = None
    

@dataclass
class ClaimSubmission837:
    """EDI 837 - Original Claim Submission."""
    # Claim header
    claim_no: str
    amount: float
    place_of_service: Optional[str]
    
    # Payer info
    payer_name: Optional[str]
    payer_id: Optional[str]
    insurance_type: str
    
    # Service dates
    service_date_from: Optional[date]
    service_date_to: Optional[date]
    
    # Diagnoses
    principal_diagnosis: Optional[str]
    additional_diagnoses: List[str]
    
    # Provider info
    bill_prov_npi: Optional[str]
    rend_prov_npi: Optional[str]
    rend_prov_specialty: Optional[str]
    
    # Authorization
    prior_authorization: Optional[str]
    
    # Claim metadata
    claim_frequency: str  # 1=Original, 7=Replacement, 8=Void
    delay_reason_code: Optional[str]
    type_of_bill: Optional[str]
    
    # Patient info
    subscriber_id: Optional[str]
    patient_relationship: Optional[str]
    
    # Service line details
    service_lines: List[Dict[str, Any]]  # cd_ prefix fields


@dataclass
class DenialAnalysis:
    """Result of analyzing a denied claim."""
    claim_id: str
    root_cause: str
    carc_codes: List[str]
    rarc_codes: List[str]
    recoverability: str  # "recoverable", "not_recoverable", "needs_review"
    confidence_score: float  # 0.0 to 1.0
    evidence: List[str]  # Supporting evidence from claim fields
    recommended_action: str
    financial_impact: float
    appeal_priority: str  # "high", "medium", "low"
    
    # Additional context
    denial_category: str  # "timely_filing", "medical_necessity", "missing_info", etc.
    payer_specific_notes: Optional[str] = None


@dataclass
class HistoricalPattern:
    """Pattern from historical claim data."""
    pattern_id: str
    payer_name: str
    procedure_codes: List[str]
    diagnosis_codes: List[str]
    denial_rate: float
    average_paid_amount: float
    sample_size: int
    common_denial_reasons: List[str]
    success_rate_on_appeal: Optional[float]


@dataclass
class DenialCluster:
    """Cluster of similar denied claims."""
    cluster_id: str
    cluster_label: str
    claim_count: int
    total_amount: float
    avg_recoverability_score: float
    primary_denial_reasons: List[str]
    payers: List[str]
    recommended_batch_action: str
    expected_recovery_amount: float
    expected_recovery_rate: float
