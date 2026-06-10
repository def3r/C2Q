# MaxCut Example

**Problem:** Partition the nodes of a graph into two sets S0 and S1 to maximise the number of edges crossing the partition.

**Instance:** 4-node cycle graph — nodes 0-1-2-3-0.

## Step 1 — Generate QASM circuits

From the repo root (requires `pip install -e .`):

```bash
c2q-json --input examples/maxcut/maxcut_01.json \
         --export-qasm \
         --qasm-output-dir examples/maxcut
```

This writes three files into this directory:
- `max_cut_qaoa.qasm` — parametric QAOA circuit (gamma/beta as `input float[64]`)
- `max_cut_vqe.qasm`  — parametric VQE circuit
- *(Grover not exported for MaxCut; use MIS example to see Grover)*

## Step 2 — Inspect and simulate

```bash
cd examples/maxcut
python circuit_sim.py
```

The script:
1. Loads `max_cut_qaoa.qasm`, substitutes `gamma=1.0, beta=0.5` for the parametric inputs
2. Draws the circuit as text
3. Runs 4096-shot Aer simulation
4. Prints the top bitstrings with their partition assignments

**What to check:** For the 4-cycle the optimal cuts have value 4 (all edges cut), achieved by alternating assignments like `0101` or `1010`. These should be among the top outcomes.

## What the circuit looks like

The QAOA circuit has one layer (p=1):
1. Hadamard on all qubits (uniform superposition)
2. Cost unitary — phase kickback from QUBO interactions
3. Mixer unitary — Rx rotations parametrized by beta

Increasing `gamma` / `beta` values or using more layers (`p>1`) improves solution quality.
