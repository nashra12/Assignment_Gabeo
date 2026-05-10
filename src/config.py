"""
CARC/RARC code reference and system configuration.
"""
from typing import Dict, List
from enum import Enum


class DenialCategory(Enum):
    """High-level denial categories."""
    TIMELY_FILING = "timely_filing"
    MISSING_INFO = "missing_information"
    MEDICAL_NECESSITY = "medical_necessity"
    DUPLICATE = "duplicate"
    CODING_ERROR = "coding_error"
    AUTHORIZATION = "authorization"
    NON_COVERED = "non_covered"
    PATIENT_LIABILITY = "patient_liability"
    OTHER = "other"


# CARC Code Reference Database
CARC_CODES: Dict[str, Dict[str, any]] = {
    "4": {
        "description": "The procedure code is inconsistent with the modifier used or a required modifier is missing",
        "category": DenialCategory.CODING_ERROR,
        "recoverability": "high",
        "typical_resolution": "Resubmit with correct modifier or add missing modifier"
    },
    "16": {
        "description": "Claim/service lacks information or has submission/billing error(s) needed for adjudication",
        "category": DenialCategory.MISSING_INFO,
        "recoverability": "high",
        "typical_resolution": "Submit missing documentation or correct billing errors"
    },
    "18": {
        "description": "Exact duplicate claim/service",
        "category": DenialCategory.DUPLICATE,
        "recoverability": "low",
        "typical_resolution": "Review for true duplicate; if not, submit with corrected claim number"
    },
    "29": {
        "description": "The time limit for filing has expired",
        "category": DenialCategory.TIMELY_FILING,
        "recoverability": "medium",
        "typical_resolution": "Appeal with delay reason code and supporting documentation"
    },
    "50": {
        "description": "These are non-covered services because this is not deemed a medical necessity",
        "category": DenialCategory.MEDICAL_NECESSITY,
        "recoverability": "medium",
        "typical_resolution": "Appeal with clinical documentation supporting medical necessity"
    },
    "96": {
        "description": "Non-covered charge(s)",
        "category": DenialCategory.NON_COVERED,
        "recoverability": "low",
        "typical_resolution": "Review contract; if coverage expected, appeal with policy documentation"
    },
    "97": {
        "description": "The benefit for this service is included in the payment/allowance for another service/procedure that has already been adjudicated",
        "category": DenialCategory.DUPLICATE,
        "recoverability": "medium",
        "typical_resolution": "Review bundling rules; appeal if services should be separately billable"
    },
    "197": {
        "description": "Precertification/authorization/notification absent",
        "category": DenialCategory.AUTHORIZATION,
        "recoverability": "high",
        "typical_resolution": "Obtain retroactive authorization if possible, or appeal with proof of emergency"
    },
    "252": {
        "description": "An attachment/other documentation is required to adjudicate this claim/service",
        "category": DenialCategory.MISSING_INFO,
        "recoverability": "high",
        "typical_resolution": "Submit requested documentation"
    },
}

# Common RARC codes
RARC_CODES: Dict[str, str] = {
    "N20": "This service/supply was not prescribed by a physician",
    "N386": "Missing/incomplete/invalid information on whether the diagnostic test was performed by an outside entity or if no purchased tests are included on the claim",
    "M20": "Missing/incomplete/invalid HCPCS",
    "M76": "Missing/incomplete/invalid/deactivated/withdrawn National Drug Code (NDC)",
}


# Payer-specific filing limits (in days)
PAYER_FILING_LIMITS: Dict[str, int] = {
    "Medicare": 365,
    "Medicare Part B": 365,
    "Medicaid": 365,
    "Blue Cross Blue Shield": 180,
    "BCBS": 180,
    "Aetna": 180,
    "United Healthcare": 180,
    "UnitedHealthcare": 180,
    "Cigna": 180,
    "Humana": 180,
    "Commercial": 90,  # Default for commercial
}


# CPT/HCPCS commonly denied procedures
HIGH_DENIAL_PROCEDURES: List[str] = [
    "99213",  # Office visit
    "99214",  # Office visit, complex
    "72148",  # MRI lumbar spine
    "27447",  # Total knee replacement
    "43239",  # Upper GI endoscopy
]


# Medical necessity commonly challenged diagnoses
MEDICAL_NECESSITY_DIAGNOSES: List[str] = [
    "M54.5",  # Low back pain
    "M17.11", # Osteoarthritis
    "J06.9",  # Upper respiratory infection
    "E11.9",  # Type 2 diabetes
]


# Configuration
class Config:
    """System configuration."""
    
    # LLM Settings
    LLM_MODEL = "claude-sonnet-4-20250514"  # or "gpt-4-turbo"
    LLM_TEMPERATURE = 0.0  # Deterministic for consistency
    LLM_MAX_TOKENS = 4000
    
    # Embedding Settings
    EMBEDDING_MODEL = "text-embedding-3-small"  # OpenAI
    EMBEDDING_DIM = 1536
    
    # Analysis Thresholds
    HIGH_CONFIDENCE_THRESHOLD = 0.75
    MEDIUM_CONFIDENCE_THRESHOLD = 0.50
    
    # Pattern Matching
    SIMILARITY_THRESHOLD = 0.70
    MIN_PATTERN_SAMPLE_SIZE = 3
    
    # Clustering
    MIN_CLUSTER_SIZE = 3
    MAX_CLUSTERS = 20
    
    # Financial
    HIGH_VALUE_THRESHOLD = 5000.0
    MEDIUM_VALUE_THRESHOLD = 1000.0


def get_filing_limit_days(payer_name: str, insurance_type: str) -> int:
    """Get filing limit in days for a payer."""
    # Try exact payer name match
    if payer_name in PAYER_FILING_LIMITS:
        return PAYER_FILING_LIMITS[payer_name]
    
    # Try insurance type
    if insurance_type in PAYER_FILING_LIMITS:
        return PAYER_FILING_LIMITS[insurance_type]
    
    # Default based on insurance type
    if insurance_type in ["Medicare", "Medicaid"]:
        return 365
    return 90  # Conservative default for commercial
