`timescale 1ns/1ps

`ifndef IMG_WIDTH
`define IMG_WIDTH 16
`endif
`ifndef IMG_HEIGHT
`define IMG_HEIGHT 16
`endif

module tb_sobel_stream #(
    parameter integer WIDTH = `IMG_WIDTH,
    parameter integer HEIGHT = `IMG_HEIGHT
);
    reg clk = 0;
    reg rst = 1;
    reg pixel_valid = 0;
    reg [7:0] pixel_in = 0;
    reg [15:0] threshold = 16'd180;
    wire edge_valid;
    wire [7:0] edge_out;
    wire [15:0] edge_score_out;
    wire [15:0] out_x, out_y;

    reg [7:0] image_mem [0:WIDTH*HEIGHT-1];
    integer infile, outfile;
    integer k;
    integer cycles;
    integer out_count;
    integer parsed_thresh;
    integer dump_vcd = 1;

    reg [1023:0] infile_name = "sample_data/input_pixels.hex";
    reg [1023:0] outfile_name = "results/edge_pixels.hex";
    reg [1023:0] vcd_file_name = "sobel_wave.vcd";

    always #5 clk = ~clk;

    sobel_stream #(.WIDTH(WIDTH), .HEIGHT(HEIGHT)) dut (
        .clk(clk), .rst(rst), .pixel_valid(pixel_valid),
        .pixel_in(pixel_in), .threshold(threshold),
        .edge_valid(edge_valid), .edge_out(edge_out),
        .edge_score_out(edge_score_out), .out_x(out_x), .out_y(out_y)
    );

    initial begin
        if ($value$plusargs("threshold=%d", parsed_thresh)) begin
            threshold = parsed_thresh[15:0];
        end
        if ($value$plusargs("dump_vcd=%d", dump_vcd)) ;
        if ($value$plusargs("infile=%s", infile_name)) ;
        if ($value$plusargs("outfile=%s", outfile_name)) ;
        if ($value$plusargs("vcdfile=%s", vcd_file_name)) ;

        if (dump_vcd != 0) begin
            $dumpfile(vcd_file_name);
            $dumpvars(0, tb_sobel_stream);
        end

        infile = $fopen(infile_name, "r");
        if (infile == 0) begin
            $display("ERROR: cannot open %0s", infile_name);
            $finish;
        end
        $fclose(infile);
        $readmemh(infile_name, image_mem);

        outfile = $fopen(outfile_name, "w");
        if (outfile == 0) begin
            $display("ERROR: cannot create %0s", outfile_name);
            $finish;
        end

        repeat (3) @(posedge clk);
        rst <= 0;
        @(posedge clk);

        out_count = 0;
        cycles = 0;
        for (k = 0; k < WIDTH*HEIGHT; k = k + 1) begin
            // Drive away from the active edge so the DUT samples this pixel.
            @(negedge clk);
            pixel_valid = 1;
            pixel_in = image_mem[k];
            @(posedge clk);
            #1;
            cycles = cycles + 1;
            if (edge_valid) begin
                // Format: x y edge_byte edge_score (all hexadecimal).
                $fdisplay(outfile, "%04h %04h %02h %04h",
                          out_x, out_y, edge_out, edge_score_out);
                out_count = out_count + 1;
            end
        end

        @(negedge clk);
        pixel_valid = 0;
        pixel_in = 0;
        repeat (2) @(posedge clk);
        $fclose(outfile);
        $display("DONE: processed %0d input pixels in %0d pixel clocks.", WIDTH*HEIGHT, cycles);
        $display("Expected interior outputs: %0d; captured outputs: %0d",
                 (WIDTH-2)*(HEIGHT-2), out_count);
        $display("Threshold = %0d. Results: %0s", threshold, outfile_name);
        $finish;
    end
endmodule
