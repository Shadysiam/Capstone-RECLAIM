%% RECLAIM — Full Run Simulation (SCAN → PURSUE → FINAL_APPROACH)
%  Simulates a complete waste collection cycle in 2D with the new
%  state machine: SCAN → PURSUE → FINAL_APPROACH → IDLE
%
%  Animates the robot path in real-time with state annotations.
%  Can be played at showcase as a live demo.
%
%  Author: Shady Siam
%  Date:   March 24, 2026

clear; clc; close all;

%% ===== Parameters =====
% Robot
wheel_sep  = 0.470;   % m
max_v      = 0.20;    % m/s
min_v      = 0.03;    % m/s
scan_vel   = 0.30;    % rad/s
dt         = 0.033;   % 30 Hz

% Controller
Kp_pursue   = 0.0012 * 320;  % scaled from pixel to rad
min_cmd     = 0.04;
alpha_ema   = 0.45;
decel_start = 0.90;   % m
stop_dist   = 0.45;   % m (FINAL_APPROACH entry)
final_stop  = 0.25;   % m (IDLE — within arm reach)
ramp_dur    = 1.5;    % s

% Speed-dependent angular limits
ang_limit_slow = 0.25;
ang_limit_fast = 0.06;

% Camera FOV (approximate)
hfov = deg2rad(69);   % OAK-D Lite horizontal FOV

%% ===== Environment Setup =====
% Place 3 waste items
targets = [
    2.0,  0.5;    % Target 1: ahead-right
    1.2, -0.8;    % Target 2: ahead-left
    3.0,  0.0;    % Target 3: far ahead
];
target_names = {'Plastic bottle', 'Aluminum can', 'Cup'};
target_colors = {[0 0.5 1], [0.8 0.4 0], [0.6 0.2 0.8]};

%% ===== State Machine Simulation =====
x = 0; y = 0; theta = 0;
state = 'SCAN';
current_target_idx = 0;
scan_accumulated = 0;
scan_start_theta = theta;
pursue_start_time = 0;
filtered_w = 0;
items_collected = 0;

% Logging
path_x = [x]; path_y = [y]; path_theta = [theta];
state_log = {state};
time_log = [0];
v_log = [0]; w_log = [0];
state_times = struct('SCAN', 0, 'PURSUE', 0, 'FINAL_APPROACH', 0);

t_total = 0;
max_time = 120;  % safety timeout

while t_total < max_time && items_collected < size(targets, 1)
    switch state
        case 'SCAN'
            % Rotate to find targets
            w = scan_vel;
            v = 0;

            % Check if any target is in FOV
            for ti = 1:size(targets, 1)
                if targets(ti, 1) == -999  % already collected
                    continue;
                end
                % Bearing to target
                dx = targets(ti, 1) - x;
                dy = targets(ti, 2) - y;
                bearing = atan2(dy, dx);
                angle_diff = atan2(sin(bearing - theta), cos(bearing - theta));

                if abs(angle_diff) < hfov/2
                    dist = sqrt(dx^2 + dy^2);
                    if dist < 3.0  % within detection range
                        % Target detected! Transition to PURSUE
                        current_target_idx = ti;
                        state = 'PURSUE';
                        pursue_start_time = t_total;
                        filtered_w = 0;
                        % Smooth scan deceleration (cosine over 0.5s)
                        decel_frames = round(0.5 / dt);
                        for df = 1:decel_frames
                            frac = df / decel_frames;
                            w_decel = scan_vel * 0.5 * (1 + cos(pi * frac));
                            theta = theta + w_decel * dt;
                            t_total = t_total + dt;
                            path_x(end+1) = x; path_y(end+1) = y;
                            path_theta(end+1) = theta;
                            state_log{end+1} = 'SCAN_DECEL';
                            time_log(end+1) = t_total;
                            v_log(end+1) = 0; w_log(end+1) = w_decel;
                        end
                        break;
                    end
                end
            end

            % Update scan accumulation
            scan_accumulated = scan_accumulated + abs(w * dt);
            if scan_accumulated > 2*pi && strcmp(state, 'SCAN')
                % Full rotation, no target found — rescan
                scan_accumulated = 0;
            end

            state_times.SCAN = state_times.SCAN + dt;

        case 'PURSUE'
            tx = targets(current_target_idx, 1);
            ty = targets(current_target_idx, 2);
            dx = tx - x; dy = ty - y;
            dist = sqrt(dx^2 + dy^2);
            bearing = atan2(dy, dx);
            angle_error = atan2(sin(bearing - theta), cos(bearing - theta));

            % P controller
            raw_w = Kp_pursue * angle_error;

            % Speed-dependent angular limiting
            if dist < decel_start
                zone_ratio = (dist - stop_dist) / (decel_start - stop_dist);
                zone_ratio = max(0, min(1, zone_ratio));
                speed_ratio = 0.5 * (1 - cos(pi * zone_ratio));
                target_v = min_v + (max_v - min_v) * speed_ratio;
            else
                target_v = max_v;
            end

            % S-curve startup ramp
            elapsed = t_total - pursue_start_time;
            if elapsed < ramp_dur
                ramp = 0.5 * (1 - cos(pi * elapsed / ramp_dur));
                target_v = target_v * ramp;
                raw_w = raw_w * ramp;
            end

            % Speed-dependent angular limit
            speed_frac = max(0, min(1, (target_v - min_v) / max(0.01, max_v - min_v)));
            max_ang = ang_limit_slow + (ang_limit_fast - ang_limit_slow) * speed_frac;
            raw_w = max(-max_ang, min(max_ang, raw_w));

            % Motor deadband override
            if abs(raw_w) > 0 && abs(raw_w) < min_cmd && abs(angle_error) > 0.03
                raw_w = sign(raw_w) * min_cmd;
            end

            % EMA
            filtered_w = alpha_ema * raw_w + (1-alpha_ema) * filtered_w;

            v = target_v;
            w = filtered_w;

            % Transition to FINAL_APPROACH
            if dist < stop_dist
                state = 'FINAL_APPROACH';
                filtered_w = 0;
            end

            state_times.PURSUE = state_times.PURSUE + dt;

        case 'FINAL_APPROACH'
            tx = targets(current_target_idx, 1);
            ty = targets(current_target_idx, 2);
            dx = tx - x; dy = ty - y;
            dist = sqrt(dx^2 + dy^2);
            bearing = atan2(dy, dx);
            angle_error = atan2(sin(bearing - theta), cos(bearing - theta));

            % Very slow approach with precise steering
            v = min_v;
            w = 0.5 * Kp_pursue * angle_error;
            w = max(-0.10, min(0.10, w));

            % Smooth final stop
            if dist < final_stop
                v = 0; w = 0;
                items_collected = items_collected + 1;
                targets(current_target_idx, :) = [-999, -999];
                state = 'SCAN';
                scan_accumulated = 0;
                current_target_idx = 0;
            end

            state_times.FINAL_APPROACH = state_times.FINAL_APPROACH + dt;
    end

    % Update pose
    theta = theta + w * dt;
    x = x + v * cos(theta) * dt;
    y = y + v * sin(theta) * dt;

    % Log
    path_x(end+1) = x; path_y(end+1) = y;
    path_theta(end+1) = theta;
    state_log{end+1} = state;
    time_log(end+1) = t_total;
    v_log(end+1) = v; w_log(end+1) = w;

    t_total = t_total + dt;
end

%% ===== PLOTTING =====
figure('Position', [50, 50, 1400, 900], 'Color', 'w');

% State color map
state_colors = containers.Map();
state_colors('SCAN') = [0.2 0.6 1.0];
state_colors('SCAN_DECEL') = [0.4 0.7 1.0];
state_colors('PURSUE') = [0 0.7 0];
state_colors('FINAL_APPROACH') = [1.0 0.5 0];

% --- Plot 1: Full 2D path with state coloring ---
subplot(2,2,[1,3]);
hold on; grid on; axis equal;

% Draw path colored by state
for i = 2:length(path_x)
    if isKey(state_colors, state_log{i})
        c = state_colors(state_log{i});
    else
        c = [0.5 0.5 0.5];
    end
    plot([path_x(i-1) path_x(i)], [path_y(i-1) path_y(i)], ...
         '-', 'Color', c, 'LineWidth', 2.5);
end

% Draw targets
for ti = 1:size(targets, 1)
    if targets(ti, 1) == -999
        % Collected — draw faded
        plot(targets(ti,1), targets(ti,2)); % skip
    end
end
% Draw original target positions
orig_targets = [2.0, 0.5; 1.2, -0.8; 3.0, 0.0];
for ti = 1:size(orig_targets, 1)
    plot(orig_targets(ti,1), orig_targets(ti,2), 'p', ...
         'MarkerSize', 18, 'MarkerFaceColor', target_colors{ti}, ...
         'MarkerEdgeColor', 'k', 'LineWidth', 1.5);
    text(orig_targets(ti,1)+0.08, orig_targets(ti,2)+0.08, ...
         target_names{ti}, 'FontSize', 9, 'FontWeight', 'bold');
end

% Start marker
plot(0, 0, 'k^', 'MarkerSize', 15, 'MarkerFaceColor', [0.3 0.3 0.3]);
text(0.05, -0.08, 'START', 'FontSize', 10, 'FontWeight', 'bold');

% Stop distance circles
for ti = 1:size(orig_targets, 1)
    th = linspace(0, 2*pi, 60);
    plot(orig_targets(ti,1) + stop_dist*cos(th), ...
         orig_targets(ti,2) + stop_dist*sin(th), ...
         '--', 'Color', [target_colors{ti} 0.4], 'LineWidth', 1);
end

% Legend entries for states
h1 = plot(NaN, NaN, '-', 'Color', state_colors('SCAN'), 'LineWidth', 3);
h2 = plot(NaN, NaN, '-', 'Color', state_colors('PURSUE'), 'LineWidth', 3);
h3 = plot(NaN, NaN, '-', 'Color', state_colors('FINAL_APPROACH'), 'LineWidth', 3);
legend([h1 h2 h3], {'SCAN', 'PURSUE (curved arc)', 'FINAL\_APPROACH'}, ...
       'Location', 'northwest', 'FontSize', 10);

xlabel('X (m)'); ylabel('Y (m)');
title(sprintf('Full Collection Run (%d items, %.1fs)', items_collected, t_total), ...
      'FontSize', 13);

% --- Plot 2: Velocity over time ---
subplot(2,2,2);
hold on; grid on;
yyaxis left;
plot(time_log, v_log, '-', 'Color', [0 0.7 0], 'LineWidth', 1.5);
ylabel('Linear v (m/s)');
yyaxis right;
plot(time_log, w_log, '-', 'Color', [0.8 0 0.5], 'LineWidth', 1);
ylabel('Angular \omega (rad/s)');
xlabel('Time (s)');
title('Velocity Commands Over Time', 'FontSize', 12);

% Shade state regions
ax = gca;
yl = ax.YLim;
unique_states = {'SCAN', 'PURSUE', 'FINAL_APPROACH'};
for si = 1:length(unique_states)
    st = unique_states{si};
    if isKey(state_colors, st)
        mask = strcmp(state_log, st);
        idx = find(mask);
        if ~isempty(idx)
            % Find contiguous regions
            breaks = [0 find(diff(idx) > 1) length(idx)];
            for bi = 1:length(breaks)-1
                region = idx(breaks(bi)+1:breaks(bi+1));
                if length(region) > 1
                    patch([time_log(region(1)) time_log(region(end)) ...
                           time_log(region(end)) time_log(region(1))], ...
                          [yl(1) yl(1) yl(2) yl(2)], ...
                          state_colors(st), 'FaceAlpha', 0.08, 'EdgeColor', 'none');
                end
            end
        end
    end
end

% --- Plot 3: State timeline ---
subplot(2,2,4);
hold on; grid on;
state_nums = zeros(size(state_log));
state_map = containers.Map({'SCAN','SCAN_DECEL','PURSUE','FINAL_APPROACH'}, ...
                           {1, 1.5, 2, 3});
for i = 1:length(state_log)
    if isKey(state_map, state_log{i})
        state_nums(i) = state_map(state_log{i});
    end
end

% Plot as colored bar
for i = 2:length(time_log)
    if isKey(state_colors, state_log{i})
        c = state_colors(state_log{i});
    else
        c = [0.5 0.5 0.5];
    end
    patch([time_log(i-1) time_log(i) time_log(i) time_log(i-1)], ...
          [0 0 1 1], c, 'EdgeColor', 'none');
end
xlabel('Time (s)');
set(gca, 'YTick', []);
title('State Timeline', 'FontSize', 12);
ylim([0 1]);

% Add state durations as text
total_time = t_total;
text(0.5, 0.5, sprintf('SCAN: %.1fs', state_times.SCAN), ...
     'Color', 'w', 'FontSize', 11, 'FontWeight', 'bold');

sgtitle('RECLAIM — Full Autonomous Collection Cycle Simulation', ...
        'FontSize', 15, 'FontWeight', 'bold');

saveas(gcf, fullfile(fileparts(mfilename('fullpath')), 'full_run_sim.png'));
fprintf('Saved full_run_sim.png\n');

%% ===== Print Summary =====
fprintf('\n========================================\n');
fprintf('  FULL RUN SIMULATION SUMMARY\n');
fprintf('========================================\n');
fprintf('Items collected: %d / %d\n', items_collected, size(orig_targets, 1));
fprintf('Total time: %.1f s\n', t_total);
fprintf('State times:\n');
fprintf('  SCAN:            %.1f s\n', state_times.SCAN);
fprintf('  PURSUE:          %.1f s\n', state_times.PURSUE);
fprintf('  FINAL_APPROACH:  %.1f s\n', state_times.FINAL_APPROACH);
fprintf('Path length: %.2f m\n', sum(sqrt(diff(path_x).^2 + diff(path_y).^2)));
fprintf('========================================\n');
