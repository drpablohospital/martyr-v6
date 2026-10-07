"""
test_subgroup_analysis.py - Tests para Análisis de Subgrupos

Prueba las funciones principales del módulo de análisis de subgrupos.
"""

import sys
import json
from pathlib import Path

# Agregar scripts al path
sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))
sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts/stats'))

import pytest
import numpy as np
from subgroup_analysis import (
    StudyData,
    SubgroupAnalyzer
)


class TestStudyData:
    """Tests para la clase StudyData."""
    
    def test_create_study(self):
        """Crear estudio con datos mínimos."""
        study = StudyData(
            study_id='S001',
            effect_size=0.8,
            variance=0.01,
            se=0.1,
            n_total=100
        )
        assert study.study_id == 'S001'
        assert study.effect_size == 0.8
        assert study.covariates == {}
    
    def test_create_with_covariates(self):
        """Crear estudio con covariables."""
        study = StudyData(
            study_id='S001',
            effect_size=0.8,
            variance=0.01,
            se=0.1,
            n_total=100,
            covariates={'dosis': 6, 'diabetes': 0}
        )
        assert study.covariates['dosis'] == 6


class TestSubgroupAnalyzerInit:
    """Tests para inicialización del analizador."""
    
    def test_empty_init(self):
        """Inicialización sin estudios."""
        analyzer = SubgroupAnalyzer()
        assert len(analyzer.studies) == 0
        assert len(analyzer.covariate_names) == 0
    
    def test_init_with_studies(self):
        """Inicialización con estudios."""
        studies = [
            StudyData('S001', 0.8, 0.01, 0.1, 100),
            StudyData('S002', 1.1, 0.02, 0.14, 150)
        ]
        analyzer = SubgroupAnalyzer(studies)
        assert len(analyzer.studies) == 2


class TestAddCovariateFromList:
    """Tests para agregar covariables."""
    
    def test_add_categorical(self):
        """Agregar covariable categórica."""
        studies = [
            StudyData('S001', 0.8, 0.01, 0.1, 100),
            StudyData('S002', 1.1, 0.02, 0.14, 150),
            StudyData('S003', 0.9, 0.015, 0.12, 120)
        ]
        analyzer = SubgroupAnalyzer(studies)
        analyzer.add_covariate_from_list('intervention', ['A', 'B', 'A'])
        
        assert 'intervention' in analyzer.covariate_names
        assert analyzer.studies[0].covariates['intervention'] == 'A'
        assert analyzer.studies[1].covariates['intervention'] == 'B'
    
    def test_add_continuous(self):
        """Agregar covariable continua."""
        studies = [
            StudyData('S001', 0.8, 0.01, 0.1, 100),
            StudyData('S002', 1.1, 0.02, 0.14, 150)
        ]
        analyzer = SubgroupAnalyzer(studies)
        analyzer.add_covariate_from_list('dosis', [6, 8])
        
        assert analyzer.studies[0].covariates['dosis'] == 6
        assert analyzer.studies[1].covariates['dosis'] == 8
    
    def test_wrong_length(self):
        """Error si la lista no coincide con número de estudios."""
        studies = [StudyData('S001', 0.8, 0.01, 0.1, 100)]
        analyzer = SubgroupAnalyzer(studies)
        
        with pytest.raises(ValueError, match="Longitud"):
            analyzer.add_covariate_from_list('dosis', [6, 8, 10])


class TestAnalyzeCategorical:
    """Tests para análisis de covariables categóricas."""
    
    def test_basic_analysis(self):
        """Análisis básico con 2 niveles."""
        studies = [
            StudyData('S001', 0.7, 0.01, 0.1, 100, covariates={'group': 'A'}),
            StudyData('S002', 0.8, 0.01, 0.1, 100, covariates={'group': 'A'}),
            StudyData('S003', 1.2, 0.02, 0.14, 150, covariates={'group': 'B'}),
            StudyData('S004', 1.3, 0.02, 0.14, 150, covariates={'group': 'B'})
        ]
        analyzer = SubgroupAnalyzer(studies)
        analyzer.add_covariate_from_list('group', ['A', 'A', 'B', 'B'])
        
        result = analyzer.analyze_categorical('group')
        
        assert result['covariate'] == 'group'
        assert result['type'] == 'categorical'
        assert len(result['levels']) == 2
        assert len(result['level_results']) == 2
    
    def test_single_level_error(self):
        """Error si solo hay 1 nivel."""
        studies = [
            StudyData('S001', 0.8, 0.01, 0.1, 100, covariates={'group': 'A'}),
            StudyData('S002', 0.9, 0.01, 0.1, 100, covariates={'group': 'A'})
        ]
        analyzer = SubgroupAnalyzer(studies)
        analyzer.add_covariate_from_list('group', ['A', 'A'])
        
        result = analyzer.analyze_categorical('group')
        assert 'error' in result
        assert 'niveles' in result['error']
    
    def test_insufficient_studies_per_level(self):
        """Maneja niveles con pocos estudios."""
        studies = [
            StudyData('S001', 0.8, 0.01, 0.1, 100, covariates={'group': 'A'}),
            StudyData('S002', 0.9, 0.01, 0.1, 100, covariates={'group': 'A'}),
            StudyData('S003', 1.2, 0.02, 0.14, 150, covariates={'group': 'B'})
        ]
        analyzer = SubgroupAnalyzer(studies)
        analyzer.add_covariate_from_list('group', ['A', 'A', 'B'])
        
        result = analyzer.analyze_categorical('group')
        # Debe manejar el nivel con 1 estudio
        assert any(r['n_studies'] == 1 for r in result['level_results'])
    
    def test_significant_difference(self):
        """Detecta diferencia significativa entre subgrupos."""
        # Grupo A: efecto ~0.7-0.8 (beneficio)
        # Grupo B: efecto ~1.2-1.3 (daño)
        studies = [
            StudyData('S001', 0.7, 0.001, 0.03, 1000, covariates={'group': 'A'}),
            StudyData('S002', 0.75, 0.001, 0.03, 1000, covariates={'group': 'A'}),
            StudyData('S003', 1.25, 0.001, 0.03, 1000, covariates={'group': 'B'}),
            StudyData('S004', 1.30, 0.001, 0.03, 1000, covariates={'group': 'B'})
        ]
        analyzer = SubgroupAnalyzer(studies)
        analyzer.add_covariate_from_list('group', ['A', 'A', 'B', 'B'])
        
        result = analyzer.analyze_categorical('group')
        
        # Con efectos tan diferentes, Q-between debe ser significativo
        assert result['Q_between'] > 0
        assert result['df_between'] == 1


class TestAnalyzeContinuous:
    """Tests para análisis de covariables continuas."""
    
    def test_basic_regression(self):
        """Meta-regresión simple."""
        studies = [
            StudyData('S001', 0.9, 0.01, 0.1, 100, covariates={'dosis': 6}),
            StudyData('S002', 0.8, 0.01, 0.1, 100, covariates={'dosis': 8}),
            StudyData('S003', 0.7, 0.01, 0.1, 100, covariates={'dosis': 10}),
            StudyData('S004', 0.6, 0.01, 0.1, 100, covariates={'dosis': 12})
        ]
        analyzer = SubgroupAnalyzer(studies)
        analyzer.add_covariate_from_list('dosis', [6, 8, 10, 12])
        
        result = analyzer.analyze_continuous('dosis')
        
        assert result['covariate'] == 'dosis'
        assert result['type'] == 'continuous'
        assert 'slope' in result
        assert 'intercept' in result
        assert 'R_squared' in result
    
    def test_positive_slope(self):
        """Detecta pendiente positiva."""
        # A mayor dosis, mayor efecto
        studies = [
            StudyData('S001', 0.5, 0.01, 0.1, 100, covariates={'dosis': 6}),
            StudyData('S002', 0.7, 0.01, 0.1, 100, covariates={'dosis': 8}),
            StudyData('S003', 0.9, 0.01, 0.1, 100, covariates={'dosis': 10}),
            StudyData('S004', 1.1, 0.01, 0.1, 100, covariates={'dosis': 12})
        ]
        analyzer = SubgroupAnalyzer(studies)
        analyzer.add_covariate_from_list('dosis', [6, 8, 10, 12])
        
        result = analyzer.analyze_continuous('dosis')
        
        assert result['slope'] > 0  # Pendiente positiva
    
    def test_negative_slope(self):
        """Detecta pendiente negativa."""
        # A mayor dosis, menor efecto (beneficio)
        studies = [
            StudyData('S001', 1.1, 0.01, 0.1, 100, covariates={'dosis': 6}),
            StudyData('S002', 0.9, 0.01, 0.1, 100, covariates={'dosis': 8}),
            StudyData('S003', 0.7, 0.01, 0.1, 100, covariates={'dosis': 10}),
            StudyData('S004', 0.5, 0.01, 0.1, 100, covariates={'dosis': 12})
        ]
        analyzer = SubgroupAnalyzer(studies)
        analyzer.add_covariate_from_list('dosis', [6, 8, 10, 12])
        
        result = analyzer.analyze_continuous('dosis')
        
        assert result['slope'] < 0  # Pendiente negativa
    
    def test_missing_values(self):
        """Maneja valores faltantes."""
        import numpy as np
        
        studies = [
            StudyData('S001', 0.8, 0.01, 0.1, 100, covariates={'dosis': 6}),
            StudyData('S002', 0.9, 0.01, 0.1, 100, covariates={'dosis': np.nan})
        ]
        analyzer = SubgroupAnalyzer(studies)
        analyzer.add_covariate_from_list('dosis', [6, np.nan])
        
        result = analyzer.analyze_continuous('dosis')
        assert 'error' in result


class TestAnalyzeAll:
    """Tests para análisis completo."""
    
    def test_all_covariates(self):
        """Análisis de todas las covariables."""
        studies = [
            StudyData('S001', 0.8, 0.01, 0.1, 100, covariates={'group': 'A', 'dosis': 6}),
            StudyData('S002', 0.9, 0.01, 0.1, 100, covariates={'group': 'A', 'dosis': 8}),
            StudyData('S003', 1.2, 0.02, 0.14, 150, covariates={'group': 'B', 'dosis': 10}),
            StudyData('S004', 1.3, 0.02, 0.14, 150, covariates={'group': 'B', 'dosis': 12})
        ]
        analyzer = SubgroupAnalyzer(studies)
        analyzer.add_covariate_from_list('group', ['A', 'A', 'B', 'B'])
        analyzer.add_covariate_from_list('dosis', [6, 8, 10, 12])
        
        results = analyzer.analyze_all()
        
        assert 'covariate_results' in results
        assert len(results['covariate_results']) == 2
        assert 'group' in results['covariate_results']
        assert 'dosis' in results['covariate_results']
    
    def test_no_covariates(self):
        """Error si no hay covariables."""
        studies = [StudyData('S001', 0.8, 0.01, 0.1, 100)]
        analyzer = SubgroupAnalyzer(studies)
        
        results = analyzer.analyze_all()
        assert 'error' in results


class TestExportResults:
    """Tests para exportación de resultados."""
    
    def test_export_json(self, temp_dir):
        """Exporta resultados a JSON."""
        studies = [
            StudyData('S001', 0.8, 0.01, 0.1, 100, covariates={'group': 'A'}),
            StudyData('S002', 0.9, 0.01, 0.1, 100, covariates={'group': 'A'}),
            StudyData('S003', 1.2, 0.02, 0.14, 150, covariates={'group': 'B'}),
            StudyData('S004', 1.3, 0.02, 0.14, 150, covariates={'group': 'B'})
        ]
        analyzer = SubgroupAnalyzer(studies)
        analyzer.add_covariate_from_list('group', ['A', 'A', 'B', 'B'])
        
        results = analyzer.analyze_all()
        
        # Exportar
        output_path = temp_dir / 'subgroup_results.json'
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2)
        
        assert output_path.exists()
        
        # Verificar que es JSON válido
        with open(output_path, 'r', encoding='utf-8') as f:
            loaded = json.load(f)
        
        assert 'covariate_results' in loaded


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
