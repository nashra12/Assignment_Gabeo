"""
Generate synthetic claim data for testing and evaluation.
"""
import random
from datetime import date, timedelta
from typing import List, Tuple, Dict, Any
import json

from src.models import (
    Remittance835, ClaimSubmission837, ServiceLine, Adjustment
)
from src.config import CARC_CODES, DenialCategory


class SyntheticClaimGenerator:
    """Generates realistic synthetic claims for testing."""
    
    # Realistic test data pools
    PAYERS = [
        ("Blue Cross Blue Shield", "BCBS", "Commercial", 180),
        ("Aetna", "AETNA", "Commercial", 180),
        ("United Healthcare", "UHC", "Commercial", 180),
        ("Medicare Part B", "MEDICARE", "Medicare", 365),
        ("Cigna", "CIGNA", "Commercial", 180),
    ]
    
    CPT_CODES = {
        "office_visit": ["99213", "99214", "99215"],
        "imaging": ["72148", "70553", "71020"],
        "surgery": ["27447", "43239", "29881"],
        "lab": ["80053", "85025", "84443"],
    }
    
    ICD10_CODES = {
        "musculoskeletal": ["M54.5", "M17.11", "M25.511"],
        "respiratory": ["J06.9", "J20.9", "J44.1"],
        "metabolic": ["E11.9", "E78.5", "E66.9"],
        "cardiovascular": ["I10", "I25.10", "I48.91"],
    }
    
    SPECIALTIES = [
        "Family Practice", "Internal Medicine", "Radiology",
        "Orthopedic Surgery", "Cardiology", "Gastroenterology"
    ]
    
    PLACES_OF_SERVICE = ["11", "22", "23", "81"]  # Office, outpatient, ER, lab
    
    def __init__(self, seed: int = 42):
        """Initialize generator with random seed."""
        random.seed(seed)
        self._claim_counter = 1000
    
    def generate_dataset(
        self,
        num_claims: int = 30,
        denial_rate: float = 0.4
    ) -> List[Tuple[Remittance835, ClaimSubmission837, bool]]:
        """
        Generate a complete dataset with mixed paid and denied claims.
        
        Args:
            num_claims: Total number of claims to generate
            denial_rate: Proportion of claims that should be denied
            
        Returns:
            List of (remittance, submission, is_denied) tuples
        """
        dataset = []
        num_denied = int(num_claims * denial_rate)
        
        # Generate denied claims
        for _ in range(num_denied):
            remittance, submission = self._generate_denied_claim()
            dataset.append((remittance, submission, True))
        
        # Generate paid claims
        for _ in range(num_claims - num_denied):
            remittance, submission = self._generate_paid_claim()
            dataset.append((remittance, submission, False))
        
        # Shuffle
        random.shuffle(dataset)
        
        return dataset
    
    def _generate_denied_claim(self) -> Tuple[Remittance835, ClaimSubmission837]:
        """Generate a realistic denied claim."""
        # Pick denial type
        denial_types = list(CARC_CODES.keys())
        carc_code = random.choice(denial_types)
        carc_info = CARC_CODES[carc_code]
        
        # Generate base claim
        remittance, submission = self._generate_base_claim()
        
        # Apply denial-specific modifications
        if carc_code == "29":  # Timely filing
            remittance, submission = self._apply_timely_filing_denial(
                remittance, submission
            )
        elif carc_code == "16":  # Missing info
            remittance, submission = self._apply_missing_info_denial(
                remittance, submission
            )
        elif carc_code == "50":  # Medical necessity
            remittance, submission = self._apply_medical_necessity_denial(
                remittance, submission
            )
        elif carc_code == "18":  # Duplicate
            remittance, submission = self._apply_duplicate_denial(
                remittance, submission
            )
        elif carc_code == "197":  # Prior auth
            remittance, submission = self._apply_prior_auth_denial(
                remittance, submission
            )
        
        # Set denial status and $0 paid
        remittance.claim_status = "4"  # Denied
        remittance.claim_paid = 0.0
        
        # Add adjustment to service line
        adjustment = Adjustment(
            group="CO",
            reason_code=carc_code,
            amount=remittance.claim_amount,
            quantity=None
        )
        
        for line in remittance.service_lines:
            line.paid_amount = 0.0
            line.adjustments = [adjustment]
        
        return remittance, submission
    
    def _generate_paid_claim(self) -> Tuple[Remittance835, ClaimSubmission837]:
        """Generate a realistic paid claim."""
        remittance, submission = self._generate_base_claim()
        
        # Set paid status
        remittance.claim_status = "1"  # Processed as primary
        
        # Payment is 70-95% of billed amount (typical)
        payment_rate = random.uniform(0.70, 0.95)
        remittance.claim_paid = round(remittance.claim_amount * payment_rate, 2)
        
        # Distribute payment across service lines
        for line in remittance.service_lines:
            line.paid_amount = round(line.charged_amount * payment_rate, 2)
            line.allowed_amount = line.paid_amount
            line.adjustments = []  # No denials
        
        return remittance, submission
    
    def _generate_base_claim(self) -> Tuple[Remittance835, ClaimSubmission837]:
        """Generate base claim structure."""
        claim_id = f"CLM-2026-{self._claim_counter:05d}"
        self._claim_counter += 1
        
        # Pick payer
        payer_name, payer_id, insurance_type, filing_limit = random.choice(self.PAYERS)
        
        # Pick service date (recent past)
        days_ago = random.randint(30, 200)
        service_date = date.today() - timedelta(days=days_ago)
        
        # Pick procedure category and codes
        category = random.choice(list(self.CPT_CODES.keys()))
        procedure_code = random.choice(self.CPT_CODES[category])
        
        # Pick diagnoses
        diag_category = random.choice(list(self.ICD10_CODES.keys()))
        principal_dx = random.choice(self.ICD10_CODES[diag_category])
        additional_dx = random.sample(
            [dx for cat in self.ICD10_CODES.values() for dx in cat],
            k=random.randint(0, 3)
        )
        
        # Generate amount
        if category == "surgery":
            amount = random.uniform(5000, 25000)
        elif category == "imaging":
            amount = random.uniform(1000, 5000)
        elif category == "office_visit":
            amount = random.uniform(200, 800)
        else:
            amount = random.uniform(100, 1000)
        
        amount = round(amount, 2)
        
        # Create service line
        service_line = ServiceLine(
            procedure_code=procedure_code,
            modifiers=[],
            charged_amount=amount,
            paid_amount=0.0,  # Will be set based on paid/denied
            allowed_amount=None,
            service_date=service_date,
            adjustments=[],
            remark_codes=[]
        )
        
        # Received date (filed some days after service)
        days_to_file = random.randint(10, filing_limit + 30)
        received_date = service_date + timedelta(days=days_to_file)
        
        # Create remittance (835)
        remittance = Remittance835(
            claim_id=claim_id,
            claim_status="1",  # Will be updated
            claim_amount=amount,
            claim_paid=0.0,  # Will be updated
            patient_responsibility=0.0,
            insurance_type=insurance_type,
            received_date=received_date,
            statement_begin=service_date,
            statement_end=service_date,
            prior_auth_num=None,
            patient_last="TestPatient",
            patient_first="John",
            rendering_id=f"{random.randint(1000000000, 9999999999)}",
            service_lines=[service_line],
            payer_name=payer_name,
            payer_id=payer_id
        )
        
        # Create submission (837)
        submission = ClaimSubmission837(
            claim_no=claim_id,
            amount=amount,
            place_of_service=random.choice(self.PLACES_OF_SERVICE),
            payer_name=payer_name,
            payer_id=payer_id,
            insurance_type=insurance_type,
            service_date_from=service_date,
            service_date_to=service_date,
            principal_diagnosis=principal_dx,
            additional_diagnoses=additional_dx,
            bill_prov_npi=f"{random.randint(1000000000, 9999999999)}",
            rend_prov_npi=remittance.rendering_id,
            rend_prov_specialty=random.choice(self.SPECIALTIES),
            prior_authorization=None,
            claim_frequency="1",  # Original
            delay_reason_code=None,
            type_of_bill=None,
            subscriber_id=f"SUB{random.randint(100000, 999999)}",
            patient_relationship="18",  # Self
            service_lines=[]
        )
        
        return remittance, submission
    
    def _apply_timely_filing_denial(
        self, rem: Remittance835, sub: ClaimSubmission837
    ) -> Tuple[Remittance835, ClaimSubmission837]:
        """Modify claim to be late filed."""
        # Make received date exceed filing limit
        _, _, _, filing_limit = next(
            p for p in self.PAYERS if p[0] == sub.payer_name
        )
        
        days_late = random.randint(10, 90)
        rem.received_date = sub.service_date_from + timedelta(
            days=filing_limit + days_late
        )
        
        # Sometimes include delay reason (makes it more recoverable)
        if random.random() < 0.3:
            sub.delay_reason_code = "1"  # Proof of coverage delay
        
        return rem, sub
    
    def _apply_missing_info_denial(
        self, rem: Remittance835, sub: ClaimSubmission837
    ) -> Tuple[Remittance835, ClaimSubmission837]:
        """Modify claim to have missing information."""
        # Remove prior auth when it might be required
        sub.prior_authorization = None
        rem.prior_auth_num = None
        
        # Add remark code
        for line in rem.service_lines:
            line.remark_codes = ["N20"]
        
        return rem, sub
    
    def _apply_medical_necessity_denial(
        self, rem: Remittance835, sub: ClaimSubmission837
    ) -> Tuple[Remittance835, ClaimSubmission837]:
        """Modify claim to be denied for medical necessity."""
        # Use a high-cost imaging procedure with weak diagnosis
        rem.service_lines[0].procedure_code = "72148"  # MRI lumbar
        sub.principal_diagnosis = "M54.5"  # Low back pain (often challenged)
        
        # Add remark
        rem.service_lines[0].remark_codes = ["N386"]
        
        return rem, sub
    
    def _apply_duplicate_denial(
        self, rem: Remittance835, sub: ClaimSubmission837
    ) -> Tuple[Remittance835, ClaimSubmission837]:
        """Modify claim to be denied as duplicate."""
        # Keep as original frequency
        sub.claim_frequency = "1"
        
        return rem, sub
    
    def _apply_prior_auth_denial(
        self, rem: Remittance835, sub: ClaimSubmission837
    ) -> Tuple[Remittance835, ClaimSubmission837]:
        """Modify claim to be missing prior authorization."""
        # Remove auth
        sub.prior_authorization = None
        rem.prior_auth_num = None
        
        # Use procedure that typically requires auth
        rem.service_lines[0].procedure_code = "27447"  # Knee replacement
        
        return rem, sub
    
    def save_dataset(
        self,
        dataset: List[Tuple[Remittance835, ClaimSubmission837, bool]],
        output_path: str
    ) -> None:
        """Save dataset to JSON file."""
        data = []
        for rem, sub, is_denied in dataset:
            data.append({
                "remittance": self._serialize_remittance(rem),
                "submission": self._serialize_submission(sub),
                "is_denied": is_denied
            })
        
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2, default=str)
    
    def _serialize_remittance(self, rem: Remittance835) -> Dict[str, Any]:
        """Convert Remittance835 to dict."""
        return {
            "claim_id": rem.claim_id,
            "claim_status": rem.claim_status,
            "claim_amount": rem.claim_amount,
            "claim_paid": rem.claim_paid,
            "patient_responsibility": rem.patient_responsibility,
            "insurance_type": rem.insurance_type,
            "received_date": str(rem.received_date) if rem.received_date else None,
            "statement_begin": str(rem.statement_begin) if rem.statement_begin else None,
            "statement_end": str(rem.statement_end) if rem.statement_end else None,
            "payer_name": rem.payer_name,
            "payer_id": rem.payer_id,
            "service_lines": [
                {
                    "procedure_code": line.procedure_code,
                    "modifiers": line.modifiers,
                    "charged_amount": line.charged_amount,
                    "paid_amount": line.paid_amount,
                    "adjustments": [
                        {
                            "group": adj.group,
                            "reason_code": adj.reason_code,
                            "amount": adj.amount
                        }
                        for adj in line.adjustments
                    ],
                    "remark_codes": line.remark_codes
                }
                for line in rem.service_lines
            ]
        }
    
    def _serialize_submission(self, sub: ClaimSubmission837) -> Dict[str, Any]:
        """Convert ClaimSubmission837 to dict."""
        return {
            "claim_no": sub.claim_no,
            "amount": sub.amount,
            "payer_name": sub.payer_name,
            "insurance_type": sub.insurance_type,
            "service_date_from": str(sub.service_date_from) if sub.service_date_from else None,
            "principal_diagnosis": sub.principal_diagnosis,
            "additional_diagnoses": sub.additional_diagnoses,
            "prior_authorization": sub.prior_authorization,
            "claim_frequency": sub.claim_frequency,
            "delay_reason_code": sub.delay_reason_code,
            "rend_prov_specialty": sub.rend_prov_specialty
        }
