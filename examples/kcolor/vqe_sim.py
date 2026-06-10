"""
VQE simulation for Graph 3-Coloring using only the QASM files from C2|Q>.

Run from this directory after generating the QASM:
    c2q-json --input kcolor_01.json --export-qasm --qasm-output-dir .
Then:
    python vqe_sim.py

Two QASM files used:
  kcolor_qaoa.qasm  — Ising Hamiltonian from rz/rzz coefficients
  kcolor_vqe.qasm   — hardware-efficient RY+CZ ansatz to optimise

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

# ── Parse Ising Hamiltonian from QAOA QASM ────────────────────────────────────

with open("kcolor_qaoa.qasm") as f:
    qaoa_src = f.read()
with open("kcolor_vqe.qasm") as f:
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
num_qubits = N_NODES * N_COLORS
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
    colors = []
    for v in range(N_NODES):
        chunk = [int(bits[v * N_COLORS + i]) for i in range(N_COLORS)]
        colors.append(chunk.index(1) if 1 in chunk else -1)
    return colors

def count_conflicts(colors):
    if -1 in colors:
        return None
    return sum(1 for u, v in EDGES if colors[u] == colors[v])

print("Sampling final circuit (4096 shots)...")
qc = qasm3.loads(bind_vqe(best_params))
counts = backend.run(transpile(qc, backend), shots=4096).result().get_counts()

top = Counter(counts).most_common(8)
print(f"\n{'Bitstring':<15} {'Shots':>6}  Colors             Conflicts")
print("-" * 60)
for bitstr, cnt in top:
    colors = decode(bitstr)
    cf = count_conflicts(colors)
    label = f"node→color {colors}  conflicts={cf}" if cf is not None else f"{colors}  INVALID"
    flag = "  ← valid" if cf == 0 else ""
    print(f"  {bitstr.replace(' ','')}  {cnt:>5}  {label}{flag}")

valid_shots = sum(cnt for b, cnt in counts.items()
                  if count_conflicts(decode(b)) == 0)
print(f"\nConflict-free colorings: {valid_shots}/4096 = {valid_shots/4096:.1%}")
