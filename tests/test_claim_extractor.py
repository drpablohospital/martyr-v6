"""
test_claim_extractor.py - Tests para Claim Extractor

Prueba las funciones principales del módulo de extracción de afirmaciones.
"""

import sys
import json
from pathlib import Path

# Agregar scripts al path
sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))

import pytest
from claim_extractor import (
    load_studies,
    determine_direction,
    determine_magnitude,
    calculate_consistency,
    extract_main_claim,
    extract_subgroup_claims,
    generate_claims,
    save_outputs
)


class TestLoadStudies:
    """Tests para la función load_studies."""
    
    def test_load_from_csv(self, temp_dir, sample_studies):
        """Prueba carga desde CSV válido."""
        import csv
        
        csv_path = temp_dir / 'test.csv'
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            if sample_studies:
                writer = csv.DictWriter(f, fieldnames=sample_studies[0].keys())
                writer.writeheader()
                writer.writerows(sample_studies)
        
        studies = load_studies(csv_path)
        assert len(studies) == 4
        assert studies[0]['study_id'] == 'S001'
        assert isinstance(studies[0]['rr'], float)
    
    def test_empty_csv(self, temp_dir):
        """Prueba CSV vacío (solo headers)."""
        import csv
        
        csv_path = temp_dir / 'empty.csv'
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['study_id', 'rr'])
            writer.writeheader()
        
        studies = load_studies(csv_path)
        assert len(studies) == 0
    
    def test_numeric_conversion(self, temp_dir):
        """Prueba conversión de campos numéricos."""
        import csv
        
        csv_path = temp_dir / 'numeric.csv'
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['study_id', 'rr', 'n_i', 'events_i'])
            writer.writeheader()
            writer.writerow({'study_id': 'S001', 'rr': '0.95', 'n_i': '100', 'events_i': '20'})
        
        studies = load_studies(csv_path)
        assert studies[0]['rr'] == 0.95
        assert studies[0]['n_i'] == 100.0


class TestDetermineDirection:
    """Tests para determine_direction."""
    
    def test_favors_intervention(self):
        """RR < 1 con CI < 1 favorece intervención."""
        result = determine_direction(0.8, 0.65, 0.98)
        assert result == "favors_intervention"
    
    def test_favors_control(self):
        """RR > 1 con CI > 1 favorece control."""
        result = determine_direction(1.5, 1.2, 1.8)
        assert result == "favors_control"
    
    def test_no_difference(self):
        """RR cerca de 1 es no diferencia."""
        result = determine_direction(1.02, 0.95, 1.10)
        assert result == "no_difference"
    
    def test_uncertain_crosses_null(self):
        """CI que cruza 1 es incierto."""
        result = determine_direction(0.9, 0.7, 1.2)
        assert result == "uncertain"
    
    def test_none_effect_size(self):
        """Effect size None retorna uncertain."""
        result = determine_direction(None, 0.8, 1.2)
        assert result == "uncertain"


class TestDetermineMagnitude:
    """Tests para determine_magnitude."""
    
    def test_large_effect(self):
        """RR < 0.70 o > 1.43 es grande."""
        assert determine_magnitude(0.65) == "large"
        assert determine_magnitude(1.50) == "large"
    
    def test_moderate_effect(self):
        """RR entre 0.70-0.85 o 1.18-1.43 es moderado."""
        assert determine_magnitude(0.80) == "moderate"
        assert determine_magnitude(1.30) == "moderate"
    
    def test_small_effect(self):
        """RR entre 0.85-0.95 o 1.05-1.18 es pequeño."""
        assert determine_magnitude(0.90) == "small"
        assert determine_magnitude(1.10) == "small"
    
    def test_uncertain_effect(self):
        """RR cerca de 1 es incierto."""
        assert determine_magnitude(0.97) == "uncertain"


class TestCalculateConsistency:
    """Tests para calculate_consistency."""
    
    def test_perfect_consistency(self):
        """Estudios con misma dirección y magnitud similar = 1.0."""
        studies = [
            {'rr': 0.80, 'ci_lower': 0.65, 'ci_upper': 0.98},
            {'rr': 0.82, 'ci_lower': 0.67, 'ci_upper': 1.00},
            {'rr': 0.79, 'ci_lower': 0.64, 'ci_upper': 0.97}
        ]
        score = calculate_consistency(studies)
        assert 0.8 <= score <= 1.0
    
    def test_no_studies(self):
        """Sin estudios retorna 0.0."""
        score = calculate_consistency([])
        assert score == 0.0
    
    def test_single_study(self):
        """Un solo estudio es consistente consigo mismo."""
        studies = [{'rr': 0.80, 'ci_lower': 0.65, 'ci_upper': 0.98}]
        score = calculate_consistency(studies)
        assert score == 1.0
    
    def test_inconsistent_directions(self):
        """Direcciones opuestas reducen consistencia."""
        studies = [
            {'rr': 0.70, 'ci_lower': 0.50, 'ci_upper': 0.98},
            {'rr': 1.30, 'ci_lower': 1.10, 'ci_upper': 1.54}
        ]
        score = calculate_consistency(studies)
        assert score < 0.7  # Debe ser bajo por direcciones opuestas


class TestExtractMainClaim:
    """Tests para extract_main_claim."""
    
    def test_basic_extraction(self, sample_studies):
        """Extracción básica de afirmación principal."""
        claim = extract_main_claim(sample_studies)
        
        assert claim is not None
        assert claim['claim_id'] == 'C001'
        assert claim['claim_type'] == 'efficacy'
        assert 'RRT temprana' in claim['claim_text']
        assert 'Mortalidad' in claim['claim_text']
        assert claim['n_supporting'] == 4
    
    def test_no_intervention_default(self):
        """Sin intervention usa default."""
        studies = [{'outcome': 'Muerte', 'rr': 0.80, 'ci_lower': 0.65, 'ci_upper': 0.98}]
        claim = extract_main_claim(studies)
        assert 'Intervención' in claim['claim_text']
    
    def test_empty_studies(self):
        """Sin estudios retorna None."""
        claim = extract_main_claim([])
        assert claim is None
    
    def test_pooled_effect_calculation(self, sample_studies):
        """Verifica cálculo de efecto combinado."""
        claim = extract_main_claim(sample_studies)
        # El pooled effect debe estar entre el min y max de los estudios
        effects = [s['rr'] for s in sample_studies]
        assert min(effects) <= claim['pooled_effect'] <= max(effects)


class TestExtractSubgroupClaims:
    """Tests para extract_subgroup_claims."""
    
    def test_subgroups_present(self, sample_studies_with_subgroups):
        """Extrae claims cuando hay subgrupos."""
        claims = extract_subgroup_claims(sample_studies_with_subgroups)
        assert len(claims) == 2
        assert any(c['subgroup'] == 'septic' for c in claims)
        assert any(c['subgroup'] == 'COVID' for c in claims)
    
    def test_no_subgroups(self, sample_studies):
        """Sin subgrupos retorna lista vacía."""
        claims = extract_subgroup_claims(sample_studies)
        assert len(claims) == 0


class TestGenerateClaims:
    """Tests para generate_claims."""
    
    def test_generate_all_claims(self, sample_studies):
        """Genera claims principales y de subgrupos."""
        result = generate_claims(sample_studies)
        
        assert 'claims' in result
        assert 'meta' in result
        assert result['meta']['total_claims'] >= 1
        assert result['meta']['total_studies_analyzed'] == 4
    
    def test_metadata_structure(self, sample_studies):
        """Verifica estructura de metadatos."""
        result = generate_claims(sample_studies)
        
        assert 'extraction_date' in result['meta']
        assert 'version' in result['meta']


class TestSaveOutputs:
    """Tests para save_outputs."""
    
    def test_save_all_files(self, temp_dir, sample_studies):
        """Guarda JSON, log y CSV de mapeo."""
        result = generate_claims(sample_studies)
        files = save_outputs(result, temp_dir)
        
        assert Path(files['claims_file']).exists()
        assert Path(files['log_file']).exists()
        assert Path(files['mapping_file']).exists()
    
    def test_json_valid(self, temp_dir, sample_studies):
        """Verifica que el JSON sea válido."""
        result = generate_claims(sample_studies)
        files = save_outputs(result, temp_dir)
        
        with open(files['claims_file'], 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        assert 'claims' in data
        assert len(data['claims']) >= 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
