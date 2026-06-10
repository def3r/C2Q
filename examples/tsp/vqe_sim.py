"""
VQE simulation for TSP using only the QASM files exported from C2|Q>.

Run from this directory after generating the QASM:
    c2q-json --input tsp_01.json --export-qasm --qasm-output-dir .
Then:
    python vqe_sim.py

Two QASM files used:
  tsp_qaoa.qasm  — Ising Hamiltonian extracted from rz/rzz gate coefficients
  tsp_vqe.qasm   — hardware-efficient RY+CZ ansatz to optimise

9 qubits: q[v*3 + t] = 1 means city v is visited at time step t.
"""
import re
import numpy as np
from collections import Counter
from scipy.optimize import minimize
from qiskit import qasm3, transpile
from qiskit_aer import AerSimulator

DIST = [[0, 2, 5], [2, 0, 3], [5, 3, 0]]
N_CITIES = 3

# ── Parse Ising Hamiltonian from QAOA QASM ────────────────────────────────────

with open("tsp_qaoa.qasm") as f:
    qaoa_src = f.read()
with open("tsp_vqe.qasm") as f:
    vqe_src = f.read()

h, J = {}, {}
for m in re.finditer(r"rz\((-?[\d.]+)\*_theta_0_\) q\[(\d+)\]", qaoa_src):
    i = int(m.group(2))
    h[i] = h.get(i, 0) + float(m.group(1)) / 2
for m in re.finditer(r"rzz\((-?[\d.]+)\*_theta_0_\) q\[(\d+)\], q\[(\d+)\]", qaoa_src):
    i, j = int(m.group(2)), int(m.group(3))
    k = (min(i, j), max(i, j))
    J[k] = J.get(k, 0) + float(m.group(1)) / 2

num_params = len(re.findall(r"input float\[64\] _θ_\d+_;", vqe_src))
num_qubits = max(max(h), max(j for pair in J for j in pair)) + 1
print(f"Ising: {num_qubits} qubits, {len(h)} diagonal + {len(J)} off-diagonal terms")
print(f"VQE ansatz: {num_params} variational parameters\n")

# ── Cost function ─────────────────────────────────────────────────────────────

backend = AerSimulator()

def bind_vqe(params):
    s = vqe_src
    for i, p in enumerate(params):
        s = s.replace(f"input float[64] _θ_{i}_;\n", "")
        s = s.replace(f"_θ_{i}_", str(p))
    return s

def ising_energy(bits):
    Z = [1 - 2 * b for b in bits]
    e = sum(h.get(i, 0) * Z[i] for i in range(len(bits)))
    e += sum(v * Z[i] * Z[j] for (i, j), v in J.items())
    return e

def expected_energy(params, shots=512):
    qc = qasm3.loads(bind_vqe(params))
    counts = backend.run(transpile(qc, backend), shots=shots).result().get_counts()
    total = sum(counts.values())
    return sum(cnt * ising_energy([int(b) for b in reversed(bs.replace(" ", ""))])
               for bs, cnt in counts.items()) / total

# ── Optimisation ──────────────────────────────────────────────────────────────

print("Running VQE optimisation (5 restarts × COBYLA)...")
print(f"{'Restart':>7}  {'E[H]':>9}  params[:3]")

best_params, best_e = None, np.inf
np.random.seed(0)
for restart in range(5):
    x0 = np.random.uniform(0, 2 * np.pi, num_params)
    res = minimize(expected_energy, x0, method="COBYLA",
                   options={"maxiter": 300, "rhobeg": 0.5})
    marker = " ← best" if res.fun < best_e else ""
    print(f"  {restart+1:>5}    {res.fun:>8.3f}  {[round(p,2) for p in res.x[:3]]}...{marker}")
    if res.fun < best_e:
        best_e, best_params = res.fun, res.x

print(f"\nConverged — E[H] = {best_e:.4f}\n")

# ── Final sample ──────────────────────────────────────────────────────────────

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

print("Sampling final circuit (4096 shots)...")
qc = qasm3.loads(bind_vqe(best_params))
counts = backend.run(transpile(qc, backend), shots=4096).result().get_counts()

top = Counter(counts).most_common(8)
print(f"\n{'Bitstring':<12} {'Shots':>6}  Tour          Cost")
print("-" * 50)
for bitstr, cnt in top:
    tour = decode(bitstr)
    cost = tour_cost(tour)
    label = f"{tour}  cost={cost}" if cost is not None else f"{tour}  INVALID"
    print(f"  {bitstr.replace(' ','')}  {cnt:>5}  {label}")

valid_shots = sum(cnt for b, cnt in counts.items() if tour_cost(decode(b)) is not None)
optimal_shots = sum(cnt for b, cnt in counts.items() if tour_cost(decode(b)) == 10)
print(f"\nValid-tour shots : {valid_shots}/4096 = {valid_shots/4096:.1%}")
print(f"Optimal-tour shots: {optimal_shots}/4096 = {optimal_shots/4096:.1%}  (cost=10)")
