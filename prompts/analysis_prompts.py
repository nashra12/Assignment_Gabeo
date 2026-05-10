"""
Prompt templates for LLM-powered claim denial analysis.

These prompts are stored separately from code for easy iteration and evaluation.
"""

ROOT_CAUSE_ANALYSIS_PROMPT = """You are an expert healthcare revenue cycle analyst specializing in claim denial analysis. 

Your task is to analyze a denied insurance claim and determine the root cause, recoverability potential, and recommended actions.

## Claim Data

### EDI 835 (Remittance - Payer's Response):
{remittance_data}

### EDI 837 (Original Claim Submission):
{submission_data}

### CARC/RARC Context:
{carc_context}

### Historical Context:
{historical_context}

## Analysis Instructions

1. **Root Cause Identification**:
   - Go BEYOND just reading the CARC code - analyze the actual claim data
   - Look for specific evidence in the claim fields that explains WHY this was denied
   - Consider timing issues, missing fields, coding inconsistencies, authorization status

2. **Recoverability Assessment**:
   - Evaluate if this denial is valid or potentially recoverable
   - Consider: Is required information actually missing? Was filing truly late? Is medical necessity supportable?
   - Check for payer errors, system issues, or correctable problems

3. **Evidence Gathering**:
   - Cite specific field values from the claim that support your analysis
   - Example: "Service date was {date}, received by payer on {date}, which is {X} days - exceeding the {Y} day filing limit for {payer}"

4. **Confidence Scoring**:
   - Assign a confidence score (0.0 to 1.0) based on:
     * Clarity of the denial reason
     * Completeness of claim data
     * Historical pattern matches
     * Ambiguity in the situation

## Output Format

Return a JSON object with this exact structure:

```json
{{
  "root_cause": "Clear, human-readable explanation of why this claim was denied",
  "denial_category": "One of: timely_filing, missing_information, medical_necessity, duplicate, coding_error, authorization, non_covered, patient_liability, other",
  "carc_codes": ["List of CARC codes from adjustments"],
  "rarc_codes": ["List of RARC codes if present"],
  "recoverability": "One of: recoverable, not_recoverable, needs_review",
  "confidence_score": 0.85,
  "evidence": [
    "Specific evidence point 1 with field citations",
    "Specific evidence point 2 with field citations",
    "..."
  ],
  "recommended_action": "Specific action to take (appeal with X documentation, resubmit with Y correction, etc.)",
  "appeal_priority": "One of: high, medium, low",
  "payer_specific_notes": "Any payer-specific considerations or historical patterns"
}}
```

Be thorough, specific, and evidence-based. Your analysis will guide billing teams on whether to appeal and how to proceed.
"""


PATTERN_MATCHING_PROMPT = """You are comparing a denied claim against historical paid claims to assess recovery potential.

## Denied Claim Summary:
{denied_claim_summary}

## Similar Historical Claims (Paid):
{historical_claims}

## Task:
Analyze the similarity and provide insights on:
1. How similar are these historical claims to the denied claim?
2. What patterns suggest this denial might be recoverable?
3. What differences might explain why historical claims were paid but this was denied?
4. What is the strength of evidence that this claim should have been paid?

Return JSON:
```json
{{
  "similarity_score": 0.75,
  "recovery_likelihood": "high/medium/low",
  "key_similarities": ["List of important matching factors"],
  "key_differences": ["List of important differences"],
  "pattern_insights": "Narrative explanation of the pattern analysis",
  "recommendation": "Specific recommendation based on historical patterns"
}}
```
"""


CLUSTERING_SUMMARY_PROMPT = """You are summarizing a cluster of denied claims to help billing teams prioritize their work.

## Cluster Data:
- Total Claims: {claim_count}
- Total Denied Amount: ${total_amount:,.2f}
- Primary Payers: {payers}
- Common Denial Reasons: {denial_reasons}
- Average Recoverability Score: {avg_recoverability}

## Individual Claims Summary:
{claims_summary}

## Task:
Create a concise, actionable summary for billing teams that answers:
1. What is the common thread in this cluster?
2. How much money is at stake?
3. What percentage is likely recoverable based on historical patterns?
4. What is the recommended batch action?
5. What is the priority level for this cluster?

Return JSON:
```json
{{
  "cluster_label": "Short, descriptive label (e.g., 'Aetna Prior Auth Missing - Radiology')",
  "executive_summary": "2-3 sentence overview for leadership",
  "recovery_potential": {{
    "total_at_stake": 128000.00,
    "estimated_recoverable": 89600.00,
    "recovery_rate": 0.70
  }},
  "recommended_action": "Specific batch action to take",
  "priority": "high/medium/low",
  "effort_estimate": "Estimated hours to process this cluster"
}}
```
"""


SYNTHETIC_CLAIM_GENERATION_PROMPT = """Generate a realistic denied healthcare claim for testing purposes.

## Requirements:
- Denial Type: {denial_type}
- Insurance Type: {insurance_type}
- Financial Range: ${min_amount} - ${max_amount}

## Guidelines:
1. Use realistic CPT codes, ICD-10 codes, NPI numbers
2. Create plausible dates and service details
3. Ensure the denial reason makes sense given the claim data
4. Include subtle details that would require analysis (not obvious denials)
5. Mix recoverable and non-recoverable scenarios

Return both 835 and 837 data as JSON matching the provided schemas.
"""
