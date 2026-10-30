import sys
import time

from src import powerbi_client as pc

CASES = {
    "base_dax": lambda: pc.execute_query('EVALUATE ROW("ok", 1)'),
    "api_tablas": pc.list_tables,
    "info_tablas": lambda: pc.execute_query("EVALUATE INFO.VIEW.TABLES()"),
    "api_describe": lambda: pc.describe_table("occ_flights"),
    "info_describe": lambda: (
        pc.execute_query("EVALUATE INFO.VIEW.COLUMNS()"),
        pc.execute_query("EVALUATE INFO.VIEW.MEASURES()"),
    ),
    "api_formula": lambda: pc.get_measure_dax("1. OTP 15"),
}

name = sys.argv[1]
repeticiones = int(sys.argv[2])
fn = CASES[name]

fn()  # calentamiento: no se apunta
for _ in range(repeticiones):
    inicio = time.perf_counter()
    fn()
    print(name, round(time.perf_counter() - inicio, 2))
    time.sleep(2)