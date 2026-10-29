#!/usr/bin/env python3
"""
Sobel Accelerator Simulation & Verification Engine.
Handles toolchain discovery, Verilog RTL compilation with Icarus Verilog,
simulation execution with VVP, VCD waveform generation, and cycle-accurate
verification against an independent Python reference model.
Supports resolutions from 16x16 up to 256x256 genuine hardware simulation.
"""

from pathlib import Path
import os
import shutil
import subprocess
import time
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "sample_data"
RESULTS_DIR = ROOT / "results"
RTL_DIR = ROOT / "rtl"
TB_DIR = ROOT / "tb"

COMMON_EDA_DIRS = [
    "/tmp/eda/bin",
    "/usr/local/bin",
    "/opt/homebrew/bin",
    os.path.expanduser("~/.local/bin"),
    "/usr/bin",
]


def find_tool(tool_name: str) -> str | None:
    """Find path to an EDA binary, checking PATH and common installation directories."""
    found = shutil.which(tool_name)
    if found:
        return found
    for d in COMMON_EDA_DIRS:
        candidate = Path(d) / tool_name
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


def get_toolchain_info() -> dict:
    """Detect Icarus Verilog and GTKWave toolchain presence and versions."""
    iverilog_path = find_tool("iverilog")
    vvp_path = find_tool("vvp")
    gtkwave_path = find_tool("gtkwave")

    info = {
        "iverilog_path": iverilog_path,
        "vvp_path": vvp_path,
        "gtkwave_path": gtkwave_path,
        "simulator_available": bool(iverilog_path and vvp_path),
        "iverilog_version": "Unknown",
        "gtkwave_available": bool(gtkwave_path),
        "error_message": None,
    }

    if info["simulator_available"]:
        try:
            res = subprocess.run([iverilog_path, "-V"], capture_output=True, text=True, timeout=5)
            first_line = res.stdout.splitlines()[0] if res.stdout else "Available"
            info["iverilog_version"] = first_line
        except Exception as e:
            info["iverilog_version"] = f"Detected ({e})"
    else:
        info["error_message"] = (
            "Icarus Verilog (iverilog / vvp) was not found in PATH or standard EDA folders.\n"
            "Installation Instructions for macOS (Intel x86_64):\n"
            "  - Install via Homebrew: brew install icarus-verilog\n"
            "  - Or add your EDA directory to PATH: export PATH=\"/tmp/eda/bin:$PATH\"\n"
            "Ubuntu/Debian: sudo apt update && sudo apt install -y iverilog\n"
            "Windows: Install Icarus Verilog and add iverilog.exe to PATH."
        )

    return info


def make_benchmark_image(width: int = 128, height: int = 128) -> np.ndarray:
    """Generate a clean, scalable geometric benchmark image with sharp edges and shapes."""
    img = Image.new("L", (width, height), 25)
    draw = ImageDraw.Draw(img)
    scale_x = width / 16.0
    scale_y = height / 16.0
    # Scaled rectangles
    draw.rectangle(
        (int(3 * scale_x), int(3 * scale_y), int(8 * scale_x), int(11 * scale_y)),
        fill=220,
    )
    draw.rectangle(
        (int(10 * scale_x), int(5 * scale_y), int(13 * scale_x), int(13 * scale_y)),
        fill=110,
    )
    # Scaled diagonal line with proportional thickness
    line_w = max(1, int(round(width / 32.0)))
    draw.line(
        (0, int(14 * scale_y), int(15 * scale_x), int(1 * scale_y)),
        fill=255,
        width=line_w,
    )
    return np.array(img, dtype=np.uint8)


def make_preset_image(preset_name: str, width: int = 128, height: int = 128) -> np.ndarray:
    """Generate specialized synthetic patterns for VLSI edge detection benchmarking."""
    img = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(img)

    if preset_name == "Default Benchmark":
        return make_benchmark_image(width, height)
    elif preset_name == "Checkerboard":
        tile = max(2, width // 8)
        for y in range(0, height, tile):
            for x in range(0, width, tile):
                if ((x // tile) + (y // tile)) % 2 == 0:
                    draw.rectangle((x, y, x + tile - 1, y + tile - 1), fill=255)
    elif preset_name == "Concentric Rings":
        cx, cy = width / 2.0, height / 2.0
        max_r = min(width, height) / 2.0 - 2
        ring_w = max(1, int(round(width / 64.0)))
        for r in np.linspace(max_r, 4, num=6):
            draw.ellipse((cx - r, cy - r, cx + r, cy + r), outline=240, width=ring_w)
    elif preset_name == "High-Contrast Cross":
        mid_x, mid_y = width // 2, height // 2
        w_bar = max(1, width // 10)
        draw.rectangle((mid_x - w_bar, 4, mid_x + w_bar, height - 5), fill=230)
        draw.rectangle((4, mid_y - w_bar, width - 5, mid_y + w_bar), fill=230)
    elif preset_name == "Diagonal Edge Ramp":
        for y in range(height):
            for x in range(width):
                val = 255 if (x + y) >= (width + height) // 2 else 30
                img.putpixel((x, y), val)
    else:
        return make_benchmark_image(width, height)

    return np.array(img, dtype=np.uint8)


def image_to_hex(arr: np.ndarray, hex_path: Path | str) -> None:
    """Write grayscale image array to hex format expected by Verilog $readmemh."""
    hex_path = Path(hex_path)
    hex_path.parent.mkdir(parents=True, exist_ok=True)
    with hex_path.open("w") as f:
        for val in arr.flatten():
            f.write(f"{int(val):02x}\n")


def sobel_reference(image: np.ndarray, threshold: int = 180) -> tuple[np.ndarray, np.ndarray]:
    """
    Pure Python / NumPy reference implementation for 3x3 Sobel L1 datapath.
    Calculates:
      Gx = -p00 + p02 - 2*p10 + 2*p12 - p20 + p22
      Gy = -p00 - 2*p01 - p02 + p20 + 2*p21 + p22
      Score = |Gx| + |Gy|
      Edge = 255 if Score >= threshold else 0
    Border pixels (outer 1 pixel margin) are set to 0 to match hardware omission.
    """
    h, w = image.shape
    a = image.astype(np.int32)
    out = np.zeros((h, w), dtype=np.uint8)
    score_img = np.zeros((h, w), dtype=np.uint16)

    for y in range(1, h - 1):
        for x in range(1, w - 1):
            p = a[y - 1 : y + 2, x - 1 : x + 2]
            gx = (
                -p[0, 0]
                + p[0, 2]
                - 2 * p[1, 0]
                + 2 * p[1, 2]
                - p[2, 0]
                + p[2, 2]
            )
            gy = (
                -p[0, 0]
                - 2 * p[0, 1]
                - p[0, 2]
                + p[2, 0]
                + 2 * p[2, 1]
                + p[2, 2]
            )
            score = abs(int(gx)) + abs(int(gy))
            score_img[y, x] = score
            out[y, x] = 255 if score >= threshold else 0

    return out, score_img


def normalize_to_grayscale_edge(score_array: np.ndarray) -> np.ndarray:
    """
    Convert raw 16-bit Sobel gradient magnitude scores to conventional 8-bit grayscale edge image.
    Strong edges appear bright white (255) against dark background (0).
    Uses full dynamic-range normalization matching standard image processing visualization.
    """
    max_score = int(np.max(score_array))
    if max_score == 0:
        return np.zeros_like(score_array, dtype=np.uint8)
    normalized = (score_array.astype(np.float32) / float(max_score)) * 255.0
    return np.clip(normalized, 0, 255).astype(np.uint8)


def compile_verilog(width: int = 16, height: int = 16, sim_dir: Path | None = None) -> tuple[Path, str, float]:
    """
    Compile Verilog RTL and testbench with Icarus Verilog.
    Returns (compiled_executable_path, compiler_log, compilation_time_sec).
    """
    tools = get_toolchain_info()
    if not tools["simulator_available"]:
        raise RuntimeError(tools["error_message"])

    iverilog_bin = tools["iverilog_path"]
    target_dir = sim_dir or RESULTS_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    exe_path = target_dir / f"simv_{width}x{height}"

    compile_cmd = [
        iverilog_bin,
        "-g2012",
        f"-DIMG_WIDTH={width}",
        f"-DIMG_HEIGHT={height}",
        "-o",
        str(exe_path),
        str(RTL_DIR / "sobel_core.v"),
        str(RTL_DIR / "sobel_stream.v"),
        str(TB_DIR / "tb_sobel_stream.v"),
    ]

    env = os.environ.copy()
    if tools["iverilog_path"]:
        iverilog_dir = str(Path(tools["iverilog_path"]).parent)
        env["PATH"] = f"{iverilog_dir}:{env.get('PATH', '')}"

    t0 = time.perf_counter()
    res = subprocess.run(compile_cmd, cwd=ROOT, capture_output=True, text=True, env=env)
    elapsed = time.perf_counter() - t0

    if res.returncode != 0:
        err_msg = f"Icarus Verilog compilation failed (code {res.returncode}):\n{res.stderr}\n{res.stdout}"
        raise RuntimeError(err_msg)

    return exe_path, res.stdout + res.stderr, elapsed


def run_verilog_simulation(
    exe_path: Path,
    input_hex_path: Path,
    output_hex_path: Path,
    vcd_path: Path,
    threshold: int = 180,
    dump_vcd: bool = True,
) -> tuple[str, float, dict]:
    """
    Execute compiled Verilog simulation with VVP, passing runtime parameters:
      +threshold={threshold}
      +dump_vcd={1 if dump_vcd else 0}
      +infile={input_hex_path}
      +outfile={output_hex_path}
      +vcdfile={vcd_path}
    Returns (simulation_log, simulation_time_sec, metrics_dict).
    """
    tools = get_toolchain_info()
    if not tools["vvp_path"]:
        raise RuntimeError("VVP simulator not found.")

    env = os.environ.copy()
    vvp_dir = str(Path(tools["vvp_path"]).parent)
    env["PATH"] = f"{vvp_dir}:{env.get('PATH', '')}"

    sim_cmd = [
        tools["vvp_path"],
        str(exe_path),
        f"+threshold={int(threshold)}",
        f"+dump_vcd={1 if dump_vcd else 0}",
        f"+infile={str(input_hex_path)}",
        f"+outfile={str(output_hex_path)}",
        f"+vcdfile={str(vcd_path)}",
    ]

    t0 = time.perf_counter()
    res = subprocess.run(sim_cmd, cwd=ROOT, capture_output=True, text=True, env=env)
    elapsed = time.perf_counter() - t0

    if res.returncode != 0:
        err_msg = f"VVP simulation failed (code {res.returncode}):\n{res.stderr}\n{res.stdout}"
        raise RuntimeError(err_msg)

    log_output = res.stdout + res.stderr

    # Parse simulation output metrics from log
    metrics = {
        "cycles": 0,
        "input_pixels": 0,
        "captured_outputs": 0,
        "expected_outputs": 0,
        "threshold": threshold,
    }
    for line in log_output.splitlines():
        if "processed" in line and "input pixels in" in line:
            parts = line.split()
            try:
                metrics["input_pixels"] = int(parts[2])
                metrics["cycles"] = int(parts[6])
            except (ValueError, IndexError):
                pass
        if "captured outputs:" in line:
            try:
                parts = line.split("captured outputs:")
                metrics["captured_outputs"] = int(parts[1].strip().split()[0])
            except (ValueError, IndexError):
                pass
        if "Expected interior outputs:" in line:
            try:
                parts = line.split("Expected interior outputs:")
                metrics["expected_outputs"] = int(parts[1].split(";")[0].strip())
            except (ValueError, IndexError):
                pass

    return log_output, elapsed, metrics


def parse_hdl_output(
    hex_path: Path | str, width: int, height: int
) -> tuple[np.ndarray, np.ndarray, int]:
    """Parse edge_pixels.hex produced by Verilog testbench."""
    hex_path = Path(hex_path)
    if not hex_path.exists():
        raise FileNotFoundError(f"Simulation output not found: {hex_path}")

    out = np.zeros((height, width), dtype=np.uint8)
    score_img = np.zeros((height, width), dtype=np.uint16)

    lines = [line.strip().split() for line in hex_path.read_text().splitlines() if line.strip()]
    valid_count = 0
    for row in lines:
        if len(row) != 4:
            continue
        try:
            x = int(row[0], 16)
            y = int(row[1], 16)
            edge = int(row[2], 16)
            score = int(row[3], 16)
            if 0 <= x < width and 0 <= y < height:
                out[y, x] = edge
                score_img[y, x] = score
                valid_count += 1
        except ValueError:
            continue

    return out, score_img, valid_count


def verify_simulation(
    hdl_edge: np.ndarray,
    ref_edge: np.ndarray,
    hdl_score: np.ndarray,
    ref_score: np.ndarray,
    width: int,
    height: int,
) -> dict:
    """
    Perform cycle-accurate verification between Verilog HDL and Python reference model.
    Checks all valid interior pixels [1..height-2, 1..width-2].
    """
    interior = (slice(1, height - 1), slice(1, width - 1))
    tested_count = (width - 2) * (height - 2)

    diff_edge = hdl_edge[interior] != ref_edge[interior]
    diff_score = hdl_score[interior] != ref_score[interior]

    edge_mismatches = int(np.count_nonzero(diff_edge))
    score_mismatches = int(np.count_nonzero(diff_score))
    total_mismatches = edge_mismatches

    diff_map = np.zeros((height, width, 3), dtype=np.uint8)
    # Highlight matching edges in green, reference in blue, mismatches in red
    for y in range(1, height - 1):
        for x in range(1, width - 1):
            h_val = hdl_edge[y, x]
            r_val = ref_edge[y, x]
            if h_val != r_val:
                diff_map[y, x] = [255, 0, 0]  # RED mismatch
            elif h_val == 255:
                diff_map[y, x] = [0, 255, 0]  # GREEN matching edge
            else:
                diff_map[y, x] = [20, 20, 20]  # Background

    pass_status = (total_mismatches == 0) and (score_mismatches == 0)

    return {
        "status": "PASS" if pass_status else "FAIL",
        "tested_interior_pixels": tested_count,
        "edge_mismatches": edge_mismatches,
        "score_mismatches": score_mismatches,
        "match_percentage": 100.0 if tested_count == 0 else 100.0 * (1.0 - total_mismatches / tested_count),
        "diff_map": diff_map,
        "interior_slice": interior,
    }


def compute_gradient_statistics(score_array: np.ndarray, threshold: int, width: int, height: int) -> dict:
    """Compute detailed mathematical distribution of gradient magnitude scores."""
    interior = score_array[1 : height - 1, 1 : width - 1]
    total_interior = (width - 2) * (height - 2)
    max_val = int(np.max(interior)) if interior.size > 0 else 0
    min_val = int(np.min(interior)) if interior.size > 0 else 0
    mean_val = float(np.mean(interior)) if interior.size > 0 else 0.0

    count_ge_thresh = int(np.count_nonzero(interior >= threshold))
    count_lt_thresh = total_interior - count_ge_thresh
    pct_ge = (count_ge_thresh / total_interior * 100.0) if total_interior > 0 else 0.0

    # Top gradient pixel locations
    flat_indices = np.argsort(interior.ravel())[::-1][:10]
    top_pixels = []
    for idx in flat_indices:
        iy, ix = np.unravel_index(idx, interior.shape)
        # Shift back to image coordinates (y+1, x+1)
        actual_x = int(ix + 1)
        actual_y = int(iy + 1)
        val = int(score_array[actual_y, actual_x])
        top_pixels.append({"x": actual_x, "y": actual_y, "score": val})

    return {
        "min_score": min_val,
        "max_score": max_val,
        "mean_score": mean_val,
        "total_interior_pixels": total_interior,
        "pixels_ge_threshold": count_ge_thresh,
        "pixels_lt_threshold": count_lt_thresh,
        "percentage_ge_threshold": pct_ge,
        "top_pixels": top_pixels,
    }


def execute_full_flow(
    image: np.ndarray,
    threshold: int = 180,
    force_recompile: bool = False,
    results_dir: Path | None = None,
    dump_vcd: bool = True,
) -> dict:
    """
    Orchestrate full end-to-end pipeline:
      1. Write input pixel hex
      2. Compile Verilog RTL (if needed or forced)
      3. Run VVP simulation with threshold and paths
      4. Parse Verilog HDL output
      5. Compute Python reference output
      6. Perform verification
      7. Collect full metrics and diagnostics
    """
    target_results = results_dir or RESULTS_DIR
    target_results.mkdir(parents=True, exist_ok=True)

    height, width = image.shape
    input_hex = target_results / f"input_pixels_{width}x{height}.hex"
    output_hex = target_results / f"edge_pixels_{width}x{height}.hex"
    vcd_path = target_results / "sobel_wave.vcd"

    # Step 1: Write input hex
    image_to_hex(image, input_hex)
    # Also write canonical input_pixels.hex for backward compatibility
    try:
        shutil.copy2(input_hex, target_results / "input_pixels.hex")
    except Exception:
        pass

    # Step 2: Compile Verilog RTL
    exe_path = target_results / f"simv_{width}x{height}"
    compile_log = "Cached executable reused."
    compile_time = 0.0

    if force_recompile or not exe_path.exists():
        exe_path, compile_log, compile_time = compile_verilog(width, height, target_results)

    # Step 3: Run Simulation
    sim_log, sim_time, sim_metrics = run_verilog_simulation(
        exe_path=exe_path,
        input_hex_path=input_hex,
        output_hex_path=output_hex,
        vcd_path=vcd_path,
        threshold=threshold,
        dump_vcd=dump_vcd,
    )

    # Copy canonical output hex
    try:
        shutil.copy2(output_hex, target_results / "edge_pixels.hex")
    except Exception:
        pass

    # Also update root sobel_wave.vcd for convenience with CLI gtkwave
    if dump_vcd and vcd_path.exists():
        try:
            shutil.copy2(vcd_path, ROOT / "sobel_wave.vcd")
        except Exception:
            pass

    # Step 4: Parse HDL Output
    hdl_edge, hdl_score, valid_records = parse_hdl_output(output_hex, width, height)

    # Step 5: Grayscale Edge Image (Normalized continuous gradient magnitude)
    hdl_gray_edge = normalize_to_grayscale_edge(hdl_score)

    # Step 6: Independent Python Reference
    ref_edge, ref_score = sobel_reference(image, threshold)
    ref_gray_edge = normalize_to_grayscale_edge(ref_score)

    # Step 7: Verification
    verification = verify_simulation(hdl_edge, ref_edge, hdl_score, ref_score, width, height)

    # Step 8: Statistics
    stats = compute_gradient_statistics(hdl_score, threshold, width, height)

    return {
        "width": width,
        "height": height,
        "threshold": threshold,
        "image": image,
        "hdl_edge": hdl_edge,
        "hdl_score": hdl_score,
        "hdl_gray_edge": hdl_gray_edge,
        "ref_edge": ref_edge,
        "ref_score": ref_score,
        "ref_gray_edge": ref_gray_edge,
        "verification": verification,
        "statistics": stats,
        "metrics": sim_metrics,
        "compile_time": compile_time,
        "sim_time": sim_time,
        "compile_log": compile_log,
        "sim_log": sim_log,
        "input_hex_path": input_hex,
        "output_hex_path": output_hex,
        "vcd_path": vcd_path,
        "dump_vcd": dump_vcd,
    }
