#!/usr/bin/env python3
"""
Martyria - PubMed Search Engine
Busqueda real en PubMed via NCBI E-utilities
"""

import requests
import json
import sys
import time
from datetime import datetime
from typing import List, Dict, Optional
import xml.etree.ElementTree as ET
import random
import threading

BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
EMAIL = "drpablo.hospita@gmail.com"  # Requerido por NCBI
TOOL = "martyria"


def retry_request(func, max_retries=3, base_delay=1.0):
    """Ejecuta funcion con retry y backoff exponencial"""
    for attempt in range(max_retries):
        try:
            return func()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                print(f"  [Retry] Rate limit (429), esperando {delay:.1f}s (intento {attempt + 1}/{max_retries})...")
                time.sleep(delay)
            else:
                raise
        except requests.exceptions.RequestException as e:
            delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
            print(f"  [Retry] Error de red: {e}, esperando {delay:.1f}s (intento {attempt + 1}/{max_retries})...")
            time.sleep(delay)
    
    raise Exception(f"Fallo despues de {max_retries} intentos")


class PubMedSearcher:
    """Buscador de PubMed con E-utilities"""
    
    _global_lock = threading.Lock()
    _global_last_request = 0
    _min_interval = 0.34  # 3 requests/second max
    
    def __init__(self, email: str = EMAIL, tool: str = TOOL):
        self.email = email
        self.tool = tool
    
    def _rate_limit(self):
        """Respeta el rate limit de NCBI globalmente (thread-safe)"""
        with self._global_lock:
            elapsed = time.time() - self._global_last_request
            if elapsed < self._min_interval:
                time.sleep(self._min_interval - elapsed)
            self._global_last_request = time.time()
    
    def search(self, query: str, max_results: int = 50, years_back: int = 5) -> List[Dict]:
        """
        Busca en PubMed y retorna lista de articulos
        """
        current_year = datetime.now().year
        min_year = current_year - years_back
        
        # Construir query con filtros
        full_query = f"({query}) AND ({min_year}:{current_year}[pdat])"
        print(f"[Martyria] Buscando: {full_query}")
        
        try:
            # Step 1: ESearch - obtener PMIDs
            params = {
                "db": "pubmed",
                "term": full_query,
                "retmax": max_results,
                "sort": "date",
                "retmode": "json",
                "email": self.email,
                "tool": self.tool
            }
            
            data = retry_request(lambda: self._search_esearch(params))
            
            pmids = data.get("esearchresult", {}).get("idlist", [])
            total_count = data.get("esearchresult", {}).get("count", 0)
            
            print(f"[Martyria] Encontrados {total_count} articulos, obteniendo {len(pmids)}")
            
            if not pmids:
                print("[Martyria] No se encontraron articulos con esos criterios")
                return []
            
            # Step 2: ESummary - obtener metadatos
            articles = retry_request(lambda: self._fetch_summaries(pmids))
            
            # Step 3: EFetch - obtener abstracts
            articles = retry_request(lambda: self._fetch_abstracts(pmids, articles))
            
            return list(articles.values())
            
        except Exception as e:
            print(f"[Martyria] Error en busqueda: {e}")
            return []
    
    def _search_esearch(self, params):
        """Wrapper para ESearch con rate limit"""
        self._rate_limit()
        esearch_url = f"{BASE_URL}/esearch.fcgi"
        response = requests.get(esearch_url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    
    def _fetch_summaries(self, pmids: List[str]) -> Dict[str, Dict]:
        """Obtiene resumenes (titulo, autores, revista, etc)"""
        self._rate_limit()
        esummary_url = f"{BASE_URL}/esummary.fcgi"
        params = {
            "db": "pubmed",
            "id": ",".join(pmids),
            "retmode": "json",
            "email": self.email,
            "tool": self.tool
        }
        
        response = requests.get(esummary_url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        articles = {}
        for pmid in pmids:
            if pmid in data.get("result", {}):
                article_data = data["result"][pmid]
                articles[pmid] = {
                    "pmid": pmid,
                    "title": article_data.get("title", ""),
                    "authors": [a.get("name", "") for a in article_data.get("authors", [])],
                    "journal": article_data.get("fulljournalname", article_data.get("source", "")),
                    "year": article_data.get("pubdate", "").split()[0] if article_data.get("pubdate") else "",
                    "doi": article_data.get("elocationid", "").replace("doi: ", "") if article_data.get("elocationid") else "",
                    "pub_types": article_data.get("pubtype", []),
                }
        
        return articles
    
    def _fetch_abstracts(self, pmids: List[str], articles: Dict[str, Dict]) -> Dict[str, Dict]:
        """Obtiene abstracts en formato XML y los parsea"""
        self._rate_limit()
        efetch_url = f"{BASE_URL}/efetch.fcgi"
        params = {
            "db": "pubmed",
            "id": ",".join(pmids),
            "retmode": "xml",
            "email": self.email,
            "tool": self.tool
        }
        
        response = requests.get(efetch_url, params=params, timeout=30)
        response.raise_for_status()
        
        # Parsear XML
        root = ET.fromstring(response.content)
        
        for article in root.findall(".//PubmedArticle"):
            pmid_elem = article.find(".//PMID")
            if pmid_elem is None:
                continue
            
            pmid = pmid_elem.text
            if pmid not in articles:
                continue
            
            # Extraer abstract
            abstract_elem = article.find(".//Abstract")
            if abstract_elem is not None:
                abstract_texts = []
                for abst_text in abstract_elem.findall("AbstractText"):
                    text = abst_text.text or ""
                    label = abst_text.get("Label", "")
                    if label:
                        abstract_texts.append(f"{label}: {text}")
                    else:
                        abstract_texts.append(text)
                articles[pmid]["abstract"] = " ".join(abstract_texts)
            else:
                articles[pmid]["abstract"] = ""
            
            # Extraer MeSH terms
            mesh_terms = []
            for mesh in article.findall(".//MeshHeading/DescriptorName"):
                mesh_terms.append(mesh.text)
            articles[pmid]["mesh_terms"] = mesh_terms
            
            # Clasificar tipo de estudio
            articles[pmid]["study_type"] = self._classify_study_type(
                articles[pmid].get("pub_types", []),
                articles[pmid].get("title", ""),
                articles[pmid].get("abstract", "")
            )
        
        return articles
    
    def _classify_study_type(self, pub_types: List[str], title: str, abstract: str) -> str:
        """Clasifica el tipo de estudio basado en pub_types y texto"""
        text = (title + " " + abstract).lower()
        
        if "meta-analysis" in pub_types or "meta-analysis" in text:
            return "Meta-analysis"
        elif "randomized controlled trial" in pub_types or "clinical trial" in pub_types:
            return "RCT"
        elif "review" in pub_types:
            return "Systematic Review"
        elif "cohort" in text or "prospective" in text:
            return "Cohort Study"
        elif "case-control" in text or "case control" in text:
            return "Case-Control"
        elif "cross-sectional" in text:
            return "Cross-Sectional"
        elif "guideline" in pub_types or "guideline" in text:
            return "Clinical Guideline"
        else:
            return "Other"


def translate_topic_to_mesh(topic: str) -> str:
    """
    Traduce un tema en lenguaje natural a terminos de busqueda PubMed.
    """
    translations = {
        "sedacion": "sedation",
        "trauma craneoencefalico": "traumatic brain injury",
        "tce": "traumatic brain injury",
        "lesion renal aguda": "acute kidney injury",
        "lra": "acute kidney injury",
        "aki": "acute kidney injury",
        "neumonia asociada a ventilador": "ventilator associated pneumonia",
        "vap": "ventilator associated pneumonia",
        "shock septico": "septic shock",
        "sepsis": "sepsis",
        "disfuncion endotelial": "endothelial dysfunction",
        "choque": "shock",
        "reanimacion": "resuscitation",
        "ventilacion mecanica": "mechanical ventilation",
        "ecmo": "extracorporeal membrane oxygenation",
        "dra": "acute respiratory distress syndrome",
        "sdra": "acute respiratory distress syndrome",
        "ards": "acute respiratory distress syndrome",
        "delirio": "delirium",
        "sindrome de abstinencia": "withdrawal syndrome",
        "fallo multiorganico": "multiple organ failure",
        "sirs": "systemic inflammatory response syndrome",
    }
    
    topic_lower = topic.lower()
    
    for es, en in translations.items():
        if es in topic_lower:
            return topic_lower.replace(es, en)
    
    return topic


def main():
    if len(sys.argv) < 2:
        print("Uso: python3 search_pubmed.py \"tema de busqueda\"")
        sys.exit(1)
    
    topic = sys.argv[1]
    print(f"=" * 60)
    print(f"Martyria - Busqueda PubMed")
    print(f"Tema: {topic}")
    print(f"=" * 60)
    
    search_query = translate_topic_to_mesh(topic)
    if search_query != topic:
        print(f"Query traducida: {search_query}")
    
    searcher = PubMedSearcher()
    articles = searcher.search(search_query, max_results=20)
    
    if not articles:
        print("No se encontraron articulos.")
        sys.exit(0)
    
    print(f"\n{'='*60}")
    print(f"RESULTADOS ({len(articles)} articulos)")
    print(f"{'='*60}\n")
    
    for i, article in enumerate(articles[:10], 1):
        print(f"{i}. [{article['pmid']}] {article['study_type']}")
        print(f"   {article['title'][:100]}...")
        print(f"   {article.get('journal', '')} ({article.get('year', '')})")
        print(f"   Autores: {', '.join(article.get('authors', [])[:3])}")
        print()
    
    output_file = f"pubmed_results_{topic.replace(' ', '_')}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(articles, f, indent=2, ensure_ascii=False)
    
    print(f"Resultados guardados en: {output_file}")


if __name__ == "__main__":
    main()
