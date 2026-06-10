"""
QAOA simulation for Minimum Vertex Cover using the QASM exported from C2|Q>.

Run from this directory after generating the QASM:
    c2q-json --input vc_01.json --export-qasm --qasm-output-dir .
Then:
    python circuit_sim.py

Instance: 4-node cycle graph, edges (0,1),(1,2),(2,3),(3,0).
Minimum vertex cover size = 2: either {0,2} or {1,3}.

4 qubits: q[v] = 1 means node v is included in the cover.
Note: QASM files are named mvc_*.qasm because the class is MVC.
"""
import re
import numpy as np
from collections import Counter
from scipy.optimize import minimize
from qiskit import qasm3, transpile
from qiskit_aer import AerSimulator

EDGES = [(0, 1), (1, 2), (2, 3), (3, 0)]
N_NODES = 4
MIN_COVER_SIZE = 2

with open("mvc_qaoa.qasm") as f:
    qaoa_src = f.read()

backend = AerSimulator()

def bind(src, gamma, beta):
    s = re.sub(r"input float\[64\] _theta_0_;\n", "", src)
    s = re.sub(r"input float\[64\] _theta_1_;\n", "", s)
    return s.replace("_theta_0_", str(gamma)).replace("_theta_1_", str(beta))

def decode(bitstr):
    bits = list(reversed(bitstr.replace(" ", "")))
    return [v for v in range(N_NODES) if bits[v] == "1"]

def is_valid_cover(nodes):
    node_set = set(nodes)
    return all(u in node_set or v in node_set for u, v in EDGES)

def neg_min_cover_fraction(params, shots=256):
    qc = qasm3.loads(bind(qaoa_src, *params))
    counts = backend.run(transpile(qc, backend), shots=shots).result().get_counts()
    # reward valid covers of minimum size
    good = sum(cnt for b, cnt in counts.items()
               if is_valid_cover(decode(b)) and len(decode(b)) == MIN_COVER_SIZE)
    return -good / shots

# ── Parameter optimisation ────────────────────────────────────────────────────
print("Optimising QAOA parameters (3 restarts)...")
best, best_val = None, -np.inf
np.random.seed(0)
for _ in range(3):
    x0 = np.random.uniform(0, np.pi, 2)
    res = minimize(neg_min_cover_fraction, x0, method="COBYLA",
                   options={"maxiter": 100, "rhobeg": 0.4})
    if -res.fun > best_val:
        best_val, best = -res.fun, res.x

gamma, beta = best
print(f"Best γ={gamma:.3f}  β={beta:.3f}  min-cover fraction≈{best_val:.1%}\n")

# ── Final sample ──────────────────────────────────────────────────────────────
qc = qasm3.loads(bind(qaoa_src, gamma, beta))
counts = backend.run(transpile(qc, backend), shots=2048).result().get_counts()

top = Counter(counts).most_common(8)
print(f"{'Bitstring':<8} {'Shots':>6}  Nodes in cover    Valid?  Size")
print("-" * 52)
for bitstr, cnt in top:
    nodes = decode(bitstr)
    valid = is_valid_cover(nodes)
    flag = "  ← min cover" if valid and len(nodes) == MIN_COVER_SIZE else ("  ← valid" if valid else "")
    print(f"  {bitstr.replace(' ','')}  {cnt:>5}  {nodes}   {'yes' if valid else 'no':>5}     {len(nodes)}{flag}")

valid_shots = sum(cnt for b, cnt in counts.items() if is_valid_cover(decode(b)))
min_shots = sum(cnt for b, cnt in counts.items()
                if is_valid_cover(decode(b)) and len(decode(b)) == MIN_COVER_SIZE)
print(f"\nValid covers  : {valid_shots}/2048 = {valid_shots/2048:.1%}")
print(f"Min covers (≤{MIN_COVER_SIZE}): {min_shots}/2048 = {min_shots/2048:.1%}")
