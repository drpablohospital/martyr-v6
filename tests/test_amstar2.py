"""
test_amstar2.py - Tests para Evaluación AMSTAR 2

Prueba las funciones principales del módulo AMSTAR 2.
"""

import sys
from pathlib import Path

# Agregar scripts al path
sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))
sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts/stats'))

import pytest
from amstar2 import (
    AMSTAR2Rating,
    CriterionStatus,
    Criterion,
    AMSTAR2Assessment
)


class TestAMSTAR2Rating:
    """Tests para los niveles de calidad."""
    
    def test_rating_values(self):
        """Verifica valores de los niveles."""
        assert AMSTAR2Rating.HIGH == "high"
        assert AMSTAR2Rating.MODERATE == "moderate"
        assert AMSTAR2Rating.LOW == "low"
        assert AMSTAR2Rating.CRITICALLY_LOW == "critically_low"


class TestCriterionStatus:
    """Tests para estados de criterios."""
    
    def test_status_values(self):
        """Verifica valores de estados."""
        assert CriterionStatus.YES == "yes"
        assert CriterionStatus.PARTIAL == "partial"
        assert CriterionStatus.NO == "no"
        assert CriterionStatus.NA == "na"


class TestCriterion:
    """Tests para la clase Criterion."""
    
    def test_create_criterion(self):
        """Crear criterio con valores por defecto."""
        criterion = Criterion(
            code="C1",
            description="Test criterion",
            is_critical=True
        )
        assert criterion.code == "C1"
        assert criterion.is_critical is True
        assert criterion.status == CriterionStatus.NA
        assert criterion.notes == ""
    
    def test_create_non_critical(self):
        """Crear criterio no crítico."""
        criterion = Criterion(
            code="C3",
            description="Test non-critical",
            is_critical=False
        )
        assert criterion.is_critical is False


class TestAMSTAR2AssessmentInit:
    """Tests para inicialización del assessment."""
    
    def test_init_criteria(self):
        """Inicializa 16 criterios."""
        amstar = AMSTAR2Assessment()
        assert len(amstar.criteria) == 16
    
    def test_critical_criteria(self):
        """Identifica criterios críticos."""
        amstar = AMSTAR2Assessment()
        critical = [c for c in amstar.criteria.values() if c.is_critical]
        assert len(critical) == 7  # C2, C4, C7, C9, C11, C13, C15
    
    def test_non_critical_criteria(self):
        """Identifica criterios no críticos."""
        amstar = AMSTAR2Assessment()
        non_critical = [c for c in amstar.criteria.values() if not c.is_critical]
        assert len(non_critical) == 9  # C1, C3, C5, C6, C8, C10, C12, C14, C16
    
    def test_default_status_na(self):
        """Estado por defecto es NA."""
        amstar = AMSTAR2Assessment()
        for criterion in amstar.criteria.values():
            assert criterion.status == CriterionStatus.NA


class TestEvaluateCriterion:
    """Tests para evaluación de criterios individuales."""
    
    def test_evaluate_yes(self):
        """Evaluar como YES."""
        amstar = AMSTAR2Assessment()
        amstar.evaluate_criterion("C2", "yes", "Protocolo registrado")
        
        assert amstar.criteria["C2"].status == CriterionStatus.YES
        assert amstar.criteria["C2"].notes == "Protocolo registrado"
    
    def test_evaluate_no(self):
        """Evaluar como NO."""
        amstar = AMSTAR2Assessment()
        amstar.evaluate_criterion("C4", "no", "Solo 1 base de datos")
        
        assert amstar.criteria["C4"].status == CriterionStatus.NO
    
    def test_evaluate_partial(self):
        """Evaluar como PARTIAL."""
        amstar = AMSTAR2Assessment()
        amstar.evaluate_criterion("C7", "partial", "Extracción simple")
        
        assert amstar.criteria["C7"].status == CriterionStatus.PARTIAL
    
    def test_evaluate_na(self):
        """Evaluar como NA."""
        amstar = AMSTAR2Assessment()
        amstar.evaluate_criterion("C1", "na", "No aplica")
        
        assert amstar.criteria["C1"].status == CriterionStatus.NA
    
    def test_invalid_code(self):
        """Código inválido lanza error."""
        amstar = AMSTAR2Assessment()
        with pytest.raises(ValueError, match="Criterio C99 no existe"):
            amstar.evaluate_criterion("C99", "yes")
    
    def test_invalid_status(self):
        """Estado inválido lanza error."""
        amstar = AMSTAR2Assessment()
        with pytest.raises(ValueError, match="Estado 'maybe' inválido"):
            amstar.evaluate_criterion("C1", "maybe")
    
    def test_case_insensitive(self):
        """Evaluación es case-insensitive."""
        amstar = AMSTAR2Assessment()
        amstar.evaluate_criterion("C1", "YES")
        assert amstar.criteria["C1"].status == CriterionStatus.YES


class TestGetCriticalFlaws:
    """Tests para deficiencias críticas."""
    
    def test_no_flaws(self):
        """Sin deficiencias críticas."""
        amstar = AMSTAR2Assessment()
        # Marcar todos los críticos como YES
        for code, criterion in amstar.criteria.items():
            if criterion.is_critical:
                amstar.evaluate_criterion(code, "yes")
        
        count, codes = amstar.get_critical_flaws()
        assert count == 0
        assert len(codes) == 0
    
    def test_one_critical_flaw(self):
        """Una deficiencia crítica."""
        amstar = AMSTAR2Assessment()
        amstar.evaluate_criterion("C2", "no")
        
        count, codes = amstar.get_critical_flaws()
        assert count == 1
        assert "C2" in codes
    
    def test_multiple_critical_flaws(self):
        """Múltiples deficiencias críticas."""
        amstar = AMSTAR2Assessment()
        amstar.evaluate_criterion("C2", "no")
        amstar.evaluate_criterion("C4", "no")
        amstar.evaluate_criterion("C7", "no")
        
        count, codes = amstar.get_critical_flaws()
        assert count == 3
    
    def test_partial_not_flaw(self):
        """PARTIAL no cuenta como deficiencia."""
        amstar = AMSTAR2Assessment()
        amstar.evaluate_criterion("C2", "partial")
        
        count, codes = amstar.get_critical_flaws()
        assert count == 0


class TestGetNonCriticalFlaws:
    """Tests para deficiencias no críticas."""
    
    def test_no_flaws(self):
        """Sin deficiencias no críticas."""
        amstar = AMSTAR2Assessment()
        count, codes = amstar.get_non_critical_flaws()
        assert count == 0
    
    def test_one_non_critical_flaw(self):
        """Una deficiencia no crítica."""
        amstar = AMSTAR2Assessment()
        amstar.evaluate_criterion("C1", "no")
        
        count, codes = amstar.get_non_critical_flaws()
        assert count == 1
        assert "C1" in codes


class TestGetOverallRating:
    """Tests para calificación global - CRÍTICO."""
    
    def test_high_quality(self):
        """0-1 deficiencia no crítica, 0 críticas → HIGH."""
        amstar = AMSTAR2Assessment()
        # Todos críticos YES
        for code, criterion in amstar.criteria.items():
            if criterion.is_critical:
                amstar.evaluate_criterion(code, "yes")
        # 1 no crítico NO
        amstar.evaluate_criterion("C1", "no")
        
        result = amstar.get_overall_rating()
        assert result["rating"] == AMSTAR2Rating.HIGH
        assert result["critical_flaws"] == 0
        assert result["non_critical_flaws"] == 1
    
    def test_moderate_quality(self):
        """>1 deficiencia no crítica, 0 críticas → MODERATE."""
        amstar = AMSTAR2Assessment()
        # Todos críticos YES
        for code, criterion in amstar.criteria.items():
            if criterion.is_critical:
                amstar.evaluate_criterion(code, "yes")
        # 2 no críticos NO
        amstar.evaluate_criterion("C1", "no")
        amstar.evaluate_criterion("C3", "no")
        
        result = amstar.get_overall_rating()
        assert result["rating"] == AMSTAR2Rating.MODERATE
    
    def test_low_quality(self):
        """1 deficiencia crítica → LOW."""
        amstar = AMSTAR2Assessment()
        # 1 crítico NO
        amstar.evaluate_criterion("C2", "no")
        # Resto YES
        for code, criterion in amstar.criteria.items():
            if code != "C2" and criterion.is_critical:
                amstar.evaluate_criterion(code, "yes")
        
        result = amstar.get_overall_rating()
        assert result["rating"] == AMSTAR2Rating.LOW
        assert result["critical_flaws"] == 1
    
    def test_critically_low_quality(self):
        """>1 deficiencia crítica → CRITICALLY_LOW."""
        amstar = AMSTAR2Assessment()
        # 2 críticos NO
        amstar.evaluate_criterion("C2", "no")
        amstar.evaluate_criterion("C4", "no")
        
        result = amstar.get_overall_rating()
        assert result["rating"] == AMSTAR2Rating.CRITICALLY_LOW
        assert result["critical_flaws"] == 2
    
    def test_critical_overrides_non_critical(self):
        """Deficiencia crítica anula estado de no críticos."""
        amstar = AMSTAR2Assessment()
        # 1 crítico NO
        amstar.evaluate_criterion("C2", "no")
        # Muchos no críticos YES (no importa)
        for code, criterion in amstar.criteria.items():
            if not criterion.is_critical:
                amstar.evaluate_criterion(code, "yes")
        
        result = amstar.get_overall_rating()
        # Igual es LOW por la crítica
        assert result["rating"] == AMSTAR2Rating.LOW


class TestExportResults:
    """Tests para exportación de resultados."""
    
    def test_export_structure(self):
        """Estructura del resultado de exportación."""
        amstar = AMSTAR2Assessment()
        amstar.evaluate_criterion("C2", "yes", "Protocolo OK")
        amstar.evaluate_criterion("C4", "no", "Faltó EMBASE")
        
        result = amstar.get_overall_rating()
        
        assert "rating" in result
        assert "critical_flaws" in result
        assert "non_critical_flaws" in result
        assert "critical_flaw_codes" in result
        assert "non_critical_flaw_codes" in result
        assert "total_criteria_evaluated" in result


class TestCompleteAssessment:
    """Tests para evaluación completa realista."""
    
    def test_perfect_review(self):
        """Revisión perfecta: todos YES."""
        amstar = AMSTAR2Assessment()
        for code in amstar.criteria.keys():
            amstar.evaluate_criterion(code, "yes")
        
        result = amstar.get_overall_rating()
        assert result["rating"] == AMSTAR2Rating.HIGH
        assert result["critical_flaws"] == 0
        assert result["non_critical_flaws"] == 0
    
    def test_minimal_acceptable(self):
        """Revisión mínima aceptable."""
        amstar = AMSTAR2Assessment()
        # Todos críticos YES
        for code, criterion in amstar.criteria.items():
            if criterion.is_critical:
                amstar.evaluate_criterion(code, "yes")
        # Algunos no críticos PARTIAL o NO
        amstar.evaluate_criterion("C1", "partial")
        amstar.evaluate_criterion("C3", "no")
        
        result = amstar.get_overall_rating()
        # Debe ser MODERATE o HIGH dependiendo de cuántos NO
        assert result["rating"] in [AMSTAR2Rating.HIGH, AMSTAR2Rating.MODERATE]
    
    def test_poor_review(self):
        """Revisión deficiente."""
        amstar = AMSTAR2Assessment()
        # Varios críticos NO
        amstar.evaluate_criterion("C2", "no")
        amstar.evaluate_criterion("C4", "no")
        amstar.evaluate_criterion("C7", "no")
        
        result = amstar.get_overall_rating()
        assert result["rating"] == AMSTAR2Rating.CRITICALLY_LOW


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
