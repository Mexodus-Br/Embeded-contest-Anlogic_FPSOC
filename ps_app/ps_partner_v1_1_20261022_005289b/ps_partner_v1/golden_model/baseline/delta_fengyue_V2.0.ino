 #include "config.h"
#include "pinout.h"
#include "logger.h"

#include <Arduino.h>

#include "robotGeometry.h"
#include "interpolation.h"
#include "fanControl.h"
#include "RampsStepper.h"
#include "queue.h"
#include "command.h"
#include "byj_gripper.h"
#include "servo_gripper.h"
#include "equipment.h"
#include "endstop.h"
#include "fanControl.h"
#include "ps2.h"
#include "xipan.h"

#if SDCARD == 1
  #include "sdcard.h"
#endif
//三个旋转轴 X Y Z定义，步进电机
RampsStepper stepperHigher(X_STEP_PIN, X_DIR_PIN, X_ENABLE_PIN, INVERSE_X_STEPPER);
RampsStepper stepperLower(Y_STEP_PIN, Y_DIR_PIN, Y_ENABLE_PIN, INVERSE_Y_STEPPER);
RampsStepper stepperRotate(Z_STEP_PIN, Z_DIR_PIN, Z_ENABLE_PIN, INVERSE_Z_STEPPER);

//RAIL OBJECTS
#if RAIL
RampsStepper stepperRail(E0_STEP_PIN, E0_DIR_PIN, E0_ENABLE_PIN, INVERSE_E0_STEPPER);
Endstop endstopE0(E0_MIN_PIN, E0_DIR_PIN, E0_STEP_PIN, E0_ENABLE_PIN, E0_MIN_INPUT, E0_HOME_STEPS, HOME_DWELL);
#endif

//ENDSTOP OBJECTS
Endstop endstopX(X_MIN_PIN, X_DIR_PIN, X_STEP_PIN, X_ENABLE_PIN, X_MIN_INPUT, X_HOME_STEPS, HOME_DWELL);
Endstop endstopY(Y_MIN_PIN, Y_DIR_PIN, Y_STEP_PIN, Y_ENABLE_PIN, Y_MIN_INPUT, Y_HOME_STEPS, HOME_DWELL);
Endstop endstopZ(Z_MIN_PIN, Z_DIR_PIN, Z_STEP_PIN, Z_ENABLE_PIN, Z_MIN_INPUT, Z_HOME_STEPS, HOME_DWELL);

//夹爪定义，可以是舵机，或28BYJ小型步进电机，或者吸盘
#if GRIPPER == SERVO
  Servo_Gripper servo_gripper(SERVO_PIN, SERVO_GRIP_DEGREE, SERVO_UNGRIP_DEGREE);
#elif GRIPPER == BYJ
  BYJ_Gripper byj_gripper(BYJ_PIN_0, BYJ_PIN_1, BYJ_PIN_2, BYJ_PIN_3, BYJ_GRIP_STEPS);
#elif GRIPPER == XIPAN
  Xipan xipan(XIPAN_PIN);
#endif

#if SDCARD == 1
  SDCard sdcard(41);
#endif

Equipment laser(LASER_PIN);
Equipment pump(PUMP_PIN);
Equipment led(LED_PIN);
FanControl fan(FAN_PIN, FAN_DELAY);
Equipment pump1(PUMP1_PIN);
Equipment pump2(PUMP2_PIN);
Equipment pump3(PUMP3_PIN);
Equipment pump4(PUMP4_PIN);

//EXECUTION & COMMAND OBJECTS
RobotGeometry geometry(END_EFFECTOR_OFFSET, LOW_SHANK_LENGTH, HIGH_SHANK_LENGTH);
Interpolation interpolator;
Queue<Cmd> queue(QUEUE_SIZE);
Queue<Cmd> queueRecord(QUEUE_SIZE); // 回放队列
Command command; // 控制命令格式定义
bool recordState = false;
 
//遥控器定义，这里使用的是ps2
#if SP2 == 1
  ps2 ps2Hander(PS2_DAT, PS2_CMD, PS2_SEL, PS2_CLK);
#endif
//夹具状态
bool lastxipanState = false;
bool lastjiazhuaSate = false;
//定时执行标志
float autoRuntimeMin = 0.0;
long curtime = 0, lasttime = 0;
int g28 = 0;
//频率控制
long curtime2 = 0, lasttime2 = 0;
bool serialFlag = false;
//初次断电启动标示
bool startFlag = false;

void setup()
{
  Serial.begin(BAUD);
  #if SDCARD == 1
    if (!SD.begin(41)) {
     Serial.println("initialization failed!");
    }
  #endif
  stepperHigher.setPositionRad(-0.48);        // 0°
  stepperLower.setPositionRad(-0.48);         // 0°
  stepperRotate.setPositionRad(-0.48);        // 0°
  #if RAIL
  stepperRail.setPosition(0);
  #endif
  if (HOME_ON_BOOT) { //HOME DURING SETUP() IF HOME_ON_BOOT ENABLED
    homeSequence(); 
    Logger::logINFO("FengYue DELTA ONLINE");
  } else {
    setStepperEnable(false); //ROBOT ADJUSTABLE BY HAND AFTER TURNING ON
    if (HOME_X_STEPPER && HOME_Y_STEPPER && HOME_Z_STEPPER) {
      Logger::logINFO("ROBOT ONLINE");
      Logger::logINFO("SEND G28 TO CALIBRATE");
    }
  }
  // 初始化XYZ坐标值，把设置电机的速度模式，以及三轴的同步细分，根据GCODE值只设置一次，运行下一条命令再设置
  interpolator.setInterpolation(INITIAL_X, INITIAL_Y, INITIAL_Z, INITIAL_E0, INITIAL_X, INITIAL_Y, INITIAL_Z, INITIAL_E0);

  //游戏手柄
  #if SP2 == 1
    ps2Hander.init();
  #endif

  //关闭吸盘
  #if GRIPPER == XIPAN
    xipan.cmdOff();
  #endif
  #if SDCARD == 1
    sdcard.initCard("test1.txt");
    readSDCardInfo();
  #endif
  #if GRIPPER == SERVO
    servo_gripper.cmdClose();
  #endif
}

void loop() {
  // 更新物理坐标，控制三轴基本同步
  interpolator.updateActualPosition();
  // 笛卡尔坐标系控制，获取三轴同步控制坐标
  geometry.set(interpolator.getXPosmm(), interpolator.getYPosmm(), interpolator.getZPosmm());
  // 机械臂弧度控制，转换成步进电机的脉冲数
  stepperRotate.stepToPositionRad(geometry.getRotRad());
  stepperLower.stepToPositionRad(geometry.getLowRad());
  stepperHigher.stepToPositionRad(geometry.getHighRad());
  #if RAIL
    stepperRail.stepToPositionMM(interpolator.getEPosmm(), STEPS_PER_MM_RAIL);
  #endif
  stepperRotate.update();
  stepperLower.update();
  stepperHigher.update();
  #if RAIL
    stepperRail.update();
  #endif
  fan.update();
  // 命令插入队列
  if (!queue.isFull()) {
    if (command.handleGcode()) {
      queue.push(command.getCmd());
    }
  }
  // 执行队列命令，必须满足三轴都执行完
  if ((!queue.isEmpty()) && interpolator.isFinished()) {
    executeCommand(queue.pop());
    if (PRINT_REPLY) {
      Serial.println(PRINT_REPLY_MSG);
    }
  }
  // 遥控器命令处理后，插入到命令队列
  ps2CommandProcess();
  // 主板灯控制
  if(millis() % 500 < 250){
    led.cmdOn();
  }else {
    led.cmdOff();
  }
  if(queue.isEmpty()) {
    recordState = false;
  }
  //红外感应执行
  autoDoRecordList();
  //定时执行标记
  autoRunOntime();
  //夹爪频率限制
  operationFrequencyLimited();
  //特殊逻辑，发送G28自动初始化
//  if(startFlag == false){
//    command.processMessage("G28");
//    queue.push(command.getCmd());
//    startFlag = true;
//  }
}

// 是否循环执行示教队列
void autoDoRecordList(){
    //回放记录
  int autodo = digitalRead(X_MAX_PIN);
  if (queue.isEmpty() && interpolator.isFinished() && digitalRead(X_MAX_PIN) == LOW) {
    Serial.println("autodo");
    //备份记录
    if (!queueRecord.isEmpty()) {
      int size = queueRecord.getUsedSpace();
      Serial.println(size);
      for (int i = 0; i < size; i++) {
        queue.push(queueRecord.getData(i));
      }
      recordState = true;
    }
  }
}
//串口命令和手柄区分，夹爪开启和关闭的限制，2秒内不接收手柄命令
void operationFrequencyLimited(){
  curtime2 = millis();
  if(curtime2 - lasttime2 > 3000) { //1s
    serialFlag = false;
    lasttime2 = curtime2;
  }
}
//按照间隔时间，定时运行
void autoRunOntime(){
  if(autoRuntimeMin > 0 && autoRuntimeMin <= 60){
    curtime = millis();
    if(curtime - lasttime >=  autoRuntimeMin * 60000) {
      if (!queueRecord.isEmpty()) {
        int size = queueRecord.getUsedSpace();
        Serial.println(size);
        for (int i = 0; i < size; i++) {
          queue.push(queueRecord.getData(i));
        }
        recordState = true;
        lasttime = curtime;
      }
    }
  }
}

// PS2 命令预处理
void ps2CommandProcess() {
#if SP2 == 1
  if (queue.isEmpty() && interpolator.isFinished()) {
    int iRet = ps2Hander.process();
    if (iRet == -1) {
      ps2Hander.init();
      Serial.println("ps2 error");
    }
    if (iRet == 28) {
      command.processMessage("G28");
      queue.push(command.getCmd());
      //清理回放记录
      //queueRecord.clearQueue(QUEUE_SIZE);
      //command.processMessage("G90");
      //queueRecord.push(command.getCmd());
    }
    //up
    if (iRet >= 10 && iRet <= 15) {
      command.processMessage("G91");
      queue.push(command.getCmd());
      if (iRet == 10) {
        command.processMessage("G0 Y7 F40");
      } else {
        command.processMessage("G0 Y7 F40");
      }
      queue.push(command.getCmd());
      command.processMessage("G90");
      queue.push(command.getCmd());
    }
    //down
    if (iRet >= -15 && iRet <= -10) {
      command.processMessage("G91");
      queue.push(command.getCmd());
      if (iRet == -10) {
        command.processMessage("G0 Y-7 F40");
      } else {
        command.processMessage("G0 Y-7 F40");
      }
      queue.push(command.getCmd());
      command.processMessage("G90");
      queue.push(command.getCmd());
    }
    //left
    if (iRet >= -20 && iRet <= -16) {
      //Serial.println(iRet);
      command.processMessage("G91");
      queue.push(command.getCmd());
      if (iRet == -16) {
        command.processMessage("G0 X-7 F40");
      } else {
        command.processMessage("G0 X-7 F40");
      }
      queue.push(command.getCmd());
      command.processMessage("G90");
      queue.push(command.getCmd());
    }
    //right
    if (iRet >= 16 && iRet <= 20) {
      command.processMessage("G91");
      queue.push(command.getCmd());
      if (iRet == 16) {
        command.processMessage("G0 X7 F40");
      } else {
        command.processMessage("G0 X7 F40");
      }
      queue.push(command.getCmd());
      command.processMessage("G90");
      queue.push(command.getCmd());
    }
    //Z-1
    if (iRet == 21) {
      command.processMessage("G91");
      queue.push(command.getCmd());
      command.processMessage("G0 Z7 F40");
      queue.push(command.getCmd());
      command.processMessage("G90");
      queue.push(command.getCmd());
    }
    //Z+1
    if (iRet == 22) {
      command.processMessage("G91");
      queue.push(command.getCmd());
      command.processMessage("G0 Z-7 F40");
      queue.push(command.getCmd());
      command.processMessage("G90");
      queue.push(command.getCmd());
    }
    //jiazhua
    if(iRet == 23 || iRet == 24){
      Serial.print("serialFlag:");
      Serial.println(serialFlag);
    }
    if (iRet == 23 && !recordState && !serialFlag)
    {
      command.processMessage("M3");
      queue.push(command.getCmd());
    }
    if (iRet == 24 && !recordState && !serialFlag) {
      command.processMessage("M5");
      queue.push(command.getCmd());
    }
    //清理录制位置
    if (iRet == 25) {
      queueRecord.clearQueue(QUEUE_SIZE);
      //回到绝对坐标
      command.processMessage("G90");
      queueRecord.push(command.getCmd());
      #if GRIPPER == SERVO
        lastjiazhuaSate = false;
        servo_gripper.cmdClose();
      #endif
      #if GRIPPER == XIPAN
        lastxipanState = false;
        xipan.cmdOff();
      #endif
    }
    //添加录制的位置
    if (iRet == 26) {
      //自动添加坐标位置
      String temp = "G0 X" + String(interpolator.getXPosmm()) + " Y" + String(interpolator.getYPosmm()) + " Z" + String(interpolator.getZPosmm()) + " E" + String(interpolator.getEPosmm()) + " F"+String(PS2SPEED);
      Serial.println(temp);
      command.processMessage(temp);
      queueRecord.push(command.getCmd());
      
      //自动添加吸盘命令
      #if GRIPPER == XIPAN
      if(lastxipanState != xipan.getState()) {
         if(xipan.getState()) {
           command.processMessage("M5");
           queueRecord.push(command.getCmd());
           Serial.println("M5 ADD");
         }else {
           command.processMessage("M3");
           queueRecord.push(command.getCmd());
           Serial.println("M3 ADD");
         }
      }
      lastxipanState = xipan.getState();
      //夹爪自动添加
      #elif GRIPPER == SERVO
      if(lastjiazhuaSate != servo_gripper.isOpen()) {
          if(servo_gripper.isOpen()) {
             command.processMessage("M5");
             queueRecord.push(command.getCmd());
             Serial.println("M5 ADD");
           } else {
             command.processMessage("M3");
             queueRecord.push(command.getCmd());
             Serial.println("M3 ADD");
           }
      }
      lastjiazhuaSate = servo_gripper.isOpen();
      #endif
    }
    //回放记录
    if (iRet == 27) {
      //备份记录
      if (!queueRecord.isEmpty()) {
        int size = queueRecord.getUsedSpace();
        Serial.println(size);
        for (int i = 0; i < size; i++) {
          Cmd cmd = queueRecord.getData(i);
          queue.push(cmd);
        }
      }
      recordState = true;
      Serial.println("Record mode");
    }
    //夹爪关闭放到录制队列中
    if(iRet == 29 && !recordState && !serialFlag) {
      command.processMessage("M3");
      queueRecord.push(command.getCmd());
    }
    //夹爪打开放到录制中
    if(iRet == 30 && !recordState && !serialFlag) {
      command.processMessage("M5");
      queueRecord.push(command.getCmd());
    }
   //rail -
    if (iRet == 35) {
      command.processMessage("G91");
      queue.push(command.getCmd());
      command.processMessage("G0 E7 F30");
      queue.push(command.getCmd());
      command.processMessage("G90");
      queue.push(command.getCmd());
    }
    //ral +
    if (iRet == 36) {
      command.processMessage("G91");
      queue.push(command.getCmd());
      command.processMessage("G0 E-7 F30");
      queue.push(command.getCmd());
      command.processMessage("G90");
      queue.push(command.getCmd());
    }
    delay(50);
    iRet = 0;
  }
#endif
}
// 执行队列命令
void executeCommand(Cmd cmd) {
  if (cmd.id == -1) {
    printErr();
    return;
  }
  if (cmd.id == 'G') {
    switch (cmd.num) {
    case 0:
    case 1:
      fan.enable(true);
      Point posoffset;
      posoffset = interpolator.getPosOffset();      
      cmdMove(cmd, interpolator.getPosmm(), posoffset, command.isRelativeCoord);
      interpolator.setInterpolation(cmd.valueX, cmd.valueY, cmd.valueZ, cmd.valueE, cmd.valueF);
      Logger::logINFO("LINEAR MOVE: X" + String(cmd.valueX-posoffset.xmm) + " Y" + String(cmd.valueY-posoffset.ymm) + " Z" + String(cmd.valueZ-posoffset.zmm) + " E" + String(cmd.valueE-posoffset.emm));
      break;
    case 4: cmdDwell(cmd); break;
    case 28: homeSequence(); 
    	command.cmdToAbsolute();//回到绝对坐标下
    	break;
    case 90: command.cmdToAbsolute(); break; // ABSOLUTE COORDINATE MODE
    case 91: command.cmdToRelative(); break; // RELATIVE COORDINATE MODE
    case 92: 
      interpolator.resetPosOffset();
      cmdMove(cmd, interpolator.getPosmm(), interpolator.getPosOffset(), false);
      interpolator.setPosOffset(cmd.valueX, cmd.valueY, cmd.valueZ, cmd.valueE);
      break;
    default: printErr();
    }
  }
  else if (cmd.id == 'M') {
    switch (cmd.num) {
      case 1: pump.cmdOn(); break;
      case 2: pump.cmdOff(); break;
      case 3:
        Logger::logINFO("M3 CLOSE");
        #if GRIPPER == BYJ
          byj_gripper.cmdOff(); break;
        #elif GRIPPER == SERVO
          servo_gripper.cmdClose(); break;
        #elif GRIPPER == XIPAN
          xipan.cmdOff();break;
        #endif
      case 5:
        Logger::logINFO("M5 OPEN");
        #if GRIPPER == BYJ
          byj_gripper.cmdOn(); break;
        #elif GRIPPER == SERVO
          servo_gripper.cmdOpen(); break;
        #elif GRIPPER == XIPAN
          xipan.cmdOn();break;
        #endif
      case 6: laser.cmdOn(); break;
      case 7: laser.cmdOff(); break;
      case 10: getRecordInfo();break;
      case 11: writeRecordInfo(command.getMessage2());break;
      case 12: doRecordList();break;
      #if GRIPPER == XIPAN
      case 13: xipan.cmdOn();break;
      case 14: xipan.cmdOff(); break;
      #endif
      case 17: setStepperEnable(true); break;
      case 18: setStepperEnable(false); break;
      case 19: autoRuntimeMin = cmd.valueS; break;
      case 20: addPosInfo();break;
      case 21: clearPosInfo();break;
      case 22: doRecordList();break;
      case 106: fan.enable(true); break;
      case 107: fan.enable(false); break;
      case 114: command.cmdGetPosition(interpolator.getPosmm(), interpolator.getPosOffset(), stepperHigher.getPosition(), stepperLower.getPosition(), stepperRotate.getPosition()); break;// Return the current positions of all axis
      case 119: {
          String endstopMsg = "ENDSTOP: [X:";
          endstopMsg += String(endstopX.state());
          endstopMsg += " Y:";
          endstopMsg += String(endstopY.state());
          endstopMsg += " Z:";
          endstopMsg += String(endstopZ.state());
      	  #if RAIL
           endstopMsg += " E:";
           endstopMsg += String(endstopE0.state());
          #endif
          endstopMsg += "]";
          //ORIGINAL LOG STRING UNDESIRABLE FOR UNO PROCESSING
          //Logger::logINFO("ENDSTOP STATE: [UPPER_SHANK(X):"+String(endstopX.state())+" LOWER_SHANK(Y):"+String(endstopY.state())+" ROTATE_GEAR(Z):"+String(endstopZ.state())+"]");
          Logger::logINFO(endstopMsg);
          break;
        }
      case 205:
        //interpolator.setSpeedProfile(cmd.valueS);
        //Logger::logINFO("SPEED PROFILE: [" + String(interpolator.speed_profile) + "]");
        break;
      default: printErr();
    }
  }
  else {
    printErr();
  }
}

void setStepperEnable(bool enable){
  stepperRotate.enable(enable);
  stepperLower.enable(enable);
  stepperHigher.enable(enable);
#if RAIL
  stepperRail.enable(enable);
#endif
  fan.enable(enable);
}

void homeSequence() {
  if(g28 == 1){
    Serial.println("Homing have completed, don't send G28 again!");
    return;
  }
  setStepperEnable(false);
  fan.enable(true);
  if (HOME_X_STEPPER){
    endstopX.home(!INVERSE_Y_STEPPER); //INDICATE STEPPER HOMING DIRECTION
  }
  if (HOME_Y_STEPPER){
    endstopY.home(!INVERSE_X_STEPPER); //INDICATE STEPPER HOMING DIRECTION
  }
  if (HOME_Z_STEPPER){
    endstopZ.home(!INVERSE_Z_STEPPER); //INDICATE STEPPER HOMING DIRECDTION
  }
  #if RAIL
    if (HOME_E0_STEPPER){
      endstopE0.home(!INVERSE_E0_STEPPER);
    }
  #endif
  autoRuntimeMin = 0.0;
  //设置点击初始状态
  stepperHigher.setPositionRad(-0.48);        // 0°
  stepperLower.setPositionRad(-0.48);         // 0°
  stepperRotate.setPositionRad(-0.48);        // 0°.
  #if RAIL
  stepperRail.setPosition(0);
  #endif
  interpolator.setInterpolation(INITIAL_X, INITIAL_Y, INITIAL_Z, INITIAL_E0, INITIAL_X, INITIAL_Y, INITIAL_Z, INITIAL_E0);
  Logger::logINFO("HOMING COMPLETE");
  g28 = 1;//初始化完成标志
}

// 执行示教命令
void doRecordList() {
  //备份记录
  if (!queueRecord.isEmpty()) {
    int size = queueRecord.getUsedSpace();
    Serial.println(size);
    for (int i = 0; i < size; i++) {
      queue.push(queueRecord.getData(i));
    }
    recordState = true;
  }
  Serial.println("Record mode");
}

// 写入示教命令
void writeRecordInfo(String messages) {
  Serial.println(messages);
  messages = messages.substring(messages.indexOf("S") + 1);
  if(messages.length() < 3) {
    Serial.println("writeRecordInfo: len to short!");
    return;
  }
  Serial.println(messages);
  queueRecord.clearQueue(QUEUE_SIZE);
  int lastpos = 0;
  for(int i=0; i< messages.length(); i++) {  
    if(messages[i] == ';') {
      String cmd = messages.substring(lastpos, i);
      Serial.println(cmd);
      if(cmd.indexOf("G") != 0 && cmd.indexOf("M") != 0) {
        Serial.println("writeRecordInfo:cmd is not valid!");
        continue;
      }
      lastpos = i + 1;
      command.processMessage(cmd);
      #if SDCARD == 1
        cmd.replace(".00","");
        Serial.println(cmd);
        sdcard.writeCard("test1.txt", cmd);
      #endif
      queueRecord.push(command.getCmd());//插入示教队列
    }
  }
  #if SDCARD == 1
    sdcard.closeFile();
  #endif
}

// 获取示教列表
void getRecordInfo() {
  if (!queueRecord.isEmpty()) {
    int size = queueRecord.getUsedSpace();
    Serial.println(size);
    Serial.print("cmdstart");
    for (int i = 0; i < size; i++) {
      Cmd cmd = queueRecord.getData(i);
      String tempStr = "";
      tempStr = cmd.id + String(cmd.num);
      if(!isnan(cmd.valueX)) {
        tempStr = tempStr +" X" + String(cmd.valueX);
      }
      if(!isnan(cmd.valueY)) {
        tempStr = tempStr +" Y" + String(cmd.valueY);
      }
      if(!isnan(cmd.valueZ)) {
        tempStr = tempStr +" Z" + String(cmd.valueZ);
      }
      if(!isnan(cmd.valueE)) {
        tempStr = tempStr +" E" + String(cmd.valueE);
      }
      if(cmd.valueF != 0) {
        tempStr = tempStr +" F" + String(cmd.valueF);
      }
      if(cmd.valueS != 0) {
        tempStr = tempStr +" S" + String(cmd.valueS);
      }
      tempStr = tempStr + "\n";
      tempStr.replace(".00 "," ");
      Serial.print(tempStr);
    }
    Serial.println("cmdend");
  }
}

//读取SD卡信息，添加回放列表
void readSDCardInfo(){
  #if SDCARD == 1
  String cmdStr = sdcard.readCard("test1.txt");
  while(cmdStr.indexOf("\n") > 0) {
    String str1 = cmdStr.substring(0, cmdStr.indexOf("\n"));
    Serial.println(str1);
    command.processMessage(str1);
    queueRecord.push(command.getCmd());
    cmdStr = cmdStr.substring(cmdStr.indexOf("\n")+1);
  }
  #endif
  Serial.println("readSDCardInfo");
}

// 添加录制信息
void addPosInfo() {
      if(queueRecord.isEmpty()) {
        command.processMessage("G90");
        queueRecord.push(command.getCmd()); 
      }
     //自动添加坐标位置
      String temp = "G0 X" + String(interpolator.getXPosmm()) + " Y" + String(interpolator.getYPosmm()) + " Z" + String(interpolator.getZPosmm()) + " E" + String(interpolator.getEPosmm()) + " F"+String(PS2SPEED);
      Serial.println(temp);
      command.processMessage(temp);
      queueRecord.push(command.getCmd());

      //自动添加吸盘命令
      #if GRIPPER == XIPAN
      if(lastxipanState != xipan.getState()) {
         if(xipan.getState()) {
           command.processMessage("M5");
           queueRecord.push(command.getCmd());
           Serial.println("M5 ADD");
         }else {
           command.processMessage("M3");
           queueRecord.push(command.getCmd());
           Serial.println("M3 ADD");
         }
      }
      lastxipanState = xipan.getState();
      //夹爪自动添加
      #elif GRIPPER == SERVO
      if(lastjiazhuaSate != servo_gripper.isOpen()) {
          if(servo_gripper.isOpen()) {
             command.processMessage("M5");
             queueRecord.push(command.getCmd());
             Serial.println("M5 ADD");
           } else {
             command.processMessage("M3");
             queueRecord.push(command.getCmd());
             Serial.println("M3 ADD");
           }
      }
      lastjiazhuaSate = servo_gripper.isOpen();
      #endif
      delay(200);
}
// 清理录制信息
void clearPosInfo() {
   queueRecord.clearQueue(QUEUE_SIZE);
   command.processMessage("G90");
   queueRecord.push(command.getCmd());
   delay(200);
}
