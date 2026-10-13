#include "rs485_gp.h"
/* BSP supplies callbacks using its driver/API, plus locking, deadline and IRQ
 * handling. This standalone example never uses /dev/mem or starts motion. */
int rs485_example_drain(const rs485_io *io) {
    rs485_capture c;rs485_decoded d;int result;
    if((result=rs485_identify(io))!=0) return result;
    /* Caller masks DATA before batch drain; remove source, W1C, readback,
     * then unmask. Keep other IRQ masks and diagnostic counts intact. */
    for(;;) {
        result=rs485_capture_read(io,&c);
        if(result==RS485_SW_NOT_READY) return 0;
        if(result!=0) return result;
        result=rs485_decode(c.word,&d);
        if(result!=0) return result;
        /* Persist raw words, validity, times and (c.generation,c.revision).
         * Lookup saved APPLIED configs, never use current revision for c.
         * d.signed_value for 33 is received command pulses, not encoder.
         * Unknown enum/status stays labelled unknown; invalid data is not 0.
         * Publish or quarantine complete data before explicit consumption. */
        if((result=rs485_consume(io,&c))!=0) return result;
    }
}
