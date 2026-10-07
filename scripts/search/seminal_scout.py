#!/usr/bin/env python3
"""
Martyria v3.4 - Seminal Study Scout (API-Integrated)
=====================================================
Busqueda web automatica de estudios seminales via Tavily API.
Extraccion robusta de datos cuantitativos.

Uso: python3 seminal_scout_v34.py '<tema>'
"""

import json
import re
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import requests
import time

# Tavily API Configuration
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "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")
TAVILY_API_URL = "https://api.tavily.com/search"


@dataclass
class StudyData:
    """Datos estructurados de un estudio clinico"""
    name: str
    title: str = ""
    pmid: str = ""
    doi: str = ""
    journal: str = ""
    year: int = 0
    study_type: str = "RCT"
    n_total: int = 0
    n_intervention: int = 0
    n_control: int = 0
    intervention: str = ""
    comparator: str = ""
    primary_outcome: str = ""
    effect_measure: str = ""
    effect_value: float = 0.0
    ci_lower: float = 0.0
    ci_upper: float = 0.0
    p_value: float = 0.0
    nnt: Optional[int] = None
    mortality_intervention: Optional[float] = None
    mortality_control: Optional[float] = None
    mortality_timepoint: str = ""
    key_findings: List[str] = None
    sources: List[str] = None
    
    def __post_init__(self):
        if self.key_findings is None:
            self.key_findings = []
        if self.sources is None:
            self.sources = []
    
    def to_dict(self) -> Dict:
        return asdict(self)


class SeminalStudyScout:
    """Scouting de estudios seminales con acceso directo a Tavily API"""
    
    # Base de datos exhaustiva
    SEMINAL_DATABASE = {
        "aki": ["AKIKI", "ELAIN", "IDEAL-ICU", "STARRT-AKI", "AKIKI-2", "BICAR-ICU", "RUBY", "FST"],
        "renal replacement": ["AKIKI", "ELAIN", "IDEAL-ICU", "STARRT-AKI", "AKIKI-2", "BICAR-ICU"],
        "sepsis": ["ARISE", "ProCESS", "ProMISe", "ADRENAL", "APROCCHSS", "CLASSIC", "CLOVERS", "VANISH"],
        "septic shock": ["ARISE", "ProCESS", "ProMISe", "ADRENAL", "APROCCHSS", "VANISH", "ATHOS-3"],
        "ards": ["PROSEVA", "ARDSNet", "OSCILLATE", "ROSE", "EPVent-2", "ACURASYS", "FACTT"],
        "prone positioning": ["PROSEVA", "PRONES"],
        "sedation": ["MIDEX", "PRODEX", "DahLIA", "SPICE-3"],
        "delirium": ["ABCDE", "PREVENTION", "SAGES", "MIND-USA"],
        "fluid resuscitation": ["FEAST", "CLASSIC", "CLOVERS", "CRYSTMAS", "CHEST", "6S", "ALBIOS", "CRISTAL"],
        "vasopressors": ["VANISH", "ATHOS-3", "ANGST"],
        "corticosteroids sepsis": ["ADRENAL", "APROCCHSS", "CORTICUS", "HYDROXX"],
        "tranexamic acid": ["CRASH-2", "WOMAN", "HALT-IT", "CRASH-3"],
        "therapeutic hypothermia": ["TTM", "TTM2", "HYPERION", "POLAR"],
        "blood transfusion": ["TRICC", "TRISS", "TITRe2", "ABLE"],
        "mechanical ventilation": ["ACURASYS", "ROSE", "FACTT", "EPVent-2"],
        "ecmo": ["EOLIA", "CESAR", "ECMO-ARDS"],
        "nutrition": ["EDEN", "PermiT", "TARGET", "EPaNIC"],
        "glucose control": ["NICE-SUGAR", "GLUCONTROL", "VISEP"],
        "bicarbonate": ["BICAR-ICU"],
        "status epilepticus": ["ESETT", "ConSEPT"],
        "stroke": ["MR CLEAN", "EXTEND-IA", "SWIFT PRIME", "DAWN"],
        "cardiac arrest": ["TTM", "TTM2", "ARREST", "BOX", "COMACARE"],
        "cardiogenic shock": ["CULPRIT-SHOCK", "ECMO-CS", "DOREMI", "IABP-SHOCK-II"],
        "pneumonia vap": ["HAPPI", "INHALE", "CURE"],
    }
    
    GUIDELINES = {
        "aki": ["KDIGO-AKI", "ADQI", "SCCM-CRRT"],
        "sepsis": ["SSC-2021", "SEP-1"],
        "ards": ["ATS-ERS-2017", "SCCM-ARDS"],
        "sedation": ["SCCM-PADIS-2018"],
        "nutrition": ["SCCM-ASPEN-2016", "ESPEN"],
    }
    
    def __init__(self, topic: str, output_dir: Path = None):
        self.topic = topic.lower()
        self.output_dir = output_dir or Path(".")
        self.studies: Dict[str, StudyData] = {}
        self.raw_results: List[Dict] = []
    
    def scout(self) -> Dict[str, StudyData]:
        """Pipeline completo de scouting automatico"""
        print(f"\n{'='*70}")
        print(f"MARTYRIA v3.4 - SEMINAL STUDY SCOUT")
        print(f"Tema: {self.topic}")
        print(f"{'='*70}\n")
        
        # 1. Identificar estudios relevantes
        relevant = self._identify_relevant_studies()
        print(f"Estudios a buscar: {', '.join(relevant)}")
        
        # 2. Ejecutar busquedas web
        self._execute_searches(relevant)
        
        # 3. Extraer datos de resultados
        self._extract_all_studies()
        
        # 4. Guardar
        self._save_results()
        
        return self.studies
    
    def _identify_relevant_studies(self) -> List[str]:
        """Identifica estudios seminales para el tema"""
        relevant = []
        for key, studies in self.SEMINAL_DATABASE.items():
            if key in self.topic or any(word in self.topic for word in key.split()):
                relevant.extend(studies)
        return list(set(relevant))
    
    def _execute_searches(self, studies: List[str]):
        """Ejecuta busquedas Tavily API - una por estudio para datos especificos"""
        print(f"\nEjecutando busquedas web...")
        
        # Buscar cada estudio individualmente para obtener datos especificos
        for i, study_name in enumerate(studies[:6], 1):  # Max 6 estudios
            query = f"{study_name} trial N total mortality results PMID"
            print(f"\n[{i}/{min(len(studies), 6)}] Buscando: {study_name}")
            results = self._tavily_search(query, max_results=3)
            self.raw_results.extend(results)
            time.sleep(1)
        
        # Meta-analisis
        query2 = f"meta-analysis {self.topic} OR RR pooled"
        print(f"\n[{min(len(studies), 6)+1}] Buscando meta-analisis...")
        results2 = self._tavily_search(query2, max_results=3)
        self.raw_results.extend(results2)
        
        print(f"\nTotal resultados: {len(self.raw_results)}")
    
    def _tavily_search(self, query: str, max_results: int = 10) -> List[Dict]:
        """Busqueda via Tavily API"""
        try:
            payload = {
                "api_key": TAVILY_API_KEY,
                "query": query,
                "max_results": max_results,
                "search_depth": "advanced",
                "include_answer": True,
            }
            
            response = requests.post(TAVILY_API_URL, json=payload, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                results = []
                
                for result in data.get("results", []):
                    results.append({
                        "title": result.get("title", ""),
                        "url": result.get("url", ""),
                        "content": result.get("content", ""),
                        "score": result.get("score", 0)
                    })
                
                if "answer" in data and data["answer"]:
                    results.append({
                        "title": "AI Summary",
                        "url": "",
                        "content": data["answer"],
                        "score": 1.0
                    })
                
                print(f"  [OK] {len(results)} resultados")
                return results
            else:
                print(f"  [WARN] API error {response.status_code}")
                return []
        except Exception as e:
            print(f"  [WARN] Error: {e}")
            return []
    
    def _extract_all_studies(self):
        """Extrae datos de todos los estudios de los resultados"""
        relevant = self._identify_relevant_studies()
        
        for study_name in relevant:
            study = self._extract_single_study(study_name)
            if study and (study.n_total > 0 or study.title or study.key_findings):
                self.studies[study_name] = study
    
    def _extract_single_study(self, name: str) -> Optional[StudyData]:
        """Extrae datos de un estudio especifico de sus propios resultados"""
        study = StudyData(name=name)
        
        # Solo usar resultados que mencionen explicitamente este estudio
        # y no otros estudios principales (para evitar contaminacion)
        all_content = ""
        for result in self.raw_results:
            content = result.get("content", "") + " " + result.get("title", "")
            
            # Verificar que menciona el estudio buscado
            if name.lower() not in content.lower():
                continue
            
            # Verificar que NO menciona otros estudios seminales (contaminacion)
            other_studies = [s for s in self._identify_relevant_studies() if s != name]
            mentions_other = any(s.lower() in content.lower() for s in other_studies[:3])
            
            # Preferir resultados que mencionen solo este estudio
            if not mentions_other or name.lower() in result.get("title", "").lower():
                all_content += " " + content
                study.sources.append(result.get("url", ""))
        
        if not all_content:
            return None
        
        # Extraer datos
        self._extract_metadata(study, all_content)
        self._extract_quantitative(study, all_content)
        self._extract_mortality(study, all_content)
        self._extract_findings(study, all_content)
        
        return study
    
    def _extract_metadata(self, study: StudyData, content: str):
        """Extrae metadatos basicos"""
        # Titulo
        title_match = re.search(r'(?:The\s+)?' + re.escape(study.name) + r'\s+(?:trial|study).*?(?:for|of|in)\s+(.{10,100}?)(?:\.|\n)', content, re.I)
        if title_match:
            study.title = title_match.group(1).strip()
        
        # Journal
        journals = [
            (r'N Engl J Med|New England Journal of Medicine', 'N Engl J Med'),
            (r'JAMA', 'JAMA'),
            (r'Lancet', 'Lancet'),
            (r'Crit(?:ical)?\s+C(?:are)?', 'Crit Care'),
            (r'Intensive Care Med', 'Intensive Care Med'),
            (r'Chest', 'Chest'),
            (r'Am J Respir Crit Care Med', 'Am J Respir Crit Care Med'),
            (r'BMJ', 'BMJ'),
        ]
        for pattern, journal_name in journals:
            if re.search(pattern, content, re.I):
                study.journal = journal_name
                break
        
        # Year
        year_match = re.search(r'\b(20\d{2})\b', content)
        if year_match:
            year = int(year_match.group(1))
            if 2000 <= year <= 2030:
                study.year = year
        
        # PMID
        pmid_match = re.search(r'PMID[\s:]*(\d+)', content)
        if pmid_match:
            study.pmid = pmid_match.group(1)
        
        # DOI
        doi_match = re.search(r'(10\.\d{4,}[\w./-]+)', content)
        if doi_match:
            study.doi = doi_match.group(1)
    
    def _extract_quantitative(self, study: StudyData, content: str):
        """Extrae datos cuantitativos"""
        # N total
        n_patterns = [
            r'(?:[Nn]\s*=\s*(\d{3,4}))',
            r'(\d{3,4})\s+(?:patients|participants|subjects)\s+(?:were\s+)?(?:randomly\s+)?(?:assigned|allocated|enrolled)',
            r'(?:randomi[sz]ed|enrolled|recruited)\s+(?:a\s+total\s+of\s+)?(\d{3,4})',
            r'(?:total\s+of\s+)(\d{3,4})',
        ]
        
        for pattern in n_patterns:
            match = re.search(pattern, content, re.I)
            if match:
                n = int(match.group(1))
                if 50 <= n <= 50000:
                    study.n_total = n
                    break
        
        # Grupos
        group_patterns = [
            r'(?:early|intervention)[\s\w]*?\(n\s*=\s*(\d+)\)',
            r'(?:delayed|control|standard)[\s\w]*?\(n\s*=\s*(\d+)\)',
        ]
        group_ns = []
        for pattern in group_patterns:
            match = re.search(pattern, content, re.I)
            if match:
                group_ns.append(int(match.group(1)))
        if len(group_ns) >= 2:
            study.n_intervention = group_ns[0]
            study.n_control = group_ns[1]
        if study.n_total == 0 and study.n_intervention > 0 and study.n_control > 0:
            study.n_total = study.n_intervention + study.n_control
        
        # OR/RR/HR
        effect_patterns = [
            r'(OR|RR|HR)[\s]*[=:\s]*(\d+\.?\d*)\s*\(?95%\s*CI[:\s]*?(\d+\.?\d*)\s*[-–,\s]+\s*(\d+\.?\d*)',
            r'(OR|RR|HR)[\s]*[=:\s]*(\d+\.?\d*)\s*\((\d+\.?\d*)\s*[-–,\s]+\s*(\d+\.?\d*)\)',
        ]
        for pattern in effect_patterns:
            match = re.search(pattern, content, re.I)
            if match:
                study.effect_measure = match.group(1).upper()
                study.effect_value = float(match.group(2))
                study.ci_lower = float(match.group(3))
                study.ci_upper = float(match.group(4))
                break
        
        # p-value
        p_match = re.search(r'[Pp][\s]*[=<](\d+\.?\d*(?:[eE][+-]?\d+)?)', content)
        if p_match:
            study.p_value = float(p_match.group(1))
    
    def _extract_mortality(self, study: StudyData, content: str):
        """Extrae datos de mortalidad - busca porcentajes cerca de palabras clave"""
        
        # Encontrar posiciones de palabras clave de mortalidad
        keywords = ['mortality', 'death', 'died', 'survival']
        all_percentages = []
        
        for keyword in keywords:
            # Buscar todas las ocurrencias
            for match in re.finditer(keyword, content, re.I):
                # Extraer contexto de ±200 chars alrededor
                start = max(0, match.start() - 100)
                end = min(len(content), match.end() + 200)
                section = content[start:end]
                
                # Encontrar todos los porcentajes en esta seccion
                percentages = re.findall(r'(\d+\.?\d*)\s*%', section)
                for p in percentages:
                    val = float(p)
                    if 10 <= val <= 90:  # Filtrar valores razonables
                        all_percentages.append(val)
        
        # Si encontramos al menos 2 porcentajes, asumir que son intervencion vs control
        if len(all_percentages) >= 2:
            # Tomar los primeros 2 (generalmente intervencion primero)
            study.mortality_intervention = all_percentages[0]
            study.mortality_control = all_percentages[1]
        
        # Timepoint
        tp_match = re.search(r'(?:mortality|death)\s+(?:at\s+)?(day\s+\d+|\d+-day|30-day|60-day|90-day|28-day|in-hospital)', content, re.I)
        if tp_match:
            study.mortality_timepoint = tp_match.group(1)
    
    def _extract_findings(self, study: StudyData, content: str):
        """Extrae hallazgos clave"""
        patterns = [
            r'(?:did not|no|not)\s+(?:significant|reduce|improve|show|difference)',
            r'(?:significantly|significant)\s+(?:reduced|increased|improved|decreased)',
            r'(?:similar|comparable|no\s+difference|no\s+benefit)',
            r'(?:lower|higher|greater|less)\s+(?:mortality|risk|rate)',
        ]
        
        sentences = re.split(r'[.\n]', content)
        for sentence in sentences:
            for pattern in patterns:
                if re.search(pattern, sentence, re.I):
                    clean = sentence.strip()
                    if 20 < len(clean) < 300 and clean not in study.key_findings:
                        study.key_findings.append(clean)
                        break
        
        study.key_findings = list(dict.fromkeys(study.key_findings))[:5]
    
    def _save_results(self):
        """Guarda resultados"""
        output = {
            "topic": self.topic,
            "timestamp": datetime.now().isoformat(),
            "studies_found": len(self.studies),
            "studies": {k: v.to_dict() for k, v in self.studies.items()},
        }
        
        output_file = self.output_dir / f"seminal_{self.topic.replace(' ', '_')}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        # Markdown
        md = self._generate_markdown()
        md_file = self.output_dir / f"seminal_{self.topic.replace(' ', '_')}.md"
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(md)
        
        print(f"\n[OK] JSON: {output_file}")
        print(f"[OK] Markdown: {md_file}")
    
    def _generate_markdown(self) -> str:
        """Genera resumen markdown"""
        md = f"""# Estudios Seminales: {self.topic}

**Fecha**: {datetime.now().strftime('%Y-%m-%d')}
**Total**: {len(self.studies)} estudios

---

"""
        for name, study in sorted(self.studies.items(), key=lambda x: x[1].year, reverse=True):
            md += f"""## {name}

| Caracteristica | Valor |
|---------------|-------|
| **Titulo** | {study.title or 'N/A'} |
| **Revista** | {study.journal or 'N/A'} {study.year or ''} |
| **PMID** | {study.pmid or 'N/A'} |
| **DOI** | {study.doi or 'N/A'} |
| **N total** | {study.n_total or 'N/A'} |
| **N intervencion** | {study.n_intervention or 'N/A'} |
| **N control** | {study.n_control or 'N/A'} |

"""
            if study.effect_measure:
                md += f"**Resultado**: {study.effect_measure} {study.effect_value} (95% CI: {study.ci_lower}-{study.ci_upper}), p={study.p_value}\n\n"
            
            if study.mortality_intervention is not None:
                md += f"**Mortalidad** ({study.mortality_timepoint}): {study.mortality_intervention}% vs {study.mortality_control}%\n\n"
            
            if study.key_findings:
                md += "**Hallazgos**:\n"
                for finding in study.key_findings[:3]:
                    md += f"- {finding}\n"
                md += "\n"
            
            md += "---\n\n"
        
        return md


def main():
    import sys
    if len(sys.argv) < 2:
        print("Uso: python3 seminal_scout_v34.py '<tema>'")
        print("Ejemplo: python3 seminal_scout_v34.py 'timing RRT AKI'")
        sys.exit(1)
    
    topic = sys.argv[1]
    scout = SeminalStudyScout(topic)
    studies = scout.scout()
    
    print(f"\n{'='*70}")
    print(f"COMPLETADO: {len(studies)} estudios encontrados")
    print(f"{'='*70}")
    for name, study in studies.items():
        print(f"  {name}: N={study.n_total}, {study.journal} {study.year}")


if __name__ == "__main__":
    main()
