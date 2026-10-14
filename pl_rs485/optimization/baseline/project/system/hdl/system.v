module system(
    output    wire              p2f_clk0
) ;
    wire              w_port__ps__p2f_clk0 ;
    wire              w_net__ps__p2f_clk0 ;

    assign w_net__ps__p2f_clk0 = w_port__ps__p2f_clk0 ;
    assign p2f_clk0 = w_net__ps__p2f_clk0 ;

    system_ARM_Processor_System_0 ps (  .p2f_clk0(w_port__ps__p2f_clk0) );

endmodule
