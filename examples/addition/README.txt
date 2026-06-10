# Addition Example

**Problem:** Compute a + b using a quantum ripple-carry adder circuit.

**Instance:** 3 + 5 = 8.

## How it works

Unlike the NPC problems (QAOA/Grover), addition uses a deterministic quantum circuit: the operand bits are encoded into input qubits, carry propagation is done with Toffoli and CNOT gates, and measurement collapses directly to the answer with probability 1 on a noiseless simulator.

## Step 1 — Generate the QASM circuit

From the repo root:

```bash
c2q-json --input examples/addition/add_01.json \
         --export-qasm \
         --qasm-output-dir examples/addition
```

This writes `add_circuit.qasm` into this directory.

## Step 2 — Inspect and simulate

```bash
cd examples/addition
python circuit_sim.py
```

The script:
1. Loads `add_circuit.qasm` and draws it as text
2. Runs a 4096-shot Aer simulation
3. Prints the dominant measurement outcome and its decimal value

**What to check:** The single dominant outcome should decode to `8` (binary `1000`).  Unlike probabilistic algorithms, all shots should give the same result.

## Circuit structure

The ripple-carry adder for n-bit operands uses `3n+1` qubits:

| Register | Qubits | Content |
|----------|--------|---------|
| A | 0…n-1 | Left operand (3) |
| B | n…2n-1 | Right operand (5) |
| Carry | 2n…3n-1 | Carry propagation ancillas |
| Sum | last qubit | Overflow bit |

The result is read from the B register after the circuit (it is overwritten in place by the sum).
