import pytest
import yaml
from psycopg2 import sql

from operators import OperatorBuilder, OperatorRegistryError, OperatorValueError


def write_registry(tmp_path, data):
    path = tmp_path / "operators.yaml"
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return path


def load_default_registry():
    with open("operators.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def test_t30_load_default_registry_has_6_ops():
    builder = OperatorBuilder("operators.yaml")

    assert set(builder.operators) == {"eq", "in", "between", "prefix", "contains", "suffix"}
    assert builder.display_order == ["eq", "in", "between", "prefix", "contains", "suffix"]
    assert len(builder.display_labels()) == 6


def test_t31_missing_display_order_raises_clear_error(tmp_path):
    data = load_default_registry()
    data.pop("display_order")

    with pytest.raises(OperatorRegistryError, match="display_order"):
        OperatorBuilder(write_registry(tmp_path, data))


def test_t32_new_operator_from_yaml_without_code_change(tmp_path):
    data = load_default_registry()
    data["operators"]["neq"] = {
        "display": "Khác",
        "hint": "1 giá trị",
        "example": "CN",
        "sql_single": "{col} <> {val}",
        "multi_value": False,
        "arity": 1,
        "supports_digits": False,
    }
    data["display_order"].append("neq")
    builder = OperatorBuilder(write_registry(tmp_path, data))

    fragment, params = builder.build_where("ma_nuoc", "neq", "CN")

    assert isinstance(fragment, sql.Composable)
    assert params == ["CN"]
    assert builder.debug_sql("ma_nuoc", "neq", "CN") == "ma_nuoc <> 'CN'"


def test_t33_prefix_multi_with_digits_builds_like_any_without_length():
    builder = OperatorBuilder("operators.yaml")

    fragment, params = builder.build_where("ma_so", "prefix", "8306,8307", digits=4)

    assert isinstance(fragment, sql.Composable)
    assert params == [["8306%", "8307%"]]
    assert builder.debug_sql("ma_so", "prefix", "8306,8307", digits=4) == "(ma_so ILIKE ANY(['8306%', '8307%']))"


def test_t34_suffix_single_with_digits_builds_suffix_like():
    builder = OperatorBuilder("operators.yaml")

    fragment, params = builder.build_where("ma_so", "suffix", "AA", digits=2)

    assert isinstance(fragment, sql.Composable)
    assert params == ["%AA"]
    assert builder.debug_sql("ma_so", "suffix", "AA", digits=2) == "ma_so ILIKE '%AA'"


def test_t35_between_ignores_digits_when_operator_does_not_support_it():
    builder = OperatorBuilder("operators.yaml")

    fragment, params = builder.build_where("gia", "between", "1000,5000", digits=4)

    assert isinstance(fragment, sql.Composable)
    assert params == ["1000", "5000"]
    assert builder.debug_sql("gia", "between", "1000,5000", digits=4) == "gia BETWEEN '1000' AND '5000'"


def test_contains_builds_case_insensitive_ilike():
    builder = OperatorBuilder("operators.yaml")

    fragment, params = builder.build_where("ten_cong_ty", "contains", "mAsAn")

    assert isinstance(fragment, sql.Composable)
    assert params == ["%mAsAn%"]
    assert builder.debug_sql("ten_cong_ty", "contains", "mAsAn") == "ten_cong_ty ILIKE '%mAsAn%'"


def test_t36_between_with_three_values_raises():
    builder = OperatorBuilder("operators.yaml")

    with pytest.raises(OperatorValueError, match="đúng 2"):
        builder.build_where("gia", "between", "1000,5000,9000")


def test_t37_prefix_digits_validate_value_length():
    builder = OperatorBuilder("operators.yaml")

    fragment, params = builder.build_where("ma_so", "prefix", "8306", digits=4)

    assert isinstance(fragment, sql.Composable)
    assert params == ["8306%"]
    with pytest.raises(OperatorValueError, match="value '84' có 2 ký tự, Digits yêu cầu 4"):
        builder.build_where("ma_so", "prefix", "84", digits=4)
