"""
Simulate the MaxCut QAOA circuit exported from C2|Q>.

Run from this directory after generating the QASM files:
    c2q-json --input maxcut_01.json --export-qasm --qasm-output-dir .
Then:
    python circuit_sim.py
"""
import re
from qiskit import qasm3, transpile
from qiskit_aer import AerSimulator
from collections import Counter

# Approximate optimal p=1 QAOA parameters for a 4-cycle graph
gamma, beta = 0.785, 1.0

# --- Load and bind QAOA parameters ---
with open("max_cut_qaoa.qasm") as f:
    qasm_str = f.read()

qasm_str = re.sub(r"input float\[64\] _theta_0_;\n", "", qasm_str)
qasm_str = re.sub(r"input float\[64\] _theta_1_;\n", "", qasm_str)
qasm_str = qasm_str.replace("_theta_0_", str(gamma))
qasm_str = qasm_str.replace("_theta_1_", str(beta))

qc = qasm3.loads(qasm_str)

print("=== MaxCut QAOA circuit (gamma={}, beta={}) ===".format(gamma, beta))
print(qc.draw(output="text", fold=-1))

# --- Simulate ---
# The QAOA QASM already includes measurement gates; run it directly.
backend = AerSimulator()
transpiled = transpile(qc, backend)
counts = backend.run(transpiled, shots=4096).result().get_counts()

top = Counter(counts).most_common(4)
print("\nTop measurement outcomes (bitstring → count):")
for bitstr, count in top:
    bits = bitstr.replace(" ", "")
    partition_0 = [i for i, b in enumerate(reversed(bits)) if b == "0"]
    partition_1 = [i for i, b in enumerate(reversed(bits)) if b == "1"]
    print(f"  |{bits}> : {count:4d}   S0={partition_0}  S1={partition_1}")
