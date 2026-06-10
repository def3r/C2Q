# Factorization Example

**Problem:** Given a semiprime N = p × q, find p and q using Grover's algorithm applied to a quantum multiplication oracle.

**Instance:** Factor 21 (= 3 × 7).

## How it works

The circuit builds a multiplication oracle that encodes `a * b == 21` in phase, then uses Grover's diffusion to amplify the states corresponding to `(a=3, b=7)` and `(a=7, b=3)`.

### Register width constraint

The oracle allocates `num_state_qubits = ceil(n.bit_length() / 2)` qubits per factor register.
Both prime factors **must fit** in that many bits, i.e. both must be <= `2^num_state_qubits - 1`.

| n         | num_state_qubits | max factor | works? |
|-----------|-----------------|------------|--------|
| 15 = 3×5  | 2               | 3          | **No** — 5 > 3, oracle marks nothing → uniform noise |
| 21 = 3×7  | 3               | 7          | Yes    |
| 35 = 5×7  | 3               | 7          | Yes    |
| 6  = 2×3  | 2               | 3          | Yes    |

## Step 1 — Generate the QASM circuit

From the repo root:

```bash
c2q-json --input examples/factor/factor_01.json \
         --export-qasm \
         --qasm-output-dir examples/factor
```

This writes `factor_grover.qasm` into this directory.

## Step 2 — Inspect and simulate

```bash
cd examples/factor
python circuit_sim.py
```

The script:
1. Loads `factor_grover.qasm` and draws the circuit as text
2. Runs 4096-shot Aer simulation
3. Prints the top measurement outcomes and decodes them to integer factor candidates

**What to check:** The two most probable outcomes should decode to `3` and `7`
(each ~2300/4096 shots). All other values should be much lower (~900 each).
The circuit only measures the `a` factor register (num_state_qubits bits),
so `decoded` is the value of factor `a`.

## Circuit structure

| Layer | Purpose |
|-------|---------|
| Hadamard prep | Uniform superposition over all (a, b) pairs |
| Multiplication oracle (RGQFTMultiplier) | Encodes a*b in result register |
| Phase kickback | Marks states where result == 21 |
| Oracle inverse | Uncomputes the multiplier |
| Grover diffusion | Amplifies marked states |

The oracle is built from Qiskit's `RGQFTMultiplier` (QFT-based integer multiplier).
