"""
Simulate the Factor Grover circuit exported from C2|Q>.

Run from this directory after generating the QASM file:
    c2q-json --input factor_01.json --export-qasm --qasm-output-dir .
Then:
    python circuit_sim.py

Expected: the two most probable outcomes decode to 3 and 7 (factors of 21).

CONSTRAINT: the oracle uses num_state_qubits = ceil(n.bit_length()/2) bits per factor
register. Both factors must fit in that width. For n=15=3x5: 5 > 2^2-1=3, so the
oracle marks nothing and the output is uniform noise. Use n=21=3x7 where both fit
in 3 bits (2^3-1=7).
"""
from qiskit import qasm3, transpile
from qiskit_aer import AerSimulator
from collections import Counter

with open("factor_grover.qasm") as f:
    qasm_str = f.read()

# Rename conflicting gate names — 'unitary' is reserved in Aer
qasm_str = qasm_str.replace("gate unitary ", "gate unitary_id ")
qasm_str = qasm_str.replace("unitary ", "unitary_id ")  # call sites too

qasm_str = qasm_str.replace("gate unitary_0 ", "gate unitary_x0 ")
qasm_str = qasm_str.replace("unitary_0 ", "unitary_x0 ")

qasm_str = qasm_str.replace("gate unitary_1 ", "gate unitary_x1 ")
qasm_str = qasm_str.replace("unitary_1 ", "unitary_x1 ")

qc = qasm3.loads(qasm_str)
print("=== Factor Grover circuit ===")
print(f"Circuit depth : {qc.depth()}")
print(f"Circuit qubits: {qc.num_qubits}")
print(f"Classical bits: {qc.num_clbits}")

backend = AerSimulator()
transpiled = transpile(qc, backend)
counts = backend.run(transpiled, shots=4096).result().get_counts()
top = Counter(counts).most_common(4)

print(f"\nTop measurement outcomes (factors of 21 = 3 × 7):")
for bitstr, count in top:
    bits = bitstr.replace(" ", "")
    val = int(bits, 2)
    print(f"  |{bits}> : {count:4d}   decoded={val}")
