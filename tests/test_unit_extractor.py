"""Tests for the syntactic unit extractor module."""

import builtins
from unittest.mock import Mock, patch

import pytest

from agentic_code_review.llm_refiner.languages.base_parser import SyntaxNode, SyntaxNodeType
from agentic_code_review.llm_refiner.unit_extractor import SyntacticUnit, SyntacticUnitExtractor

# Constants for test values
START_LINE = 1
END_LINE = 2
MODULE_AND_CLASS_AND_TWO_METHODS = 4
TWO_METHODS = 2
TWO_OVERLAPPING_UNITS = 2


class TestSyntacticUnit:
    """Tests for the SyntacticUnit class."""

    def test_initialization(self):
        """Test basic initialization of a syntactic unit."""
        # Create a mock node
        node = Mock(spec=SyntaxNode)
        node.metadata = {"signature": "def test_function():"}

        # Create a syntactic unit
        unit = SyntacticUnit(
            node=node,
            code="def test_function():\n    pass",
            file_path="test.py",
            unit_type=SyntaxNodeType.FUNCTION,
            name="test_function",
            start_line=START_LINE,
            end_line=END_LINE,
            parent_unit=None,
        )

        # Check basic properties
        assert unit.name == "test_function"
        assert unit.code == "def test_function():\n    pass"
        assert unit.file_path == "test.py"
        assert unit.unit_type == SyntaxNodeType.FUNCTION
        assert unit.start_line == START_LINE
        assert unit.end_line == END_LINE
        assert unit.parent_unit is None
        assert unit.children == []  # Should be initialized as empty list

    def test_signature_property(self):
        """Test the signature property for different unit types."""
        # Function unit
        function_node = Mock(spec=SyntaxNode)
        function_node.metadata = {"signature": "def test_function():"}
        function_unit = SyntacticUnit(node=function_node, code="", file_path="", unit_type=SyntaxNodeType.FUNCTION, name="", start_line=0, end_line=0)
        assert function_unit.signature == "def test_function():"

        # Method unit
        method_node = Mock(spec=SyntaxNode)
        method_node.metadata = {"signature": "def test_method(self):"}
        method_unit = SyntacticUnit(node=method_node, code="", file_path="", unit_type=SyntaxNodeType.METHOD, name="", start_line=0, end_line=0)
        assert method_unit.signature == "def test_method(self):"

        # Class unit
        class_node = Mock(spec=SyntaxNode)
        class_node.metadata = {"class_definition": "class TestClass:"}
        class_unit = SyntacticUnit(node=class_node, code="", file_path="", unit_type=SyntaxNodeType.CLASS, name="", start_line=0, end_line=0)
        assert class_unit.signature == "class TestClass:"

        # Other unit types should return None
        other_node = Mock(spec=SyntaxNode)
        other_node.metadata = {}
        other_unit = SyntacticUnit(node=other_node, code="", file_path="", unit_type=SyntaxNodeType.MODULE, name="", start_line=0, end_line=0)
        assert other_unit.signature is None

    def test_location_str_property(self):
        """Test the location_str property."""
        unit = SyntacticUnit(node=Mock(spec=SyntaxNode), code="", file_path="test.py", unit_type=SyntaxNodeType.FUNCTION, name="", start_line=10, end_line=20)
        assert unit.location_str == "test.py:10-20"

    def test_full_path_property(self):
        """Test the full_path property with and without parent units."""
        # Unit without parent
        unit = SyntacticUnit(
            node=Mock(spec=SyntaxNode), code="", file_path="", unit_type=SyntaxNodeType.FUNCTION, name="test_function", start_line=0, end_line=0
        )
        assert unit.full_path == "test_function"

        # Unit with parent
        parent_unit = SyntacticUnit(
            node=Mock(spec=SyntaxNode), code="", file_path="", unit_type=SyntaxNodeType.CLASS, name="TestClass", start_line=0, end_line=0
        )
        child_unit = SyntacticUnit(
            node=Mock(spec=SyntaxNode),
            code="",
            file_path="",
            unit_type=SyntaxNodeType.METHOD,
            name="test_method",
            start_line=0,
            end_line=0,
            parent_unit=parent_unit,
        )
        assert child_unit.full_path == "TestClass.test_method"

        # Nested units
        grandparent_unit = SyntacticUnit(
            node=Mock(spec=SyntaxNode), code="", file_path="", unit_type=SyntaxNodeType.MODULE, name="module", start_line=0, end_line=0
        )
        parent_unit.parent_unit = grandparent_unit
        assert child_unit.full_path == "module.TestClass.test_method"


class TestSyntacticUnitExtractor:
    """Tests for the SyntacticUnitExtractor class."""

    @pytest.fixture
    def extractor(self):
        """Create a SyntacticUnitExtractor instance for testing."""
        return SyntacticUnitExtractor()

    @patch("agentic_code_review.llm_refiner.languages.parser_registry.ParserRegistry.get_parser_for_file")
    def test_extract_units_from_file(self, mock_get_parser, extractor):
        """Test extracting syntactic units from a file."""
        # Mock parser and syntax tree
        mock_parser = Mock()
        mock_parser.extract_syntax_tree.return_value = self._create_mock_syntax_tree()
        mock_get_parser.return_value = mock_parser

        # Mock the extract_relevant_code function
        with patch("agentic_code_review.llm_refiner.unit_extractor.extract_relevant_code") as mock_extract_code:
            mock_extract_code.return_value = "def test_function():\n    pass"

            # Extract units
            units = extractor.extract_units_from_file("test.py", "file content")

            # Verify results
            assert len(units) == MODULE_AND_CLASS_AND_TWO_METHODS  # Module, class, and two methods

            # Check module unit
            module_unit = next(u for u in units if u.unit_type == SyntaxNodeType.MODULE)
            assert module_unit.name == "module"

            # Check class unit
            class_unit = next(u for u in units if u.unit_type == SyntaxNodeType.CLASS)
            assert class_unit.name == "TestClass"
            assert class_unit.parent_unit == module_unit

            # Check method units
            method_units = [u for u in units if u.unit_type == SyntaxNodeType.METHOD]
            assert len(method_units) == TWO_METHODS
            method_names = [m.name for m in method_units]
            assert "__init__" in method_names
            assert "test_method" in method_names

            # Check parent-child relationships
            for method_unit in method_units:
                assert method_unit.parent_unit == class_unit

    @patch("agentic_code_review.llm_refiner.languages.parser_registry.ParserRegistry.get_parser_for_file")
    def test_extract_unit_at_location(self, mock_get_parser, extractor):
        """Test extracting a syntactic unit at a specific location."""
        # Mock parser
        mock_parser = Mock()
        mock_parser.find_node_at_position.return_value = self._create_mock_method_node()
        mock_get_parser.return_value = mock_parser

        # Mock the _find_closest_unit_node method
        with patch.object(extractor, "_find_closest_unit_node") as mock_find_closest:
            mock_find_closest.return_value = self._create_mock_method_node()

            # Mock extract_relevant_code
            with patch("agentic_code_review.llm_refiner.unit_extractor.extract_relevant_code") as mock_extract_code:
                mock_extract_code.return_value = "def test_method(self):\n    pass"

                # Extract unit at location
                unit = extractor.extract_unit_at_location("test.py", "file content", 5, 10)

                # Verify results
                assert unit is not None
                assert unit.unit_type == SyntaxNodeType.METHOD
                assert unit.name == "test_method"
                assert unit.file_path == "test.py"

    @patch("agentic_code_review.llm_refiner.languages.parser_registry.ParserRegistry.get_parser_for_file")
    def test_extract_units_at_specific_lines(self, mock_get_parser, extractor):
        """Test extracting syntactic units at specific line ranges."""
        # Mock extract_units_from_file
        with patch.object(extractor, "extract_units_from_file") as mock_extract:
            # Create mock units at different line ranges
            units = [
                SyntacticUnit(
                    node=Mock(), code="", file_path="test.py", unit_type=SyntaxNodeType.FUNCTION, name="func1", start_line=1, end_line=5, parent_unit=None
                ),
                SyntacticUnit(
                    node=Mock(), code="", file_path="test.py", unit_type=SyntaxNodeType.FUNCTION, name="func2", start_line=10, end_line=15, parent_unit=None
                ),
                SyntacticUnit(
                    node=Mock(), code="", file_path="test.py", unit_type=SyntaxNodeType.FUNCTION, name="func3", start_line=20, end_line=25, parent_unit=None
                ),
            ]
            mock_extract.return_value = units

            # Test with a line range that overlaps with the first and second units
            result = extractor.extract_units_at_specific_lines("test.py", "content", [(5, 12)])

            assert len(result) == TWO_OVERLAPPING_UNITS
            assert "func1" in [u.name for u in result]
            assert "func2" in [u.name for u in result]
            assert "func3" not in [u.name for u in result]

    def test_find_closest_unit_node(self, extractor):
        """Test finding the closest unit node from a node."""
        # Test when the node itself is a unit
        node = Mock(spec=SyntaxNode)
        node.node_type = SyntaxNodeType.FUNCTION

        result = extractor._find_closest_unit_node(node)
        assert result == node

        # Test when a parent is a unit
        child_node = Mock(spec=SyntaxNode)
        child_node.node_type = SyntaxNodeType.EXPRESSION

        parent_node = Mock(spec=SyntaxNode)
        parent_node.node_type = SyntaxNodeType.FUNCTION

        # Setup parent-child relationship
        child_node.raw_node = Mock()
        child_node.raw_node.parent = parent_node

        # Create a mock_hasattr function that always returns True for our test
        def mock_hasattr(*args, **kwargs):
            return True

        # Patch the hasattr function
        with patch.object(builtins, "hasattr", mock_hasattr):
            result = extractor._find_closest_unit_node(child_node)
            assert result == parent_node

    def _create_mock_syntax_tree(self):
        """Create a mock syntax tree for testing."""
        # Create module node
        module_node = Mock(spec=SyntaxNode)
        module_node.node_type = SyntaxNodeType.MODULE
        module_node.name = "module"
        module_node.start_point = (0, 0)
        module_node.end_point = (30, 0)
        module_node.start_byte = 0
        module_node.end_byte = 500

        # Create class node
        class_node = Mock(spec=SyntaxNode)
        class_node.node_type = SyntaxNodeType.CLASS
        class_node.name = "TestClass"
        class_node.start_point = (1, 0)
        class_node.end_point = (25, 0)
        class_node.start_byte = 0
        class_node.end_byte = 400
        class_node.metadata = {"class_definition": "class TestClass:"}

        # Create method nodes
        init_method = Mock(spec=SyntaxNode)
        init_method.node_type = SyntaxNodeType.METHOD
        init_method.name = "__init__"
        init_method.start_point = (2, 4)
        init_method.end_point = (5, 0)
        init_method.start_byte = 20
        init_method.end_byte = 100
        init_method.metadata = {"signature": "def __init__(self):"}
        init_method.children = []

        test_method = Mock(spec=SyntaxNode)
        test_method.node_type = SyntaxNodeType.METHOD
        test_method.name = "test_method"
        test_method.start_point = (7, 4)
        test_method.end_point = (20, 0)
        test_method.start_byte = 120
        test_method.end_byte = 300
        test_method.metadata = {"signature": "def test_method(self):"}
        test_method.children = []

        # Set up the tree structure
        module_node.children = [class_node]
        class_node.children = [init_method, test_method]

        return module_node

    def _create_mock_method_node(self):
        """Create a mock method node for testing."""
        method_node = Mock(spec=SyntaxNode)
        method_node.node_type = SyntaxNodeType.METHOD
        method_node.name = "test_method"
        method_node.start_point = (5, 4)
        method_node.end_point = (8, 0)
        method_node.start_byte = 100
        method_node.end_byte = 150
        method_node.metadata = {"signature": "def test_method(self):"}
        method_node.children = []
        return method_node
