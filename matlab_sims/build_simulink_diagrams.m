%% RECLAIM — Auto-build Simulink Block Diagrams
%  Author: Shady Siam  |  Date: March 25, 2026
clear; clc;
fprintf('Building RECLAIM Simulink block diagrams...\n\n');

% =========================================================================
%  MODEL 1 — PROTOTYPE PI CONTROL LOOP
%  Strategy: use simple single-word names for all add_block/add_line calls
%  Rename for display ONLY after all connections are made
% =========================================================================
mdl1 = 'reclaim_prototype_control';
if bdIsLoaded(mdl1), close_system(mdl1, 0); end
if exist([mdl1 '.slx'], 'file'), delete([mdl1 '.slx']); end
new_system(mdl1);
open_system(mdl1);
set_param(mdl1, 'SolverType', 'Fixed-step', 'FixedStep', '0.001');
set_param(mdl1, 'Location', [50 50 1300 700]);

% ---- Add blocks (simple names only — no spaces, no special chars) ----
add_block('simulink/Sources/Step',               [mdl1 '/Ref']);
add_block('simulink/Math Operations/Sum',         [mdl1 '/Sum']);
add_block('simulink/Continuous/Transfer Fcn',     [mdl1 '/PI']);
add_block('simulink/Discontinuities/Saturation',  [mdl1 '/Sat']);
add_block('simulink/Continuous/Transfer Fcn',     [mdl1 '/Plant']);
add_block('simulink/Math Operations/Gain',        [mdl1 '/Enc']);
add_block('simulink/Math Operations/Gain',        [mdl1 '/Odom']);
add_block('simulink/Sinks/Scope',                 [mdl1 '/Out']);

% ---- Positions ----
set_param([mdl1 '/Ref'],   'Position', [30  215 130 265]);
set_param([mdl1 '/Sum'],   'Position', [175 225 215 265]);
set_param([mdl1 '/PI'],    'Position', [265 210 395 270]);
set_param([mdl1 '/Sat'],   'Position', [445 210 545 270]);
set_param([mdl1 '/Plant'], 'Position', [595 210 745 270]);
set_param([mdl1 '/Out'],   'Position', [800 228 830 252]);
set_param([mdl1 '/Enc'],   'Position', [595 370 705 410]);
set_param([mdl1 '/Odom'],  'Position', [390 370 510 410]);

% ---- Block parameters ----
set_param([mdl1 '/Ref'],   'Time', '0.5', 'Before', '0', 'After', '0.20', 'SampleTime', '0');
set_param([mdl1 '/Sum'],   'Inputs', '+-');
% Actual firmware values — pole placement with zeta=0.7, wn=1.5/tau=29.82 rad/s
% Kp = (2*zeta*wn*tau - 1) / K = (2*0.7*1.5 - 1) / 0.001170 = 940
% Ki = (wn^2 * tau) / K = (29.82^2 * 0.0503) / 0.001170 = 38230
set_param([mdl1 '/PI'],    'Numerator', '[940 38230]', 'Denominator', '[1 0]');
set_param([mdl1 '/Sat'],   'UpperLimit', '255', 'LowerLimit', '-255');
% 1st order plant — firmware uses single time constant tau=0.0503s
% G(s) = K / (tau*s + 1) = 0.001170 / (0.0503s + 1)
set_param([mdl1 '/Plant'], 'Numerator', '[0.001170]', 'Denominator', '[0.0503 1]');
set_param([mdl1 '/Enc'],   'Gain', '1');
set_param([mdl1 '/Odom'],  'Gain', '1');

% ---- Connect forward path FIRST (using original simple names) ----
add_line(mdl1, 'Ref/1',   'Sum/1',   'autorouting', 'on');
add_line(mdl1, 'Sum/1',   'PI/1',    'autorouting', 'on');
add_line(mdl1, 'PI/1',    'Sat/1',   'autorouting', 'on');
add_line(mdl1, 'Sat/1',   'Plant/1', 'autorouting', 'on');
add_line(mdl1, 'Plant/1', 'Out/1',   'autorouting', 'on');

% ---- Connect feedback path ----
add_line(mdl1, 'Plant/1', 'Enc/1',  'autorouting', 'on');
add_line(mdl1, 'Enc/1',   'Odom/1', 'autorouting', 'on');
add_line(mdl1, 'Odom/1',  'Sum/2',  'autorouting', 'on');

% ---- Rename for display (AFTER all connections) ----
set_param([mdl1 '/Ref'],   'Name', 'cmd_vel Ref (m/s)');
set_param([mdl1 '/PI'],    'Name', 'PI Controller Kp=80 Ki=20');
set_param([mdl1 '/Sat'],   'Name', 'PWM Saturation [-255 to 255]');
set_param([mdl1 '/Plant'], 'Name', 'DC Motor Plant (JGB37-520)');
set_param([mdl1 '/Out'],   'Name', 'Wheel Velocity (m/s)');
set_param([mdl1 '/Enc'],   'Name', 'Encoder 7560 ticks/rev');
set_param([mdl1 '/Odom'],  'Name', 'Odometry (m/s)');

% ---- Title annotation ----
add_block('built-in/Note', [mdl1 '/Title']);
set_param([mdl1 '/Title'], 'Position', [30 140 900 162], ...
    'Text', 'RECLAIM PROTOTYPE — PI Closed-Loop Velocity Controller  |  Teensy 4.1 @ 50 Hz  |  Kp=940  Ki=38230  |  zeta=0.7  wn=29.8 rad/s', ...
    'FontSize', '11', 'FontWeight', 'bold');

save_system(mdl1);
fprintf('  Model 1 saved: %s.slx\n', mdl1);


% =========================================================================
%  MODEL 2 — PRODUCT NAV2 ARCHITECTURE (visual hierarchy only)
% =========================================================================
mdl2 = 'reclaim_product_control';
if bdIsLoaded(mdl2), close_system(mdl2, 0); end
if exist([mdl2 '.slx'], 'file'), delete([mdl2 '.slx']); end
new_system(mdl2);
open_system(mdl2);
set_param(mdl2, 'Location', [100 50 900 950]);

% ---- Add subsystem blocks (simple names) ----
add_block('simulink/Ports & Subsystems/Subsystem', [mdl2 '/BT']);
add_block('simulink/Ports & Subsystems/Subsystem', [mdl2 '/GP']);
add_block('simulink/Ports & Subsystems/Subsystem', [mdl2 '/RPP']);
add_block('simulink/Ports & Subsystems/Subsystem', [mdl2 '/TPI']);
add_block('simulink/Ports & Subsystems/Subsystem', [mdl2 '/MOT']);

% ---- Positions (stacked vertically) ----
set_param([mdl2 '/BT'],  'Position', [100  60 700 130]);
set_param([mdl2 '/GP'],  'Position', [100 200 700 270]);
set_param([mdl2 '/RPP'], 'Position', [100 340 700 410]);
set_param([mdl2 '/TPI'], 'Position', [100 480 700 550]);
set_param([mdl2 '/MOT'], 'Position', [100 620 700 690]);

% ---- Connect layers (simple names) ----
add_line(mdl2, 'BT/1',  'GP/1',  'autorouting', 'on');
add_line(mdl2, 'GP/1',  'RPP/1', 'autorouting', 'on');
add_line(mdl2, 'RPP/1', 'TPI/1', 'autorouting', 'on');
add_line(mdl2, 'TPI/1', 'MOT/1', 'autorouting', 'on');

% ---- Rename for display (AFTER connections) ----
set_param([mdl2 '/BT'],  'Name', 'Behaviour Tree');
set_param([mdl2 '/GP'],  'Name', 'Global Planner (Smac)');
set_param([mdl2 '/RPP'], 'Name', 'Local Controller (Regulated Pure Pursuit)');
set_param([mdl2 '/TPI'], 'Name', 'Teensy PI Controller (50 Hz)');
set_param([mdl2 '/MOT'], 'Name', 'Drive Motors + Encoders');

% ---- Signal label annotations ----
add_block('built-in/Note', [mdl2 '/n1']);
set_param([mdl2 '/n1'], 'Position', [710  87 870 107], 'Text', 'goal pose',        'FontSize', '10');
add_block('built-in/Note', [mdl2 '/n2']);
set_param([mdl2 '/n2'], 'Position', [710 227 870 247], 'Text', 'reference path',   'FontSize', '10');
add_block('built-in/Note', [mdl2 '/n3']);
set_param([mdl2 '/n3'], 'Position', [710 367 870 387], 'Text', 'cmd_vel (Twist)',  'FontSize', '10');
add_block('built-in/Note', [mdl2 '/n4']);
set_param([mdl2 '/n4'], 'Position', [710 507 870 527], 'Text', 'PWM 0-255',        'FontSize', '10');
add_block('built-in/Note', [mdl2 '/n5']);
set_param([mdl2 '/n5'], 'Position', [710 647 870 667], 'Text', 'encoder feedback', 'FontSize', '10');

% ---- Title ----
add_block('built-in/Note', [mdl2 '/Title']);
set_param([mdl2 '/Title'], 'Position', [100 15 700 45], ...
    'Text', 'RECLAIM PRODUCT — Full Autonomy Stack  |  ROS2 Nav2 + SLAM Toolbox + Livox Mid-360 LiDAR', ...
    'FontSize', '11', 'FontWeight', 'bold');

save_system(mdl2);
fprintf('  Model 2 saved: %s.slx\n\n', mdl2);

fprintf('Done. Run sim(''%s'') to simulate.\n', mdl1);
