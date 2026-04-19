%% RECLAIM — 2D Path Comparison: Old (L-shape) vs New (Curved Arc)
%  Simulates the differential-drive robot pursuing a waste target
%  using two control strategies:
%    1. OLD: TURN until centered → stop → APPROACH straight (L-shaped path)
%    2. NEW: PURSUE curved arc (turn + drive simultaneously)
%
%  Robot parameters from calibrated prototype:
%    wheel_radius  = 0.05232 m
%    wheel_sep     = 0.470 m
%    max_linear    = 0.20 m/s
%    max_angular   = 0.25 rad/s (speed-limited)
%
%  Author: Shady Siam
%  Date:   March 24, 2026

clear; clc; close all;

%% ===== Robot Parameters =====
wheel_radius = 0.05232;   % m (calibrated)
wheel_sep    = 0.470;     % m (calibrated)
max_v        = 0.20;      % m/s (pursue_max_linear)
min_v        = 0.03;      % m/s (pursue_min_linear)
dt           = 0.033;     % s (~30 Hz tick)

% Target position (in robot's initial frame)
target_x = 1.5;   % m ahead
target_y = 0.8;   % m to the left

%% ===== OLD CONTROL: TURN then APPROACH (L-shape) =====
% Phase 1: Turn in place until facing target
% Phase 2: Drive straight to target

x_old = 0; y_old = 0; theta_old = 0;
path_old_x = x_old; path_old_y = y_old;
v_old_log = []; w_old_log = []; t_old = 0;

% Phase 1: TURN — P controller on bearing error
Kp_turn = 0.003 * (640/2);  % scaled: 0.003 rad/s per pixel → rad/s per rad
bearing_to_target = atan2(target_y - y_old, target_x - x_old);

while abs(theta_old - bearing_to_target) > 0.05  % ~3 deg tolerance
    error = atan2(sin(bearing_to_target - theta_old), cos(bearing_to_target - theta_old));
    w = min(0.25, max(-0.25, Kp_turn * error));
    v = 0;  % stationary turn

    % Update pose (diff drive kinematics)
    theta_old = theta_old + w * dt;
    x_old = x_old + v * cos(theta_old) * dt;
    y_old = y_old + v * sin(theta_old) * dt;

    path_old_x(end+1) = x_old;
    path_old_y(end+1) = y_old;
    v_old_log(end+1) = v;
    w_old_log(end+1) = w;
    t_old = t_old + dt;
end

% Hard stop between TURN and APPROACH
v_old_log(end+1) = 0; w_old_log(end+1) = 0;
path_old_x(end+1) = x_old; path_old_y(end+1) = y_old;
t_old = t_old + dt;

% Phase 2: APPROACH — drive straight with P steering
Kp_approach = 0.001 * (640/2);
stop_dist = 0.40;  % m

dist_to_target = sqrt((target_x - x_old)^2 + (target_y - y_old)^2);
while dist_to_target > stop_dist
    bearing_to_target = atan2(target_y - y_old, target_x - x_old);
    error = atan2(sin(bearing_to_target - theta_old), cos(bearing_to_target - theta_old));

    w = min(0.10, max(-0.10, Kp_approach * error));

    % Distance-proportional speed (linear ramp)
    dist_ratio = (dist_to_target - stop_dist) / 1.1;
    dist_ratio = max(0, min(1, dist_ratio));
    v = min_v + (max_v - min_v) * dist_ratio;

    theta_old = theta_old + w * dt;
    x_old = x_old + v * cos(theta_old) * dt;
    y_old = y_old + v * sin(theta_old) * dt;

    path_old_x(end+1) = x_old;
    path_old_y(end+1) = y_old;
    v_old_log(end+1) = v;
    w_old_log(end+1) = w;
    t_old = t_old + dt;

    dist_to_target = sqrt((target_x - x_old)^2 + (target_y - y_old)^2);
end

% Hard stop
v_old_log(end+1) = 0; w_old_log(end+1) = 0;
path_old_x(end+1) = x_old; path_old_y(end+1) = y_old;

%% ===== NEW CONTROL: PURSUE (curved arc) =====
x_new = 0; y_new = 0; theta_new = 0;
path_new_x = x_new; path_new_y = y_new;
v_new_log = []; w_new_log = []; t_new = 0;

% Controller parameters (from waste_tracker_trt_v2.py)
Kp_pursue  = 0.0012 * (640/2);  % scaled to rad
min_cmd    = 0.04;    % rad/s motor deadband override
decel_start = 0.90;   % m — begin deceleration zone
decel_end   = 0.45;   % m — end deceleration zone
ramp_dur    = 1.0;    % s — S-curve startup ramp
ang_limit_fast = 0.06; % rad/s max angular at max speed
ang_limit_slow = 0.25; % rad/s max angular at min speed

% EMA filter state
filtered_w = 0;
alpha = 0.45;

dist_to_target = sqrt((target_x - x_new)^2 + (target_y - y_new)^2);
pursue_start = 0;

while dist_to_target > stop_dist
    bearing_to_target = atan2(target_y - y_new, target_x - x_new);
    error = atan2(sin(bearing_to_target - theta_new), cos(bearing_to_target - theta_new));

    % P controller
    raw_w = Kp_pursue * error;

    % Distance-based speed with cosine deceleration zone
    if dist_to_target < decel_start
        zone_ratio = (dist_to_target - decel_end) / (decel_start - decel_end);
        zone_ratio = max(0, min(1, zone_ratio));
        speed_ratio = 0.5 * (1 - cos(pi * zone_ratio));
        target_v = min_v + (max_v - min_v) * speed_ratio;
    else
        target_v = max_v;
    end

    % S-curve startup ramp
    elapsed = t_new - pursue_start;
    if elapsed < ramp_dur
        ramp = 0.5 * (1 - cos(pi * elapsed / ramp_dur));
        target_v = target_v * ramp;
        raw_w = raw_w * ramp;
    end

    % Speed-dependent angular limiting
    speed_frac = (target_v - min_v) / max(0.01, max_v - min_v);
    speed_frac = max(0, min(1, speed_frac));
    max_ang = ang_limit_slow + (ang_limit_fast - ang_limit_slow) * speed_frac;
    raw_w = max(-max_ang, min(max_ang, raw_w));

    % Motor deadband override
    if abs(raw_w) > 0 && abs(raw_w) < min_cmd && abs(error) > 0.05
        raw_w = sign(raw_w) * min_cmd;
    end

    % EMA filter
    filtered_w = alpha * raw_w + (1 - alpha) * filtered_w;

    v = target_v;
    w = filtered_w;

    theta_new = theta_new + w * dt;
    x_new = x_new + v * cos(theta_new) * dt;
    y_new = y_new + v * sin(theta_new) * dt;

    path_new_x(end+1) = x_new;
    path_new_y(end+1) = y_new;
    v_new_log(end+1) = v;
    w_new_log(end+1) = w;
    t_new = t_new + dt;

    dist_to_target = sqrt((target_x - x_new)^2 + (target_y - y_new)^2);
end

%% ===== PLOTTING =====

figure('Position', [100, 100, 1200, 900], 'Color', 'w');

% --- Plot 1: Top-down path comparison ---
subplot(2,2,[1,3]);
hold on; grid on; axis equal;

% Target
plot(target_x, target_y, 'rp', 'MarkerSize', 20, 'MarkerFaceColor', 'r');
text(target_x + 0.05, target_y + 0.05, 'TARGET', 'FontSize', 11, 'Color', 'r', 'FontWeight', 'bold');

% Stop radius circle
theta_circle = linspace(0, 2*pi, 100);
plot(target_x + stop_dist*cos(theta_circle), target_y + stop_dist*sin(theta_circle), ...
    'r--', 'LineWidth', 1);

% Old path (L-shape)
plot(path_old_x, path_old_y, 'b-', 'LineWidth', 2.5);
plot(path_old_x(1), path_old_y(1), 'bs', 'MarkerSize', 12, 'MarkerFaceColor', 'b');
plot(path_old_x(end), path_old_y(end), 'bo', 'MarkerSize', 10, 'MarkerFaceColor', 'b');

% New path (curved arc)
plot(path_new_x, path_new_y, 'Color', [0 0.7 0], 'LineWidth', 2.5);
plot(path_new_x(1), path_new_y(1), 's', 'Color', [0 0.7 0], 'MarkerSize', 12, 'MarkerFaceColor', [0 0.7 0]);
plot(path_new_x(end), path_new_y(end), 'o', 'Color', [0 0.7 0], 'MarkerSize', 10, 'MarkerFaceColor', [0 0.7 0]);

% Robot start
plot(0, 0, 'k^', 'MarkerSize', 15, 'MarkerFaceColor', [0.3 0.3 0.3]);
text(0.05, -0.05, 'START', 'FontSize', 11, 'FontWeight', 'bold');

% Decel zone
plot(target_x + decel_start*cos(theta_circle), target_y + decel_start*sin(theta_circle), ...
    'Color', [1 0.6 0], 'LineStyle', ':', 'LineWidth', 1);
text(target_x + decel_start*0.7, target_y - decel_start*0.7, 'decel zone', ...
    'Color', [1 0.6 0], 'FontSize', 9);

legend('Target', 'Stop radius (0.4m)', ...
       'Old: TURN then APPROACH', 'Old: start', 'Old: stop', ...
       'New: PURSUE (curved arc)', 'New: start', 'New: stop', ...
       'Robot start', 'Location', 'northwest');
xlabel('X (m)'); ylabel('Y (m)');
title('Path Comparison: L-shape vs Curved Arc', 'FontSize', 14);

% --- Plot 2: Linear velocity over time ---
subplot(2,2,2);
t_old_vec = (0:length(v_old_log)-1) * dt;
t_new_vec = (0:length(v_new_log)-1) * dt;

hold on; grid on;
plot(t_old_vec, v_old_log, 'b-', 'LineWidth', 2);
plot(t_new_vec, v_new_log, 'Color', [0 0.7 0], 'LineWidth', 2);
xlabel('Time (s)'); ylabel('Linear velocity (m/s)');
title('Linear Velocity Profile', 'FontSize', 13);
legend('Old (hard stop between phases)', 'New (smooth S-curve + cosine decel)', ...
       'Location', 'northeast');

% Annotate the hard stop
[~, stop_idx] = min(abs(v_old_log(1:end-1) - 0) + (1:length(v_old_log)-1)*0);
% Find where old v drops to 0 between turn and approach
zero_crossings = find(diff(v_old_log > 0.001));
if ~isempty(zero_crossings)
    xline(t_old_vec(zero_crossings(1)), 'b--', 'TURN→APPROACH', 'FontSize', 9);
end

% --- Plot 3: Angular velocity over time ---
subplot(2,2,4);
hold on; grid on;
plot(t_old_vec, w_old_log, 'b-', 'LineWidth', 2);
plot(t_new_vec, w_new_log, 'Color', [0 0.7 0], 'LineWidth', 2);
xlabel('Time (s)'); ylabel('Angular velocity (rad/s)');
title('Angular Velocity Profile', 'FontSize', 13);
legend('Old (aggressive turn then corrections)', 'New (smooth blended arc)', ...
       'Location', 'northeast');

% Add overall title
sgtitle('RECLAIM Prototype — Drive Control Comparison', 'FontSize', 16, 'FontWeight', 'bold');

% Save figure
saveas(gcf, fullfile(fileparts(mfilename('fullpath')), 'path_comparison.png'));
fprintf('Saved path_comparison.png\n');
