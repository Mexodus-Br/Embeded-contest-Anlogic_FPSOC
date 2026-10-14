cd {D:/Works/Embedded_contest/dev/pl_dma/build/ps_telemetry_candidate}
import_device dr1_90.db -package DR1M90GEG400 -speed 2
xmlipgen -usernamed_file {D:/Works/Embedded_contest/dev/pl_dma/build/ps_telemetry_candidate/system_ARM_Processor_System_0.xml} -design_file {D:/Works/Embedded_contest/dev/pl_dma/build/ps_telemetry_candidate/Design.xml} -designConfig_file {D:/Works/Embedded_contest/dev/pl_dma/build/ps_telemetry_candidate/DesignConfiguration.xml} -component_file {D:/Anlogic/TD_Release_2026.1_SP2.200.067/ip/depot/ARM_Processor_System_F9F0D0P0_1.0/Component.xml} -mode behavior -package DR1M90GEG400
puts TELEMETRY_HP1_AUDIT_COMPLETE
exit
