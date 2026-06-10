"""
Quantum multiplication circuit simulation using the QASM exported from C2|Q>.

Run from this directory after generating the QASM:
    c2q-json --input mul_01.json --export-qasm --qasm-output-dir .
Then:
    python circuit_sim.py

Instance: 7 × 11 = 77.
The circuit is deterministic — one shot suffices to read the result.

The RGQFTMultiplier generates gate names 'unitary', 'unitary_0', ..., 'unitary_N'
which conflict with Aer's reserved 'unitary' built-in. We rename them all to
'umul' / 'umul_0' etc. before loading.
"""
from qiskit import qasm3, transpile
from qiskit_aer import AerSimulator

with open("mul_circuit.qasm") as f:
    src = f.read()

# Rename all 'unitary*' gate variants to 'umul*' to avoid Aer's reserved name.
src = src.replace("unitary", "umul")

qc = qasm3.loads(src)
backend = AerSimulator()
result = backend.run(transpile(qc, backend), shots=1).result()
counts = result.get_counts()

bitstr = next(iter(counts)).replace(" ", "")
value = int(bitstr, 2)

print(f"Raw bitstring : {bitstr}")
print(f"Decoded value : {value}")
print(f"Expected      : 7 × 11 = 77")
print(f"Correct       : {'yes' if value == 77 else 'NO — check QASM'}")
