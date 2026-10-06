#include "robotGeometry.h"

#include <math.h>
#include <Arduino.h>

RobotGeometry::RobotGeometry(float a_ee_offset, float a_low_shank_length, float a_high_shank_length) {
  ee_offset = a_ee_offset;
  low_shank_length = a_low_shank_length;
  high_shank_length = a_high_shank_length;
}

void RobotGeometry::set(float axmm, float aymm, float azmm) {
  xmm = axmm;
  ymm = aymm;
  zmm = azmm; 
  calculateGrad();
}

float RobotGeometry::getXmm() const {
  return xmm;
}

float RobotGeometry::getYmm() const {
  return ymm;
}

float RobotGeometry::getZmm() const {
  return zmm;
}

float RobotGeometry::getRotRad() const {
  return rot;
}

float RobotGeometry::getLowRad() const {
  return low;
}

float RobotGeometry::getHighRad() const {
  return high;
}

void RobotGeometry::calculateGrad() {
  float R=83.7;//84.61
  float r=30.4;//30.37
  float L=150.0;
  float l=280.0;
  double K,M,N;
  K=((-(xmm*xmm+ymm*ymm+zmm*zmm)+(ymm+sqrt(3)*xmm)*(R-r)-(R-r)*(R-r)-L*L+l*l)/L+2*zmm);
  M=-2*(2*(R-r)-ymm-sqrt(3)*xmm);
  N=((-(xmm*xmm+ymm*ymm+zmm*zmm)+(ymm+sqrt(3)*xmm)*(R-r)-(R-r)*(R-r)-L*L+l*l)/L-2*zmm);
  rot=(PI/2)-2*atan((-M-sqrt(M*M-4*K*N))/(2*K));

  K=((-(xmm*xmm+ymm*ymm+zmm*zmm)-(-ymm+sqrt(3)*xmm)*(R-r)-(R-r)*(R-r)-L*L+l*l)/L+2*zmm);
  M=-2*(2*(R-r)-ymm+sqrt(3)*xmm);
  N=((-(xmm*xmm+ymm*ymm+zmm*zmm)-(-ymm+sqrt(3)*xmm)*(R-r)-(R-r)*(R-r)-L*L+l*l)/L-2*zmm);
  low=(PI/2)-2*atan((-M-sqrt(M*M-4*K*N))/(2*K));

  K=((-(xmm*xmm+ymm*ymm+zmm*zmm)-2*ymm*(R-r)-(R-r)*(R-r)-L*L+l*l)/(2*L)+zmm);
  M=-2*(R-r+ymm);
  N=((-(xmm*xmm+ymm*ymm+zmm*zmm)-2*ymm*(R-r)-(R-r)*(R-r)-L*L+l*l)/(2*L)-zmm);
  high=(PI/2)-2*atan((-M-sqrt(M*M-4*K*N))/(2*K));
}
