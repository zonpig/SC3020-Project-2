# test_whatif.py
import pytest
from whatif import process_whatif_query
import os
import json

@pytest.fixture
def region_relations():
    """Fixture providing region table information"""
    return {
        "region": {
            "columns": ["r_regionkey", "r_name", "r_comment"],
            "size": 5  # Region table typically has 5 rows in TPC-H
        }
    }

@pytest.fixture
def basic_parameters():
    """Basic set of parameters for testing"""
    return {
        "enable_seqscan": True,
        "enable_indexscan": True,
        "work_mem": "64MB"
    }

def test_region_simple_select(region_relations, basic_parameters):
    """Test simple SELECT from region table"""
    query = "SELECT * FROM region"
    
    error, result = process_whatif_query(query, region_relations, basic_parameters)
    
    assert not error, f"Error occurred: {result.get('msg', '')}"
    assert "plan_data_path" in result
    assert "summary_data" in result
    assert os.path.exists(result["plan_data_path"])

def test_region_primary_key_lookup(region_relations):
    """Test lookup using primary key with different scan methods"""
    query = "SELECT * FROM region WHERE r_regionkey = 1"
    
    # Test with index scan enabled
    params_index = {
        "enable_seqscan": False,
        "enable_indexscan": True,
        "enable_bitmapscan": False
    }
    
    error, result_index = process_whatif_query(query, region_relations, params_index)
    assert not error, f"Error occurred: {result_index.get('msg', '')}"
    
    # Test forcing sequential scan
    params_seq = {
        "enable_seqscan": True,
        "enable_indexscan": False,
        "enable_bitmapscan": False
    }
    
    error, result_seq = process_whatif_query(query, region_relations, params_seq)
    assert not error, f"Error occurred: {result_seq.get('msg', '')}"

def test_region_name_search(region_relations):
    """Test search by r_name with different parameters"""
    query = "SELECT * FROM region WHERE r_name LIKE 'ASIA%'"
    
    parameters = {
        "enable_seqscan": True,
        "enable_indexscan": True,
        "enable_bitmapscan": True,
        "cpu_tuple_cost": 0.01,
        "cpu_operator_cost": 0.0025
    }
    
    error, result = process_whatif_query(query, region_relations, parameters)
    assert not error, f"Error occurred: {result.get('msg', '')}"

def test_region_sort(region_relations):
    """Test sorting with different work_mem settings"""
    query = "SELECT * FROM region ORDER BY r_name"
    
    # Test with smaller work_mem
    small_mem_params = {
        "work_mem": "64kB",
        "enable_sort": True
    }
    
    error, result_small = process_whatif_query(query, region_relations, small_mem_params)
    assert not error, f"Error occurred: {result_small.get('msg', '')}"
    
    # Test with larger work_mem
    large_mem_params = {
        "work_mem": "1MB",
        "enable_sort": True
    }
    
    error, result_large = process_whatif_query(query, region_relations, large_mem_params)
    assert not error, f"Error occurred: {result_large.get('msg', '')}"

def test_region_comment_search(region_relations):
    """Test search in r_comment field"""
    query = """
    SELECT r_name, r_comment 
    FROM region 
    WHERE r_comment LIKE '%test%'
    """
    
    parameters = {
        "enable_seqscan": True,
        "enable_indexscan": True,
        "cpu_operator_cost": 0.0025
    }
    
    error, result = process_whatif_query(query, region_relations, parameters)
    assert not error, f"Error occurred: {result.get('msg', '')}"

def test_region_aggregate(region_relations):
    """Test aggregation query"""
    query = """
    SELECT COUNT(*), r_name 
    FROM region 
    GROUP BY r_name
    """
    
    parameters = {
        "enable_hashagg": True,
        "enable_sort": True,
        "work_mem": "64MB"
    }
    
    error, result = process_whatif_query(query, region_relations, parameters)
    assert not error, f"Error occurred: {result.get('msg', '')}"

def test_cleanup():
    """Clean up plan files after tests"""
    for filename in os.listdir():
        if filename.startswith("plan_whatif_") and filename.endswith(".json"):
            try:
                os.remove(filename)
            except OSError:
                pass

if __name__ == "__main__":
    pytest.main(["-v", __file__])