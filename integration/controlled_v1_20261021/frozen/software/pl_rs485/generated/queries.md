<!-- GENERATED -->
|index|query|code|request/response bytes|data|source|mode|
|---|---|---|---|---|---|---|
|0|ENCODER|30|3/8|carry:int32 BE, value:uint16 BE|manual 5.1 p12; calibrated motor|STP concurrency unverified|
|1|PULSES|33|3/6|pulses:int32 BE|manual 5.1 p12 example 00000100=256|STP concurrency unverified|
|2|ERROR|39|3/4|angle_error:int16 BE, 65536 counts/revolution|manual p12-13 example 00B7|STP concurrency unverified|
|3|ENABLE|3A|3/3|1=enabled,2=disabled|manual 5.1 p13|STP concurrency unverified|
|4|PROTECT|3E|3/3|1=protected,2=not protected|manual 5.1 p13|STP concurrency unverified|
