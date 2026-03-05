"""
Test suite for API endpoints.
Tests /api/health and /api/ingest (xlsx-only) endpoints.
"""

import pytest
import sys
import os
from unittest.mock import patch, Mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app2 import app, limiter

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), 'fixtures')


@pytest.fixture
def client():
    """Flask test client with rate limiting disabled"""
    app.config['TESTING'] = True
    limiter.enabled = False
    with app.test_client() as client:
        yield client
    limiter.enabled = True


class TestIngestEndpoint:
    """Test /api/ingest endpoint — XLSX only."""

    @patch('app2._upsert_xlsx_to_sqlite', return_value=5)
    def test_ingest_xlsx_success(self, mock_upsert, client):
        """Ingesting XLSX should return 200 with classifications_upserted"""
        filepath = os.path.join(FIXTURES_DIR, 'sample.xlsx')
        response = client.post('/api/ingest', json={'file_path': filepath})
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert 'classifications_upserted' in data

    def test_ingest_pdf_rejected(self, client):
        """Ingesting PDF should return 400"""
        filepath = os.path.join(FIXTURES_DIR, 'sample.pdf')
        response = client.post('/api/ingest', json={'file_path': filepath})
        assert response.status_code == 400
        data = response.get_json()
        assert 'XLSX' in data['error']

    def test_ingest_csv_rejected(self, client):
        """Ingesting CSV should return 400"""
        filepath = os.path.join(FIXTURES_DIR, 'sample.csv')
        response = client.post('/api/ingest', json={'file_path': filepath})
        assert response.status_code == 400

    def test_ingest_png_rejected(self, client):
        """Ingesting PNG should return 400"""
        filepath = os.path.join(FIXTURES_DIR, 'sample.png')
        response = client.post('/api/ingest', json={'file_path': filepath})
        assert response.status_code == 400

    def test_ingest_txt_rejected(self, client):
        """Ingesting TXT should return 400"""
        filepath = os.path.join(FIXTURES_DIR, 'sample.txt')
        response = client.post('/api/ingest', json={'file_path': filepath})
        assert response.status_code == 400

    def test_ingest_no_file_path(self, client):
        """Missing file_path in JSON payload should return 400"""
        response = client.post('/api/ingest', json={})
        assert response.status_code == 400


class TestHealthEndpoint:
    """Test /api/health CHROMADB_IN_MEMORY flag reporting."""

    @patch('app2.openai_client')
    def test_health_reports_chromadb_in_memory_flag_true(self, mock_openai, client):
        """Health endpoint includes chromadb_in_memory: True when flag is set."""
        from app2 import app as flask_app
        flask_app.config['CHROMADB_IN_MEMORY'] = True
        response = client.get('/api/health')
        assert response.status_code == 200
        data = response.get_json()
        assert data['chromadb_in_memory'] is True

    @patch('app2.openai_client')
    def test_health_reports_chromadb_in_memory_flag_false(self, mock_openai, client):
        """Health endpoint includes chromadb_in_memory: False when flag is set."""
        from app2 import app as flask_app
        flask_app.config['CHROMADB_IN_MEMORY'] = False
        response = client.get('/api/health')
        assert response.status_code == 200
        data = response.get_json()
        assert data['chromadb_in_memory'] is False
