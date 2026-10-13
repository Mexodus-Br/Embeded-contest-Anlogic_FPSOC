// SPDX-License-Identifier: (GPL-2.0+ OR MIT)

#ifndef _ANLOGIC_DRM190_PLAT_H_
#define _ANLOGIC_DRM190_PLAT_H_

#include "anlogic-dr1m90-hpf.h"

#ifndef AL_PROCESSOR_CORE0_CLOCK
#define AL_PROCESSOR_CORE0_CLOCK			800000000
#endif

#ifndef AL_PROCESSOR_CORE0_COUNTER_CLOCK
#define AL_PROCESSOR_CORE0_COUNTER_CLOCK	33333333
#endif

#ifndef AL_PROCESSOR_CORE1_CLOCK
#define AL_PROCESSOR_CORE1_CLOCK			800000000
#endif

#ifndef AL_PROCESSOR_CORE1_COUNTER_CLOCK
#define AL_PROCESSOR_CORE1_COUNTER_CLOCK	33333333
#endif

#ifndef AL_ETH_CLOCK
#define AL_ETH_CLOCK						25000000
#endif

#ifndef AL_ETH0_PHY_MODE
#define AL_ETH0_PHY_MODE					"rgmii"
#endif

#ifndef AL_ETH1_PHY_MODE
#define AL_ETH1_PHY_MODE					"rgmii"
#endif

#ifndef AL_ETH_PHY_CLOCK
#define AL_ETH_PHY_CLOCK					25000000
#endif

#ifndef AL_ETH_PTP_CLOCK
#define AL_ETH_PTP_CLOCK					100000000
#endif

#ifndef AL_ETH_TX_CLOCK
#define AL_ETH_TX_CLOCK						25000000
#endif

#ifndef AL_ETH_RX_CLOCK
#define AL_ETH_RX_CLK						25000000
#endif

#ifndef AL_AXI_DMAC_CLOCK
#define AL_AXI_DMAC_CLOCK					50000000
#endif

#ifndef AL_AHB_DMA_CLOCK
#define AL_AHB_DMA_CLOCK					400000000
#endif

#ifndef AL_I2C_CLOCK
#define AL_I2C_CLOCK						100000000
#endif

#ifndef AL_GPIO_CLOCK
#define AL_GPIO_CLOCK						25000000
#endif

#ifndef AL_TC_CLOCK
#define AL_TC_CLOCK						200000000
#endif

#ifndef AL_ADC_CLOCK
#define AL_ADC_CLOCK						200000000
#endif

#ifndef AL_WDT_CLOCK
#define AL_WDT_CLOCK						16666666
#endif

#ifndef AL_SMC_CLOCK
#define AL_SMC_CLOCK						50000000
#endif

#ifndef AL_UART_CLOCK
#define AL_UART_CLOCK						50000000
#endif

#ifndef AL_MMC0_PS_MAX_FREQ
#define AL_MMC0_PS_MAX_FREQ					50000000
#endif

#ifndef AL_MMC0_PS_CD_ENABLE
#define AL_MMC0_PS_CD_ENABLE				0
#endif

#ifndef AL_MMC0_PS_CD_GPIO_BANK
#define AL_MMC0_PS_CD_GPIO_BANK				porta
#endif

#ifndef AL_MMC0_PS_CD_GPIO_PORT
#define AL_MMC0_PS_CD_GPIO_PORT				0
#endif

#ifndef AL_MMC0_PS_BUS_WIDTH
#define AL_MMC0_PS_BUS_WIDTH				4
#endif

#ifndef AL_MMC1_PS_MAX_FREQ
#define AL_MMC1_PS_MAX_FREQ					50000000
#endif

#ifndef AL_MMC1_PS_CD_ENABLE
#define AL_MMC1_PS_CD_ENABLE				0
#endif

#ifndef AL_MMC1_PS_CD_GPIO_BANK
#define AL_MMC1_PS_CD_GPIO_BANK				porta
#endif

#ifndef AL_MMC1_PS_CD_GPIO_PORT
#define AL_MMC1_PS_CD_GPIO_PORT				0
#endif

#ifndef AL_MMC1_PS_BUS_WIDTH
#define AL_MMC1_PS_BUS_WIDTH				4
#endif

#ifndef AL_QSPI_CLOCK
#define AL_QSPI_CLOCK						200000000
#endif

#ifndef AL_QSPI_MAX_FREQUENCY
#define AL_QSPI_MAX_FREQUENCY				50000000
#endif

#ifndef AL_SPI0_MAX_FREQUENCY
#define AL_SPI0_MAX_FREQUENCY				8000000
#endif

#ifndef AL_SPI1_MAX_FREQUENCY
#define AL_SPI1_MAX_FREQUENCY				8000000
#endif

#ifndef AL_I2C0PS_RATE
#define AL_I2C0PS_RATE					400000
#endif

#ifndef AL_I2C1PS_RATE
#define AL_I2C1PS_RATE					400000
#endif

#endif /* _ANLOGIC_DRM190_PLAT_H_ */
