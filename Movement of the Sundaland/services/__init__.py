"""
services/__init__.py
Lazy imports to avoid pulling PyQt6 at module load time.
Qt-dependent workers (CalculationWorker, SearchWorker) are imported
directly by the files that need them.
"""
