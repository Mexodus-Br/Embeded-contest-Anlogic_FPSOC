#ifndef SOC_PLAT_DTS_H
#define SOC_PLAT_DTS_H


/* ip enable cfg strat*/
#define GBE0PS_ENABLE                "okay"
#define GBE1PS_ENABLE            "disabled"
#define I2C0PS_ENABLE            "disabled"
#define I2C1PS_ENABLE            "disabled"
#define CAN0PS_ENABLE            "disabled"
#define CAN1PS_ENABLE            "disabled"
#define SMCPS_ENABLE             "disabled"
#define GPIOPL_ENABLE            "disabled"
#define GPIOPS_ENABLE                "okay"
#define QSPIPS_ENABLE                "okay"
#define MMC0PS_ENABLE                "okay"
#define MMC1PS_ENABLE                "okay"
#define UART0PS_ENABLE           "disabled"
#define UART1PS_ENABLE               "okay"
#define SPI0PS_ENABLE            "disabled"
#define SPI1PS_ENABLE            "disabled"
#define TC0PS_ENABLE             "disabled"
#define TC1PS_ENABLE             "disabled"
#define USB0PS_ENABLE                "okay"
#define USB1PS_ENABLE            "disabled"
#define WDTPS_ENABLE             "disabled"
/* ip enable cfg end*/

/* ip freq cfg strat*/
#define AL_AHB_DMA_CLOCK                                  1000000000
#define AL_AXI_DMAC_CLOCK                                 2000000000
#define AL_PROCESSOR_CORE0_CLOCK                          1000000000
#define AL_PROCESSOR_CORE1_CLOCK                          1000000000
#define AL_ETH0_CLOCK                                      499950000
#define AL_ETH0_PHY_CLOCK                                  124987500
#define AL_ETH0_PTP_CLOCK                                  100000000
#define AL_ETH0_RX_CLOCK                                   124987500
#define AL_ETH0_TX_CLOCK                                   124987500
#define AL_CRYST_OSC_CLOCK                                  33333333
#define QSPI_2ND_DIVISOR                                           2
#define AL_QSPI_CLOCK                                       99990000
#define AL_MMC_CLOCK                                       399960000
#define SD0_2ND_DIVISOR                                            2
#define SD1_2ND_DIVISOR                                            2
#define AL_UART_CLOCK                                      400000000
#define AL_PROCESSOR_CORE0_COUNTER_CLOCK                    33333333
#define AL_PROCESSOR_CORE1_COUNTER_CLOCK                    33333333
/* ip freq cfg end*/

/* freq default cfg start*/
#define AL_I2C_CLOCK                        100000000
#define AL_I2C0PS_RATE                         400000
#define AL_I2C1PS_RATE                         400000
#define AL_GPIO_CLOCK                        12500000
#define AL_ADC_CLOCK                        200000000
#define AL_ETH1_CLOCK                       500000000
#define AL_ETH1_PTP_CLOCK                   100000000
#define AL_ETH1_PHY_CLOCK                   125000000
#define AL_ETH1_TX_CLOCK                    125000000
#define AL_ETH1_RX_CLOCK                    125000000
#define AL_QSPI_MAX_FREQUENCY    (AL_QSPI_CLOCK/QSPI_2ND_DIVISOR)
#define AL_TC_CLOCK                         200000000
#define AL_WDT_CLOCK                         16666666
#define AL_SMC_CLOCK                         50000000
#define AL_MMC0_PS_MAX_FREQ      (AL_MMC_CLOCK/SD0_2ND_DIVISOR)
#define AL_MMC1_PS_MAX_FREQ      (AL_MMC_CLOCK/SD1_2ND_DIVISOR)
/* freq default cfg end*/

/* ip other cfg strat*/
#define AL_DDRC_CAPACITY                         4096
#define AL_ETH0_PHY_MODE                      "rgmii"
#define AL_MMC0_PS_CD_ENABLE                        1
#define AL_MMC0_PS_CD_GPIO_BANK                 portb
#define AL_MMC0_PS_CD_GPIO_PORT                    15
#define AL_MMC0_PS_H_DOT                            0
#define AL_MMC1_PS_CD_ENABLE                        0
/* ip other cfg end*/

/* other default cfg start*/
#define AL_ETH1_PHY_MODE                      "rgmii"
#define AL_MMC1_PS_CD_GPIO_BANK                 porta
#define AL_MMC1_PS_CD_GPIO_PORT                     0
#define AL_MMC0_PS_BUS_WIDTH                        4
#define AL_MMC1_PS_BUS_WIDTH                        4
/* other default cfg end*/




#endif /* SOC_PLAT_DTS_H */

/* Project compatibility: actual FSBL values take precedence. */
#undef AL_PROCESSOR_CORE0_CLOCK
#define AL_PROCESSOR_CORE0_CLOCK 999900000
#undef AL_PROCESSOR_CORE1_CLOCK
#define AL_PROCESSOR_CORE1_CLOCK 999900000
#undef AL_UART_CLOCK
#define AL_UART_CLOCK 400000000
#undef AL_MMC0_PS_MAX_FREQ
#define AL_MMC0_PS_MAX_FREQ 49995000
#undef AL_MMC1_PS_MAX_FREQ
#define AL_MMC1_PS_MAX_FREQ 49995000
#undef AL_DDRC_CAPACITY
#define AL_DDRC_CAPACITY 1024
#undef AL_ETH_CLOCK
#define AL_ETH_CLOCK AL_ETH0_CLOCK
#undef AL_ETH_PHY_CLOCK
#define AL_ETH_PHY_CLOCK AL_ETH0_PHY_CLOCK
#undef AL_ETH_PTP_CLOCK
#define AL_ETH_PTP_CLOCK AL_ETH0_PTP_CLOCK
#undef AL_ETH_TX_CLOCK
#define AL_ETH_TX_CLOCK AL_ETH0_TX_CLOCK
#undef AL_ETH_RX_CLOCK
#define AL_ETH_RX_CLOCK AL_ETH0_RX_CLOCK
