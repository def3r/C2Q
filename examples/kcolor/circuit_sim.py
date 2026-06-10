"""
QAOA simulation for Graph 3-Coloring using the QASM exported from C2|Q>.

Run from this directory after generating the QASM:
    c2q-json --input kcolor_01.json --export-qasm --qasm-output-dir .
Then:
    python circuit_sim.py

Instance: 4-node diamond graph, edges (0,1),(0,2),(1,2),(1,3),(2,3), k=3 colors.
One valid 3-coloring: node 0→color 1, node 1→color 2, node 2→color 3, node 3→color 1.

12 qubits: q[v*3 + i] = 1 means node v is assigned color i.
"""
import re
import numpy as np
from collections import Counter
from scipy.optimize import minimize
from qiskit import qasm3, transpile
from qiskit_aer import AerSimulator

EDGES = [(0, 1), (0, 2), (1, 2), (1, 3), (2, 3)]
N_NODES, N_COLORS = 4, 3

with open("kcolor_qaoa.qasm") as f:
    qaoa_src = f.read()

backend = AerSimulator()

def bind(src, gamma, beta):
    s = re.sub(r"input float\[64\] _theta_0_;\n", "", src)
    s = re.sub(r"input float\[64\] _theta_1_;\n", "", s)
    return s.replace("_theta_0_", str(gamma)).replace("_theta_1_", str(beta))

def decode(bitstr):
    bits = list(reversed(bitstr.replace(" ", "")))
    colors = []
    for v in range(N_NODES):
        chunk = [int(bits[v * N_COLORS + i]) for i in range(N_COLORS)]
        colors.append(chunk.index(1) if 1 in chunk else -1)
    return colors

def count_conflicts(colors):
    if -1 in colors:
        return None
    return sum(1 for u, v in EDGES if colors[u] == colors[v])

def neg_valid_fraction(params, shots=256):
    qc = qasm3.loads(bind(qaoa_src, *params))
    counts = backend.run(transpile(qc, backend), shots=shots).result().get_counts()
    valid = sum(cnt for b, cnt in counts.items()
                if count_conflicts(decode(b)) == 0)
    return -valid / shots

# ── Parameter optimisation ────────────────────────────────────────────────────
print("Optimising QAOA parameters (3 restarts)...")
best, best_val = None, -np.inf
np.random.seed(0)
for _ in range(3):
    x0 = np.random.uniform(0, np.pi, 2)
    res = minimize(neg_valid_fraction, x0, method="COBYLA",
                   options={"maxiter": 100, "rhobeg": 0.4})
    if -res.fun > best_val:
        best_val, best = -res.fun, res.x

gamma, beta = best
print(f"Best γ={gamma:.3f}  β={beta:.3f}  valid-coloring fraction≈{best_val:.1%}\n")

# ── Final sample ──────────────────────────────────────────────────────────────
qc = qasm3.loads(bind(qaoa_src, gamma, beta))
counts = backend.run(transpile(qc, backend), shots=2048).result().get_counts()

top = Counter(counts).most_common(8)
print(f"{'Bitstring':<15} {'Shots':>6}  Colors             Conflicts")
print("-" * 55)
for bitstr, cnt in top:
    colors = decode(bitstr)
    cf = count_conflicts(colors)
    label = f"node→color {colors}  conflicts={cf}" if cf is not None else f"{colors}  INVALID"
    print(f"  {bitstr.replace(' ','')}  {cnt:>5}  {label}")

valid_shots = sum(cnt for b, cnt in counts.items()
                  if count_conflicts(decode(b)) == 0)
print(f"\nConflict-free colorings: {valid_shots}/2048 = {valid_shots/2048:.1%}")
