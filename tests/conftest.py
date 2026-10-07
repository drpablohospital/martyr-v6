"""
conftest.py - Configuración de pytest para Martyr v6.0

Fixtures y utilidades compartidas para todos los tests.
"""

import json
import csv
import tempfile
import pytest
from pathlib import Path


@pytest.fixture
def sample_studies():
    """Datos de ejemplo de estudios para testing."""
    return [
        {
            'study_id': 'S001',
            'author': 'Gaudry 2016',
            'year': '2016',
            'intervention': 'RRT temprana',
            'control': 'RRT tardía',
            'outcome': 'Mortalidad',
            'n_i': 247,
            'n_c': 246,
            'events_i': 48,
            'events_c': 50,
            'rr': 0.96,
            'rr_ci_lower': 0.68,
            'rr_ci_upper': 1.35,
            'weight': 25
        },
        {
            'study_id': 'S002',
            'author': 'Zarbock 2016',
            'year': '2016',
            'intervention': 'RRT temprana',
            'control': 'RRT tardía',
            'outcome': 'Mortalidad',
            'n_i': 112,
            'n_c': 119,
            'events_i': 22,
            'events_c': 31,
            'rr': 0.75,
            'rr_ci_lower': 0.48,
            'rr_ci_upper': 1.18,
            'weight': 20
        },
        {
            'study_id': 'S003',
            'author': 'STARRT-AKI 2019',
            'year': '2019',
            'intervention': 'RRT temprana',
            'control': 'RRT tardía',
            'outcome': 'Mortalidad',
            'n_i': 1465,
            'n_c': 1462,
            'events_i': 296,
            'events_c': 292,
            'rr': 1.02,
            'rr_ci_lower': 0.89,
            'rr_ci_upper': 1.17,
            'weight': 41
        },
        {
            'study_id': 'S004',
            'author': 'IDEAL-ICU 2020',
            'year': '2020',
            'intervention': 'RRT temprana',
            'control': 'RRT tardía',
            'outcome': 'Mortalidad',
            'n_i': 141,
            'n_c': 140,
            'events_i': 48,
            'events_c': 43,
            'rr': 1.11,
            'rr_ci_lower': 0.80,
            'rr_ci_upper': 1.54,
            'weight': 14
        }
    ]


@pytest.fixture
def sample_studies_with_subgroups():
    """Datos de ejemplo con subgrupos para testing."""
    return [
        {
            'study_id': 'S001',
            'author': 'Gaudry 2016',
            'year': '2016',
            'intervention': 'Hidrocortisona',
            'control': 'Placebo',
            'outcome': 'Mortalidad',
            'subgroup': 'septic',
            'n_i': 100,
            'n_c': 100,
            'events_i': 20,
            'events_c': 25,
            'rr': 0.80,
            'rr_ci_lower': 0.50,
            'rr_ci_upper': 1.28,
            'weight': 25
        },
        {
            'study_id': 'S002',
            'author': 'Zarbock 2016',
            'year': '2016',
            'intervention': 'Dexametasona',
            'control': 'Placebo',
            'outcome': 'Mortalidad',
            'subgroup': 'COVID',
            'n_i': 150,
            'n_c': 150,
            'events_i': 30,
            'events_c': 45,
            'rr': 0.67,
            'rr_ci_lower': 0.45,
            'rr_ci_upper': 0.99,
            'weight': 30
        }
    ]


@pytest.fixture
def temp_dir():
    """Directorio temporal para tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_csv_file(temp_dir, sample_studies):
    """Crea un archivo CSV temporal con datos de ejemplo."""
    csv_path = temp_dir / 'test_studies.csv'
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        if sample_studies:
            writer = csv.DictWriter(f, fieldnames=sample_studies[0].keys())
            writer.writeheader()
            writer.writerows(sample_studies)
    return csv_path


@pytest.fixture
def mock_json_file(temp_dir):
    """Crea un archivo JSON temporal para testing."""
    def _create(data, filename='test.json'):
        json_path = temp_dir / filename
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        return json_path
    return _create
