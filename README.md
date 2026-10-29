# Verilog-Based Sobel Edge Detection Accelerator with Python Verification

[![Verilog HDL](https://img.shields.io/badge/HDL-Verilog_IEEE--1364-blue.svg)](rtl/)
[![Simulator](https://img.shields.io/badge/Simulator-Icarus_Verilog_13.0-green.svg)](https://steveicarus.github.io/iverilog/)
[![Verification](https://img.shields.io/badge/Verification-Bit--Exact_PASS-brightgreen.svg)](results/verification.txt)
[![UI](https://img.shields.io/badge/UI-Streamlit-red.svg)](app.py)

An interactive, cycle-accurate VLSI mini-project implementing a hardware-accelerated 2D Sobel edge detector in synthesizable Verilog HDL with genuine Icarus Verilog simulation and bit-exact Python verification. Supports resolutions up to **256×256** with dual **Grayscale Sobel Edge** and **Binary Edge Map** visualization.

---

## 1. Project Overview

This project bridges digital VLSI datapath design and modern software visualization. A grayscale raster-scanned image is streamed pixel-by-pixel into a clocked Verilog pipeline. The RTL design uses:
- **Dual Line Buffers** to hold previous scanlines in on-chip storage.
- A **3×3 Sliding Window** to tap spatial neighborhoods with zero external memory re-reads.
- A **Combinational Sobel Arithmetic Core** that computes signed horizontal ($G_x$) and vertical ($G_y$) gradients.
- An **L1 Magnitude Approximator** ($|G_x| + |G_y|$) and programmable threshold comparator that asserts binary edge pixels.

Unlike purely software filters, **the hardware simulation is the source of truth**:
- Image pixels are serialized to memory format (`input_pixels.hex`).
- Icarus Verilog compiles and simulates the actual Verilog RTL.
- The simulator emits pixel coordinates, edge bits, and gradient scores (`edge_pixels.hex`).
- Python reconstructs both the **Grayscale Sobel Edge Image** (continuous gradient magnitude) and the **Binary Edge Map** (threshold-gated).
- Cycle-accurate, bit-exact verification against an independent software reference is performed on all interior pixels.
- Standard GTKWave VCD waveforms (`sobel_wave.vcd`) are generated for signal timing analysis.

---

## 2. Directory Structure

```text
sobel_edge_detection_vlsi/
├── app.py                      # Interactive Streamlit Web Application
├── block_diagram.png           # Hardware datapath block diagram
├── README.md                   # Complete documentation and setup guide
├── requirements.txt            # Python dependencies
├── rtl/                        # Synthesizable Verilog RTL source
│   ├── sobel_core.v            # Combinational gradient & threshold datapath
│   └── sobel_stream.v          # Raster stream controller with dual line buffers
├── tb/                         # Verilog Testbench
│   └── tb_sobel_stream.v       # Parameterized testbench with runtime plusargs
├── python/                     # Python Orchestration & Reference Engine
│   ├── sobel_engine.py         # Toolchain discovery, compiler, simulator & verifier
│   └── run_sobel.py            # CLI simulation and verification runner
├── sample_data/                # Input test images and memory hex
│   ├── sample_input.png        # Baseline input image
│   ├── sample_input.pgm        # PGM grayscale format
│   └── input_pixels.hex        # Hexadecimal pixel stream for $readmemh
├── results/                    # Generated simulation outputs & artifacts
│   ├── edge_pixels.hex         # Simulation output records (x y edge score)
│   ├── hdl_edges.png           # Reconstructed hardware binary edge map
│   ├── hdl_gray_edges.png      # Continuous grayscale edge magnitude image
│   ├── hdl_edge_scores_preview.png # Hardware gradient magnitude heatmap
│   ├── python_reference_edges.png  # Independent Python reference edge map
│   └── verification.txt        # Bit-exact verification audit log
├── tests/                      # Automated test suite
│   └── test_sobel.py           # Pytest test cases for RTL, VVP, and verification
├── report/                     # Academic documentation
│   └── Project_Report.md       # Full VLSI project report
└── sobel_wave.vcd              # GTKWave-compatible waveform dump
```

---

## 3. Quick Start (Single Simple Launch Command)

### Prerequisites

- Python 3.9+
- Icarus Verilog (`iverilog` and `vvp`)

### macOS Intel Setup

1. **Install dependencies via Homebrew:**
   ```bash
   brew install icarus-verilog
   brew install --cask gtkwave
   ```
   *(Note: The project automatically detects Icarus Verilog in standard paths including `/tmp/eda/bin`, `/usr/local/bin`, and `/opt/homebrew/bin`.)*

2. **Install Python packages:**
   ```bash
   python3 -m pip install -r requirements.txt
   ```

### Launch the Application

Run the following command from the project root:

```bash
streamlit run app.py
```

The web dashboard will automatically open at `http://localhost:8501`.

---

## 4. Key Application Improvements

1. **Dual Edge Visualization:**
   - **Grayscale Sobel Edge Image:** Displays the full continuous gradient magnitude ($|G_x| + |G_y|$) in smooth grayscale, where strong edges appear bright white against a dark background, exactly like conventional image processing textbooks.
   - **Binary Edge Map:** Displays the hardware-thresholded edge map, where pixels $\ge \text{threshold}$ are 255 (white) and below are 0 (black).

2. **High-Resolution Support (up to 256×256):**
   - **128×128 (Recommended Default):** Streams 16,384 clock cycles with 15,876 interior pixels in ~1.0 second. Edges are sharp, thin, and continuous rather than blocky.
   - **256×256 (Ultra Resolution):** Streams 65,536 clock cycles with 64,516 interior pixels in ~3.8s with full VCD waveform (or ~0.5s with VCD toggled off).
   - **16×16 / 32×32 / 64×64:** Coarse hardware options retained for low-complexity hardware inspection.

3. **Gradient Magnitude & Threshold Analytics:**
   - Investigates the distribution of edge scores across the image.
   - Displays peak score, mean score, and the exact count and percentage of pixels meeting the active threshold.
   - Explains single-pixel edge detection at high thresholds: if a high threshold (e.g. 600) is set above the second-highest score in an image (e.g. 546), only the single peak pixel (e.g. 608) is asserted as white.

4. **Dynamic Update & Cycle-Accurate Verification:**
   - Adjusting the threshold slider passes `+threshold={val}` directly to the Verilog simulation.
   - Python reference model verifies every coordinate $(x, y)$ on the interior grid with 0 allowable mismatches.

---

## 5. Command-Line Simulation & Verification

To run the simulation and verification directly from the command line:

```bash
python3 python/run_sobel.py --width 128 --height 128 --threshold 180
```

### Options:
```bash
python3 python/run_sobel.py --threshold 220 --width 256 --height 256 --no-vcd
```

---

## 6. Automated Test Suite

Run the integration test suite using `pytest`:

```bash
python3 -m pytest tests/test_sobel.py -v
```

Tests cover:
- Toolchain discovery and path resolution.
- Baseline 16×16 benchmark simulation (0 mismatches).
- High-resolution 128×128 hardware simulation (15,876 interior pixels, 0 mismatches).
- Ultra-resolution 256×256 hardware simulation (64,516 interior pixels, 0 mismatches).
- Grayscale edge normalization to 8-bit dynamic range.
- Threshold sensitivity and score distribution counting.
- Peak score and single-pixel threshold gating.
- VCD waveform generation and header integrity.

---

## 7. Viewing Waveforms in GTKWave

```bash
gtkwave sobel_wave.vcd
```

Recommended signals to inspect:
- `tb_sobel_stream.clk`: Master pixel clock.
- `tb_sobel_stream.rst`: Synchronous reset.
- `tb_sobel_stream.pixel_valid`: Raster data valid strobe.
- `tb_sobel_stream.pixel_in[7:0]`: Input pixel stream.
- `tb_sobel_stream.dut.row[15:0]`, `dut.col[15:0]`: Raster position counters.
- `tb_sobel_stream.edge_valid`: Valid interior output strobe.
- `tb_sobel_stream.edge_out[7:0]`: Hardware binary edge output (0x00 / 0xFF).
- `tb_sobel_stream.edge_score_out[15:0]`: Gradient magnitude score.
- `tb_sobel_stream.out_x[15:0]`, `out_y[15:0]`: Output coordinates.
