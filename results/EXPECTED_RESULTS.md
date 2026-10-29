# Expected results

- Input frame: 16 × 16 = 256 grayscale pixels.
- Threshold: 180.
- Valid interior output pixels: (16 - 2) × (16 - 2) = 196.
- Python reference output is included as `python_reference_edges.png`.
- After running the Verilog simulation, the HDL and Python edge maps should match on the interior pixels, with zero mismatches.
- The simulation output is written to `edge_pixels.hex`; waveform output is `sobel_wave.vcd` in the project root.

The HDL simulation has not been run as part of package generation unless Icarus Verilog is installed in the execution environment. Run the README instructions to produce actual local simulation results.
