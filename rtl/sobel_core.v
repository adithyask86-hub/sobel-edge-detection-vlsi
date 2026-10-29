`timescale 1ns/1ps
// Combinational Sobel datapath.
// Inputs are a 3x3 grayscale pixel window, each pixel 8 bits.
// Edge score = |Gx| + |Gy|; output is 255 when score >= threshold.
module sobel_core (
    input  wire [7:0] p00, p01, p02,
    input  wire [7:0] p10, p11, p12,
    input  wire [7:0] p20, p21, p22,
    input  wire [15:0] threshold,
    output wire [15:0] edge_score,
    output wire        edge_pixel
);
    // Signed gradient values range from -1020 to +1020.
    wire signed [11:0] gx;
    wire signed [11:0] gy;
    wire signed [11:0] gx_abs;
    wire signed [11:0] gy_abs;

    assign gx = -$signed({1'b0,p00}) + $signed({1'b0,p02})
                - ( $signed({1'b0,p10}) <<< 1 )
                + ( $signed({1'b0,p12}) <<< 1 )
                - $signed({1'b0,p20}) + $signed({1'b0,p22});

    assign gy = -$signed({1'b0,p00}) - ( $signed({1'b0,p01}) <<< 1 )
                - $signed({1'b0,p02})
                + $signed({1'b0,p20}) + ( $signed({1'b0,p21}) <<< 1 )
                + $signed({1'b0,p22});

    assign gx_abs = gx[11] ? -gx : gx;
    assign gy_abs = gy[11] ? -gy : gy;
    assign edge_score = gx_abs + gy_abs;
    assign edge_pixel = (edge_score >= threshold) ? 1'b1 : 1'b0;
endmodule
