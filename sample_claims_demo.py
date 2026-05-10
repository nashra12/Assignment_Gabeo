"""
Process the 4 sample claims provided in the assignment.
"""
import json
from datetime import date

from src.models import Remittance835, ClaimSubmission837, ServiceLine, Adjustment
from src.analyzer import ClaimAnalyzer
from src.pattern_matcher import PatternMatcher


def create_sample_claims():
    """Create the 4 sample claims from the assignment."""
    
    claims = []
    
    # CLAIM A - Timely Filing Denial
    rem_a = Remittance835(
        claim_id="CLM-2026-00142",
        claim_status="4",
        claim_amount=4500.00,
        claim_paid=0.00,
        patient_responsibility=0.00,
        insurance_type="Commercial",
        received_date=date(2026, 3, 20),
        statement_begin=date(2025, 6, 15),
        statement_end=date(2025, 6, 15),
        prior_auth_num=None,
        patient_last=None,
        patient_first=None,
        rendering_id=None,
        service_lines=[
            ServiceLine(
                procedure_code="99214",
                modifiers=[],
                charged_amount=4500.00,
                paid_amount=0.00,
                allowed_amount=None,
                service_date=date(2025, 6, 15),
                adjustments=[
                    Adjustment(group="CO", reason_code="29", amount=4500.00)
                ],
                remark_codes=[]
            )
        ],
        payer_name="Blue Cross Blue Shield",
        payer_id="BCBS-IL"
    )
    
    sub_a = ClaimSubmission837(
        claim_no="CLM-2026-00142",
        amount=4500.00,
        place_of_service=None,
        payer_name="Blue Cross Blue Shield",
        payer_id="BCBS-IL",
        insurance_type="Commercial",
        service_date_from=date(2025, 6, 15),
        service_date_to=None,
        principal_diagnosis="J06.9",
        additional_diagnoses=[],
        bill_prov_npi="1234567890",
        rend_prov_npi=None,
        rend_prov_specialty=None,
        prior_authorization=None,
        claim_frequency="1",
        delay_reason_code="",
        type_of_bill=None,
        subscriber_id="XYZ123456",
        patient_relationship=None,
        service_lines=[]
    )
    
    claims.append((rem_a, sub_a, True, "Timely Filing"))
    
    # CLAIM B - Missing Information Denial
    rem_b = Remittance835(
        claim_id="CLM-2026-00287",
        claim_status="4",
        claim_amount=12800.00,
        claim_paid=0.00,
        patient_responsibility=0.00,
        insurance_type="Medicare",
        received_date=date(2026, 2, 10),
        statement_begin=None,
        statement_end=None,
        prior_auth_num=None,
        patient_last=None,
        patient_first=None,
        rendering_id=None,
        service_lines=[
            ServiceLine(
                procedure_code="27447",
                modifiers=[],
                charged_amount=12800.00,
                paid_amount=0.00,
                allowed_amount=None,
                service_date=None,
                adjustments=[
                    Adjustment(group="CO", reason_code="16", amount=12800.00)
                ],
                remark_codes=["N20"]
            )
        ],
        payer_name="Medicare Part B",
        payer_id=None
    )
    
    sub_b = ClaimSubmission837(
        claim_no="CLM-2026-00287",
        amount=12800.00,
        place_of_service=None,
        payer_name="Medicare Part B",
        payer_id=None,
        insurance_type="Medicare",
        service_date_from=date(2026, 1, 8),
        service_date_to=None,
        principal_diagnosis="M17.11",
        additional_diagnoses=[],
        bill_prov_npi="9876543210",
        rend_prov_npi=None,
        rend_prov_specialty=None,
        prior_authorization="AUTH-998877",
        claim_frequency="1",
        delay_reason_code=None,
        type_of_bill="131",
        subscriber_id=None,
        patient_relationship=None,
        service_lines=[]
    )
    
    claims.append((rem_b, sub_b, True, "Missing Info"))
    
    # CLAIM C - Medical Necessity Denial
    rem_c = Remittance835(
        claim_id="CLM-2026-00391",
        claim_status="4",
        claim_amount=8200.00,
        claim_paid=0.00,
        patient_responsibility=0.00,
        insurance_type="Commercial",
        received_date=None,
        statement_begin=None,
        statement_end=None,
        prior_auth_num=None,
        patient_last=None,
        patient_first=None,
        rendering_id=None,
        service_lines=[
            ServiceLine(
                procedure_code="72148",
                modifiers=[],
                charged_amount=8200.00,
                paid_amount=0.00,
                allowed_amount=None,
                service_date=None,
                adjustments=[
                    Adjustment(group="CO", reason_code="50", amount=8200.00)
                ],
                remark_codes=["N386"]
            )
        ],
        payer_name="Aetna",
        payer_id=None
    )
    
    sub_c = ClaimSubmission837(
        claim_no="CLM-2026-00391",
        amount=8200.00,
        place_of_service=None,
        payer_name="Aetna",
        payer_id=None,
        insurance_type="Commercial",
        service_date_from=date(2026, 2, 20),
        service_date_to=None,
        principal_diagnosis="M54.5",
        additional_diagnoses=["M51.16"],
        bill_prov_npi="5678901234",
        rend_prov_npi=None,
        rend_prov_specialty="Radiology",
        prior_authorization="",
        claim_frequency=None,
        delay_reason_code=None,
        type_of_bill=None,
        subscriber_id=None,
        patient_relationship=None,
        service_lines=[]
    )
    
    claims.append((rem_c, sub_c, True, "Medical Necessity"))
    
    # CLAIM D - Duplicate Claim Denial
    rem_d = Remittance835(
        claim_id="CLM-2026-00455",
        claim_status="4",
        claim_amount=3200.00,
        claim_paid=0.00,
        patient_responsibility=0.00,
        insurance_type="Commercial",
        received_date=None,
        statement_begin=None,
        statement_end=None,
        prior_auth_num=None,
        patient_last=None,
        patient_first=None,
        rendering_id=None,
        service_lines=[
            ServiceLine(
                procedure_code="99213",
                modifiers=[],
                charged_amount=3200.00,
                paid_amount=0.00,
                allowed_amount=None,
                service_date=None,
                adjustments=[
                    Adjustment(group="CO", reason_code="18", amount=3200.00)
                ],
                remark_codes=[]
            )
        ],
        payer_name="United Healthcare",
        payer_id=None
    )
    
    sub_d = ClaimSubmission837(
        claim_no="CLM-2026-00455",
        amount=3200.00,
        place_of_service=None,
        payer_name="United Healthcare",
        payer_id=None,
        insurance_type="Commercial",
        service_date_from=date(2026, 1, 10),
        service_date_to=None,
        principal_diagnosis="J20.9",
        additional_diagnoses=[],
        bill_prov_npi="1234567890",
        rend_prov_npi=None,
        rend_prov_specialty=None,
        prior_authorization=None,
        claim_frequency="1",
        delay_reason_code=None,
        type_of_bill=None,
        subscriber_id=None,
        patient_relationship=None,
        service_lines=[]
    )
    
    claims.append((rem_d, sub_d, True, "Duplicate"))
    
    return claims


def main():
    """Analyze the 4 sample claims."""
    import os
    
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    if not anthropic_key:
        print("ERROR: ANTHROPIC_API_KEY environment variable not set")
        return
    
    print("=" * 70)
    print("ANALYZING ASSIGNMENT SAMPLE CLAIMS")
    print("=" * 70)
    
    # Create analyzer
    analyzer = ClaimAnalyzer(api_key=anthropic_key)
    
    # Load sample claims
    claims = create_sample_claims()
    
    results = []
    
    for idx, (remittance, submission, is_denied, denial_type) in enumerate(claims, 1):
        print(f"\n{'='*70}")
        print(f"CLAIM {idx}: {remittance.claim_id} - {denial_type}")
        print(f"{'='*70}")
        print(f"Amount: ${remittance.claim_amount:,.2f}")
        print(f"Payer: {submission.payer_name}")
        print(f"CARC Code: {remittance.service_lines[0].adjustments[0].reason_code}")
        
        try:
            # Analyze
            print("\nAnalyzing...")
            analysis = analyzer.analyze_denial(remittance, submission)
            
            print(f"\n{'─'*70}")
            print("ANALYSIS RESULT:")
            print(f"{'─'*70}")
            print(f"Root Cause:\n  {analysis.root_cause}\n")
            print(f"Recoverability: {analysis.recoverability.upper()}")
            print(f"Confidence: {analysis.confidence_score:.2f}")
            print(f"Appeal Priority: {analysis.appeal_priority.upper()}")
            print(f"\nRecommended Action:\n  {analysis.recommended_action}\n")
            
            print("Evidence:")
            for i, evidence in enumerate(analysis.evidence, 1):
                print(f"  {i}. {evidence}")
            
            results.append({
                "claim_id": remittance.claim_id,
                "denial_type": denial_type,
                "analysis": {
                    "root_cause": analysis.root_cause,
                    "recoverability": analysis.recoverability,
                    "confidence": analysis.confidence_score,
                    "recommended_action": analysis.recommended_action,
                    "evidence": analysis.evidence,
                    "financial_impact": analysis.financial_impact
                }
            })
            
        except Exception as e:
            print(f"\nERROR: {str(e)}")
            continue
    
    # Save results
    output_path = "outputs/sample_claims_analysis.json"
    os.makedirs("outputs", exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n{'='*70}")
    print("ANALYSIS COMPLETE")
    print(f"{'='*70}")
    print(f"\nResults saved to: {output_path}")
    print(f"\nTotal Denied Amount: ${sum(r['analysis']['financial_impact'] for r in results):,.2f}")
    
    recov_counts = {}
    for r in results:
        recov = r['analysis']['recoverability']
        recov_counts[recov] = recov_counts.get(recov, 0) + 1
    
    print("\nRecoverability Breakdown:")
    for recov, count in recov_counts.items():
        print(f"  {recov}: {count} claims")


if __name__ == "__main__":
    main()
