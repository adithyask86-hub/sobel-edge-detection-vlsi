# Verilog-Based Sobel Edge Detection Accelerator with Python Verification

## Abstract

Edge detection is a fundamental operation in digital image processing and computer vision. This mini project designs and verifies a Sobel edge detection accelerator using Verilog HDL. The design accepts 8-bit grayscale pixels in raster order, uses line buffers and a sliding 3×3 window, calculates horizontal and vertical image gradients, and applies a programmable threshold to generate a binary edge image. A Python program generates a sample image, runs the HDL simulation through Icarus Verilog, reconstructs the result, and checks it against an independent software reference. The project demonstrates the mapping of an image-processing algorithm to a digital hardware datapath without requiring a physical FPGA board.

## 1. Introduction

Image processing can be accelerated by dedicated digital hardware because each pixel can be processed using predictable arithmetic and control logic. The Sobel operator is a common gradient-based edge detector. It approximates changes in image intensity in the horizontal and vertical directions using two 3×3 convolution kernels.

The project is suitable for a VLSI course because it combines combinational arithmetic, registers, line buffers, clocked control, streaming interfaces, and verification through simulation.

## 2. Problem statement

Develop a software-simulatable Verilog design that accepts a grayscale image as a stream of 8-bit pixels and outputs a binary edge map. Verify its correctness against a Python reference and inspect its timing behavior through a waveform.

## 3. Objectives

1. Implement Sobel gradient calculations in Verilog.
2. Design a streaming architecture using two line buffers and a 3×3 sliding window.
3. Apply a configurable threshold to the gradient magnitude approximation.
4. Create a self-checking workflow using a testbench and Python reference.
5. Measure output count and compare HDL results with the reference.
6. Document the design, simulation procedure, and limitations.

## 4. Theory

For a 3×3 window:

```text
p00 p01 p02
p10 p11 p12
p20 p21 p22
```

The Sobel horizontal gradient is:

```text
Gx = -p00 + p02 - 2*p10 + 2*p12 - p20 + p22
```

The vertical gradient is:

```text
Gy = -p00 - 2*p01 - p02 + p20 + 2*p21 + p22
```

The implementation uses the approximation:

```text
Magnitude = |Gx| + |Gy|
```

The output is 255 if `Magnitude >= threshold`; otherwise it is 0. A 16-bit score output is retained for analysis. The true Euclidean magnitude is `sqrt(Gx² + Gy²)`, but the absolute-sum approximation avoids square-root hardware and is commonly useful in low-cost designs.

## 5. System architecture

The system consists of:
- Python sample-image generator and reference model.
- Input pixel memory file.
- Verilog streaming controller.
- Two line buffers storing previous image rows.
- Horizontal registers forming the 3×3 pixel window.
- Sobel arithmetic core.
- Threshold comparator and binary output.
- Testbench that writes output coordinates, edge pixels, and scores.
- Python reconstruction and verification.

See `block_diagram.png` in the project directory.

## 6. Module description

### 6.1 `sobel_core.v`

A combinational datapath. It calculates signed `Gx` and `Gy`, converts them to absolute values, adds them, and compares the result with the threshold.

### 6.2 `sobel_stream.v`

A clocked stream processor. It accepts pixels in raster order, stores prior rows in two line buffers, and maintains horizontal window registers. Output is valid for interior pixels only. The output coordinate is one pixel left and one row above the current incoming pixel because the 3×3 window is complete at its bottom-right corner.

### 6.3 `tb_sobel_stream.v`

The testbench reads `sample_data/input_pixels.hex`, applies reset, streams all 256 pixels, captures valid outputs, writes `results/edge_pixels.hex`, and generates a VCD waveform.

### 6.4 `run_sobel.py`

The Python script creates a deterministic sample image, converts pixels to hexadecimal, invokes Icarus Verilog, reconstructs the HDL edge map, computes a reference result, and reports any mismatch in the interior region.

## 7. Block diagram

```text
Sample grayscale image
          |
          v
  Python pixel serializer
          |
          v
  input_pixels.hex
          |
          v
  Verilog streaming input
          |
          v
  Two line buffers + 3x3 window
          |
          v
  Sobel Gx/Gy arithmetic
          |
          v
  |Gx| + |Gy| and threshold
          |
          v
  Binary edge pixel + score
          |
          v
  Testbench output file
          |
          v
  Python image reconstruction
          |
          v
  HDL/reference comparison
```

## 8. Tools and implementation procedure

1. Install Python, NumPy, Pillow, and Icarus Verilog.
2. Run `python python/run_sobel.py` from the project root.
3. The script generates a 16×16 grayscale sample image and pixel memory file.
4. Icarus Verilog compiles the Sobel core, streaming module, and testbench.
5. The simulator applies reset and streams the image.
6. The testbench records valid edge outputs and creates a VCD waveform.
7. Python reconstructs the output image and compares the interior pixels against the reference.
8. Open the waveform with GTKWave for timing inspection.

## 9. Test plan

| Test | Purpose | Expected result |
|---|---|---|
| Reset | Initialize counters, buffers, and outputs | Outputs inactive during reset |
| 16×16 frame | Verify complete raster scan | 256 input pixels consumed |
| Interior output count | Verify window-valid condition | 196 output records |
| Flat regions | Check low gradient response | Mostly black pixels |
| Strong intensity boundaries | Check edge response | White pixels near detected boundaries |
| Threshold change | Check programmability | Higher threshold generally yields fewer edge pixels |
| Reference comparison | Check HDL arithmetic and alignment | Zero interior mismatches |

## 10. Results

The simulation is expected to process 256 input pixels and emit 196 interior edge pixels. The Python reference compares all 196 valid interior positions with the HDL result. A successful run reports `Mismatch count: 0` and `Status: PASS`.

Actual results should be recorded from the user's local simulator output. Do not report a measured clock frequency or FPGA resource count unless synthesis is performed for a specified target device.

## 11. Advantages

- No physical FPGA board is required.
- Modular RTL is easy to simulate and debug.
- The threshold can be changed without modifying the datapath.
- Streaming architecture demonstrates line-buffer reuse.
- Python provides an independent reference and visual results.
- The design is extensible to Prewitt filtering, threshold selection, or multiple image-processing modes.

## 12. Limitations

- The sample image is only 16×16 pixels to keep simulation small.
- The output omits the outer one-pixel border because a full 3×3 neighborhood is unavailable there.
- The gradient magnitude uses `|Gx| + |Gy|`, not exact Euclidean magnitude.
- This project demonstrates RTL simulation, not physical timing closure or measured FPGA performance.
- The line-buffer array implementation and asynchronous array reads should be reviewed for synthesis compatibility if the project is later moved to a particular FPGA target.

## 13. Future enhancements

1. Support configurable frame dimensions.
2. Add a selectable threshold register.
3. Compare Sobel and Prewitt operators.
4. Add grayscale conversion to create an RGB-to-edge pipeline.
5. Add a more comprehensive self-checking testbench with assertions.
6. Synthesize for a specific FPGA and report LUT, flip-flop, memory, and timing estimates.

## 14. Conclusion

This project demonstrates how a classic image-processing operation can be expressed as digital hardware. The Sobel core performs gradient arithmetic, while line buffers and shift registers provide the required pixel neighborhood. The simulation-only flow combines Verilog RTL, a testbench, waveform inspection, and Python-based image verification, making it a complete software-based VLSI mini project.

## References

1. I. Sobel and G. Feldman, “A 3×3 Isotropic Gradient Operator for Image Processing,” presentation at Stanford Artificial Intelligence Project, 1968.
2. R. C. Gonzalez and R. E. Woods, *Digital Image Processing*, Pearson.
3. IEEE Standard Verilog Hardware Description Language, IEEE Std 1364.
