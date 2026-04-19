%% RECLAIM — Smoothing Pipeline Visualization
%  Visualizes the 4-stage angular smoothing pipeline:
%    Stage 1: Raw bbox center from TRT (30fps, noisy)
%    Stage 2: Bbox EMA smoothing (alpha=0.5)
%    Stage 3: P controller output
%    Stage 4: Angular EMA (alpha=0.45) + deadband taper + sinusoidal ramp
%
%  Also shows feed-forward prediction benefit and detection hold behavior.
%
%  Author: Shady Siam
%  Date:   March 24, 2026

clear; clc; close all;

%% ===== Parameters =====
dt = 0.033;             % 30 fps
N  = 450;               % 15 seconds of data
image_width = 640;
img_cx = image_width / 2;

% Controller
Kp = 0.0012;            % P gain (prototype V2)
alpha_bbox = 0.5;       % bbox EMA
alpha_ang  = 0.45;      % angular EMA
deadband   = 0.015;     % smooth taper zone
ramp_rate  = 0.6;       % sinusoidal ramp limiter
min_cmd    = 0.04;      % motor deadband override

% Detection hold
det_hold_max = 4;       % frames to hold last detection

%% ===== Simulate Realistic Detection Data =====
% Scenario: target starts at 150px right of center, robot approaches
% Target drifts slightly, has noise, and has flicker gaps

rng(42);
t = (0:N-1) * dt;

% True target position (smooth drift toward center as robot corrects)
true_cx = img_cx + 150 * exp(-t / 4.0) + 20 * sin(0.5 * t);

% Noisy measurements (TRT bbox noise)
noise_std = 8;  % pixels — typical bbox center noise at 30fps
measured_cx = true_cx + noise_std * randn(1, N);

% Simulate detection flicker — randomly drop detections
flicker_mask = ones(1, N);
% Create random gaps of 1-5 frames
i = 1;
while i <= N
    if rand < 0.08  % 8% chance of gap start
        gap_len = randi([1, 5]);
        gap_end = min(N, i + gap_len - 1);
        flicker_mask(i:gap_end) = 0;
        i = gap_end + 1;
    else
        i = i + 1;
    end
end

%% ===== Stage 1: Raw input (with flicker) =====
raw_cx = measured_cx .* flicker_mask;
raw_cx(flicker_mask == 0) = NaN;  % NaN = no detection

%% ===== Stage 2: Bbox EMA + Detection Hold =====
bbox_smooth = zeros(1, N);
bbox_smooth(1) = measured_cx(1);
hold_counter = 0;
held_value = measured_cx(1);

for i = 2:N
    if flicker_mask(i) == 1
        % Got a detection — apply EMA
        bbox_smooth(i) = alpha_bbox * measured_cx(i) + (1-alpha_bbox) * bbox_smooth(i-1);
        held_value = bbox_smooth(i);
        hold_counter = 0;
    else
        % No detection — use hold
        hold_counter = hold_counter + 1;
        if hold_counter <= det_hold_max
            bbox_smooth(i) = held_value;  % hold last good value
        else
            bbox_smooth(i) = NaN;  % expired — truly lost
        end
    end
end

%% ===== Stage 3: P controller output =====
p_output = zeros(1, N);
for i = 1:N
    if ~isnan(bbox_smooth(i))
        offset = bbox_smooth(i) - img_cx;
        p_output(i) = -Kp * offset;
        p_output(i) = max(-0.15, min(0.15, p_output(i)));
    else
        p_output(i) = 0;
    end
end

%% ===== Stage 4: Angular EMA + deadband taper + sinusoidal ramp =====
final_w = zeros(1, N);
filtered_w = 0;
last_w = 0;

for i = 1:N
    raw_w = p_output(i);

    % EMA
    filtered_w = alpha_ang * raw_w + (1-alpha_ang) * filtered_w;

    % Smooth taper near zero (quadratic)
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
    final_w(i) = w_out;
end

%% ===== Feed-forward comparison =====
% Without feed-forward: just the pipeline above (already computed)
% With feed-forward: predict next position from velocity estimate

ff_w = zeros(1, N);
ff_filtered = 0;
ff_last = 0;
bbox_vel = 0;  % estimated bbox velocity (px/frame)

for i = 2:N
    if ~isnan(bbox_smooth(i)) && ~isnan(bbox_smooth(i-1))
        % Estimate velocity
        raw_vel = (bbox_smooth(i) - bbox_smooth(i-1)) / dt;
        bbox_vel = 0.3 * raw_vel + 0.7 * bbox_vel;  % smooth velocity estimate

        % Predicted position = current + velocity * dt
        predicted_cx = bbox_smooth(i) + bbox_vel * dt;
        offset = predicted_cx - img_cx;
    elseif ~isnan(bbox_smooth(i))
        offset = bbox_smooth(i) - img_cx;
    else
        offset = 0;
    end

    raw_w = -Kp * offset;
    raw_w = max(-0.15, min(0.15, raw_w));

    ff_filtered = alpha_ang * raw_w + (1-alpha_ang) * ff_filtered;
    w_out = ff_filtered;
    if abs(w_out) < deadband
        scale = (w_out / deadband)^2;
        w_out = w_out * scale;
    end
    max_delta = ramp_rate * dt;
    delta = w_out - ff_last;
    if abs(delta) > max_delta
        t_ratio = max_delta / abs(delta);
        smooth_t = 0.5 * (1 - cos(pi * t_ratio));
        w_out = ff_last + delta * smooth_t;
    end
    ff_last = w_out;
    ff_w(i) = w_out;
end

%% ===== PLOTTING =====
figure('Position', [50, 50, 1400, 1000], 'Color', 'w');

% Color scheme
c_raw   = [0.8 0.2 0.2];
c_bbox  = [0.2 0.2 0.8];
c_p     = [0.8 0.6 0];
c_final = [0 0.7 0];
c_ff    = [0.5 0 0.8];
c_true  = [0.4 0.4 0.4];

% --- Plot 1: Raw vs smoothed bbox center ---
subplot(3,2,1);
hold on; grid on;
plot(t, true_cx, '-', 'Color', c_true, 'LineWidth', 1);
scatter(t(flicker_mask==1), raw_cx(flicker_mask==1), 4, c_raw, 'filled');
plot(t, bbox_smooth, '-', 'Color', c_bbox, 'LineWidth', 1.5);
yline(img_cx, 'k--', 'Center');
xlabel('Time (s)'); ylabel('Bbox center X (px)');
title('Stage 1→2: Raw Detection → Bbox EMA', 'FontSize', 11);
legend('True position', 'Raw (with flicker)', 'EMA smoothed + hold', ...
       'Location', 'northeast');

% --- Plot 2: Detection hold behavior (zoom) ---
subplot(3,2,2);
% Find a flicker gap to zoom into
gap_starts = find(diff(flicker_mask) == -1);
if ~isempty(gap_starts)
    zoom_center = gap_starts(min(3, length(gap_starts)));
    zoom_range = max(1, zoom_center-30):min(N, zoom_center+50);
    hold on; grid on;

    % Background: shade gap frames
    for j = zoom_range
        if flicker_mask(j) == 0
            patch([t(j)-dt/2 t(j)+dt/2 t(j)+dt/2 t(j)-dt/2], ...
                  [min(bbox_smooth(zoom_range))-10 min(bbox_smooth(zoom_range))-10 ...
                   max(bbox_smooth(zoom_range))+10 max(bbox_smooth(zoom_range))+10], ...
                  [1 0.9 0.9], 'EdgeColor', 'none', 'FaceAlpha', 0.5);
        end
    end

    scatter(t(zoom_range), raw_cx(zoom_range), 20, c_raw, 'filled');
    plot(t(zoom_range), bbox_smooth(zoom_range), '-o', 'Color', c_bbox, ...
         'LineWidth', 1.5, 'MarkerSize', 3);
    xlabel('Time (s)'); ylabel('Bbox center X (px)');
    title('Detection Hold Behavior (Zoomed)', 'FontSize', 11);
    text(t(zoom_center), max(bbox_smooth(zoom_range))+5, ...
         sprintf('Hold %d frames', det_hold_max), 'FontSize', 9, ...
         'Color', [0.8 0 0], 'FontWeight', 'bold');
    legend('Raw (NaN = gap)', 'Held + smoothed', 'Location', 'best');
end

% --- Plot 3: P controller output ---
subplot(3,2,3);
hold on; grid on;
plot(t, p_output, '-', 'Color', c_p, 'LineWidth', 1.5);
yline(0, 'k--');
yline(deadband, 'r:', 'Deadband');
yline(-deadband, 'r:');
xlabel('Time (s)'); ylabel('\omega_{raw} (rad/s)');
title('Stage 3: P Controller Output', 'FontSize', 11);

% --- Plot 4: Full pipeline comparison ---
subplot(3,2,4);
hold on; grid on;
plot(t, p_output, '-', 'Color', c_p, 'LineWidth', 1, 'DisplayName', 'P output');
plot(t, final_w, '-', 'Color', c_final, 'LineWidth', 2, 'DisplayName', 'Final (EMA+taper+ramp)');
yline(0, 'k--');
xlabel('Time (s)'); ylabel('\omega (rad/s)');
title('Stage 3→4: Before vs After Smoothing', 'FontSize', 11);
legend('Location', 'northeast');

% --- Plot 5: Feed-forward comparison ---
subplot(3,2,5);
hold on; grid on;
plot(t, final_w, '-', 'Color', c_final, 'LineWidth', 2);
plot(t, ff_w, '-', 'Color', c_ff, 'LineWidth', 2);
yline(0, 'k--');
xlabel('Time (s)'); ylabel('\omega (rad/s)');
title('With vs Without Feed-Forward Prediction', 'FontSize', 11);
legend('Without FF (reactive)', 'With FF (predictive)', 'Location', 'northeast');

% Compute and annotate phase lead
% Cross-correlation to estimate lead
[xc, lags] = xcorr(final_w, ff_w, 30);
[~, max_idx] = max(xc);
lead_frames = lags(max_idx);
lead_ms = lead_frames * dt * 1000;
text(t(end)*0.6, max(final_w)*0.8, sprintf('FF leads by ~%.0fms', abs(lead_ms)), ...
    'FontSize', 10, 'Color', c_ff, 'FontWeight', 'bold');

% --- Plot 6: Smoothing reduction metric ---
subplot(3,2,6);
hold on; grid on;

% Compute jerk (derivative of angular velocity)
jerk_p = abs(diff(p_output)) / dt;
jerk_final = abs(diff(final_w)) / dt;

% Smooth for plotting
window = 10;
jerk_p_smooth = movmean(jerk_p, window);
jerk_final_smooth = movmean(jerk_final, window);

plot(t(1:end-1), jerk_p_smooth, '-', 'Color', c_p, 'LineWidth', 1.5);
plot(t(1:end-1), jerk_final_smooth, '-', 'Color', c_final, 'LineWidth', 2);
xlabel('Time (s)'); ylabel('Angular jerk (rad/s^2)');
title('Jerk Reduction (Smoothness Metric)', 'FontSize', 11);

% Compute reduction percentage
jerk_reduction = (1 - rms(jerk_final) / rms(jerk_p)) * 100;
legend(sprintf('Raw P (RMS=%.3f)', rms(jerk_p)), ...
       sprintf('Smoothed (RMS=%.3f, %.0f%% reduction)', rms(jerk_final), jerk_reduction), ...
       'Location', 'northeast');

sgtitle('RECLAIM — Angular Smoothing Pipeline (4-Stage)', 'FontSize', 15, 'FontWeight', 'bold');

saveas(gcf, fullfile(fileparts(mfilename('fullpath')), 'smoothing_pipeline.png'));
fprintf('Saved smoothing_pipeline.png\n');

%% ===== Summary Stats =====
fprintf('\n========================================\n');
fprintf('  SMOOTHING PIPELINE SUMMARY\n');
fprintf('========================================\n');
fprintf('Detection rate: %.0f%% (%.0f/%.0f frames detected)\n', ...
    sum(flicker_mask)/N*100, sum(flicker_mask), N);
fprintf('Bbox EMA alpha: %.2f\n', alpha_bbox);
fprintf('Angular EMA alpha: %.2f\n', alpha_ang);
fprintf('Deadband: %.3f rad/s\n', deadband);
fprintf('Ramp rate: %.1f rad/s^2\n', ramp_rate);
fprintf('P gain: %.4f\n', Kp);
fprintf('Jerk reduction: %.0f%%\n', jerk_reduction);
fprintf('Feed-forward lead: ~%.0fms\n', abs(lead_ms));
fprintf('========================================\n');
