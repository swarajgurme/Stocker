# Test Configuration for Stocker API
import pytest
import json
from datetime import datetime, timedelta
from backend.server import app, validate_input, VALID_STORES, VALID_PRODUCTS

@pytest.fixture
def client():
    """Create test client"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

# ============= HEALTH CHECK TESTS =============

def test_health_check_success(client):
    """Test health check endpoint returns healthy status"""
    response = client.get('/health')
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'healthy'
    assert 'timestamp' in data
    assert 'records_count' in data
    assert data['version'] == '2.0'

def test_health_check_has_data(client):
    """Test health check confirms data is loaded"""
    response = client.get('/health')
    data = response.get_json()
    assert data['data_loaded'] == 'OK'
    assert data['records_count'] > 0

# ============= FORECAST ENDPOINT TESTS =============

def test_forecast_valid_request(client):
    """Test forecast endpoint with valid input"""
    data = {
        "store_id": "S001",
        "product_name": "Battery",
        "start_date": "2024-01-01",
        "end_date": "2024-12-31"
    }
    response = client.post('/forecast', 
                          data=json.dumps(data),
                          content_type='application/json')
    assert response.status_code == 200
    result = response.get_json()
    assert result['status'] == 'success'
    assert result['data']['store_id'] == 'S001'
    assert result['data']['product_name'] == 'Battery'
    assert 'actual_sales' in result['data']
    assert 'predicted_sales' in result['data']

def test_forecast_empty_request_body(client):
    """Test forecast with empty request body"""
    response = client.post('/forecast',
                          data=json.dumps({}),
                          content_type='application/json')
    assert response.status_code == 400
    result = response.get_json()
    assert result['status'] == 'error'
    assert result['code'] == 'VALIDATION_ERROR'

def test_forecast_invalid_store(client):
    """Test forecast with invalid store ID"""
    data = {
        "store_id": "INVALID",
        "product_name": "Battery",
        "start_date": "2024-01-01",
        "end_date": "2024-12-31"
    }
    response = client.post('/forecast',
                          data=json.dumps(data),
                          content_type='application/json')
    assert response.status_code == 400
    result = response.get_json()
    assert result['code'] == 'VALIDATION_ERROR'
    assert 'Invalid Store ID' in result['error']

def test_forecast_invalid_product(client):
    """Test forecast with invalid product name"""
    data = {
        "store_id": "S001",
        "product_name": "InvalidProduct",
        "start_date": "2024-01-01",
        "end_date": "2024-12-31"
    }
    response = client.post('/forecast',
                          data=json.dumps(data),
                          content_type='application/json')
    assert response.status_code == 400
    result = response.get_json()
    assert result['code'] == 'VALIDATION_ERROR'
    assert 'Invalid Product Name' in result['error']

def test_forecast_invalid_date_format(client):
    """Test forecast with invalid date format"""
    data = {
        "store_id": "S001",
        "product_name": "Battery",
        "start_date": "01-01-2024",  # Wrong format
        "end_date": "2024-12-31"
    }
    response = client.post('/forecast',
                          data=json.dumps(data),
                          content_type='application/json')
    assert response.status_code == 400
    result = response.get_json()
    assert result['code'] == 'VALIDATION_ERROR'
    assert 'Invalid date format' in result['error']

def test_forecast_start_after_end(client):
    """Test forecast with start date after end date"""
    data = {
        "store_id": "S001",
        "product_name": "Battery",
        "start_date": "2024-12-31",
        "end_date": "2024-01-01"
    }
    response = client.post('/forecast',
                          data=json.dumps(data),
                          content_type='application/json')
    assert response.status_code == 400
    result = response.get_json()
    assert result['code'] == 'VALIDATION_ERROR'
    assert 'Start date must be before end date' in result['error']

def test_forecast_date_range_too_large(client):
    """Test forecast with date range exceeding 730 days"""
    data = {
        "store_id": "S001",
        "product_name": "Battery",
        "start_date": "2020-01-01",
        "end_date": "2026-01-01"
    }
    response = client.post('/forecast',
                          data=json.dumps(data),
                          content_type='application/json')
    assert response.status_code == 400
    result = response.get_json()
    assert result['code'] == 'VALIDATION_ERROR'
    assert 'cannot exceed 730 days' in result['error']

def test_forecast_response_has_timestamp(client):
    """Test forecast response includes timestamp"""
    data = {
        "store_id": "S001",
        "product_name": "Battery",
        "start_date": "2024-01-01",
        "end_date": "2024-12-31"
    }
    response = client.post('/forecast',
                          data=json.dumps(data),
                          content_type='application/json')
    result = response.get_json()
    assert 'timestamp' in result
    # Validate ISO format
    try:
        datetime.fromisoformat(result['timestamp'].replace('Z', '+00:00'))
    except ValueError:
        pytest.fail("Invalid timestamp format")

def test_forecast_metrics_in_response(client):
    """Test forecast response includes metrics"""
    data = {
        "store_id": "S001",
        "product_name": "Battery",
        "start_date": "2024-01-01",
        "end_date": "2024-12-31"
    }
    response = client.post('/forecast',
                          data=json.dumps(data),
                          content_type='application/json')
    result = response.get_json()
    metrics = result['data']['metrics']
    assert 'historical_records' in metrics
    assert 'forecast_records' in metrics
    assert 'confidence_interval' in metrics
    assert metrics['confidence_interval'] == '95%'

# ============= CLUSTERING ENDPOINT TESTS =============

def test_clustering_success(client):
    """Test clustering endpoint returns successful response"""
    response = client.get('/clustering')
    assert response.status_code == 200
    result = response.get_json()
    assert result['status'] == 'success'
    assert 'optimal_clusters' in result['data']
    assert result['data']['optimal_clusters'] >= 1

def test_clustering_has_cluster_data(client):
    """Test clustering response includes cluster data"""
    response = client.get('/clustering')
    result = response.get_json()
    assert 'clusters' in result['data']
    assert len(result['data']['clusters']) > 0
    
    # Validate cluster data structure
    for cluster in result['data']['clusters']:
        assert 'category' in cluster
        assert 'store_id' in cluster
        assert 'sales' in cluster
        assert 'cluster' in cluster

def test_clustering_has_statistics(client):
    """Test clustering response includes statistics"""
    response = client.get('/clustering')
    result = response.get_json()
    assert 'statistics' in result['data']
    
    # Validate statistics structure
    for cluster_id, stats in result['data']['statistics'].items():
        assert 'count' in stats
        assert 'total_sales' in stats
        assert 'avg_sales' in stats

def test_clustering_response_has_timestamp(client):
    """Test clustering response includes timestamp"""
    response = client.get('/clustering')
    result = response.get_json()
    assert 'timestamp' in result
    # Validate ISO format
    try:
        datetime.fromisoformat(result['timestamp'].replace('Z', '+00:00'))
    except ValueError:
        pytest.fail("Invalid timestamp format")

# ============= INPUT VALIDATION TESTS =============

def test_validate_input_valid(self):
    """Test input validation with valid parameters"""
    valid, msg = validate_input("S001", "Battery", "2024-01-01", "2024-12-31")
    assert valid == True
    assert msg == ""

def test_validate_input_invalid_store(self):
    """Test input validation rejects invalid store"""
    valid, msg = validate_input("INVALID", "Battery", "2024-01-01", "2024-12-31")
    assert valid == False
    assert "Invalid Store ID" in msg

def test_validate_input_invalid_product(self):
    """Test input validation rejects invalid product"""
    valid, msg = validate_input("S001", "InvalidProduct", "2024-01-01", "2024-12-31")
    assert valid == False
    assert "Invalid Product Name" in msg

def test_validate_input_invalid_date_format(self):
    """Test input validation rejects invalid date format"""
    valid, msg = validate_input("S001", "Battery", "01-01-2024", "2024-12-31")
    assert valid == False
    assert "Invalid date format" in msg

def test_validate_input_start_after_end(self):
    """Test input validation rejects start > end"""
    valid, msg = validate_input("S001", "Battery", "2024-12-31", "2024-01-01")
    assert valid == False
    assert "Start date must be before end date" in msg

# ============= ERROR HANDLING TESTS =============

def test_404_not_found(client):
    """Test 404 error handling"""
    response = client.get('/invalid_endpoint')
    assert response.status_code == 404
    result = response.get_json()
    assert result['status'] == 'error'
    assert result['code'] == 'NOT_FOUND'
    assert result['path'] == '/invalid_endpoint'

def test_405_method_not_allowed(client):
    """Test 405 error handling"""
    response = client.post('/clustering')  # GET only endpoint
    assert response.status_code == 405
    result = response.get_json()
    assert result['status'] == 'error'
    assert result['code'] == 'METHOD_NOT_ALLOWED'

# ============= PERFORMANCE TESTS =============

def test_forecast_completes_within_timeout(client):
    """Test forecast completes within timeout (development only)"""
    import time
    data = {
        "store_id": "S001",
        "product_name": "Battery",
        "start_date": "2024-01-01",
        "end_date": "2024-12-31"
    }
    
    start_time = time.time()
    response = client.post('/forecast',
                          data=json.dumps(data),
                          content_type='application/json')
    elapsed_time = time.time() - start_time
    
    # Should complete within 15 seconds (development environment)
    assert elapsed_time < 15
    assert response.status_code == 200

def test_clustering_completes_within_timeout(client):
    """Test clustering completes within timeout"""
    import time
    
    start_time = time.time()
    response = client.get('/clustering')
    elapsed_time = time.time() - start_time
    
    # Should complete within 10 seconds
    assert elapsed_time < 10
    assert response.status_code == 200

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
