"""
QAOA simulation for TSP using the QASM exported from C2|Q>.

Run from this directory after generating the QASM:
    c2q-json --input tsp_01.json --export-qasm --qasm-output-dir .
Then:
    python circuit_sim.py

Instance: 3-city TSP with distances [[0,2,5],[2,0,3],[5,3,0]]
Optimal tour: 0 -> 1 -> 2 -> 0  (cost = 2+3+5 = 10)

9 qubits: q[v*3 + t] = 1 means city v is visited at time step t
"""
import re
import numpy as np
from collections import Counter
from scipy.optimize import minimize
from qiskit import qasm3, transpile
from qiskit_aer import AerSimulator

DIST = [[0, 2, 5], [2, 0, 3], [5, 3, 0]]
N_CITIES = 3

with open("tsp_qaoa.qasm") as f:
    qaoa_src = f.read()

backend = AerSimulator()

def bind(src, gamma, beta):
    s = re.sub(r"input float\[64\] _theta_0_;\n", "", src)
    s = re.sub(r"input float\[64\] _theta_1_;\n", "", s)
    return s.replace("_theta_0_", str(gamma)).replace("_theta_1_", str(beta))

def decode(bitstr):
    bits = list(reversed(bitstr.replace(" ", "")))
    tour = []
    for t in range(N_CITIES):
        col = [int(bits[v * N_CITIES + t]) for v in range(N_CITIES)]
        tour.append(col.index(1) if 1 in col else -1)
    return tour

def tour_cost(tour):
    if -1 in tour or len(set(tour)) != N_CITIES:
        return None
    return sum(DIST[tour[t]][tour[(t + 1) % N_CITIES]] for t in range(N_CITIES))

def neg_valid_fraction(params, shots=256):
    qc = qasm3.loads(bind(qaoa_src, *params))
    counts = backend.run(transpile(qc, backend), shots=shots).result().get_counts()
    valid = sum(cnt for b, cnt in counts.items() if tour_cost(decode(b)) is not None)
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
print(f"Best γ={gamma:.3f}  β={beta:.3f}  valid-tour fraction≈{best_val:.1%}\n")

# ── Final sample ──────────────────────────────────────────────────────────────
qc = qasm3.loads(bind(qaoa_src, gamma, beta))
counts = backend.run(transpile(qc, backend), shots=2048).result().get_counts()

top = Counter(counts).most_common(8)
print(f"{'Bitstring':<12} {'Shots':>6}  Tour          Cost")
print("-" * 45)
for bitstr, cnt in top:
    tour = decode(bitstr)
    cost = tour_cost(tour)
    label = f"{tour}  cost={cost}" if cost is not None else f"{tour}  INVALID"
    print(f"  {bitstr.replace(' ','')}  {cnt:>5}  {label}")

valid_shots = sum(cnt for b, cnt in counts.items() if tour_cost(decode(b)) is not None)
min_cost = min((tour_cost(decode(b)) for b in counts if tour_cost(decode(b)) is not None),
               default=None)
print(f"\nValid-tour shots: {valid_shots}/2048 = {valid_shots/2048:.1%}")
print(f"Best cost found : {min_cost}  (optimal = 10)")
