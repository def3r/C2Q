"""
Run mis_qaoa.qasm on the Qiskit Aer simulator.

The QASM file uses OpenQASM 3.0 with two input parameters:
  _theta_0_  — gamma (cost layer angle)
  _theta_1_  — beta  (mixer layer angle)

Usage:
  python run_qaoa_sim.py [gamma] [beta] [shots]

Defaults: gamma=1.0, beta=0.5, shots=4096
"""

import re
import sys
from qiskit import qasm3, transpile
from qiskit_aer import AerSimulator

gamma = float(sys.argv[1]) if len(sys.argv) > 1 else 1.0
beta  = float(sys.argv[2]) if len(sys.argv) > 2 else 0.5
shots = int(sys.argv[3])   if len(sys.argv) > 3 else 4096

qasm_path = "mis_qaoa.qasm"

with open(qasm_path) as f:
    qasm_str = f.read()

# Remove 'input' declarations and substitute concrete float values
qasm_str = re.sub(r"input float\[64\] _theta_0_;\n", "", qasm_str)
qasm_str = re.sub(r"input float\[64\] _theta_1_;\n", "", qasm_str)
qasm_str = qasm_str.replace("_theta_0_", str(gamma))
qasm_str = qasm_str.replace("_theta_1_", str(beta))

qc = qasm3.loads(qasm_str)

backend = AerSimulator()
qc_t = transpile(qc, backend)
counts = backend.run(qc_t, shots=shots).result().get_counts()

print(f"gamma={gamma}  beta={beta}  shots={shots}")
print()
print(f"  {'State':6}  {'Count':>5}  {'Prob':>6}  Histogram")
for state, count in sorted(counts.items(), key=lambda x: -x[1]):
    bar  = "#" * (count * 40 // shots)
    prob = count / shots
    print(f"  {state}  {count:5d}  {prob:6.3f}  {bar}")

best = max(counts, key=counts.get)
print()
print(f"Most probable state : {best}  ({counts[best]}/{shots} shots, {counts[best]/shots:.1%})")
print()
print("Bit order: q[3] q[2] q[1] q[0]  (1 = node selected in MIS)")
print("Graph (mis_01.json): path  0 — 1 — 2 — 3")
print("Valid MIS solutions : 0101={0,2}  1010={1,3}  1001={0,3}")
