%% RECLAIM — DC Motor Plant Model & Step Response
%  Models the JGB37-520 12V 37RPM geared DC motor with encoder feedback.
%  Derives transfer function, simulates step response, and compares
%  open-loop vs closed-loop (PI on Teensy) performance.
%
%  Motor: JGB37-520 (12V, 37 RPM no-load, ~7560 ticks/rev encoder)
%  Driver: BTS7960 (right) / MD10C (left)
%  Wheel: r = 0.05232 m, separation = 0.470 m
%
%  PI gains from firmware (arm_commander.cpp) via pole placement:
%    PLANT_K_L   = 0.001170 m/s per PWM
%    PLANT_TAU_L = 0.0503 s
%    zeta = 0.7, wn = 1.5/tau = 29.82 rad/s
%    Kp = (2*zeta*wn*tau - 1) / K = 940
%    Ki = (wn^2 * tau) / K = 38230
%    Kf = 1/K = 855 (feed-forward, not modelled here)
%
%  Author: Shady Siam
%  Date:   March 25, 2026

clear; clc; close all;

%% ===== Firmware-Identified Plant Model (1st order) =====
% From STEP_TEST data on actual robot — used for controller design
K_id   = 0.001170;   % DC gain: m/s per PWM unit
tau_id = 0.0503;     % time constant (s)

s = tf('s');

% Identified plant: PWM → wheel velocity (m/s)
G_id = K_id / (tau_id * s + 1);

%% ===== Physics-Derived Motor Model (2nd order, for Bode) =====
V_nom      = 12.0;
R_a        = 3.0;
L_a        = 0.005;
K_t        = 0.15;
K_e        = 0.15;
J_m        = 1.0e-5;
b_m        = 1.0e-4;
gear_ratio = 30;
J_load     = 0.005;
b_load     = 0.001;
wheel_radius = 0.05232;
ticks_per_rev = 7560;
wheel_sep    = 0.470;

J_total = J_m + J_load / gear_ratio^2;
b_total = b_m + b_load / gear_ratio^2;

num_m   = K_t;
den_a2  = L_a * J_total;
den_a1  = L_a * b_total + R_a * J_total;
den_a0  = R_a * b_total + K_t * K_e;

G_motor     = tf(num_m, [den_a2, den_a1, den_a0]);
G_output    = G_motor / gear_ratio;
G_wheel     = G_output * wheel_radius;
pwm_to_volts = V_nom / 255.0;
G_pwm_to_vel = G_wheel * pwm_to_volts;

%% ===== Teensy PI Controller (actual firmware values) =====
% From arm_commander.cpp — pole placement design
Kp = 940;
Ki = 38230;

C_pi = Kp + Ki / s;

%% ===== Closed-Loop Systems =====
% Using identified plant — this is what was actually designed against
G_ol_id = C_pi * G_id;
G_cl_id = feedback(G_ol_id, 1);

% Using physics plant (for comparison/Bode)
G_ol_phys = C_pi * G_pwm_to_vel;
G_cl_phys = feedback(G_ol_phys, 1);

%% ===== Simulation =====
t_sim = 0:0.001:1.0;   % 1 second — fast controller, don't need 3s

% Step responses (identified plant)
[y_cl_020, t_cl]  = step(G_cl_id * 0.20, t_sim);
[y_cl_012, ~]     = step(G_cl_id * 0.12, t_sim);

% Open-loop: apply PWM that would give 0.20 m/s at steady state
PWM_for_020 = 0.20 / K_id;   % = 171 PWM units
[y_ol_020, t_ol]  = step(G_id * PWM_for_020, t_sim);

% Ramp-limited input (ramp limiter: 0.3 m/s^2)
max_accel  = 0.3;
v_target   = 0.20;
v_ramp     = min(v_target, max_accel * t_sim);
y_ramp     = lsim(G_cl_id, v_ramp, t_sim);

% Step metrics
info_020   = stepinfo(G_cl_id * 0.20);
info_012   = stepinfo(G_cl_id * 0.12);
bw_hz      = bandwidth(G_cl_id) / (2*pi);

fprintf('=== RECLAIM PI Controller Performance ===\n');
fprintf('Kp = %d   Ki = %d\n', Kp, Ki);
fprintf('Plant: K=%.4f m/s/PWM   tau=%.4f s\n', K_id, tau_id);
fprintf('\nStep to 0.20 m/s:\n');
fprintf('  Rise time:     %.0f ms\n', info_020.RiseTime*1000);
fprintf('  Settling time: %.0f ms\n', info_020.SettlingTime*1000);
fprintf('  Overshoot:     %.1f%%\n',  info_020.Overshoot);
fprintf('\nStep to 0.12 m/s:\n');
fprintf('  Rise time:     %.0f ms\n', info_012.RiseTime*1000);
fprintf('  Settling time: %.0f ms\n', info_012.SettlingTime*1000);
fprintf('Bandwidth: %.1f Hz\n', bw_hz);
fprintf('=========================================\n');

%% ===== FIGURE — 3 clean plots for presentation =====
figure('Position', [50 50 1300 450], 'Color', 'w');

% -----------------------------------------------------------------------
% PLOT 1 — Step Response: Open vs Closed Loop
% -----------------------------------------------------------------------
subplot(1,3,1);
hold on; grid on; box on;

plot(t_ol, y_ol_020, 'b--', 'LineWidth', 1.8);
plot(t_cl, y_cl_020, 'Color', [0 0.65 0], 'LineWidth', 2.2);
yline(0.20, 'r--', 'LineWidth', 1.2);

ylim([0 0.28]);
xlim([0 1.0]);
xlabel('Time (s)', 'FontSize', 11);
ylabel('Wheel velocity (m/s)', 'FontSize', 11);
title('Step Response: 0.20 m/s', 'FontSize', 12, 'FontWeight', 'bold');
legend('Open-loop (PWM only)', 'Closed-loop (PI)', '0.20 m/s target', ...
       'Location', 'southeast', 'FontSize', 9);

text(0.45, 0.04, ...
    sprintf('Rise:  %.0f ms\nSettle: %.0f ms\nOvershoot: %.1f%%', ...
    info_020.RiseTime*1000, info_020.SettlingTime*1000, info_020.Overshoot), ...
    'FontSize', 9, 'BackgroundColor', [1 1 1 0.8], 'EdgeColor', [0.7 0.7 0.7]);

% -----------------------------------------------------------------------
% PLOT 2 — Approach Speeds: 0.12 vs 0.20 m/s
% -----------------------------------------------------------------------
subplot(1,3,2);
hold on; grid on; box on;

plot(t_cl, y_cl_012, 'Color', [0.85 0.33 0.10], 'LineWidth', 2.2);
plot(t_cl, y_cl_020, 'Color', [0 0.65 0],       'LineWidth', 2.2);
yline(0.12, '--', 'Color', [0.85 0.33 0.10], 'LineWidth', 1);
yline(0.20, '--', 'Color', [0 0.65 0],       'LineWidth', 1);

ylim([0 0.28]);
xlim([0 1.0]);
xlabel('Time (s)', 'FontSize', 11);
ylabel('Wheel velocity (m/s)', 'FontSize', 11);
title('Approach Speed Comparison', 'FontSize', 12, 'FontWeight', 'bold');
legend('v = 0.12 m/s (align)', 'v = 0.20 m/s (approach)', ...
       'Location', 'southeast', 'FontSize', 9);

text(0.45, 0.04, ...
    sprintf('Rise 0.12:  %.0f ms\nRise 0.20:  %.0f ms', ...
    info_012.RiseTime*1000, info_020.RiseTime*1000), ...
    'FontSize', 9, 'BackgroundColor', [1 1 1 0.8], 'EdgeColor', [0.7 0.7 0.7]);

% -----------------------------------------------------------------------
% PLOT 3 — Ramp-Limited vs Instant Step
% -----------------------------------------------------------------------
subplot(1,3,3);
hold on; grid on; box on;

plot(t_sim, v_ramp,   'r-',  'LineWidth', 1.8);
plot(t_sim, y_ramp,   'Color', [0 0.65 0], 'LineWidth', 2.2);
plot(t_cl,  y_cl_020, 'b--', 'LineWidth', 1.5);
yline(0.20, 'k:', 'LineWidth', 1);

ylim([0 0.28]);
xlim([0 1.0]);
xlabel('Time (s)', 'FontSize', 11);
ylabel('Wheel velocity (m/s)', 'FontSize', 11);
title('Ramp Limiter Effect (0.3 m/s²)', 'FontSize', 12, 'FontWeight', 'bold');
legend('Ramp reference', 'Actual (ramp + PI)', 'Instant step (no ramp)', ...
       'Location', 'southeast', 'FontSize', 9);

sgtitle('RECLAIM — PI Velocity Controller  |  JGB37-520  |  Kp=940  Ki=38230', ...
    'FontSize', 13, 'FontWeight', 'bold');

saveas(gcf, fullfile(fileparts(mfilename('fullpath')), 'dc_motor_model.png'));
fprintf('\nSaved dc_motor_model.png\n');

%% ===== SEPARATE FIGURE — Frequency Response (Bode, standalone) =====
figure('Position', [100 100 600 400], 'Color', 'w');
opts = bodeoptions;
opts.FreqUnits   = 'Hz';
opts.PhaseVisible = 'off';
opts.Grid         = 'on';
opts.Title.String   = sprintf('Closed-Loop Frequency Response  |  BW = %.1f Hz', bw_hz);
opts.Title.FontSize  = 12;
opts.XLabel.FontSize = 11;
opts.YLabel.FontSize = 11;
bode(G_cl_id, opts);
yline(-3, 'r--');   % -3dB line
saveas(gcf, fullfile(fileparts(mfilename('fullpath')), 'bode_plot.png'));
fprintf('Saved bode_plot.png\n');
