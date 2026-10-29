`timescale 1ns/1ps
// Streaming Sobel processor with two line buffers and 3x3 sliding window.
// Feed WIDTH*HEIGHT grayscale pixels in raster order, one per valid clock.
// Output is asserted for interior pixels only. Borders are omitted.
// The output pixel corresponds to input coordinate (row-1, col-1).
module sobel_stream #(
    parameter integer WIDTH  = 16,
    parameter integer HEIGHT = 16
) (
    input  wire       clk,
    input  wire       rst,
    input  wire       pixel_valid,
    input  wire [7:0] pixel_in,
    input  wire [15:0] threshold,
    output reg        edge_valid,
    output reg  [7:0] edge_out,
    output reg  [15:0] edge_score_out,
    output reg  [15:0] out_x,
    output reg  [15:0] out_y
);
    reg [7:0] line1 [0:WIDTH-1];
    reg [7:0] line2 [0:WIDTH-1];

    reg [7:0] r0_left, r0_mid;
    reg [7:0] r1_left, r1_mid;
    reg [7:0] r2_left, r2_mid;

    reg [15:0] col;
    reg [15:0] row;
    integer i;

    wire [15:0] score;
    wire edge_bit;

    sobel_core u_sobel_core (
        .p00(r0_left), .p01(r0_mid), .p02(line2[col]),
        .p10(r1_left), .p11(r1_mid), .p12(line1[col]),
        .p20(r2_left), .p21(r2_mid), .p22(pixel_in),
        .threshold(threshold),
        .edge_score(score),
        .edge_pixel(edge_bit)
    );

    always @(posedge clk) begin
        if (rst) begin
            col <= 0;
            row <= 0;
            edge_valid <= 0;
            edge_out <= 0;
            edge_score_out <= 0;
            out_x <= 0;
            out_y <= 0;
            r0_left <= 0; r0_mid <= 0;
            r1_left <= 0; r1_mid <= 0;
            r2_left <= 0; r2_mid <= 0;
            for (i = 0; i < WIDTH; i = i + 1) begin
                line1[i] <= 0;
                line2[i] <= 0;
            end
        end else begin
            edge_valid <= 0;
            if (pixel_valid && (row < HEIGHT) && (col < WIDTH)) begin
                // A window is valid once the third row and third column arrive.
                if ((row >= 2) && (col >= 2)) begin
                    edge_valid <= 1;
                    edge_score_out <= score;
                    edge_out <= edge_bit ? 8'hFF : 8'h00;
                    out_x <= col - 1;
                    out_y <= row - 1;
                end

                // Move the two line buffers down one row.
                line2[col] <= line1[col];
                line1[col] <= pixel_in;

                // Shift each row's horizontal window.
                r0_left <= r0_mid;
                r0_mid  <= line2[col];
                r1_left <= r1_mid;
                r1_mid  <= line1[col];
                r2_left <= r2_mid;
                r2_mid  <= pixel_in;

                if (col == WIDTH-1) begin
                    col <= 0;
                    row <= row + 1;
                    // Reset horizontal window history at each row boundary.
                    r0_left <= 0; r0_mid <= 0;
                    r1_left <= 0; r1_mid <= 0;
                    r2_left <= 0; r2_mid <= 0;
                end else begin
                    col <= col + 1;
                end
            end
        end
    end
endmodule
