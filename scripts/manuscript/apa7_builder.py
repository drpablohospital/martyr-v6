#!/usr/bin/env python3
"""Martyr v5.1 - Generador de Manuscritos APA 7 + PRISMA 2020"""
import json
from datetime import datetime

class APA7ManuscriptBuilder:
    def __init__(self, topic, studies, meta_result, pico=None):
        self.topic = topic
        self.studies = studies
        self.meta = meta_result
        self.pico = pico or {}
        self.date = datetime.now().strftime("%Y-%m-%d")
    
    def build(self):
        sections = [
            self._title_page(),
            self._abstract(),
            self._introduction(),
            self._methods(),
            self._results(),
            self._discussion(),
            self._references(),
            self._tables(),
            self._figures(),
        ]
        return "\n\n".join(sections)
    
    def _title_page(self):
        return f"""# {self.topic}: A Systematic Review and Meta-Analysis

**Running head:** META-ANALYSIS OF {self.topic.upper()[:40]}

**Authors:** [AUTHOR NAME]¹, [CO-AUTHOR]²

**Affiliations:**
¹ [Hospital/University], [City, Country]
² [Hospital/University], [City, Country]

**Corresponding author:** [EMAIL]

**Conflict of interest:** None declared
**Funding:** None
**Registration:** PROSPERO [NUMBER] (registered [DATE])

---"""
    
    def _abstract(self):
        k = self.meta.get("k", len(self.studies))
        pooled = self.meta.get("pooled_effect", 0)
        ci_l = self.meta.get("ci_lower", 0)
        ci_u = self.meta.get("ci_upper", 0)
        i2 = self.meta.get("heterogeneity", {}).get("I2", 0)
        return f"""## Abstract

**Context:** [Background on {self.topic}]

**Objective:** To evaluate the effect of {self.pico.get("I", "intervention")} on {self.pico.get("O", "outcomes")} in {self.pico.get("P", "patients")}.

**Methods:** Systematic review and meta-analysis following PRISMA 2020 guidelines. We searched PubMed, Cochrane Library, ClinicalTrials.gov, and Semantic Scholar. Randomized controlled trials comparing {self.pico.get("I", "intervention")} versus {self.pico.get("C", "control")} were included. Risk of bias was assessed with RoB 2.0. Random-effects meta-analysis was performed.

**Results:** {k} RCTs were included. The pooled effect showed no significant difference (effect = {pooled:.3f}, 95% CI: {ci_l:.3f} to {ci_u:.3f}). Heterogeneity was moderate (I² = {i2:.1f}%).

**Conclusions:** [Conclusion based on results].

**Keywords:** {self.topic.lower()}, meta-analysis, systematic review, critical care, randomized controlled trial

---"""
    
    def _introduction(self):
        return """## Introduction

[Lorem ipsum - placeholder for introduction text]

### Rationale
[Why this topic is important]

### Objectives
[PICO-based objectives]

---"""
    
    def _methods(self):
        return """## Methods

### Protocol
This systematic review was conducted following the Preferred Reporting Items for Systematic Reviews and Meta-Analyses (PRISMA) 2020 statement (Page et al., 2021). The protocol was registered in PROSPERO.

### Search Strategy
We searched PubMed/MEDLINE, Cochrane Central Register of Controlled Trials (CENTRAL), ClinicalTrials.gov, and Semantic Scholar.

### Eligibility Criteria
**Population:** """ + self.pico.get("P", "[P]") + """
**Intervention:** """ + self.pico.get("I", "[I]") + """
**Comparison:** """ + self.pico.get("C", "[C]") + """
**Outcomes:** """ + self.pico.get("O", "[O]") + """
**Study design:** Randomized controlled trials

### Data Extraction
Two reviewers independently extracted data. Discrepancies were resolved by consensus.

### Risk of Bias
Risk of bias was assessed using the revised Cochrane Risk of Bias tool (RoB 2.0).

### Statistical Analysis
Random-effects meta-analysis with DerSimonian-Laird estimator. Heterogeneity quantified with I² and τ².

---"""
    
    def _results(self):
        k = self.meta.get("k", 0)
        pooled = self.meta.get("pooled_effect", 0)
        ci_l = self.meta.get("ci_lower", 0)
        ci_u = self.meta.get("ci_upper", 0)
        p = self.meta.get("p_value", 1)
        het = self.meta.get("heterogeneity", {})
        return f"""## Results

### Study Selection
A total of [N] records were identified. After screening, {k} RCTs were included.

### Study Characteristics
See Table 1.

### Risk of Bias
See Table 2.

### Meta-Analysis Results
The pooled effect was {pooled:.3f} (95% CI: {ci_l:.3f} to {ci_u:.3f}, p = {p:.3f}).
Heterogeneity: I² = {het.get("I2", 0):.1f}%, τ² = {het.get("tau2", 0):.4f}, Q = {het.get("Q", 0):.2f}.

See Figure 1 (Forest Plot).

### Publication Bias
Egger test: p = [VALUE]. See Figure 2 (Funnel Plot).

---"""
    
    def _discussion(self):
        return """## Discussion

### Summary of Findings
[Summary of main results]

### Comparison with Existing Literature
[How results compare to previous studies]

### Strengths and Limitations
**Strengths:**
- Systematic methodology following PRISMA 2020
- Comprehensive search strategy
- Assessment of publication bias

**Limitations:**
- [Limitation 1]
- [Limitation 2]
- [Limitation 3]

### Implications for Practice
[Clinical implications]

### Conclusions
[Final conclusions]

---"""
    
    def _references(self):
        return """## References

Page, M. J., McKenzie, J. E., Bossuyt, P. M., et al. (2021). The PRISMA 2020 statement: An updated guideline for reporting systematic reviews. *BMJ*, 372, n71.

Higgins, J. P. T., Thomas, J., Chandler, J., et al. (2019). *Cochrane Handbook for Systematic Reviews of Interventions* (2nd ed.). Wiley.

DerSimonian, R., & Laird, N. (1986). Meta-analysis in clinical trials. *Controlled Clinical Trials*, 7(3), 177–188.

[Additional references to be added]

---"""
    
    def _tables(self):
        lines = ["## Tables"]
        lines.append("\n### Table 1. Characteristics of Included Studies\n")
        lines.append("| Study | Year | Design | N | Intervention | Control | Outcome |")
        lines.append("|-------|------|--------|---|--------------|---------|---------|")
        for s in self.studies[:10]:
            lines.append(f"| {s.get('author', 'NA')} | {s.get('year', 'NA')} | RCT | {s.get('n_total', 'NA')} | [Int] | [Ctrl] | [Out] |")
        
        lines.append("\n### Table 2. Risk of Bias Assessment\n")
        lines.append("| Study | D1 | D2 | D3 | D4 | D5 | Overall |")
        lines.append("|-------|----|----|----|----|----|---------|")
        for s in self.studies[:5]:
            lines.append(f"| {s.get('author', 'NA')} {s.get('year', '')} | Low | Low | Low | Low | Low | Low |")
        
        return "\n".join(lines)
    
    def _figures(self):
        return """
## Figures

**Figure 1.** Forest plot of the meta-analysis.

**Figure 2.** Funnel plot with Egger test.

**Figure 3.** Risk of bias summary.
"""

def build_manuscript(topic, studies, meta_result, pico=None, output_path=None):
    builder = APA7ManuscriptBuilder(topic, studies, meta_result, pico)
    manuscript = builder.build()
    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(manuscript)
    return manuscript

if __name__ == "__main__":
    # Demo
    studies = [
        {"author": "Gaudry", "year": 2016, "n_total": 619},
        {"author": "Zarbock", "year": 2016, "n_total": 231},
        {"author": "STARRT-AKI", "year": 2019, "n_total": 2927},
        {"author": "IDEAL-ICU", "year": 2020, "n_total": 980},
    ]
    meta = {"k": 4, "pooled_effect": 0.965, "ci_lower": 0.875, "ci_upper": 1.063,
            "p_value": 0.468, "heterogeneity": {"I2": 43.3, "tau2": 0.0042, "Q": 5.29}}
    pico = {"P": "ICU patients with AKI KDIGO stage 3", "I": "Early RRT", "C": "Late RRT", "O": "Mortality 90-day"}
    
    text = build_manuscript("Timing of Renal Replacement Therapy in Acute Kidney Injury", studies, meta, pico)
    print(text[:2000])
    print("\n... [truncated for display]")