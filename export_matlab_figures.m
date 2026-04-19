%% RECLAIM — Export All MATLAB Figures to PNG
% Run this from the RECLAIM root directory in MATLAB 2024a
% Output goes to: docs/matlab_figures/

outDir = fullfile(fileparts(mfilename('fullpath')), 'docs', 'matlab_figures');
if ~exist(outDir, 'dir'), mkdir(outDir); end

fprintf('Output directory: %s\n\n', outDir);

%% ========================================================================
%  1. Step Response ID (docs/showcase/matlab/)
%  ========================================================================
fprintf('=== step_response_id ===\n');
run(fullfile('docs','showcase','matlab','step_response_id.m'));
saveas(figure(1), fullfile(outDir, 'step_response_plant_id.png'));
saveas(figure(2), fullfile(outDir, 'step_response_pole_zero.png'));
close all;

%% ========================================================================
%  2. PI Design
%  ========================================================================
fprintf('=== pi_design ===\n');
run(fullfile('docs','showcase','matlab','pi_design.m'));
saveas(figure(1), fullfile(outDir, 'pi_open_loop_bode.png'));
saveas(figure(2), fullfile(outDir, 'pi_root_locus.png'));
saveas(figure(3), fullfile(outDir, 'pi_step_response.png'));
saveas(figure(4), fullfile(outDir, 'pi_sensitivity.png'));
close all;

%% ========================================================================
%  3. Simulate Closed-Loop
%  ========================================================================
fprintf('=== simulate_closedloop ===\n');
run(fullfile('docs','showcase','matlab','simulate_closedloop.m'));
saveas(figure(1), fullfile(outDir, 'closedloop_velocity_tracking.png'));
saveas(figure(2), fullfile(outDir, 'closedloop_ramp_filter_zoom.png'));
saveas(figure(3), fullfile(outDir, 'closedloop_tracking_error.png'));
close all;

%% ========================================================================
%  4. Product Motor Comparison
%  ========================================================================
fprintf('=== product_motor_comparison ===\n');
run(fullfile('docs','showcase','matlab','product_motor_comparison.m'));
saveas(figure(1), fullfile(outDir, 'product_motor_step_response.png'));
saveas(figure(2), fullfile(outDir, 'product_motor_gain_comparison.png'));
saveas(figure(3), fullfile(outDir, 'product_motor_encoder_quantisation.png'));
close all;

%% ========================================================================
%  5. DC Motor Model (matlab_sims/)
%  ========================================================================
fprintf('=== reclaim_dc_motor_model ===\n');
run(fullfile('matlab_sims','reclaim_dc_motor_model.m'));
saveas(figure(1), fullfile(outDir, 'dc_motor_model.png'));
saveas(figure(2), fullfile(outDir, 'dc_motor_bode.png'));
close all;

%% ========================================================================
%  6. Path Comparison
%  ========================================================================
fprintf('=== reclaim_path_comparison ===\n');
run(fullfile('matlab_sims','reclaim_path_comparison.m'));
saveas(figure(1), fullfile(outDir, 'path_comparison.png'));
close all;

%% ========================================================================
%  7. Velocity Profiles
%  ========================================================================
fprintf('=== reclaim_velocity_profiles ===\n');
run(fullfile('matlab_sims','reclaim_velocity_profiles.m'));
saveas(figure(1), fullfile(outDir, 'velocity_profiles.png'));
close all;

%% ========================================================================
%  8. Smoothing Pipeline
%  ========================================================================
fprintf('=== reclaim_smoothing_pipeline ===\n');
run(fullfile('matlab_sims','reclaim_smoothing_pipeline.m'));
saveas(figure(1), fullfile(outDir, 'smoothing_pipeline.png'));
close all;

%% ========================================================================
%  9. Full Run Simulation
%  ========================================================================
fprintf('=== reclaim_full_run_sim ===\n');
run(fullfile('matlab_sims','reclaim_full_run_sim.m'));
saveas(figure(1), fullfile(outDir, 'full_run_sim.png'));
close all;

%% ========================================================================
fprintf('\n=== DONE === All figures saved to:\n  %s\n', outDir);
fprintf('Total: 18 figures\n');
dir(fullfile(outDir, '*.png'));
