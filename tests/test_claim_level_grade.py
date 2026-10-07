"""
test_claim_level_grade.py - Tests para Claim-Level GRADE

Prueba la evaluación GRADE por afirmación individual.
"""

import sys
from pathlib import Path

# Agregar scripts al path
sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))
sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts/stats'))

import pytest
from claim_level_grade import (
    GRADERating,
    ClaimLevelGRADE
)


class TestGRADERating:
    """Tests para los niveles de certeza GRADE."""
    
    def test_rating_values(self):
        """Verifica valores de los niveles."""
        assert GRADERating.HIGH == "high"
        assert GRADERating.MODERATE == "moderate"
        assert GRADERating.LOW == "low"
        assert GRADERating.VERY_LOW == "very_low"


class TestClaimLevelGRADEInit:
    """Tests para inicialización de ClaimLevelGRADE."""
    
    def test_init(self):
        """Inicialización correcta."""
        grade = ClaimLevelGRADE()
        assert grade.ratings_order[GRADERating.HIGH] == 4
        assert grade.ratings_order[GRADERating.VERY_LOW] == 1


class TestEvaluateRiskOfBias:
    """Tests para evaluación de riesgo de sesgo."""
    
    def test_no_studies(self):
        """Sin estudios → no downgrade."""
        grade = ClaimLevelGRADE()
        level, reason = grade.evaluate_risk_of_bias([])
        assert level == 0
        assert "Sin datos" in reason
    
    def test_all_low_rob(self):
        """Todos con bajo RoB → no downgrade."""
        grade = ClaimLevelGRADE()
        studies = [
            {'rob_level': 'low'},
            {'rob_level': 'low'},
            {'rob_level': 'low'}
        ]
        level, reason = grade.evaluate_risk_of_bias(studies)
        assert level == 0
        assert "bajo RoB" in reason
    
    def test_majority_high_rob(self):
        """Mayoría con alto RoB → downgrade 2 niveles."""
        grade = ClaimLevelGRADE()
        studies = [
            {'rob_level': 'high'},
            {'rob_level': 'high'},
            {'rob_level': 'low'}
        ]
        level, reason = grade.evaluate_risk_of_bias(studies)
        assert level == 2
        assert "Mayoría con alto RoB" in reason
    
    def test_some_high_rob(self):
        """Algunos con alto RoB → downgrade 1 nivel."""
        grade = ClaimLevelGRADE()
        studies = [
            {'rob_level': 'high'},
            {'rob_level': 'low'},
            {'rob_level': 'low'}
        ]
        level, reason = grade.evaluate_risk_of_bias(studies)
        assert level == 1
    
    def test_mixed_concerns(self):
        """Mitad con preocupaciones → downgrade 1 nivel."""
        grade = ClaimLevelGRADE()
        studies = [
            {'rob_level': 'some_concerns'},
            {'rob_level': 'some_concerns'},
            {'rob_level': 'low'},
            {'rob_level': 'low'}
        ]
        level, reason = grade.evaluate_risk_of_bias(studies)
        assert level == 1
    
    def test_string_studies_filtered(self):
        """Estudios que son strings se filtran."""
        grade = ClaimLevelGRADE()
        studies = [
            {'rob_level': 'low'},
            "string_study"  # Debe ser filtrado
        ]
        level, reason = grade.evaluate_risk_of_bias(studies)
        assert level == 0


class TestEvaluateInconsistency:
    """Tests para evaluación de inconsistencia - CRÍTICO."""
    
    def test_high_i2_serious(self):
        """I² > 50% → downgrade SERIO (2 niveles)."""
        grade = ClaimLevelGRADE()
        claim = {
            'consistency_score': 0.3,
            'i2': 65.0,
            'supporting_studies': [
                {'effect_size': 0.7, 'ci_lower': 0.5, 'ci_upper': 0.98},
                {'effect_size': 1.3, 'ci_lower': 1.1, 'ci_upper': 1.54}
            ]
        }
        level, reason = grade.evaluate_inconsistency(claim)
        assert level == 2
        assert "I²=65.0%" in reason or "alta heterogeneidad" in reason.lower()
    
    def test_moderate_i2_some(self):
        """I² entre 30-50% → downgrade ALGUNO (1 nivel)."""
        grade = ClaimLevelGRADE()
        claim = {
            'consistency_score': 0.5,
            'i2': 42.0,
            'supporting_studies': [
                {'effect_size': 0.8, 'ci_lower': 0.6, 'ci_upper': 1.0},
                {'effect_size': 1.1, 'ci_lower': 0.9, 'ci_upper': 1.3}
            ]
        }
        level, reason = grade.evaluate_inconsistency(claim)
        assert level == 1
        assert "I²=42.0%" in reason
    
    def test_low_i2_no_downgrade(self):
        """I² < 30% → no downgrade."""
        grade = ClaimLevelGRADE()
        claim = {
            'consistency_score': 0.8,
            'i2': 15.0,
            'supporting_studies': [
                {'effect_size': 0.8, 'ci_lower': 0.6, 'ci_upper': 1.0},
                {'effect_size': 0.9, 'ci_lower': 0.7, 'ci_upper': 1.1}
            ]
        }
        level, reason = grade.evaluate_inconsistency(claim)
        assert level == 0
    
    def test_no_i2_uses_consistency(self):
        """Sin I² disponible, usa consistency_score."""
        grade = ClaimLevelGRADE()
        claim = {
            'consistency_score': 0.2,
            'supporting_studies': [
                {'effect_size': 0.5, 'ci_lower': 0.3, 'ci_upper': 0.8},
                {'effect_size': 2.0, 'ci_lower': 1.5, 'ci_upper': 2.5}
            ]
        }
        level, reason = grade.evaluate_inconsistency(claim)
        assert level >= 1


class TestEvaluateImprecision:
    """Tests para evaluación de imprecisión."""
    
    def test_large_ci_serious(self):
        """CI muy amplio → downgrade."""
        grade = ClaimLevelGRADE()
        claim = {
            'pooled_effect': 0.9,
            'ci_lower': 0.3,
            'ci_upper': 2.7,
            'supporting_studies': [
                {'n_total': 100}
            ]
        }
        level, reason = grade.evaluate_imprecision(claim)
        assert level >= 1


class TestEvaluatePublicationBias:
    """Tests para evaluación de sesgo de publicación."""
    
    def test_no_studies(self):
        """Sin estudios → no downgrade."""
        grade = ClaimLevelGRADE()
        level, reason = grade.evaluate_publication_bias([])
        assert level == 0


class TestEvaluateClaim:
    """Tests para evaluación completa de una afirmación."""
    
    def test_full_evaluation(self):
        """Evaluación completa de claim típico."""
        grade = ClaimLevelGRADE()
        claim = {
            'claim_id': 'C001',
            'claim_text': 'Test claim',
            'pooled_effect': 0.85,
            'ci_lower': 0.75,
            'ci_upper': 0.97,
            'p_value': 0.015,
            'magnitude': 'small',
            'direction': 'favors_intervention',
            'consistency_score': 0.75,
            'i2': 25.0,
            'supporting_studies': [
                {'study_id': 'S001', 'n_total': 500, 'rob_level': 'low'},
                {'study_id': 'S002', 'n_total': 400, 'rob_level': 'low'}
            ]
        }
        
        result = grade.evaluate_claim(claim)
        
        assert result['claim_id'] == 'C001'
        assert 'overall_quality' in result
        assert 'clinical_rating' in result
        assert 'downgrades' in result
        assert len(result['downgrades']) >= 0
    
    def test_empty_claim(self):
        """Claim sin estudios → LOW (base RCT=HIGH, sin datos baja a LOW)."""
        grade = ClaimLevelGRADE()
        claim = {
            'claim_id': 'C_empty',
            'supporting_studies': []
        }
        
        result = grade.evaluate_claim(claim)
        # Sin estudios: imprecision downgrades 2, base RCT=HIGH → LOW
        assert result['overall_quality'] == GRADERating.LOW


class TestCalculateRecommendation:
    """Tests para cálculo de recomendación clínica."""
    
    def test_strong_rating(self):
        """HIGH quality + dirección definida → STRONG."""
        grade = ClaimLevelGRADE()
        claim = {'magnitude': 'large', 'consistency_score': 0.9, 'n_total': 1500, 'direction': 'favors_intervention'}
        rating = grade._calculate_recommendation(GRADERating.HIGH, claim)
        assert rating == "STRONG"
    
    def test_conditional_moderate(self):
        """MODERATE quality + dirección definida → CONDITIONAL."""
        grade = ClaimLevelGRADE()
        claim = {'magnitude': 'moderate', 'consistency_score': 0.7, 'n_total': 1000, 'direction': 'favors_intervention'}
        rating = grade._calculate_recommendation(GRADERating.MODERATE, claim)
        assert rating == "CONDITIONAL"
    
    def test_weak_low(self):
        """LOW quality → WEAK."""
        grade = ClaimLevelGRADE()
        claim = {'magnitude': 'small', 'consistency_score': 0.6, 'n_total': 500}
        rating = grade._calculate_recommendation(GRADERating.LOW, claim)
        assert rating == "WEAK"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
