"""
VQE simulation for the Clique problem using only the QASM files from C2|Q>.

Run from this directory after generating the QASM:
    c2q-json --input clique_01.json --export-qasm --qasm-output-dir .
Then:
    python vqe_sim.py

Two QASM files used:
  clique_qaoa.qasm  — Ising Hamiltonian from rz/rzz coefficients
  clique_vqe.qasm   — hardware-efficient RY+CZ ansatz to optimise

4 qubits: q[v] = 1 means node v is in the clique. Target K=3 (n-1 for K4).
"""
import re
import numpy as np
from collections import Counter
from scipy.optimize import minimize
from qiskit import qasm3, transpile
from qiskit_aer import AerSimulator

EDGES = {(0,1),(0,2),(0,3),(1,2),(1,3),(2,3)}
N_NODES = 4
TARGET_K = 3

# ── Parse Ising Hamiltonian from QAOA QASM ────────────────────────────────────

with open("clique_qaoa.qasm") as f:
    qaoa_src = f.read()
with open("clique_vqe.qasm") as f:
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
print(f"Ising: {N_NODES} qubits, {len(h)} diagonal + {len(J)} off-diagonal terms")
print(f"VQE ansatz: {num_params} variational parameters")
print(f"Target: {TARGET_K}-clique in K4 (any 3-node subset)\n")

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
    return [v for v in range(N_NODES) if bits[v] == "1"]

def is_valid_clique(nodes):
    if len(nodes) != TARGET_K:
        return False
    return all((min(u,v), max(u,v)) in EDGES
               for i, u in enumerate(nodes) for v in nodes[i+1:])

print("Sampling final circuit (4096 shots)...")
qc = qasm3.loads(bind_vqe(best_params))
counts = backend.run(transpile(qc, backend), shots=4096).result().get_counts()

top = Counter(counts).most_common(8)
print(f"\n{'Bitstring':<8} {'Shots':>6}  Nodes  Valid?")
print("-" * 38)
for bitstr, cnt in top:
    nodes = decode(bitstr)
    valid = is_valid_clique(nodes)
    flag = "  ← valid clique" if valid else ""
    print(f"  {bitstr.replace(' ','')}  {cnt:>5}  {nodes}{flag}")

valid_shots = sum(cnt for b, cnt in counts.items() if is_valid_clique(decode(b)))
print(f"\nValid {TARGET_K}-clique shots: {valid_shots}/4096 = {valid_shots/4096:.1%}")
