#!/usr/bin/env python3
"""
Martyria v1.5 - Parallel Multi-Database Search Engine
Busqueda simultanea en PubMed + Cochrane + ClinicalTrials.gov + Semantic Scholar
"""

import requests
import json
import time
import concurrent.futures
from datetime import datetime
from typing import List, Dict, Optional, Set
from dataclasses import dataclass, asdict
import xml.etree.ElementTree as ET

# APIs
PUBMED_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
SEMANTIC_SCHOLAR_BASE = "https://api.semanticscholar.org/graph/v1"
CLINICALTRIALS_API = "https://clinicaltrials.gov/api/v2/studies"

EMAIL = "drpablo.hospita@gmail.com"
TOOL = "martyria"


@dataclass
class UnifiedArticle:
    """Articulo unificado de cualquier fuente"""
    id: str
    title: str
    authors: List[str]
    year: str
    journal: str
    abstract: str
    doi: str
    pmid: str
    nct_id: str
    source: str  # pubmed, cochrane, clinicaltrials, semanticscholar
    study_type: str
    url: str
    citation_count: int
    reference_count: int
    influential_citation_count: int
    score: float = 0.0  # Score de relevancia
    mesh_terms: List[str] = None
    
    def __post_init__(self):
        if self.mesh_terms is None:
            self.mesh_terms = []


class ParallelSearcher:
    """Buscador paralelo multi-base"""
    
    def __init__(self, email: str = EMAIL, max_workers: int = 4):
        self.email = email
        self.max_workers = max_workers
        self.last_request_time = {}
        self.min_interval = 0.34
        self.results = {}
        
    def _rate_limit(self, source: str, seconds: float = 0.34):
        """Rate limit por fuente"""
        now = time.time()
        last = self.last_request_time.get(source, 0)
        if now - last < seconds:
            time.sleep(seconds - (now - last))
        self.last_request_time[source] = time.time()
    
    def search_all(self, topic: str, max_results: int = 50, years_back: int = 5,
                    year_start: int = None, year_end: int = None) -> Dict:
        """
        Busca en paralelo en todas las bases
        
        Args:
            topic: Tema de busqueda
            max_results: Maximo por base
            years_back: Anos hacia atras (usado si no se especifica year_start/year_end)
            year_start: Año inicial del rango (opcional)
            year_end: Año final del rango (opcional)
        
        Returns:
            Dict con resultados unificados y por fuente
        """
        current_year = datetime.now().year
        
        # Si se especifica rango exacto, usarlo
        if year_start is not None and year_end is not None:
            min_year = year_start
            max_year = year_end
        else:
            min_year = current_year - years_back
            max_year = current_year
        
        print(f"[Martyria v1.5] Iniciando busqueda paralela")
        print(f"Topic: {topic}")
        print(f"Periodo: {min_year}-{max_year}")
        print(f"Workers: {self.max_workers}")
        print("=" * 70)
        
        start_time = time.time()
        
        # Ejecutar busquedas en paralelo
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(self._search_pubmed, topic, max_results, min_year, max_year): "pubmed",
                executor.submit(self._search_cochrane, topic, max_results, min_year, max_year): "cochrane",
                executor.submit(self._search_clinicaltrials, topic, max_results, min_year, max_year): "clinicaltrials",
                executor.submit(self._search_semantic_scholar, topic, max_results, min_year, max_year): "semanticscholar",
            }
            
            for future in concurrent.futures.as_completed(futures):
                source = futures[future]
                try:
                    results = future.result()
                    self.results[source] = results
                    print(f"\n[{source.upper()}] {len(results)} resultados")
                except Exception as e:
                    print(f"\n[{source.upper()}] ERROR: {e}")
                    self.results[source] = []
        
        # Unificar y rankear
        unified = self._unify_and_rank()
        
        elapsed = time.time() - start_time
        
        print("\n" + "=" * 70)
        print(f"BUSQUEDA PARALELA COMPLETADA en {elapsed:.2f}s")
        print(f"Total unico: {len(unified)} articulos")
        for source, results in self.results.items():
            print(f"  - {source}: {len(results)}")
        print("=" * 70)
        
        return {
            "unified": [asdict(a) for a in unified],
            "by_source": {k: [asdict(a) for a in v] for k, v in self.results.items()},
            "total_unique": len(unified),
            "total_by_source": {k: len(v) for k, v in self.results.items()},
            "elapsed_seconds": round(elapsed, 2)
        }
    
    def _search_pubmed(self, topic: str, max_results: int, min_year: int, max_year: int) -> List[UnifiedArticle]:
        """Busca en PubMed E-utilities"""
        from scripts.search_pubmed import PubMedSearcher, translate_topic_to_mesh
        
        search_query = translate_topic_to_mesh(topic)
        full_query = f"({search_query}) AND ({min_year}:{max_year}[pdat])"
        
        self._rate_limit("pubmed")
        
        try:
            searcher = PubMedSearcher(email=self.email)
            articles = searcher.search(search_query, max_results=max_results, years_back=max_year - min_year)
            
            unified = []
            for art in articles:
                unified.append(UnifiedArticle(
                    id=art.get("pmid", ""),
                    title=art.get("title", ""),
                    authors=art.get("authors", []),
                    year=art.get("year", ""),
                    journal=art.get("journal", ""),
                    abstract=art.get("abstract", "")[:500],
                    doi=art.get("doi", ""),
                    pmid=art.get("pmid", ""),
                    nct_id="",
                    source="pubmed",
                    study_type=art.get("study_type", "Other"),
                    url=f"https://pubmed.ncbi.nlm.nih.gov/{art.get('pmid', '')}/",
                    citation_count=0,
                    reference_count=0,
                    influential_citation_count=0,
                    mesh_terms=art.get("mesh_terms", [])
                ))
            
            return unified
            
        except Exception as e:
            print(f"PubMed error: {e}")
            return []
    
    def _search_cochrane(self, topic: str, max_results: int, min_year: int, max_year: int) -> List[UnifiedArticle]:
        """Busca en Cochrane via PubMed (Cochrane esta indexada en PubMed)"""
        
        search_query = f"({topic}) AND (cochrane database syst rev[Journal]) AND ({min_year}:{max_year}[pdat])"
        
        self._rate_limit("cochrane", 0.5)
        
        try:
            url = f"{PUBMED_BASE}/esearch.fcgi"
            params = {
                "db": "pubmed",
                "term": search_query,
                "retmax": max_results,
                "retmode": "json",
                "email": self.email,
                "tool": TOOL
            }
            
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            pmids = data.get("esearchresult", {}).get("idlist", [])
            
            if not pmids:
                return []
            
            # Obtener resumenes
            self._rate_limit("cochrane", 0.5)
            
            summary_url = f"{PUBMED_BASE}/esummary.fcgi"
            summary_params = {
                "db": "pubmed",
                "id": ",".join(pmids),
                "retmode": "json",
                "email": self.email,
                "tool": TOOL
            }
            
            response = requests.get(summary_url, params=summary_params, timeout=30)
            response.raise_for_status()
            summary_data = response.json()
            
            unified = []
            for pmid in pmids:
                if pmid in summary_data.get("result", {}):
                    art = summary_data["result"][pmid]
                    unified.append(UnifiedArticle(
                        id=pmid,
                        title=art.get("title", ""),
                        authors=[a.get("name", "") for a in art.get("authors", [])],
                        year=art.get("pubdate", "").split()[0] if art.get("pubdate") else "",
                        journal="Cochrane Database of Systematic Reviews",
                        abstract="",
                        doi=art.get("elocationid", "").replace("doi: ", "") if art.get("elocationid") else "",
                        pmid=pmid,
                        nct_id="",
                        source="cochrane",
                        study_type="Systematic Review",
                        url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                        citation_count=0,
                        reference_count=0,
                        influential_citation_count=0
                    ))
            
            return unified
            
        except Exception as e:
            print(f"Cochrane error: {e}")
            return []
    
    def _search_clinicaltrials(self, topic: str, max_results: int, min_year: int, max_year: int) -> List[UnifiedArticle]:
        """Busca en ClinicalTrials.gov API v2"""
        
        search_query = topic.replace("AND", " ").replace("OR", " ")
        
        self._rate_limit("clinicaltrials", 0.5)
        
        try:
            url = CLINICALTRIALS_API
            params = {
                "query.term": search_query,
                "pageSize": min(max_results, 100),
                "filter.overallStatus": "COMPLETED",
                "filter.advanced": f"AREA[StartDate]RANGE[{min_year}-01-01, MAX]"
            }
            
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            unified = []
            for study in data.get("studies", []):
                protocol = study.get("protocolSection", {})
                identification = protocol.get("identificationModule", {})
                status = protocol.get("statusModule", {})
                design = protocol.get("designModule", {})
                sponsor = protocol.get("sponsorCollaboratorsModule", {})
                
                nct_id = identification.get("nctId", "")
                
                unified.append(UnifiedArticle(
                    id=nct_id,
                    title=identification.get("briefTitle", ""),
                    authors=[sponsor.get("leadSponsor", {}).get("name", "")],
                    year=status.get("startDate", {}).get("date", "")[:4] if status.get("startDate") else "",
                    journal="ClinicalTrials.gov",
                    abstract=identification.get("officialTitle", "")[:200],
                    doi="",
                    pmid="",
                    nct_id=nct_id,
                    source="clinicaltrials",
                    study_type=design.get("studyType", ""),
                    url=f"https://clinicaltrials.gov/study/{nct_id}",
                    citation_count=0,
                    reference_count=0,
                    influential_citation_count=0
                ))
            
            return unified
            
        except Exception as e:
            print(f"ClinicalTrials error: {e}")
            return []
    
    def _search_semantic_scholar(self, topic: str, max_results: int, min_year: int, max_year: int) -> List[UnifiedArticle]:
        """Busca en Semantic Scholar API"""
        
        self._rate_limit("semanticscholar", 0.2)
        
        try:
            url = f"{SEMANTIC_SCHOLAR_BASE}/paper/search"
            params = {
                "query": topic,
                "fields": "title,authors,year,abstract,citationCount,referenceCount,influentialCitationCount,externalIds,journal",
                "limit": max_results,
                "publicationDateOrYear": f"{min_year}:{max_year}"
            }
            
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            unified = []
            for paper in data.get("data", []):
                external_ids = paper.get("externalIds", {})
                
                unified.append(UnifiedArticle(
                    id=paper.get("paperId", ""),
                    title=paper.get("title", ""),
                    authors=[a.get("name", "") for a in paper.get("authors", [])],
                    year=str(paper.get("year", "")),
                    journal=paper.get("journal", {}).get("name", "") if paper.get("journal") else "",
                    abstract=paper.get("abstract", "")[:500] if paper.get("abstract") else "",
                    doi=external_ids.get("DOI", ""),
                    pmid=external_ids.get("PubMed", ""),
                    nct_id="",
                    source="semanticscholar",
                    study_type="Other",
                    url=f"https://www.semanticscholar.org/paper/{paper.get('paperId', '')}",
                    citation_count=paper.get("citationCount", 0),
                    reference_count=paper.get("referenceCount", 0),
                    influential_citation_count=paper.get("influentialCitationCount", 0)
                ))
            
            return unified
            
        except Exception as e:
            print(f"Semantic Scholar error: {e}")
            return []
    
    def _unify_and_rank(self) -> List[UnifiedArticle]:
        """Unifica resultados de todas las fuentes y rankea por relevancia"""
        
        # Deduplicar por PMID o DOI
        seen_pmids = set()
        seen_dois = set()
        unified = []
        
        # Prioridad: PubMed > Cochrane > Semantic Scholar > ClinicalTrials
        priority_order = ["pubmed", "cochrane", "semanticscholar", "clinicaltrials"]
        
        for source in priority_order:
            for article in self.results.get(source, []):
                # Deduplicar
                key = None
                if article.pmid:
                    key = ("pmid", article.pmid)
                elif article.doi:
                    key = ("doi", article.doi)
                else:
                    key = ("id", article.id)
                
                if key in seen_pmids or key in seen_dois:
                    continue
                
                if key[0] == "pmid":
                    seen_pmids.add(key)
                elif key[0] == "doi":
                    seen_dois.add(key)
                
                # Calcular score de relevancia
                article.score = self._calculate_relevance_score(article)
                unified.append(article)
        
        # Ordenar por score
        unified.sort(key=lambda x: x.score, reverse=True)
        
        return unified
    
    def _calculate_relevance_score(self, article: UnifiedArticle) -> float:
        """Calcula score de relevancia (0-100)"""
        score = 0.0
        
        # Factor 1: Tipo de estudio (mayor puntaje para estudios de mayor nivel)
        study_type_scores = {
            "Meta-analysis": 25,
            "Systematic Review": 25,
            "RCT": 20,
            "Clinical Guideline": 20,
            "Cohort Study": 15,
            "Case-Control": 10,
            "Cross-Sectional": 5,
            "Other": 3
        }
        score += study_type_scores.get(article.study_type, 3)
        
        # Factor 2: Citaciones (Semantic Scholar)
        if article.citation_count > 0:
            score += min(article.citation_count / 10, 15)
        
        # Factor 3: Influencia (citas influyentes)
        if article.influential_citation_count > 0:
            score += min(article.influential_citation_count / 5, 10)
        
        # Factor 4: Recencia
        try:
            year = int(article.year)
            current_year = datetime.now().year
            if year >= current_year - 2:
                score += 15  # Muy reciente
            elif year >= current_year - 5:
                score += 10  # Reciente
            elif year >= current_year - 10:
                score += 5   # Moderado
        except (ValueError, TypeError):
            pass
        
        # Factor 5: Fuente
        source_scores = {
            "pubmed": 5,
            "cochrane": 5,
            "semanticscholar": 3,
            "clinicaltrials": 2
        }
        score += source_scores.get(article.source, 0)
        
        # Factor 6: Abstract disponible
        if article.abstract and len(article.abstract) > 100:
            score += 5
        
        return min(100, score)


def main():
    import sys
    
    if len(sys.argv) < 2:
        print("Uso: python3 search_parallel.py \"tema de busqueda\"")
        sys.exit(1)
    
    topic = sys.argv[1]
    
    searcher = ParallelSearcher(max_workers=4)
    results = searcher.search_all(topic, max_results=15, years_back=5)
    
    # Guardar
    output_file = f"parallel_search_{topic.replace(' ', '_')}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\nResultados guardados: {output_file}")
    print(f"Total unico: {results['total_unique']}")
    
    # Mostrar top 10
    print("\nTop 10 por relevancia:")
    for i, art in enumerate(results['unified'][:10], 1):
        print(f"{i}. [{art['source']}] Score: {art['score']:.1f}")
        print(f"   {art['title'][:80]}...")
        print(f"   Tipo: {art['study_type']} | Citas: {art['citation_count']}")
        print()


if __name__ == "__main__":
    main()
