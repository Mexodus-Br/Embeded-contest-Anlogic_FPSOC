#pragma once
// Host-only no-op shim: no motor IO. Original numeric code is compiled unchanged.
#define PI 3.1415926535897932384626433832795
#define OUTPUT 1
#define HIGH 1
#define LOW 0
inline void pinMode(int,int) {}
inline void digitalWrite(int,int) {}
inline void delayMicroseconds(int) {}
