`timescale 1ns/1ps
module tb_continuous_motion;
 parameter MODE=0,SCALE=1;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,rebase_req=0,enable_req=0,disable_req=0,open_req=0;
 reg start_req=0,pause_req=0,resume_req=0,stop_req=0,clear_fault=0;
 reg [3:0] fault=0,rebase_mask=15,enable_mask=15,disable_mask=15;
 reg [255:0] rebase_position=0,point_target=0;
 reg [63:0] open_session_id=1,point_session=1,duration_tick=1;
 reg [31:0] point_sequence=0;reg point_valid=0,point_end=0;reg [3:0] point_mask=15;
 wire ready,session_valid,running,paused,busy,start_ready,resume_ready;
 wire accepted,stale,rejected,cancelled,underflow_event,session_done,start,done,stopped;
 wire [3:0] step,dir,en,position_valid,fl,cv,pulse;wire [255:0] position;
 wire [63:0] session_id,slot_id;wire slot;wire [31:0] raw_level,plan_level,buffered,active_seq,done_seq;
 localparam H=3*SCALE,L=2*SCALE,S=4*SCALE,Q=7*SCALE,E=5*SCALE;
 continuous_motion #(.FIFO_DEPTH(3),.PLAN_DEPTH(2),.START_MIN_POINTS(2),
  .STEP_HIGH_CYCLES({4{64'd3*SCALE}}),.STEP_LOW_CYCLES({4{64'd2*SCALE}}),
  .DIR_SETUP_CYCLES({4{64'd4*SCALE}}),.DIR_HOLD_CYCLES({4{64'd7*SCALE}}),
  .EN_SETUP_CYCLES({4{64'd5*SCALE}}),.EN_DISABLE_CYCLES({4{64'd3*SCALE}}),
  .MAX_STEP_HZ({4{64'd10000000/SCALE}})) dut(
  .clk(clk),.rst_n(rst_n),.rebase_req(rebase_req),.rebase_mask(rebase_mask),.rebase_position(rebase_position),
  .enable_req(enable_req),.enable_mask(enable_mask),.disable_req(disable_req),.disable_mask(disable_mask),
  .open_req(open_req),.open_session_id(open_session_id),.start_req(start_req),.pause_req(pause_req),
  .resume_req(resume_req),.stop_req(stop_req),.clear_fault(clear_fault),.fault(fault),
  .point_valid(point_valid),.point_ready(ready),.point_session(point_session),.point_sequence(point_sequence),
  .point_end(point_end),.point_mask(point_mask),.point_target(point_target),.duration_tick(duration_tick),
  .step(step),.dir(dir),.en(en),.position_valid(position_valid),.fault_latched(fl),.config_valid(cv),.position(position),
  .session_valid(session_valid),.session_id(session_id),.running(running),.paused(paused),.busy(busy),
  .start_ready(start_ready),.resume_ready(resume_ready),.fifo_level(raw_level),.prepared_level(plan_level),
  .buffered_points(buffered),.accepted(accepted),.stale(stale),.rejected(rejected),.cancelled(cancelled),
  .underflow_event(underflow_event),.session_done(session_done),.point_start(start),.point_done(done),.stopped(stopped),
  .active_sequence(active_seq),.done_sequence(done_seq),.pulse_event(pulse),.slot_event(slot),.slot_id(slot_id));
 reg [255:0] targets[0:15];reg [63:0] durations[0:15];reg [3:0] masks[0:15];
 reg signed [63:0] model[0:3];reg signed [64:0] delta,next_position;
 reg [63:0] n[0:3],master,guard,cycles,expected_slot;
 reg [127:0] product;reg [3:0] signs,expected_emit,previous=0,prev_dir=15;
 integer rise[0:3],fall[0:3],dir_change[0:3],enable_time;
 integer checks=0,cycle=0,starts=0,dones=0,ends=0,underflows=0,stales=0,abort_cases=0;
 integer point_at=0,first_at=0,last_done=-1,total_duration=0,seq_now=0,j;
 reg tracking=0,sample_abort,sample_rebase;
 task check;input condition;input [511:0] message;
  begin checks=checks+1;if(condition!==1'b1)begin $display("FAIL continuous mode=%0d cycle=%0d %0s",MODE,cycle,message);$fatal(1);end end
 endtask
 always @(posedge clk)begin
  sample_abort=stop_req || disable_req || (|fault);
  sample_rebase=rebase_req && !session_valid && !busy;
  #1;cycle=cycle+1;
  if(!rst_n)begin
   tracking=0;previous=0;prev_dir=15;last_done=-1;total_duration=0;first_at=0;
   for(j=0;j<4;j=j+1)begin model[j]=0;rise[j]=-10000;fall[j]=cycle;dir_change[j]=cycle;end
   enable_time=cycle;
   check(position==0 && position_valid==0 && step==0 && en==0 && !session_valid,"reset safe/no session");
  end else begin
   if(accepted)begin targets[point_sequence]=point_target;durations[point_sequence]=duration_tick;masks[point_sequence]=point_mask;end
   if(open_req && session_valid && session_id==open_session_id)begin last_done=-1;first_at=0;total_duration=0;end
   if(enable_req)enable_time=cycle;
   if(sample_abort || cancelled || underflow_event)begin tracking=0;check((step&~previous)==0 && !start,"cancel priority");end
   expected_emit=0;
   if(tracking && master!=0 && expected_slot<master)begin
    product={64'b0,expected_slot}*{64'b0,(cycles-guard)};
    if(cycle-point_at==guard+product/master)begin
     for(j=0;j<4;j=j+1)if(n[j]!=0)begin
      product={64'b0,expected_slot}*{64'b0,n[j]};
      expected_emit[j]=expected_slot==0 || product/master>(product-n[j])/master;
     end
     check(slot && slot_id==expected_slot,"exact slot/time");expected_slot=expected_slot+1;
    end else check(!slot,"no unplanned slot");
   end else if(tracking)check(!slot,"dwell/tail has no slot");
   if(tracking)check((step&~previous)==expected_emit,"same-slot corresponding edges");
   check(pulse==(step&~previous),"physical edge event");
   for(j=0;j<4;j=j+1)begin
    if(sample_rebase && rebase_mask[j])model[j]=$signed(rebase_position[j*64+:64]);
    if(dir[j]!=prev_dir[j])begin check(!step[j] && !previous[j] && cycle-rise[j]>=Q,"DIR hold");dir_change[j]=cycle;end
    if(step[j]&&!previous[j])begin
     check(en[j] && position_valid[j],"EN/position valid at edge");
     check(cycle-fall[j]>=L && cycle-dir_change[j]>=S && cycle-enable_time>=E,"pulse low/setup");
     check(cycle-rise[j]>=10*SCALE,"instantaneous max rate");
     check(dir[j]==signs[j],"signed65 direction");
     next_position=$signed({model[j][63],model[j]})+(dir[j] ? 65'sd1 : -65'sd1);
     check(next_position[64]==next_position[63],"no position overflow");model[j]=next_position[63:0];rise[j]=cycle;
    end
    if(!step[j]&&previous[j])begin check(cycle-rise[j]==H,"complete high pulse on stop");fall[j]=cycle;end
    check($signed(position[j*64+:64])===model[j],"actual position never advanced by planning");
    if(done || stopped)check(!step[j] && cycle-fall[j]>=L && cycle-rise[j]>=Q,"pulse safe completion");
   end
   previous=step;prev_dir=dir;
   if(done)begin
    check(tracking && cycle-point_at==cycles && done_seq==seq_now,"exact duration/sequence completion");
    for(j=0;j<4;j=j+1)if(masks[seq_now][j])check(model[j]==$signed(targets[seq_now][j*64+:64]),"absolute target reached");
    tracking=0;dones=dones+1;last_done=cycle;total_duration=total_duration+cycles;
   end
   if(start)begin
    if(last_done>=0 && !resume_req)check(cycle==last_done,"zero inter-point planning gap");
    tracking=1;point_at=cycle;seq_now=active_seq;expected_slot=0;master=0;guard=0;
    cycles=durations[active_seq]*100;signs=dir;
    for(j=0;j<4;j=j+1)begin
     n[j]=0;
     if(masks[active_seq][j])begin
      delta=$signed({targets[active_seq][j*64+63],targets[active_seq][j*64+:64]})-$signed({model[j][63],model[j]});
      n[j]=delta[64] ? -delta : delta;
      if(n[j]!=0)begin signs[j]=!delta[64];guard=Q+S+2;if(n[j]>master)master=n[j];end
     end
    end
    if(first_at==0)first_at=cycle;starts=starts+1;
   end
   if(session_done)begin check(done && !session_valid && !underflow_event,"END closes normally");ends=ends+1;end
   if(underflow_event)underflows=underflows+1;
   if(stale)stales=stales+1;
  end
 end
 task tick;begin @(posedge clk);#2;end endtask
 task wait_idle;integer k;begin k=0;while(busy && k<2000)begin tick;k=k+1;end check(!busy,"bounded drain/complete");end endtask
 task setup;input [63:0] id;
  begin
   @(negedge clk);rst_n=0;point_valid=0;rebase_req=0;enable_req=0;disable_req=0;open_req=0;
   start_req=0;pause_req=0;resume_req=0;stop_req=0;fault=0;clear_fault=0;
   tick;tick;@(negedge clk);rst_n=1;repeat(20*SCALE)tick;
   @(negedge clk);rebase_position=0;rebase_req=1;tick;
   @(negedge clk);rebase_req=0;enable_req=1;tick;
   @(negedge clk);enable_req=0;repeat(10*SCALE)tick;
   @(negedge clk);open_session_id=id;open_req=1;tick;
   check(session_valid && session_id==id,"explicit OPEN");
   @(negedge clk);open_req=0;point_session=id;
  end
 endtask
 task enqueue;input [31:0] seq;input [255:0] target;input [3:0] mask;input last;
  integer k;
  begin @(negedge clk);point_sequence=seq;point_target=target;point_mask=mask;point_end=last;duration_tick=SCALE;point_valid=1;
   k=0;tick;while(!(accepted||stale||rejected) && k<1000)begin tick;k=k+1;end
   check(k<1000,"bounded input handshake");@(negedge clk);point_valid=0;
  end
 endtask
 task start_motion;integer k;
  begin k=0;while(!start_ready && session_valid && k<1000)begin tick;k=k+1;end
   check(start_ready,"START prebuffer+precheck gate");@(negedge clk);start_req=1;tick;check(start,"explicit START accepted");
   @(negedge clk);start_req=0;
  end
 endtask
 integer i,kind,before_starts,before_ends,before_edges_at,before_underflows,k;
 reg [255:0] snapshot;
 initial begin
  if(MODE==0)begin
   setup(1);
   enqueue(0,{64'd0,-64'sd1,64'd2,64'd3},7,0);
   @(negedge clk);start_req=1;tick;check(rejected && !start,"START too little prebuffer rejected");@(negedge clk);start_req=0;
   enqueue(1,{64'd0,64'd0,-64'sd1,-64'sd2},3,0);
   enqueue(2,{64'd0,-64'sd1,-64'sd1,-64'sd2},15,0);
   enqueue(3,{64'd2,64'hdeadbeef,64'hdeadbeef,64'hdeadbeef},8,0);
   enqueue(4,{4{64'hdeadbeef}},0,0);
   enqueue(5,{-64'sd1,64'd0,64'd0,64'd1},15,1);
   start_motion;wait_idle;
   check(!session_valid && total_duration==600*SCALE && cycle-first_at==600*SCALE,"six exact continuous durations");
   setup(2);enqueue(0,64'd1,1,1);start_motion;wait_idle;
   check(total_duration==100*SCALE && !session_valid,"short END exception to prebuffer threshold");
  end
  if(MODE==1)begin
   setup(10);enqueue(0,64'd2,1,0);enqueue(1,-64'sd1,1,0);enqueue(2,64'd3,1,1);start_motion;
   while(cycle-point_at<100*SCALE-1)tick;
   @(negedge clk);pause_req=1;tick;check(paused && !start && done,"boundary same-clock PAUSE");
   @(negedge clk);pause_req=0;snapshot=position;before_starts=starts;
   repeat(80)tick;check(paused && starts==before_starts && position==snapshot && en==15,"pause retains queue/session/EN");
   point_session=999;enqueue(0,64'd100,1,0);check(session_valid && paused,"stale point does not disrupt pause");point_session=10;
   while(!resume_ready)tick;@(negedge clk);resume_req=1;tick;check(start && !paused,"RESUME uses ready prefetched point");
   @(negedge clk);resume_req=0;
   while(active_seq!=2)tick;
   while(cycle-point_at<100*SCALE-1)tick;
   @(negedge clk);pause_req=1;tick;
   check(session_done && done && !paused && !session_valid,"END wins boundary PAUSE");
   @(negedge clk);pause_req=0;wait_idle;
   check(total_duration==300*SCALE && cycle-first_at>300*SCALE,"paused wall time excluded");
  end
  if(MODE==2)begin
   setup(20);enqueue(0,64'd2,1,0);enqueue(1,-64'sd1,1,0);start_motion;
   while(active_seq!=1)tick;
   while(cycle-point_at<100*SCALE-1)tick;
   @(negedge clk);point_valid=1;point_sequence=2;point_target=3;point_end=1;
   tick;check(underflow_event && cancelled && !start && !session_valid,"same-boundary late point cannot cure underflow");
   tick;check(stale,"late old point discarded");@(negedge clk);point_valid=0;wait_idle;
   check(buffered==0 && raw_level==0 && plan_level==0,"underflow clears FIFO and prefetch");
  end
  if(MODE==3)begin
   setup(30);
   fork
    begin for(i=0;i<8;i=i+1)enqueue(i,(i%2) ? -64'sd1 : 64'sd2,1,i==7);end
    begin
     k=0;while(!(raw_level==3 && plan_level==2 && buffered==6) && k<1000)begin tick;k=k+1;end
     check(k<1000 && position==0,"full planning cache does not move position");
     // Allow the source to advance from the just-accepted sequence to the
     // next valid payload before interpreting data-dependent ready.
     repeat(3)tick;
     repeat(5)tick;check(!ready,"full holds backpressure");start_motion;
    end
   join
   wait_idle;check(total_duration==800*SCALE && !session_valid,"full FIFO stream drains continuously");
  end
  if(MODE==4)begin
   setup(40);enqueue(1,1,1,0);check(!session_valid && cancelled,"missing sequence cancels");wait_idle;
   setup(41);enqueue(0,1,1,0);enqueue(0,1,1,0);check(!session_valid,"duplicate cancels");wait_idle;
   setup(42);enqueue(0,1,1,1);enqueue(1,2,1,0);check(!session_valid,"post-END same-session point cancels");wait_idle;
   setup(43);point_session=42;enqueue(0,100,1,1);check(stale && session_valid && buffered==0,"old ID isolated from new session");
   point_session=43;enqueue(0,1,1,1);start_motion;wait_idle;
  end
  if(MODE>=5 && MODE<=7)begin
   kind=MODE-5;
   for(i=0;i<280*SCALE;i=i+1)begin
    setup(1000+i);enqueue(0,64'd3,1,0);enqueue(1,-64'sd2,1,1);abort_cases=abort_cases+1;
    fork
     begin
      while(!start_ready && session_valid)tick;
      if(session_valid)begin @(negedge clk);start_req=1;tick;@(negedge clk);start_req=0;end
     end
     begin
      repeat(i)tick;@(negedge clk);
      case(kind)0:stop_req=1;1:fault=2;2:rst_n=0;endcase
      tick;snapshot=position;check(!session_valid && !start,"cancel/reset during prefetch/run");
      @(negedge clk);stop_req=0;if(kind==2)rst_n=1;
     end
    join
    wait_idle;repeat(30*SCALE)tick;check(position==snapshot && !session_valid,"no old prefetch recovery");
    check(buffered==0 && raw_level==0 && plan_level==0,"all cancelled caches clear");
    point_session=1000+i;enqueue(2,100,1,1);check(stale && !session_valid,"late cancelled point stays stale");
   end
  end
  if(MODE==8)begin
   setup(80);enqueue(0,64'd3,1,0);enqueue(1,64'h8000000000000000,1,1);start_motion;
   k=0;while(session_valid && k<500)begin tick;k=k+1;end
   check(k<500 && cancelled && !session_done,"unexecutable prefetch cancels current session");
   wait_idle;check(position[63:0]<3 && buffered==0 && raw_level==0 && plan_level==0,"no speculative position commit");
   snapshot=position;
   @(negedge clk);open_req=1;open_session_id=81;tick;
   check(session_valid && position==snapshot,"new session snapshots actual partial count");
   @(negedge clk);open_req=0;point_session=81;enqueue(0,64'd1,1,1);start_motion;wait_idle;
   check(position[63:0]==1 && !session_valid,"new plan recovers from actual count, not old endpoint");
  end
  if(MODE==9)begin
   setup(90);enqueue(0,64'd2,1,0);enqueue(1,-64'sd1,1,0);start_motion;
   while(active_seq!=1)tick;while(cycle-point_at<100*SCALE-1)tick;
   @(negedge clk);pause_req=1;tick;check(paused && !underflow_event,"PAUSE wins missing next at boundary");
   @(negedge clk);pause_req=0;resume_req=1;tick;
   check(rejected && paused && !start,"RESUME without prepared next remains paused");
   @(negedge clk);resume_req=0;enqueue(2,64'd3,1,1);
   while(!resume_ready)tick;@(negedge clk);resume_req=1;tick;check(start,"explicit RESUME after late precheck");
   @(negedge clk);resume_req=0;wait_idle;check(total_duration==300*SCALE,"paused empty queue resumes exact durations");
  end
  $display("PASS continuous mode=%0d scale=%0d checks=%0d starts=%0d dones=%0d END=%0d underflows=%0d stale=%0d abort_offsets=%0d",
   MODE,SCALE,checks,starts,dones,ends,underflows,stales,abort_cases);$finish;
 end
 initial begin #30000000;$fatal(1,"continuous timeout");end
endmodule
