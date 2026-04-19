%% RECLAIM — Velocity Profile Visualization
%  Shows the full velocity command pipeline during a simulated PURSUE:
%    1. Distance-proportional speed with cosine deceleration zone
%    2. S-curve startup ramp
%    3. Speed-dependent angular limiting
%    4. Angular EMA + sinusoidal ramp limiter
%
%  Compares old (linear ramp + hard stops) vs new (cosine decel + S-curve)
%
%  Author: Shady Siam
%  Date:   March 24, 2026

clear; clc; close all;

%% ===== Parameters =====
% Robot
max_v     = 0.20;    % m/s
min_v     = 0.03;    % m/s
stop_dist = 0.40;    % m (cam_z stop distance)
dt        = 0.033;   % ~30 Hz

% New controller
decel_start   = 0.90;  % m — begin deceleration
ramp_duration = 1.5;   % s — S-curve startup
alpha_ema     = 0.45;  % angular EMA blend
deadband      = 0.015; % angular smooth taper zone
ramp_rate     = 0.6;   % sinusoidal ramp limiter

% Simulated approach: start at 2.0m, drive toward target
initial_dist = 2.0;  % m

%% ===== Simulate OLD velocity profile =====
dist = initial_dist;
v_old = []; d_old = [];
t = 0; t_old = [];

while dist > stop_dist
    % Old: linear distance-proportional speed, no startup ramp
    dist_ratio = (dist - stop_dist) / 1.1;
    dist_ratio = max(0, min(1, dist_ratio));
    v = min_v + (max_v - min_v) * dist_ratio;

    v_old(end+1) = v;
    d_old(end+1) = dist;
    t_old(end+1) = t;

    dist = dist - v * dt;
    t = t + dt;
end
% Hard stop
v_old(end+1) = 0; d_old(end+1) = dist; t_old(end+1) = t;

%% ===== Simulate NEW velocity profile =====
dist = initial_dist;
v_new = []; d_new = [];
t = 0; t_new = [];
start_time = 0;

while dist > stop_dist
    % Cosine deceleration zone
    if dist < decel_start
        zone_ratio = (dist - stop_dist) / (decel_start - stop_dist);
        zone_ratio = max(0, min(1, zone_ratio));
        speed_ratio = 0.5 * (1 - cos(pi * zone_ratio));
        v = min_v + (max_v - min_v) * speed_ratio;
    else
        v = max_v;
    end

    % S-curve startup ramp
    elapsed = t - start_time;
    if elapsed < ramp_duration
        ramp = 0.5 * (1 - cos(pi * elapsed / ramp_duration));
        v = v * ramp;
    end

    v_new(end+1) = v;
    d_new(end+1) = dist;
    t_new(end+1) = t;

    dist = dist - v * dt;
    t = t + dt;
end
% Smooth final approach to zero (already near min_v)
v_new(end+1) = 0; d_new(end+1) = dist; t_new(end+1) = t;

%% ===== Simulate angular pipeline =====
% Simulate a target that starts 100px off-center, robot corrects
N = 300;  % frames (~10s at 30fps)
pixel_offset = zeros(1, N);
pixel_offset(1) = 100;  % start 100px off center

% Simulate detection noise
rng(42);
noise = randn(1, N) * 5;  % 5px RMS noise at 30fps

% Controller states
Kp = 0.0012;
filtered_w = 0;
last_w = 0;

raw_w_log = zeros(1, N);
ema_w_log = zeros(1, N);
final_w_log = zeros(1, N);
offset_log = zeros(1, N);

for i = 1:N
    % Simulated pixel offset (decays as robot corrects + noise)
    if i > 1
        pixel_offset(i) = pixel_offset(i-1) * 0.97 + noise(i);
    end
    offset_log(i) = pixel_offset(i);

    % P controller
    raw_w = -Kp * pixel_offset(i);
    raw_w = max(-0.15, min(0.15, raw_w));
    raw_w_log(i) = raw_w;

    % EMA filter
    filtered_w = alpha_ema * raw_w + (1 - alpha_ema) * filtered_w;
    ema_w_log(i) = filtered_w;

    % Smooth taper near zero
    w_out = filtered_w;
    if abs(w_out) < deadband
        scale = (w_out / deadband)^2;
        w_out = w_out * scale;
    end

    % Sinusoidal ramp limiter
    max_delta = ramp_rate * dt;
    delta = w_out - last_w;
    if abs(delta) > max_delta
        t_ratio = max_delta / abs(delta);
        smooth_t = 0.5 * (1 - cos(pi * t_ratio));
        w_out = last_w + delta * smooth_t;
    end
    last_w = w_out;
    final_w_log(i) = w_out;
end

t_ang = (0:N-1) * dt;

%% ===== Simulate speed-dependent angular limiting =====
speeds = linspace(0, max_v, 100);
ang_limit_slow = 0.25;
ang_limit_fast = 0.06;
ang_limits = zeros(size(speeds));
for i = 1:length(speeds)
    speed_frac = (speeds(i) - min_v) / max(0.01, max_v - min_v);
    speed_frac = max(0, min(1, speed_frac));
    ang_limits(i) = ang_limit_slow + (ang_limit_fast - ang_limit_slow) * speed_frac;
end

%% ===== PLOTTING =====
figure('Position', [50, 50, 1400, 900], 'Color', 'w');

% --- Plot 1: Linear velocity vs time ---
subplot(2,3,1);
hold on; grid on;
plot(t_old, v_old, 'b-', 'LineWidth', 2);
plot(t_new, v_new, 'Color', [0 0.7 0], 'LineWidth', 2);
xlabel('Time (s)'); ylabel('v (m/s)');
title('Linear Velocity vs Time', 'FontSize', 12);
legend('Old (linear ramp)', 'New (S-curve + cosine decel)', 'Location', 'northeast');
ylim([-0.01 max_v*1.1]);

% --- Plot 2: Linear velocity vs distance ---
subplot(2,3,4);
hold on; grid on;
plot(d_old, v_old, 'b-', 'LineWidth', 2);
plot(d_new, v_new, 'Color', [0 0.7 0], 'LineWidth', 2);
% Mark decel zone
xline(decel_start, 'r--', 'Decel start', 'FontSize', 9, 'LabelOrientation', 'horizontal');
xline(stop_dist, 'r-', 'Stop', 'FontSize', 9, 'LabelOrientation', 'horizontal');
% Shade decel zone
patch([stop_dist decel_start decel_start stop_dist], ...
      [-0.01 -0.01 max_v*1.1 max_v*1.1], ...
      [1 0.9 0.9], 'FaceAlpha', 0.3, 'EdgeColor', 'none');
xlabel('Distance to target (m)'); ylabel('v (m/s)');
title('Linear Velocity vs Distance', 'FontSize', 12);
legend('Old', 'New', 'Location', 'northwest');
set(gca, 'XDir', 'reverse');  % distance decreases left-to-right
ylim([-0.01 max_v*1.1]);

% --- Plot 3: Angular smoothing pipeline ---
subplot(2,3,2);
hold on; grid on;
plot(t_ang, raw_w_log, 'Color', [0.8 0.2 0.2], 'LineWidth', 1);
plot(t_ang, ema_w_log, 'Color', [0.2 0.2 0.8], 'LineWidth', 1.5);
plot(t_ang, final_w_log, 'Color', [0 0.7 0], 'LineWidth', 2);
xlabel('Time (s)'); ylabel('\omega (rad/s)');
title('Angular Smoothing Pipeline', 'FontSize', 12);
legend('Raw P output', 'After EMA (\alpha=0.45)', ...
       'Final (taper + ramp)', 'Location', 'northeast');

% --- Plot 4: Pixel offset convergence ---
subplot(2,3,5);
hold on; grid on;
plot(t_ang, offset_log, 'Color', [0.6 0.6 0.6], 'LineWidth', 1);
yline(0, 'k--');
yline(15, 'r--', 'Deadband', 'FontSize', 9);
yline(-15, 'r--');
xlabel('Time (s)'); ylabel('Pixel offset (px)');
title('Target Centering Convergence', 'FontSize', 12);

% --- Plot 5: Speed-dependent angular limit ---
subplot(2,3,3);
hold on; grid on;
plot(speeds, ang_limits, 'Color', [0.8 0 0.5], 'LineWidth', 2.5);
fill([speeds fliplr(speeds)], [ang_limits zeros(size(ang_limits))], ...
     [0.8 0 0.5], 'FaceAlpha', 0.15, 'EdgeColor', 'none');
xlabel('Forward speed (m/s)'); ylabel('Max |\omega| (rad/s)');
title('Speed-Dependent Angular Limit', 'FontSize', 12);
text(0.02, 0.23, sprintf('Slow: %.2f rad/s', ang_limit_slow), 'FontSize', 10);
text(0.14, 0.08, sprintf('Fast: %.2f rad/s', ang_limit_fast), 'FontSize', 10);

% --- Plot 6: Acceleration comparison ---
subplot(2,3,6);
hold on; grid on;
% Compute accelerations
accel_old = diff(v_old) / dt;
accel_new = diff(v_new) / dt;
plot(t_old(1:end-1), accel_old, 'b-', 'LineWidth', 1.5);
plot(t_new(1:end-1), accel_new, 'Color', [0 0.7 0], 'LineWidth', 1.5);
xlabel('Time (s)'); ylabel('Acceleration (m/s^2)');
title('Acceleration (Jerk Comparison)', 'FontSize', 12);
legend('Old (abrupt)', 'New (smooth)', 'Location', 'northeast');

sgtitle('RECLAIM Prototype — Velocity & Control Profiles', 'FontSize', 15, 'FontWeight', 'bold');

saveas(gcf, fullfile(fileparts(mfilename('fullpath')), 'velocity_profiles.png'));
fprintf('Saved velocity_profiles.png\n');
