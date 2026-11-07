"""Главные числа отчётов совпадают с сырыми данными (runs/verify_report_numbers.py)."""
from runs import verify_report_numbers as v


def test_mcnemar_floor():
    assert abs(v.mcnemar_exact(8, 0) - 0.0078125) < 1e-12
    assert abs(v.mcnemar_exact(6, 0) - 0.03125) < 1e-12
    assert v.mcnemar_exact(0, 0) == 1.0


def test_report_numbers_match_data():
    assert v.main([]) == 0
