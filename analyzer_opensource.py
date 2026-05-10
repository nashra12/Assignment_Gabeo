"""
Simple rule-based analyzer - BYPASS for the date bug.
This works WITHOUT LLM, just uses CARC code logic.

Use this temporarily to see the system work while you fix the real analyzer.
"""
from src.models import DenialAnalysis
from src.config import CARC_CODES
from datetime import datetime
from typing import Optional


class SimpleAnalyzer:
    """
    Basic rule-based analyzer without LLM.
    Maps CARC codes to root causes and recoverability.
    """
    
    def __init__(self, model_name: str = None):
        """Initialize (model_name ignored for compatibility)."""
        print("  Using SimpleAnalyzer (rule-based, no LLM)")
    
    def analyze_denial(
        self,
        remittance,
        submission,
        historical_context: Optional[str] = None
    ) -> DenialAnalysis:
        """
        Analyze denial using CARC code rules.
        
        This is a simplified version that works without LLM.
        """
        # Extract CARC code from adjustments
        carc_code = None
        denial_amount = 0.0
        
        for service_line in remittance.service_lines:
            for adj in service_line.adjustments:
                if adj.group == "CO":  # Contractual Obligation
                    carc_code = adj.reason_code
                    denial_amount += adj.amount
        
        if not carc_code:
            carc_code = "UNKNOWN"
        
        # Get CARC info from config
        carc_info = CARC_CODES.get(carc_code, {
            "description": f"Unknown denial code {carc_code}",
            "category": "Other",
            "recoverability": "requires_review",
            "typical_resolution": "Manual review required"
        })
        
        # Determine recoverability
        recov_map = {
            "High (80-95%)": "recoverable_with_info",
            "Medium (50-70%)": "partially_recoverable", 
            "Low (10-30%)": "non_recoverable",
            "Very Low (<10%)": "non_recoverable"
        }
        
        recoverability = recov_map.get(
            carc_info.get('recoverability', 'requires_review'),
            'requires_review'
        )
        
        # Build root cause
        root_cause = carc_info.get('description', f'CARC {carc_code}')
        
        # Determine priority
        if denial_amount > 5000:
            priority = "high"
        elif denial_amount > 1000:
            priority = "medium"
        else:
            priority = "low"
        
        # Build evidence
        evidence = [
            f"CARC Code: {carc_code}",
            f"Denial Amount: ${denial_amount:,.2f}",
            f"Payer: {remittance.payer_name}",
        ]
        
        # Add date info if available (handle both string and datetime)
        try:
            service_date = submission.service_date_from
            if isinstance(service_date, str):
                service_date_str = service_date
            else:
                service_date_str = service_date.strftime("%Y-%m-%d")
            evidence.append(f"Service Date: {service_date_str}")
        except:
            pass
        
        # Confidence based on CARC clarity
        confidence = 0.8 if carc_code in CARC_CODES else 0.5
        
        # Get RARC codes from service lines
        rarc_codes = []
        for service_line in remittance.service_lines:
            rarc_codes.extend(service_line.remark_codes or [])
        
        # Determine denial category
        category = carc_info.get('category', 'Other')
        if hasattr(category, 'value'):
            category = category.value
        
        return DenialAnalysis(
            claim_id=remittance.claim_id,
            root_cause=root_cause,
            recoverability=recoverability,
            confidence_score=confidence,
            financial_impact=denial_amount,
            recommended_action=carc_info.get('typical_resolution', 'Review and resubmit'),
            appeal_priority=priority,
            evidence=evidence,
            carc_codes=[carc_code] if carc_code else [],
            rarc_codes=rarc_codes,
            denial_category=category
        )


# Compatibility alias
ClaimAnalyzerOpenSource = SimpleAnalyzer