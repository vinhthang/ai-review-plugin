---
name: en-vi-book-translation-review
description: Review, critique, score, and polish English-to-Vietnamese book translations across genres. Use when the user or an automated pipeline (agent-translator, ai-review-plugin) submits an English source and Vietnamese draft to check semantic fidelity, terminology precision, and natural literary flow, or to eliminate translationese.
---
# English-to-Vietnamese Book Translation Review

Evaluate English-to-Vietnamese book translations for fidelity, terminology, and natural literary flow. All critique notes and explanations must be in English.

## 1. Genre Calibration

- **Non-Fiction/Philosophy:** Conceptual precision, exact logical connectors, consistent canonical terms, authoritative rhythm.
- **Literature/Fiction:** Narrative cadence, sensory subtext, natural dialogue & contextual pronoun shifts (xưng hô).
- **Technical/Economics:** Structural logic, strict adherence to Book Record / Term Table terminology, first-mention-only English glosses (never repeat parenthetical glosses in running text).

## 2. 4-Pass Audit

1. **Fidelity:** Mistranslations, polysemy errors, dropped qualifiers, inverted causality, or reversed debtor/creditor roles.
2. **Anti-Translationese (Khử văn dịch):** Overused passives ("bị/được"), nominalization clutter ("sự/việc"), mechanical pronouns ("họ/nó" for inanimate nouns), and automated glossary injection bloat.
3. **Register/Terms:** Han-Viet vs. Thuan-Viet balance, consistent authorial voice (tôi/bạn/chúng ta vs. chúng tôi), canonical terms.
4. **Rhythm/Flow:** Natural Vietnamese breathability, restructuring heavily nested English clauses, fixing broken line-wraps.

## 3. Output Format

1. **Executive Diagnosis & Score:**
   - Overall assessment + Calibrated score (`1.00–5.00` across `fidelity`, `fluency`, `terminology`, `register`, `structure`, `completeness`) + Verdict (`PASS` if >= 4.00 and zero Critical issues; otherwise `FAIL`) + Top 3 recurring habits to fix.
   - *Scoring Guardrail:* Any `[Critical]` fidelity reversal or unedited machine-translation block automatically caps `weighted_total` at `<= 3.00` (`FAIL`).
2. **Critique Table (All defective segments):**
   | Segment ID | Severity (`[Critical]`/`[Major]`/`[Minor]`) | Original Span (EN) | Faulty Span (VI) | Problem & Explanation (EN) | Suggested Fix (VI) |
   *Rule: Quote strictly the flawed phrase (<25 words), never full paragraphs.*
3. **Polished Passages (VI):**
   - Provide **Faithful Polish** and **Literary/Natural Polish** (full text for excerpts <800 words; top 3–5 most problematic passages for full chapters so the JSON payload is never truncated).
4. **Pipeline JSON Payload:**
   - End with a valid ```json block matching this exact schema:
   ```json
   {
     "dimensions": {"fidelity": 0.0, "fluency": 0.0, "terminology": 0.0, "register": 0.0, "structure": 0.0, "completeness": 0.0},
     "weighted_total": 0.00,
     "verdict": "PASS | FAIL",
     "issues": [
       {"segment_id": "S-0001", "dimension": "fidelity|fluency|terminology|register|structure|completeness", "severity": "critical|major|minor", "span_source": "...", "span_target": "...", "problem": "...", "suggestion": "..."}
     ]
   }
   ```
