#!/usr/bin/env python3
"""
Unit and integration tests for Verilog-based Sobel Edge Detection Accelerator.
Tests toolchain discovery, RTL compilation, VVP simulation, resolution scaling up to 256x256,
threshold variations, grayscale edge normalization, and cycle-accurate verification.
"""

from pathlib import Path
import sys
import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))
import sobel_engine


def test_toolchain_discovery():
    """Verify Icarus Verilog is discovered and available in the environment."""
    info = sobel_engine.get_toolchain_info()
    assert info["simulator_available"], f"Simulator not available: {info.get('error_message')}"
    assert info["iverilog_path"] is not None
    assert info["vvp_path"] is not None


def test_baseline_16x16_simulation():
    """Verify the 16x16 baseline processes 256 pixels and matches Python reference with 0 mismatches."""
    img = sobel_engine.make_benchmark_image(16, 16)
    res = sobel_engine.execute_full_flow(img, threshold=180, force_recompile=True, dump_vcd=True)

    verif = res["verification"]
    assert verif["status"] == "PASS"
    assert verif["edge_mismatches"] == 0
    assert verif["score_mismatches"] == 0
    assert verif["tested_interior_pixels"] == 196
    assert res["metrics"]["input_pixels"] == 256
    assert res["metrics"]["cycles"] == 256
    assert res["metrics"]["captured_outputs"] == 196


def test_high_resolution_128x128_simulation():
    """Verify hardware datapath scales to 128x128 with genuine Verilog simulation and zero mismatches."""
    img = sobel_engine.make_benchmark_image(128, 128)
    res = sobel_engine.execute_full_flow(img, threshold=180, force_recompile=True, dump_vcd=False)

    verif = res["verification"]
    assert verif["status"] == "PASS"
    assert verif["tested_interior_pixels"] == (128 - 2) * (128 - 2)  # 15,876
    assert verif["edge_mismatches"] == 0
    assert verif["score_mismatches"] == 0
    assert res["metrics"]["input_pixels"] == 16384
    assert res["metrics"]["captured_outputs"] == 15876


def test_ultra_resolution_256x256_simulation():
    """Verify hardware datapath scales to 256x256 (65,536 clocks) with genuine Verilog simulation and zero mismatches."""
    img = sobel_engine.make_benchmark_image(256, 256)
    res = sobel_engine.execute_full_flow(img, threshold=180, force_recompile=True, dump_vcd=False)

    verif = res["verification"]
    assert verif["status"] == "PASS"
    assert verif["tested_interior_pixels"] == (256 - 2) * (256 - 2)  # 64,516
    assert verif["edge_mismatches"] == 0
    assert verif["score_mismatches"] == 0
    assert res["metrics"]["input_pixels"] == 65536
    assert res["metrics"]["captured_outputs"] == 64516


def test_grayscale_edge_normalization():
    """Verify conversion of 16-bit hardware gradient scores into conventional 8-bit grayscale edge image."""
    scores = np.array([
        [0, 0, 0, 0],
        [0, 100, 500, 0],
        [0, 1000, 200, 0],
        [0, 0, 0, 0]
    ], dtype=np.uint16)
    gray = sobel_engine.normalize_to_grayscale_edge(scores)
    assert gray.dtype == np.uint8
    assert gray.shape == scores.shape
    assert gray[2, 1] == 255  # Peak score (1000) normalized to 255 (bright white)
    assert gray[0, 0] == 0    # Zero score normalized to 0 (dark black)
    assert 0 < gray[1, 1] < 255


def test_threshold_sensitivity_and_score_counting():
    """Verify that changing threshold dynamically updates edge density and pixel statistics."""
    img = sobel_engine.make_benchmark_image(128, 128)

    # Low threshold: more edges
    res_low = sobel_engine.execute_full_flow(img, threshold=90, dump_vcd=False)
    low_edges = res_low["statistics"]["pixels_ge_threshold"]

    # Mid threshold
    res_mid = sobel_engine.execute_full_flow(img, threshold=180, dump_vcd=False)
    mid_edges = res_mid["statistics"]["pixels_ge_threshold"]

    # High threshold: fewer edges
    res_high = sobel_engine.execute_full_flow(img, threshold=400, dump_vcd=False)
    high_edges = res_high["statistics"]["pixels_ge_threshold"]

    assert low_edges > mid_edges > high_edges
    assert res_low["verification"]["status"] == "PASS"
    assert res_high["verification"]["status"] == "PASS"


def test_peak_score_and_single_pixel_threshold():
    """
    Specifically test the scenario investigated by user:
    When threshold is set between the second-highest score and the peak score,
    the binary edge output produces exactly the pixels >= threshold, matching Python reference.
    """
    img = np.zeros((16, 16), dtype=np.uint8)
    # A single 3x3 step feature producing a localized peak gradient
    img[6:9, 8:11] = 200

    res_all = sobel_engine.execute_full_flow(img, threshold=100, dump_vcd=False)
    max_score = res_all["statistics"]["max_score"]

    # Choose a threshold just below the max score
    target_thresh = max_score - 10
    res = sobel_engine.execute_full_flow(img, threshold=target_thresh, dump_vcd=False)
    stats = res["statistics"]

    # Number of white pixels in HDL output matches statistics count
    hdl_white_count = int(np.count_nonzero(res["hdl_edge"] == 255))
    assert hdl_white_count == stats["pixels_ge_threshold"]
    assert res["verification"]["status"] == "PASS"
    assert stats["pixels_ge_threshold"] > 0


def test_vcd_generation():
    """Verify VCD waveform is generated and populated with signal headers."""
    img = sobel_engine.make_benchmark_image(16, 16)
    res = sobel_engine.execute_full_flow(img, threshold=180, dump_vcd=True)
    vcd_path = res["vcd_path"]
    assert vcd_path.exists(), "VCD file does not exist"
    assert vcd_path.stat().st_size > 1000, "VCD file is unexpectedly small"

    content = vcd_path.read_text(errors="ignore")[:2000]
    assert "$timescale" in content
    assert "dut" in content or "pixel_in" in content or "clk" in content
