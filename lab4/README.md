## Transliavimo Metodai, 4 Lab. Darbas

**Autorius:** Balys Žalneravičius
**Data:** 2025-11-19

Programa atlieka supaprastintą C kodo analizę.

### Failų Paskirtis:

* **`compiler.py`:** Programos paleidimui. Savyje turi skanerį ir paleidžia kitus komponentus.
* **`parser.py`:** Sintaksinis analizatorius. Grąžina abstraktųjį sintaksės medį (AST).
* **`semantic_analyzer.py`:** Semantinis analizatorius. Tikrina kintamųjų deklaracijas, tipų suderinamumą ir pildo simbolių lentelę.

### Paleidimas:

Programą paleiskite iš to paties katalogo, kuriame yra `compiler.py` failas:

```powershell
python .\compiler.py .\sample.c