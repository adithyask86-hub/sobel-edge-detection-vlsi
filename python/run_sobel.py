#!/usr/bin/env python3
"""Generate sample pixels, run the Verilog simulation, and reconstruct its output."""
from pathlib import Path
import sys
import argparse
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))
import sobel_engine


def main():
    parser = argparse.ArgumentParser(description="Run Sobel hardware simulation & verification")
    parser.add_argument("--threshold", type=int, default=180, help="Sobel edge threshold (default: 180)")
    parser.add_argument("--width", type=int, default=128, help="Image width (default: 128, or 16, 32, 64, 256)")
    parser.add_argument("--height", type=int, default=128, help="Image height (default: 128, or 16, 32, 64, 256)")
    parser.add_argument("--recompile", action="store_true", help="Force recompilation of RTL")
    parser.add_argument("--no-vcd", action="store_true", help="Disable VCD waveform generation for speed")
    args = parser.parse_args()

    width, height = args.width, args.height
    threshold = args.threshold
    dump_vcd = not args.no_vcd

    DATA = ROOT / "sample_data"
    RESULTS = ROOT / "results"
    DATA.mkdir(exist_ok=True)
    RESULTS.mkdir(exist_ok=True)

    tools = sobel_engine.get_toolchain_info()
    if not tools["simulator_available"]:
        print("Icarus Verilog was not found.")
        print(tools["error_message"])
        return

    # Generate sample input
    img_arr = sobel_engine.make_benchmark_image(width, height)
    Image.fromarray(img_arr).save(DATA / "sample_input.png")
    Image.fromarray(img_arr).save(DATA / "sample_input.pgm")

    # Run full hardware flow
    res = sobel_engine.execute_full_flow(
        image=img_arr,
        threshold=threshold,
        force_recompile=args.recompile,
        results_dir=RESULTS,
        dump_vcd=dump_vcd,
    )

    # Save output images
    Image.fromarray(res["ref_edge"]).save(RESULTS / "python_reference_edges.png")
    Image.fromarray(res["ref_gray_edge"]).save(RESULTS / "python_reference_gray_edges.png")
    Image.fromarray(res["hdl_edge"]).save(RESULTS / "hdl_edges.png")
    Image.fromarray(res["hdl_gray_edge"]).save(RESULTS / "hdl_gray_edges.png")
    Image.fromarray(res["hdl_gray_edge"]).save(RESULTS / "hdl_edge_scores_preview.png")

    verif = res["verification"]
    stats = res["statistics"]
    print(res["sim_log"].strip())
    print(f"Interior pixels checked: {verif['tested_interior_pixels']}")
    print(f"HDL output records: {res['metrics'].get('captured_outputs', verif['tested_interior_pixels'])}")
    print(f"Mismatch count versus Python reference: {verif['edge_mismatches']}")
    print(f"Max Gradient Score: {stats['max_score']}, Mean Score: {stats['mean_score']:.1f}")
    print(f"Pixels with score >= {threshold}: {stats['pixels_ge_threshold']} ({stats['percentage_ge_threshold']:.1f}%)")
    print("PASS" if verif["status"] == "PASS" else "CHECK RTL: mismatches detected")

    (RESULTS / "verification.txt").write_text(
        f"Image: {width}x{height} grayscale\nThreshold: {threshold}\n"
        f"Expected interior outputs: {(width-2)*(height-2)}\n"
        f"HDL output records: {res['metrics'].get('captured_outputs', verif['tested_interior_pixels'])}\n"
        f"Max gradient score: {stats['max_score']}\n"
        f"Pixels >= threshold ({threshold}): {stats['pixels_ge_threshold']} ({stats['percentage_ge_threshold']:.1f}%)\n"
        f"Mismatch count: {verif['edge_mismatches']}\n"
        f"Status: {verif['status']}\n"
    )
    print(f"Files are in: {ROOT}")


if __name__ == "__main__":
    main()
