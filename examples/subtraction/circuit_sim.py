"""
Quantum subtraction circuit simulation using the QASM exported from C2|Q>.

Run from this directory after generating the QASM:
    c2q-json --input sub_01.json --export-qasm --qasm-output-dir .
Then:
    python circuit_sim.py

Instance: 20 - 7 = 13.
The circuit is deterministic — one shot suffices to read the result.
"""
from qiskit import qasm3, transpile
from qiskit_aer import AerSimulator

with open("sub_circuit.qasm") as f:
    src = f.read()

qc = qasm3.loads(src)
backend = AerSimulator()
result = backend.run(transpile(qc, backend), shots=1).result()
counts = result.get_counts()

bitstr = next(iter(counts)).replace(" ", "")
value = int(bitstr, 2)

print(f"Raw bitstring : {bitstr}")
print(f"Decoded value : {value}")
print(f"Expected      : 20 - 7 = 13")
print(f"Correct       : {'yes' if value == 13 else 'NO — check QASM'}")
