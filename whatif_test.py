import pytest
from whatif import process_whatif_query
import os


@pytest.fixture
def region_relations():
    return {"region": {"columns": ["r_regionkey", "r_name", "r_comment"], "size": 5}}


@pytest.fixture
def basic_parameters():
    """Basic set of parameters for testing"""
    return {"enable_seqscan": True, "enable_indexscan": True, "work_mem": "64MB"}


def test_region_simple_select(region_relations, basic_parameters):
    """Test simple SELECT from region table"""
    query = "SELECT * FROM region"

    error, result = process_whatif_query(query, region_relations, basic_parameters)

    assert not error, f"Error occurred: {result.get('msg', '')}"
    assert "plan_data_path" in result
    assert "summary_data" in result
    assert "natural_explain" in result
    assert "block_analysis" in result
    assert os.path.exists(result["plan_data_path"])


def test_region_primary_key_lookup(region_relations):
    """Test lookup using primary key with different scan methods"""
    query = "SELECT * FROM region WHERE r_regionkey = 1"

    # Test with index scan enabled
    params_index = {
        "enable_seqscan": False,
        "enable_indexscan": True,
        "enable_bitmapscan": False,
    }

    error, result_index = process_whatif_query(query, region_relations, params_index)
    assert not error, f"Error occurred: {result_index.get('msg', '')}"

    # Test forcing sequential scan
    params_seq = {
        "enable_seqscan": True,
        "enable_indexscan": False,
        "enable_bitmapscan": False,
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
        "cpu_operator_cost": 0.0025,
    }

    error, result = process_whatif_query(query, region_relations, parameters)
    assert not error, f"Error occurred: {result.get('msg', '')}"


def test_region_sort(region_relations):
    """Test sorting with different work_mem settings"""
    query = "SELECT * FROM region ORDER BY r_name"

    # Test with smaller work_mem
    small_mem_params = {"work_mem": "64kB", "enable_sort": True}

    error, result_small = process_whatif_query(
        query, region_relations, small_mem_params
    )
    assert not error, f"Error occurred: {result_small.get('msg', '')}"

    # Test with larger work_mem
    large_mem_params = {"work_mem": "1MB", "enable_sort": True}

    error, result_large = process_whatif_query(
        query, region_relations, large_mem_params
    )
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
        "cpu_operator_cost": 0.0025,
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

    parameters = {"enable_hashagg": True, "enable_sort": True, "work_mem": "64MB"}

    error, result = process_whatif_query(query, region_relations, parameters)
    assert not error, f"Error occurred: {result.get('msg', '')}"


class TestProgrammingErrors:
    """Test cases for ProgrammingError exceptions"""

    def test_syntax_error(self, region_relations):
        """Test SQL syntax errors"""
        query = "SELCT * FROM region"  # Misspelled SELECT
        error, result = process_whatif_query(query, region_relations, {})

        assert error is True
        assert "msg" in result
        assert "Error during what-if analysis" in result["msg"]
        assert "syntax error" in result["msg"].lower()

    def test_undefined_table(self, region_relations):
        """Test queries with non-existent tables"""
        query = "SELECT * FROM nonexistent_table"
        error, result = process_whatif_query(query, region_relations, {})

        assert error is True
        assert "msg" in result
        assert "Error during what-if analysis" in result["msg"]
        assert "does not exist" in result["msg"]


class TestParameterErrors:
    """Test cases for parameter-related errors"""

    def test_float_parameter_error(self, region_relations):
        """Test error handling for invalid float parameters"""
        test_cases = [
            {"random_page_cost": "invalid"},
            {"cpu_tuple_cost": "invalid"},
            {"cpu_index_tuple_cost": "invalid"},
            {"cpu_operator_cost": "invalid"},
        ]

        query = "SELECT * FROM region"
        for params in test_cases:
            error, result = process_whatif_query(query, region_relations, params)

            assert error is True
            assert "msg" in result
            assert "An error has occurred" in result["msg"]
            assert "ValueError" in result["msg"]
            assert "could not convert string to float" in result["msg"]

    def test_memory_parameter_error(self, region_relations):
        """Test error handling for invalid memory parameters"""
        test_cases = [{"work_mem": "invalid"}, {"effective_cache_size": "invalid"}]

        query = "SELECT * FROM region"
        for params in test_cases:
            error, result = process_whatif_query(query, region_relations, params)

            assert error is True
            assert "msg" in result
            assert "An error has occurred" in result["msg"]
            assert any(
                expected in result["msg"]
                for expected in ["ValueError", "invalid value for parameter"]
            )


class TestOperationalErrors:
    """Test cases for OperationalError exceptions"""

    def test_connection_error(self, region_relations):
        """Test database connection error"""
        try:
            query = "SELECT * FROM region"
            error, result = process_whatif_query(query, region_relations, {})

            if error and "Failed to connect to the database" in result["msg"]:
                assert "ensure that the database is running" in result["msg"]
        except Exception:
            pytest.skip("Database is running, cannot test connection error")


class TestInvalidInputs:
    """Test cases for invalid inputs"""

    def test_none_query(self, region_relations):
        """Test with None as query"""
        error, result = process_whatif_query(None, region_relations, {})

        assert error is True
        assert "msg" in result
        assert "Error during what-if analysis" in result["msg"]
        assert "syntax error" in result["msg"].lower()

    def test_empty_query(self, region_relations):
        """Test with empty query"""
        error, result = process_whatif_query("", region_relations, {})

        assert error is True
        assert "msg" in result
        assert "Error during what-if analysis" in result["msg"]
        assert "syntax error" in result["msg"].lower()


if __name__ == "__main__":
    pytest.main(["-v", __file__])
