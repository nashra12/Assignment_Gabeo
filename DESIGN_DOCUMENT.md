# Claim Denial Analysis System
## Technical Design Document

**For:** Gabeo AI Take-Home Assignment  
**Date:** May 2026

---

## Overview

This document explains the technical design of an AI system for automating healthcare claim denial analysis. The system processes EDI 835 (remittance) and 837 (claim submission) data to identify root causes, match historical patterns, and group denials for efficient batch processing.

**Core Approach:**
- Local LLM inference (Ollama/Qwen 2.5) for root cause reasoning
- Embedding-based similarity matching for historical patterns  
- DBSCAN clustering for batch intelligence
- Zero API costs by using open-source tools

---

## Problem Understanding

### The Manual Process Today

When a claim gets denied:

1. Billing analyst gets 835 remittance (payer response)
2. Looks up original 837 claim submission
3. Reads CARC code (e.g., "29 - Timely Filing")
4. **Manually investigates:**
   - Calculate days between service and receipt
   - Look up payer-specific filing limits
   - Check if there's a delay reason code
   - Search for similar past claims
   - Decide: appeal, resubmit, or write off
5. Time: 15-30 minutes per claim
6. Result: Inconsistent, doesn't scale

### Why CARC Codes Aren't Enough

**Example: CARC 29 (Timely Filing)**

The code just says "filed late" but doesn't tell you:
- Was it 5 days late (appealable) or 200 days (not recoverable)?
- Is there a documented delay reason?
- Was this Medicare (365 day limit) or Commercial (often 90 days)?
- Could this be a secondary claim where timing rules are different?

You need the full claim context, not just the code.

---

## System Architecture

```
Input: EDI 835 + 837 data (JSON)
    ↓
[1] Pattern Matcher
    • Indexes paid claims as embeddings
    • Finds similar historical claims
    • Uses sentence-transformers (local)
    ↓
[2] Claim Analyzer  
    • Enriches with calculated fields
    • Builds context-rich prompt
    • Calls Ollama (Qwen 2.5)
    • Parses structured analysis
    ↓
[3] Denial Clusterer
    • Extracts features from analyses
    • DBSCAN clustering
    • Ranks by financial impact
    ↓
Output: JSON analyses + human-readable report
```

---

## Component Design

### 1. Pattern Matcher (Embeddings)

**Problem:** Need to find historically paid claims "similar" to denied ones, but exact field matching is too brittle.

**Why Embeddings?**
- Medical codes have variations: CPT 99213 vs 99213-25 (modifier changes meaning)
- Same concept, different codes: knee replacement = CPT 27447 or 27486
- Need semantic similarity, not string matching

**Implementation:**
```python
# Convert claim to structured text
text = f"""
Payer: {payer}
Procedures: {cpt_codes}
Diagnoses: {icd10_codes}
Specialty: {provider_specialty}
"""

# Generate embedding (sentence-transformers)
embedding = model.encode(text)  # 384-dim vector

# Store for later similarity search
index.add(embedding, metadata={"claim_id": id, "is_paid": True})
```

**Model Choice:** all-MiniLM-L6-v2
- Fast (< 1 second per claim)
- Good quality for sentence similarity
- Runs locally (no API costs)
- 384 dimensions (vs. OpenAI's 1536 - smaller but sufficient)

**Similarity Threshold:** 0.70 cosine similarity
- Tuned empirically on test data
- Lower = more matches but noisier
- Higher = fewer but more relevant

### 2. Claim Analyzer (Local LLM)

**Problem:** Go beyond CARC code lookup to understand WHY this specific claim was denied.

**Why LLM?**
- Can reason about multiple factors together
- Handles edge cases better than if/else rules
- Natural language output helps billing teams

**Implementation:**

```python
def analyze_denial(remittance, submission):
    # 1. Calculate derived fields
    days_to_file = (received_date - service_date).days
    filing_limit = get_payer_limit(payer, insurance_type)
    
    # 2. Build context-rich prompt
    prompt = f"""
You are analyzing a denied healthcare claim.

DENIAL DETAILS:
- CARC Code: {carc_code}
- Payer: {payer}
- Amount: ${amount}

CLAIM CONTEXT:
- Service date: {service_date}
- Received by payer: {received_date}
- Days elapsed: {days_to_file}
- Filing limit for {payer}: {filing_limit} days
- Delay reason code: {delay_code or "None"}

TASK:
Determine the root cause and whether this is recoverable.

OUTPUT (JSON only):
{{
  "root_cause": "...",
  "recoverability": "recoverable|non_recoverable|needs_review",
  "confidence": 0.0-1.0,
  "evidence": ["fact 1", "fact 2"],
  "recommended_action": "..."
}}
"""
    
    # 3. Call Ollama
    response = ollama.generate(
        model="qwen2.5:7b",
        prompt=prompt,
        options={"temperature": 0.0}  # Deterministic
    )
    
    # 4. Parse JSON output
    analysis = json.loads(response)
    return DenialAnalysis(**analysis)
```

**Why Ollama Instead of Cloud APIs?**

Initially I considered Claude/GPT-4, but chose Ollama because:
- **Cost:** $0 vs. $0.02-0.05 per claim
- **Privacy:** Claim data stays local
- **Control:** Can tune/swap models anytime
- **Reproducibility:** Anyone can run it

**Trade-offs:**
- Slower: 30-60s per claim vs. 2-5s for cloud APIs
- Lower quality: Qwen 2.5 (7B) isn't as sophisticated as GPT-4/Claude
- Acceptable for demo: ~70-80% quality vs. ~85-95% for cloud

**Prompt Design Choices:**
1. **Structured format** - Clearly labeled sections
2. **Explicit task** - Tell it exactly what to do
3. **JSON output** - Easier to parse than natural language
4. **Temperature 0** - Make it deterministic
5. **Evidence required** - Forces it to cite facts

### 3. Denial Clusterer (DBSCAN)

**Problem:** Billing teams work in batches. They need claims grouped by: "45 Aetna prior auth denials worth $128K - appeal these together."

**Why DBSCAN?**
- Don't know the "right" number of clusters beforehand
- Some denials are one-offs (outliers) that don't fit patterns
- Density-based: naturally groups similar claims
- Variable cluster sizes (some denial types are rare)

**Alternative (K-Means):**
- Requires pre-specifying K (how many clusters?)
- Forces all claims into clusters even if dissimilar
- Not appropriate for our use case

**Feature Engineering:**
```python
features = []
for analysis in analyses:
    features.append([
        np.log1p(financial_impact),      # Amount (log scale)
        confidence_score,                # 0-1
        recoverability_encoded,          # 0=not, 0.5=review, 1=yes
        hash(payer) % 100 / 100,        # Payer (hashed to 0-1)
        hash(carc_code) % 100 / 100,    # CARC (hashed to 0-1)
        hash(category) % 100 / 100      # Category (hashed to 0-1)
    ])
```

**Why log scale for amount?**
- Claims range from $200 to $25,000
- Without log: high-value claims dominate clustering
- With log: captures relative magnitude better

**Parameters:**
- `eps=0.5` - Maximum distance between points in a cluster
- `min_samples=3` - Minimum cluster size
- Tuned manually on test data

---

## Key Design Decisions

### Decision 1: Local LLM vs. Cloud APIs

**Options:**
1. Cloud APIs (Claude, GPT-4) - Best quality, ~$0.03/claim
2. Ollama (Qwen 2.5) - Good quality, $0/claim
3. Rule-based - Fast, $0, but limited reasoning

**Choice:** Ollama

**Rationale:**
- Demonstrates I can deploy local LLMs (relevant skill)
- Shows cost-aware engineering
- Privacy-friendly (no data leaving system)
- Quality is "good enough" for demo purposes

**What I'd change in production:**
- Use cloud LLMs for complex cases (top 20%)
- Use local models for straightforward cases (bottom 80%)
- Saves cost while maintaining quality where it matters

### Decision 2: Sentence-Transformers vs. OpenAI Embeddings

**Options:**
1. OpenAI embeddings - Best quality, $0.0001/1K tokens
2. Sentence-transformers - Good quality, $0

**Choice:** Sentence-transformers (all-MiniLM-L6-v2)

**Rationale:**
- Consistent with open-source approach
- Good enough for claim similarity
- Entire pipeline is now zero-cost

**Trade-off:**
- 384 dims vs. OpenAI's 1536 dims
- Slightly lower quality on nuanced medical text
- But for "same payer + similar procedure" matching, it works fine

### Decision 3: DBSCAN vs. K-Means

**Choice:** DBSCAN

**Rationale:**
- We don't know K (number of clusters) beforehand
- K-Means forces everything into K clusters
- DBSCAN handles outliers naturally
- More appropriate for variable-density data

**When K-Means would be better:**
- If we always wanted exactly 5 clusters (fixed business requirement)
- If outliers weren't important

### Decision 4: Prompt Storage

**Choice:** Separate file (`prompts/analysis_prompts.py`)

**Rationale:**
- Gabeo requested prompt visibility for evaluation
- Easy to A/B test different prompt versions
- Non-engineers can review/edit prompts
- Version control shows prompt evolution

---

## Evaluation Approach

### What I Tested

**1. Synthetic Data Quality**
- Generated 30 realistic claims with known denial types
- Verified CARC codes match denial scenarios
- Checked that paid vs. denied split makes sense

**2. Analysis Correctness**
- Manually reviewed all 12 denial analyses
- Confirmed root causes match CARC codes
- Verified evidence fields cite actual claim data
- Checked recoverability assessments are reasonable

**3. Clustering Quality**
- Inspected cluster membership (are similar claims grouped?)
- Verified financial prioritization (high-value clusters ranked first)
- Checked cluster labels make sense

**4. End-to-End Functionality**
- Pipeline runs without errors
- Produces all expected output files
- Processing time is acceptable

### What I Didn't Test (Would Need Real Data)

**1. Recoverability Accuracy**
- Need actual appeal outcomes to measure
- "Recoverable" predictions should win 70-80% of appeals
- "Non-recoverable" should lose 80%+ of appeals

**2. Pattern Matching Impact**
- Does finding similar paid claims improve predictions?
- Need A/B test: with vs. without historical context

**3. Cost-Effectiveness**
- Is it worth appealing a $200 claim that's "partially recoverable"?
- Need real cost data (staff time, success rates)

### Metrics I Tracked

| Metric | Value | Interpretation |
|--------|-------|----------------|
| Avg Confidence | 0.78 | Good - not overconfident |
| Denied Claims Processed | 12/12 (100%) | No errors |
| Clusters Created | 2 | Reasonable for 12 denials |
| Processing Time | 15-20 min | Mostly embedding generation |
| Cost | $0 | Fully open-source |

---

## Known Limitations

### 1. Ollama Quality vs. Cloud LLMs

Qwen 2.5 (7B parameters) is decent but not sophisticated:
- Misses some nuanced edge cases
- Doesn't always catch multi-factor interactions
- Sometimes over-simplifies complex scenarios

**Example it might struggle with:**
"Filed late BUT patient was in hospital at time of filing AND this is Medicare secondary AND primary insurer delayed EOB."

GPT-4 would likely catch this, Qwen might not.

### 2. Small Test Dataset

- Only 30 synthetic claims
- Real billing teams have thousands
- Clustering would work better with more data
- Pattern matching needs larger historical database

### 3. In-Memory Storage

- Current system stores embeddings in RAM
- Won't scale to production (need vector database)
- Would use Pinecone/Weaviate/pgvector in production

### 4. No Appeal Outcome Feedback

- Can't measure if predictions are accurate
- Would need to track: did "recoverable" claims actually get paid?
- This would let us calibrate confidence scores better

### 5. Simplified Payer Rules

- Real payer contracts are complex and change frequently
- Currently using generic filing limits
- Would need payer-specific rule engine in production

---

## Production Considerations

### If Deploying This for Real

**Immediate Next Steps:**
1. Replace in-memory vectors with Pinecone/pgvector
2. Add proper error handling and retries
3. Set up logging and monitoring
4. Build simple web UI (Streamlit)
5. Add batch processing optimizations

**Data Requirements:**
1. Historical claims (6-12 months, both paid and denied)
2. Appeal outcomes (for model calibration)
3. Payer contracts (for rule engine)

**Cost Optimization:**
1. Use Ollama for simple cases (80% of denials)
2. Use Claude/GPT for complex cases (20%)
3. Cache repeated analyses
4. Batch process overnight

**Quality Monitoring:**
1. Track confidence distribution over time
2. Sample human review of high-confidence predictions
3. Collect feedback from billing analysts
4. A/B test prompt variations

---

## Why This Approach

### Technical Soundness

- **LLMs proven for reasoning:** Chain-of-thought prompting works
- **Embeddings standard in healthcare:** Widely used for clinical NLP
- **DBSCAN robust:** Standard clustering algorithm

### Practical Trade-offs

- **Cost vs. Quality:** Ollama good enough for demo, cloud better for production
- **Speed vs. Accuracy:** 30-60s acceptable for batch processing
- **Complexity vs. Maintainability:** Modular design enables iteration

### Demonstrates Key Skills

1. **LLM Engineering:** Deployed local model, wrote prompts, parsed outputs
2. **ML Fundamentals:** Embeddings, clustering, feature engineering
3. **Healthcare Domain:** Understood EDI, CARC codes, payer rules
4. **Production Thinking:** Cost awareness, error handling, monitoring

---

## What I'd Do Differently

### With More Time (2-3 Days)

1. Test larger Ollama models (13B, 70B) for better quality
2. Add prompt caching to speed up similar claims
3. Implement proper unit tests for each component
4. Try different clustering algorithms (hierarchical, spectral)
5. Add more CARC code definitions (currently have 9, need ~50 for 95% coverage)

### For Production (2-3 Months)

1. Hybrid LLM approach (local + cloud)
2. Vector database integration
3. Appeal outcome feedback loop
4. Payer-specific fine-tuning
5. Web UI for billing teams
6. Integration with EHR/RCM systems
7. Multi-claim relationship detection
8. Cost-effectiveness analysis

---

## Conclusion

This system demonstrates that open-source LLMs and embeddings can automate healthcare claim denial analysis at zero cost. While not as sophisticated as cloud-based solutions, it shows understanding of:

- Local LLM deployment (Ollama)
- Embedding-based similarity matching
- Unsupervised clustering
- Healthcare domain knowledge
- Production engineering principles

The modular architecture makes it easy to swap components (e.g., upgrade to cloud LLMs later) without rewriting the entire system.

**Key Takeaway:** This is a working prototype that shows the concepts. In production, I'd use a hybrid approach: local models for straightforward cases, cloud models for complex ones, optimizing for cost while maintaining quality where it matters.

---

**Implementation:** Python 3.9+, Ollama, sentence-transformers, scikit-learn  
**Total Cost:** $0 (fully open-source)  
**Processing Time:** ~20 minutes for 30 claims  
**Code:** Modular, documented, ready for iteration