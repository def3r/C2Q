#!/usr/bin/env bash
# Benchmark c2q-json --export-qasm for each example JSON.
# Results written to benchmark_results.txt

OUTFILE="benchmark_results.txt"
QASM_DIR="/tmp/c2q_bench_qasm"
mkdir -p "$QASM_DIR"

echo "c2q-json --export-qasm benchmark (unoptimized)" > "$OUTFILE"
echo "Date: $(date)" >> "$OUTFILE"
echo "----------------------------------------" >> "$OUTFILE"

examples=(
    "examples/addition/add_01.json"
    "examples/clique/clique_01.json"
    "examples/factor/factor_01.json"
    "examples/kcolor/kcolor_01.json"
    "examples/maxcut/maxcut_01.json"
    "examples/multiplication/mul_01.json"
    "examples/readmeExample/mis_01.json"
    "examples/subtraction/sub_01.json"
    "examples/tsp/tsp_01.json"
    "examples/vc/vc_01.json"
)

for json in "${examples[@]}"; do
    name=$(basename "$json" .json)
    echo -n "Timing $json ... "
    start=$(date +%s%N)
    python -m src.json_engine --input "$json" --export-qasm --qasm-output-dir "$QASM_DIR" > /dev/null 2>&1
    end=$(date +%s%N)
    elapsed_ms=$(( (end - start) / 1000000 ))
    echo "${elapsed_ms} ms"
    echo "$name : ${elapsed_ms} ms" >> "$OUTFILE"
done

echo "----------------------------------------" >> "$OUTFILE"
echo "Done. Results saved to $OUTFILE"
