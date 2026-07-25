#!/bin/zsh
# Автономная цепочка после A.5. Порядок строго по блокам: доделать блок A
# (A.1, A.4) -> блок B -> блок C (C.1..C.4). Ждёт завершения compare.jsonl
# (48 строк). Всё однопоточным BLAS, логи по шагам в runs/*.log.
cd "$(dirname "$0")/.."
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1
export PYTHONPATH=.
PY=.venv/bin/python

echo "[chain] $(date +%H:%M:%S) жду завершения A.5 (48 строк в compare.jsonl)"
while [ "$(wc -l < runs/compare.jsonl 2>/dev/null || echo 0)" -lt 48 ]; do sleep 30; done
echo "[chain] $(date +%H:%M:%S) A.5 готов, анализирую (A.5 + A.3)"
$PY runs/analyze_compare.py > runs/analyze_compare.log 2>&1

# --- доделать блок A ---
echo "[chain] $(date +%H:%M:%S) A.1 калибровка внутриагентной метрики"
$PY runs/a1_calibrate.py > runs/a1_calibrate.log 2>&1
echo "[chain] $(date +%H:%M:%S) A.1 размер выборки"
$PY runs/a1_samplesize.py > runs/a1_samplesize.log 2>&1
echo "[chain] $(date +%H:%M:%S) A.4 выход на плато (долгий)"
$PY runs/a4_plateau.py > runs/a4_plateau.log 2>&1
touch runs/BLOCK_A_DONE

# --- блок B ---
echo "[chain] $(date +%H:%M:%S) блок B (свип regrowth, фазовый переход)"
$PY runs/b_sweep.py > runs/b_sweep.log 2>&1
$PY runs/analyze_b.py > runs/analyze_b.log 2>&1
touch runs/BLOCK_B_DONE

# --- блок C ---
echo "[chain] $(date +%H:%M:%S) C.1 пилот жизнеспособности"
$PY runs/c1_pilot.py > runs/c1_pilot.log 2>&1
echo "[chain] $(date +%H:%M:%S) C.2 свип mark_cost"
$PY runs/c2_markcost.py > runs/c2_markcost.log 2>&1
echo "[chain] $(date +%H:%M:%S) C.3 калибровка метрик знака"
$PY runs/c3_signcalib.py > runs/c3_signcalib.log 2>&1
echo "[chain] $(date +%H:%M:%S) C.4 тест порядка развития"
$PY runs/c4_devorder.py > runs/c4_devorder.log 2>&1
touch runs/BLOCK_C_DONE

echo "[chain] $(date +%H:%M:%S) ВСЁ ГОТОВО"
touch runs/CHAIN_DONE
