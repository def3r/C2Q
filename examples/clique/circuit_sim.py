"""
QAOA simulation for the Clique problem using the QASM exported from C2|Q>.

Run from this directory after generating the QASM:
    c2q-json --input clique_01.json --export-qasm --qasm-output-dir .
Then:
    python circuit_sim.py

Instance: K4 complete graph (all 6 edges). Default clique target K=n-1=3.
Any 3-node subset is a valid 3-clique in K4.

4 qubits: q[v] = 1 means node v is in the clique.
"""
import re
import numpy as np
from collections import Counter
from scipy.optimize import minimize
from qiskit import qasm3, transpile
from qiskit_aer import AerSimulator

EDGES = {(0,1),(0,2),(0,3),(1,2),(1,3),(2,3)}
N_NODES = 4
TARGET_K = 3   # default: n - 1

with open("clique_qaoa.qasm") as f:
    qaoa_src = f.read()

backend = AerSimulator()

def bind(src, gamma, beta):
    s = re.sub(r"input float\[64\] _theta_0_;\n", "", src)
    s = re.sub(r"input float\[64\] _theta_1_;\n", "", s)
    return s.replace("_theta_0_", str(gamma)).replace("_theta_1_", str(beta))

def decode(bitstr):
    bits = list(reversed(bitstr.replace(" ", "")))
    return [v for v in range(N_NODES) if bits[v] == "1"]

def is_valid_clique(nodes):
    if len(nodes) != TARGET_K:
        return False
    return all((min(u,v), max(u,v)) in EDGES
               for i, u in enumerate(nodes) for v in nodes[i+1:])

def neg_valid_fraction(params, shots=256):
    qc = qasm3.loads(bind(qaoa_src, *params))
    counts = backend.run(transpile(qc, backend), shots=shots).result().get_counts()
    valid = sum(cnt for b, cnt in counts.items() if is_valid_clique(decode(b)))
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
print(f"Best γ={gamma:.3f}  β={beta:.3f}  valid-clique fraction≈{best_val:.1%}\n")

# ── Final sample ──────────────────────────────────────────────────────────────
qc = qasm3.loads(bind(qaoa_src, gamma, beta))
counts = backend.run(transpile(qc, backend), shots=2048).result().get_counts()

top = Counter(counts).most_common(8)
print(f"{'Bitstring':<8} {'Shots':>6}  Nodes in set       Valid K={TARGET_K}-clique?")
print("-" * 50)
for bitstr, cnt in top:
    nodes = decode(bitstr)
    valid = is_valid_clique(nodes)
    flag = "  ← valid clique" if valid else ""
    print(f"  {bitstr.replace(' ','')}  {cnt:>5}  {nodes}{flag}")

valid_shots = sum(cnt for b, cnt in counts.items() if is_valid_clique(decode(b)))
print(f"\nValid {TARGET_K}-clique shots: {valid_shots}/2048 = {valid_shots/2048:.1%}")
