"""Generated assumption cards (do not hand-edit). {node_id: {law, assumptions[...]}}."""
CARDS = {
    'fluid_dynamics.bernoulli': {
        'law': 'p + 0.5*rho*V**2 + rho*g*z = const along a streamline',
        'assumptions': [
            {'name': 'incompressible', 'regime_variable': 'mach', 'valid_when': '< 0.3', 'error_when_violated': '0.25*mach**2', 'generalizes_to': 'compressible_bernoulli', 'why': 'density varies with pressure at high speed, so constant-rho form under-predicts stagnation pressure'},
            {'name': 'inviscid', 'regime_variable': 'reynolds', 'valid_when': '> 1e4', 'error_when_violated': '5/reynolds**0.5', 'generalizes_to': 'mechanical_energy_equation_with_head_loss', 'why': 'viscous shear dissipates mechanical energy, so the sum is not conserved along the path'},
            {'name': 'steady', 'regime_variable': 'strouhal', 'valid_when': '< 0.1', 'error_when_violated': 'strouhal', 'generalizes_to': 'unsteady_bernoulli', 'why': 'local time-acceleration adds a d(phi)/dt term omitted by the steady form'},
        ],
    },
    'fluid_dynamics.incompressible_navier_stokes': {
        'law': 'rho*(dV/dt) = -grad p + mu*lap V ; div V = 0',
        'assumptions': [
            {'name': 'incompressible', 'regime_variable': 'mach', 'valid_when': '< 0.3', 'error_when_violated': '0.5*mach**2', 'generalizes_to': 'compressible_navier_stokes', 'why': 'div V != 0 once density responds to pressure, coupling continuity, momentum and energy'},
            {'name': 'newtonian', 'regime_variable': 'weissenberg', 'valid_when': '< 0.1', 'error_when_violated': 'weissenberg', 'generalizes_to': 'viscoelastic_flow', 'why': 'stress stops being linear in strain-rate for polymeric/complex fluids'},
        ],
    },
    'fluid_dynamics.potential_flow': {
        'law': 'V = grad(phi), lap(phi) = 0',
        'assumptions': [
            {'name': 'irrotational_inviscid', 'regime_variable': 'reynolds', 'valid_when': '> 1e5', 'error_when_violated': '10/reynolds**0.5', 'generalizes_to': 'viscous_rotational_flow', 'why': 'viscosity generates vorticity in the boundary layer and wake, breaking irrotationality'},
            {'name': 'incompressible', 'regime_variable': 'mach', 'valid_when': '< 0.3', 'error_when_violated': '0.5*mach**2', 'generalizes_to': 'full_potential_equation', 'why': 'compressibility makes the velocity potential obey a nonlinear, not Laplace, equation'},
        ],
    },
    'fluid_dynamics.stokes_flow': {
        'law': '0 = -grad p + mu*lap V (creeping flow, inertia neglected)',
        'assumptions': [
            {'name': 'negligible_inertia', 'regime_variable': 'reynolds', 'valid_when': '< 1.0', 'error_when_violated': 'reynolds', 'generalizes_to': 'full_navier_stokes', 'why': 'convective inertia rho*(V.grad)V becomes comparable to viscous term as Re rises'},
        ],
    },
    'fluid_dynamics.stokes_drag': {
        'law': 'F = 6*pi*mu*R*V for a sphere',
        'assumptions': [
            {'name': 'creeping_flow', 'regime_variable': 'reynolds', 'valid_when': '< 1.0', 'error_when_violated': '0.1875*reynolds', 'generalizes_to': 'oseen_drag_and_standard_drag_curve', 'why': 'inertial wake adds drag beyond the linear viscous prediction (Oseen correction ~1+3Re/16)'},
        ],
    },
    'fluid_dynamics.boundary_layer_equations': {
        'law': 'u*du/dx + v*du/dy = -1/rho dp/dx + nu*d2u/dy2 (Prandtl)',
        'assumptions': [
            {'name': 'thin_shear_layer', 'regime_variable': 'reynolds', 'valid_when': '> 1e3', 'error_when_violated': '1/reynolds**0.5', 'generalizes_to': 'full_navier_stokes', 'why': 'at low Re the layer is not thin, streamwise diffusion and normal pressure gradients matter'},
        ],
    },
    'fluid_dynamics.hagen_poiseuille': {
        'law': 'Q = pi*R**4*dP/(8*mu*L)',
        'assumptions': [
            {'name': 'laminar_flow', 'regime_variable': 'reynolds', 'valid_when': '< 2300', 'error_when_violated': '1-(2300/reynolds)**0.75', 'generalizes_to': 'turbulent_pipe_flow_colebrook', 'why': 'turbulent eddies steepen the wall gradient so pressure drop grows faster than linearly with Q'},
            {'name': 'fully_developed', 'regime_variable': 'entrance_length_ratio', 'valid_when': '< 0.05', 'error_when_violated': 'entrance_length_ratio', 'generalizes_to': 'developing_entrance_flow', 'why': 'near the inlet the velocity profile still evolves, raising the effective pressure drop'},
        ],
    },
    'fluid_dynamics.continuum_hypothesis': {
        'law': 'fluid treated as a continuum field (rho, V, p continuous)',
        'assumptions': [
            {'name': 'continuum', 'regime_variable': 'knudsen', 'valid_when': '< 0.01', 'error_when_violated': 'knudsen', 'generalizes_to': 'slip_flow_then_kinetic_theory_boltzmann', 'why': 'when mean free path nears the length scale, molecular discreteness and wall slip appear'},
        ],
    },
    'fluid_dynamics.no_slip_wall_bc': {
        'law': 'V = V_wall at a solid boundary',
        'assumptions': [
            {'name': 'no_slip', 'regime_variable': 'knudsen', 'valid_when': '< 0.001', 'error_when_violated': 'knudsen', 'generalizes_to': 'maxwell_slip_boundary_condition', 'why': 'rarefied gas retains finite tangential velocity at the wall proportional to Kn'},
        ],
    },
    'fluid_dynamics.darcy_friction_laminar': {
        'law': 'f = 64/reynolds (laminar Darcy friction factor)',
        'assumptions': [
            {'name': 'laminar', 'regime_variable': 'reynolds', 'valid_when': '< 2300', 'error_when_violated': 'reynolds/2300-1', 'generalizes_to': 'colebrook_white_turbulent_friction', 'why': 'beyond transition friction depends on roughness and weakly on Re, not the 64/Re law'},
        ],
    },
    'fluid_dynamics.incompressible_flow_assumption': {
        'law': 'rho = const (Mach-based density change neglected)',
        'assumptions': [
            {'name': 'low_mach', 'regime_variable': 'mach', 'valid_when': '< 0.3', 'error_when_violated': '0.5*mach**2', 'generalizes_to': 'compressible_gas_dynamics', 'why': 'fractional density change scales as ~0.5*M^2, becoming significant above M~0.3'},
        ],
    },
    'aerodynamics.thin_airfoil_theory': {
        'law': 'cl = 2*pi*alpha (lift-curve slope for a thin airfoil)',
        'assumptions': [
            {'name': 'small_angle_attached', 'regime_variable': 'angle_of_attack_ratio', 'valid_when': '< 0.3', 'error_when_violated': 'angle_of_attack_ratio', 'generalizes_to': 'nonlinear_lift_with_stall', 'why': 'at high incidence flow separates and lift falls below the linearized 2*pi*alpha line'},
        ],
    },
    'fluid_dynamics.hydrostatics': {
        'law': 'dp/dz = -rho*g (fluid at rest)',
        'assumptions': [
            {'name': 'static_no_acceleration', 'regime_variable': 'froude', 'valid_when': '< 0.1', 'error_when_violated': 'froude**2', 'generalizes_to': 'dynamic_pressure_field_euler', 'why': 'fluid acceleration adds inertial pressure gradients absent in the static balance'},
        ],
    },
    'fluid_dynamics.laminar_flat_plate_blasius': {
        'law': 'cf = 0.664/reynolds_x**0.5 (Blasius local skin friction)',
        'assumptions': [
            {'name': 'laminar_boundary_layer', 'regime_variable': 'reynolds_x', 'valid_when': '< 5e5', 'error_when_violated': '1-(5e5/reynolds_x)**0.3', 'generalizes_to': 'turbulent_flat_plate_power_law', 'why': 'past transition Re_x~5e5 turbulent mixing raises skin friction above the Blasius law'},
        ],
    },
    'rocket_propulsion.isentropic_flow': {
        'law': 'p/rho**gamma = const across a compressible process',
        'assumptions': [
            {'name': 'shock_free_reversible', 'regime_variable': 'mach', 'valid_when': '< 1.0', 'error_when_violated': '0.4*(mach-1)**2', 'generalizes_to': 'rankine_hugoniot_shock_relations', 'why': 'supersonic flow forms shocks that raise entropy, breaking the isentropic relation'},
        ],
    },
    'fluid_dynamics.linear_acoustics': {
        'law': 'd2p/dt2 = c**2 * lap p (small-amplitude wave equation)',
        'assumptions': [
            {'name': 'small_amplitude', 'regime_variable': 'acoustic_mach', 'valid_when': '< 0.01', 'error_when_violated': 'acoustic_mach', 'generalizes_to': 'nonlinear_acoustics_shock_steepening', 'why': 'finite-amplitude waves convect at speed-dependent rates, steepening into shocks'},
        ],
    },
    'aerodynamics.thin_airfoil_lift': {
        'law': 'cl = 2*pi*alpha (lift coefficient of a thin airfoil, alpha in radians)',
        'assumptions': [
            {'name': 'small_angle_of_attack', 'regime_variable': 'alpha_rad', 'valid_when': '< 0.26', 'error_when_violated': 'alpha_rad**2/6', 'generalizes_to': 'nonlinear_lift_with_stall', 'why': 'Linearized boundary condition sin(alpha)~alpha breaks down and flow separates at high incidence, capping lift far below 2*pi*alpha.'},
            {'name': 'thin_airfoil', 'regime_variable': 'thickness_ratio', 'valid_when': '< 0.12', 'error_when_violated': 'thickness_ratio', 'generalizes_to': 'full_potential_panel_method', 'why': 'The camber/thickness are collapsed onto the chord line; finite thickness alters the surface velocity and the effective lift slope.'},
        ],
    },
    'aerodynamics.incompressible_flow': {
        'law': 'density = const; pressure coefficient independent of Mach (Cp0)',
        'assumptions': [
            {'name': 'incompressible', 'regime_variable': 'mach', 'valid_when': '< 0.3', 'error_when_violated': '0.5*mach**2', 'generalizes_to': 'compressible_flow', 'why': 'Density variations scale with Mach^2; above M~0.3 they can no longer be neglected in the pressure-velocity relation.'},
        ],
    },
    'aerodynamics.prandtl_glauert_correction': {
        'law': 'cl = cl_incompressible / sqrt(1 - mach**2) (subsonic compressibility correction)',
        'assumptions': [
            {'name': 'subsonic_no_shocks', 'regime_variable': 'mach', 'valid_when': '< 0.7', 'error_when_violated': 'mach**2/(1-mach**2)', 'generalizes_to': 'transonic_small_disturbance_theory', 'why': 'The linearization singularity at M=1 and the onset of local shocks in the transonic regime destroy the simple 1/sqrt(1-M^2) scaling.'},
        ],
    },
    'aerodynamics.drag_polar_incompressible': {
        'law': 'cd = cd0 + cl**2/(pi*AR*e) (parabolic drag polar)',
        'assumptions': [
            {'name': 'attached_flow_low_cl', 'regime_variable': 'cl_over_clmax', 'valid_when': '< 0.8', 'error_when_violated': '(cl_over_clmax)**4', 'generalizes_to': 'separated_flow_drag_rise', 'why': 'Near stall the drag grows faster than cl^2 as flow separates, so the parabolic form badly underpredicts drag.'},
            {'name': 'elliptic_span_efficiency_constant', 'regime_variable': 'taper_deviation', 'valid_when': '< 0.3', 'error_when_violated': 'taper_deviation', 'generalizes_to': 'lifting_line_span_loading', 'why': 'Span efficiency e is treated as fixed, but non-elliptic loading changes induced drag and makes e depend on planform and cl.'},
        ],
    },
    'aerodynamics.lifting_line_theory': {
        'law': 'induced_drag = cl**2/(pi*AR*e); downwash from a bound vortex line',
        'assumptions': [
            {'name': 'high_aspect_ratio', 'regime_variable': 'aspect_ratio', 'valid_when': '>= 4', 'error_when_violated': '1/aspect_ratio', 'generalizes_to': 'lifting_surface_vortex_lattice', 'why': 'Collapsing the wing to a single spanwise line ignores chordwise vorticity; for low-AR wings the 3D chordwise flow dominates.'},
        ],
    },
    'aerodynamics.attached_boundary_layer': {
        'law': 'attached-flow aerodynamics: forces set by potential flow plus thin viscous correction',
        'assumptions': [
            {'name': 'no_separation', 'regime_variable': 'alpha_over_alpha_stall', 'valid_when': '< 1.0', 'error_when_violated': 'alpha_over_alpha_stall - 1', 'generalizes_to': 'separated_flow_aerodynamics', 'why': 'Adverse pressure gradient detaches the boundary layer past the stall angle, collapsing lift and voiding potential-flow predictions.'},
        ],
    },
    'aerodynamics.skin_friction_laminar': {
        'law': 'cf = 1.328/sqrt(reynolds) (Blasius laminar flat-plate skin friction)',
        'assumptions': [
            {'name': 'laminar_boundary_layer', 'regime_variable': 'reynolds', 'valid_when': '< 5e5', 'error_when_violated': 'reynolds**0.3/500', 'generalizes_to': 'turbulent_skin_friction', 'why': 'Above the transition Reynolds number the boundary layer becomes turbulent, raising cf by roughly an order of magnitude versus Blasius.'},
        ],
    },
    'aerodynamics.continuum_flow': {
        'law': 'Navier-Stokes with no-slip wall boundary condition (continuum aerodynamics)',
        'assumptions': [
            {'name': 'continuum_no_slip', 'regime_variable': 'knudsen', 'valid_when': '< 0.01', 'error_when_violated': 'knudsen', 'generalizes_to': 'rarefied_slip_flow', 'why': 'When the mean free path approaches body scale, the gas slips at the wall and continuum no-slip aerodynamics fails.'},
        ],
    },
    'aerodynamics.newtonian_impact_theory': {
        'law': 'cp = 2*sin(theta)**2 (Newtonian hypersonic surface pressure)',
        'assumptions': [
            {'name': 'hypersonic_thin_shock_layer', 'regime_variable': 'mach', 'valid_when': '>= 5', 'error_when_violated': '25/mach**2', 'generalizes_to': 'shock_layer_euler_solution', 'why': 'The impact model assumes the shock lies on the body; at lower Mach the shock stands off and the pressure is not set by simple momentum transfer.'},
        ],
    },
    'aerodynamics.ackeret_supersonic_lift': {
        'law': 'cl = 4*alpha/sqrt(mach**2 - 1) (linearized supersonic thin-airfoil lift)',
        'assumptions': [
            {'name': 'linear_supersonic_small_perturbation', 'regime_variable': 'mach', 'valid_when': '> 1.2', 'error_when_violated': '1/(mach**2 - 1)', 'generalizes_to': 'shock_expansion_theory', 'why': 'Near M=1 the sqrt(M^2-1) term blows up and at high Mach nonlinear shock/expansion effects dominate the linear result.'},
        ],
    },
    'aerodynamics.quasi_steady_aerodynamics': {
        'law': 'forces depend only on instantaneous alpha (quasi-steady assumption)',
        'assumptions': [
            {'name': 'quasi_steady', 'regime_variable': 'reduced_frequency', 'valid_when': '< 0.05', 'error_when_violated': 'reduced_frequency', 'generalizes_to': 'unsteady_theodorsen_aerodynamics', 'why': 'When the flow timescale is comparable to the motion period, wake vorticity and added-mass introduce phase lag the steady model omits.'},
        ],
    },
    'aerodynamics.constant_lift_slope': {
        'law': 'cl_alpha = 2*pi (per radian), independent of Reynolds and Mach',
        'assumptions': [
            {'name': 'inviscid_lift_slope', 'regime_variable': 'reynolds', 'valid_when': '> 1e6', 'error_when_violated': '1e6/reynolds', 'generalizes_to': 'viscous_reduced_lift_slope', 'why': 'At low Reynolds the thick/separating boundary layer decambers the airfoil, reducing the effective lift-curve slope below 2*pi.'},
        ],
    },
    'aerodynamics.incompressible_bernoulli': {
        'law': 'p + 0.5*rho*V**2 = const (incompressible Bernoulli for dynamic pressure)',
        'assumptions': [
            {'name': 'incompressible_bernoulli', 'regime_variable': 'mach', 'valid_when': '< 0.3', 'error_when_violated': '0.25*mach**2', 'generalizes_to': 'compressible_stagnation_relation', 'why': 'The dynamic-pressure form omits the (1+M^2/4+...) compressibility terms in the stagnation pressure, growing with Mach^2.'},
        ],
    },
    'aerodynamics.flat_plate_normal_force_linear': {
        'law': 'cn = 2*pi*alpha (linear normal-force slope for slender lifting surfaces)',
        'assumptions': [
            {'name': 'linear_potential_no_vortex_lift', 'regime_variable': 'alpha_rad', 'valid_when': '< 0.35', 'error_when_violated': 'alpha_rad', 'generalizes_to': 'polhamus_leading_edge_suction', 'why': 'On slender/delta wings, leading-edge vortices add a nonlinear (alpha^2) vortex-lift term absent from the linear slope.'},
        ],
    },
    'aerodynamics.slender_body_theory': {
        'law': 'lift from cross-flow momentum of a slender body, cn_alpha = 2 (per radian) on base area',
        'assumptions': [
            {'name': 'slender_body', 'regime_variable': 'diameter_to_length', 'valid_when': '< 0.1', 'error_when_violated': 'diameter_to_length', 'generalizes_to': 'full_body_of_revolution_panel', 'why': 'The theory assumes axial gradients are small; a stubby body has strong longitudinal flow and 3D effects the cross-flow model ignores.'},
        ],
    },
    'compressible_flow.isentropic_relations': {
        'law': 'p0/p = (1 + (gamma-1)/2 * M^2)^(gamma/(gamma-1)); T0/T = 1 + (gamma-1)/2 * M^2',
        'assumptions': [
            {'name': 'reversible_no_shock', 'regime_variable': 'mach', 'valid_when': '<= 1.0', 'error_when_violated': '(mach-1)**3', 'generalizes_to': 'flow_with_shocks_rankine_hugoniot', 'why': 'Supersonic decelerations form shocks that generate entropy, so stagnation pressure is no longer conserved and the isentropic p0 relation over-predicts recovery.'},
            {'name': 'adiabatic_no_heat_addition', 'regime_variable': 'heat_ratio', 'valid_when': '< 0.05', 'error_when_violated': 'heat_ratio', 'generalizes_to': 'rayleigh_flow', 'why': 'Heat addition/removal changes stagnation temperature, breaking the T0-constant basis of the isentropic temperature relation.'},
            {'name': 'calorically_perfect', 'regime_variable': 'temperature_ratio', 'valid_when': '< 0.1', 'error_when_violated': 'temperature_ratio', 'generalizes_to': 'thermally_perfect_variable_gamma_flow', 'why': 'At high T/theta_vib vibrational modes excite so gamma drops below 1.4, and the constant-exponent power law no longer holds.'},
        ],
    },
    'compressible_flow.bernoulli': {
        'law': 'p + 0.5*rho*V^2 = p0 = const along a streamline',
        'assumptions': [
            {'name': 'incompressible', 'regime_variable': 'mach', 'valid_when': '< 0.3', 'error_when_violated': 'mach**2/4', 'generalizes_to': 'compressible_bernoulli_isentropic', 'why': 'As Mach rises density varies with pressure, so the incompressible dynamic-pressure form underestimates the true stagnation pressure by roughly M^2/4.'},
        ],
    },
    'compressible_flow.incompressible_continuity': {
        'law': 'rho = const, so A*V = const (volumetric continuity)',
        'assumptions': [
            {'name': 'constant_density', 'regime_variable': 'mach', 'valid_when': '< 0.3', 'error_when_violated': '0.5*mach**2', 'generalizes_to': 'compressible_mass_continuity', 'why': 'Density changes scale as ~0.5*M^2; ignoring them mispredicts velocity through an area change and misses choking behavior near M=1.'},
        ],
    },
    'compressible_flow.ideal_gas_eos': {
        'law': 'p = rho*R*T (thermally perfect gas)',
        'assumptions': [
            {'name': 'ideal_gas', 'regime_variable': 'reduced_pressure', 'valid_when': '< 0.1', 'error_when_violated': 'reduced_pressure', 'generalizes_to': 'van_der_waals_real_gas', 'why': 'At high reduced pressure (or near the critical point) molecular volume and intermolecular attraction make the compressibility factor Z deviate from 1.'},
        ],
    },
    'compressible_flow.calorically_perfect_gas': {
        'law': 'h = cp*T with cp, gamma constant',
        'assumptions': [
            {'name': 'constant_specific_heats', 'regime_variable': 'temperature_ratio', 'valid_when': '< 0.1', 'error_when_violated': 'temperature_ratio', 'generalizes_to': 'thermally_perfect_gas_variable_cp', 'why': 'As T approaches the vibrational/dissociation temperature scale, internal energy modes activate and cp rises, so enthalpy is no longer linear in T.'},
        ],
    },
    'compressible_flow.quasi_one_dimensional': {
        'law': 'Uniform properties across each cross-section: (1/A)dA + (1/rho)drho + (1/V)dV = 0',
        'assumptions': [
            {'name': 'one_dimensional', 'regime_variable': 'area_gradient', 'valid_when': '< 0.1', 'error_when_violated': 'area_gradient**2', 'generalizes_to': 'multidimensional_flow', 'why': 'Rapid area change (large dA/dx or wall angle) makes streamlines curve and properties vary across the section, so section-averaged 1-D relations lose accuracy.'},
        ],
    },
    'compressible_flow.prandtl_glauert': {
        'law': 'Cp = Cp0 / sqrt(1 - M^2) (subsonic compressibility correction)',
        'assumptions': [
            {'name': 'small_perturbation_linearized', 'regime_variable': 'mach', 'valid_when': '< 0.7', 'error_when_violated': 'mach**4', 'generalizes_to': 'karman_tsien_full_potential', 'why': 'Linearization drops higher-order density terms; approaching the critical Mach number nonlinear transonic effects dominate and the sqrt(1-M^2) singularity is unphysical.'},
        ],
    },
    'compressible_flow.linearized_supersonic_ackeret': {
        'law': 'Cp = 2*theta / sqrt(M^2 - 1) for thin bodies in supersonic flow',
        'assumptions': [
            {'name': 'small_deflection', 'regime_variable': 'deflection_ratio', 'valid_when': '< 0.1', 'error_when_violated': 'deflection_ratio', 'generalizes_to': 'shock_expansion_theory', 'why': 'Linearized supersonic theory assumes tiny turning angles; at finite deflection the true oblique-shock/expansion pressures depart nonlinearly from the 2*theta form.'},
        ],
    },
    'compressible_flow.frictionless_duct_flow': {
        'law': 'Constant-area adiabatic duct flow with no wall friction preserves stagnation pressure',
        'assumptions': [
            {'name': 'frictionless', 'regime_variable': 'friction_parameter', 'valid_when': '< 0.05', 'error_when_violated': 'friction_parameter', 'generalizes_to': 'fanno_flow', 'why': 'Wall shear (4fL/D) generates entropy and drives the flow toward M=1, so neglecting friction mispredicts pressure drop and choking length in long ducts.'},
        ],
    },
    'compressible_flow.adiabatic_duct_flow': {
        'law': 'Constant-area frictionless duct flow with no heat exchange keeps stagnation temperature constant',
        'assumptions': [
            {'name': 'adiabatic', 'regime_variable': 'heat_ratio', 'valid_when': '< 0.05', 'error_when_violated': 'heat_ratio', 'generalizes_to': 'rayleigh_flow', 'why': 'Heat addition raises T0 and moves the flow along the Rayleigh line toward thermal choking, which the adiabatic assumption cannot capture.'},
        ],
    },
    'compressible_flow.weak_shock_isentropic': {
        'law': 'Weak compression treated as isentropic (Mach-wave / expansion-like) with negligible entropy jump',
        'assumptions': [
            {'name': 'weak_shock', 'regime_variable': 'normal_mach', 'valid_when': '< 1.2', 'error_when_violated': '(normal_mach-1)**3', 'generalizes_to': 'rankine_hugoniot_normal_shock', 'why': 'Entropy rise and stagnation-pressure loss across a shock scale as (M1n-1)^3, negligible for weak shocks but dominant as the normal Mach number grows.'},
        ],
    },
    'compressible_flow.continuum_navier_stokes': {
        'law': 'Continuum flow with no-slip walls governed by Navier-Stokes',
        'assumptions': [
            {'name': 'continuum', 'regime_variable': 'knudsen', 'valid_when': '< 0.01', 'error_when_violated': 'knudsen', 'generalizes_to': 'slip_flow_and_dsmc', 'why': 'When the mean free path is not tiny relative to the length scale, velocity slip and non-equilibrium appear and the continuum no-slip closure breaks down.'},
        ],
    },
    'compressible_flow.linear_acoustics': {
        'law': 'Sound propagates at a0 = sqrt(gamma*R*T0) with disturbances superposing linearly',
        'assumptions': [
            {'name': 'small_amplitude', 'regime_variable': 'pressure_ratio', 'valid_when': '< 0.01', 'error_when_violated': 'pressure_ratio', 'generalizes_to': 'nonlinear_acoustics_shock_formation', 'why': 'Finite-amplitude waves travel faster at their crests, steepening into shocks; the constant-speed linear superposition fails once dp/p is appreciable.'},
        ],
    },
    'rotorcraft_bemt.momentum_theory_induced_velocity': {
        'law': 'v_i = sqrt(T / (2*rho*A))',
        'assumptions': [
            {'name': 'incompressible', 'regime_variable': 'tip_mach', 'valid_when': '< 0.3', 'error_when_violated': '0.5*tip_mach**2', 'generalizes_to': 'compressible_actuator_disk', 'why': 'Density varies across the disk at high tip Mach, breaking the constant-density mass/momentum balance.'},
            {'name': 'no_wake_swirl', 'regime_variable': 'tip_speed_ratio', 'valid_when': '> 3', 'error_when_violated': '1/tip_speed_ratio**2', 'generalizes_to': 'general_momentum_theory_with_swirl', 'why': 'Reaction to rotor torque leaves rotational kinetic energy in the wake that simple axial momentum theory ignores, worst at low tip-speed ratio.'},
        ],
    },
    'rotorcraft_bemt.uniform_inflow': {
        'law': 'lambda = C_T / (2*sqrt(mu**2 + lambda**2)) constant over the disk',
        'assumptions': [
            {'name': 'uniform_inflow', 'regime_variable': 'advance_ratio', 'valid_when': '< 0.1', 'error_when_violated': 'advance_ratio', 'generalizes_to': 'nonuniform_inflow_glauert_drees', 'why': 'Edgewise flight skews the wake, producing strong fore-aft inflow gradients that a single mean inflow cannot represent.'},
        ],
    },
    'rotorcraft_bemt.no_tip_loss': {
        'law': 'Blade lift is retained to r/R = 1 (tip-loss factor B = 1)',
        'assumptions': [
            {'name': 'no_tip_loss', 'regime_variable': 'blade_number', 'valid_when': '>= 6', 'error_when_violated': '1/blade_number', 'generalizes_to': 'prandtl_tip_loss_model', 'why': 'With finite blades, flow escapes around each tip and unloads the outboard span; the deficit scales inversely with blade count.'},
        ],
    },
    'rotorcraft_bemt.small_inflow_angle': {
        'law': 'dT = dL and dQ = (phi + Cd/Cl)*r*dL, using sin(phi) ~ phi and cos(phi) ~ 1',
        'assumptions': [
            {'name': 'small_inflow_angle', 'regime_variable': 'inflow_angle', 'valid_when': '< 0.35', 'error_when_violated': '0.5*inflow_angle**2', 'generalizes_to': 'large_angle_blade_element_theory', 'why': 'At high inflow angles (low speed ratio, hover of highly loaded rotors) the small-angle projection of lift onto thrust and torque breaks down.'},
        ],
    },
    'rotorcraft_bemt.linear_lift_curve': {
        'law': 'c_l = a*(alpha - alpha_0)',
        'assumptions': [
            {'name': 'no_stall', 'regime_variable': 'alpha_ratio', 'valid_when': '< 1.0', 'error_when_violated': 'alpha_ratio - 1', 'generalizes_to': 'nonlinear_stalled_airfoil_polar', 'why': 'Past the stall angle the boundary layer separates and lift collapses, so a constant lift-curve slope grossly over-predicts loading.'},
        ],
    },
    'rotorcraft_bemt.quasi_steady_aerodynamics': {
        'law': 'Sectional loads are set by the instantaneous angle of attack',
        'assumptions': [
            {'name': 'quasi_steady', 'regime_variable': 'reduced_frequency', 'valid_when': '< 0.05', 'error_when_violated': '2*reduced_frequency', 'generalizes_to': 'unsteady_theodorsen_aerodynamics', 'why': 'Shed wake vorticity and added-mass effects lag and attenuate the loads when the flow changes fast relative to the chord passage time.'},
        ],
    },
    'rotorcraft_bemt.prandtl_glauert_compressibility': {
        'law': 'c_l = c_l_incompressible / sqrt(1 - mach**2)',
        'assumptions': [
            {'name': 'subcritical_linearized', 'regime_variable': 'mach', 'valid_when': '< 0.7', 'error_when_violated': 'mach**2', 'generalizes_to': 'transonic_small_disturbance', 'why': 'Above the critical Mach number local shocks and nonlinear compressibility appear, which the linearized Prandtl-Glauert scaling cannot capture.'},
        ],
    },
    'rotorcraft_bemt.reynolds_independent_drag': {
        'law': 'Profile drag coefficient c_d ~ constant',
        'assumptions': [
            {'name': 'high_reynolds', 'regime_variable': 'reynolds', 'valid_when': '> 5e5', 'error_when_violated': '1/reynolds**0.5', 'generalizes_to': 'reynolds_dependent_drag_polar', 'why': 'At low chord Reynolds number (small rotors, inboard stations) laminar separation and thicker boundary layers raise drag substantially.'},
        ],
    },
    'rotorcraft_bemt.hover_no_climb': {
        'law': 'v_i = v_h = sqrt(T / (2*rho*A))',
        'assumptions': [
            {'name': 'zero_climb', 'regime_variable': 'climb_ratio', 'valid_when': '< 0.1', 'error_when_violated': 'climb_ratio', 'generalizes_to': 'climbing_momentum_theory', 'why': 'A climb velocity adds to the disk mass flux, lowering the induced velocity required for a given thrust.'},
        ],
    },
    'rotorcraft_bemt.independent_blade_elements': {
        'law': 'Each radial station behaves as an isolated 2D airfoil section',
        'assumptions': [
            {'name': 'no_radial_flow', 'regime_variable': 'radial_flow_ratio', 'valid_when': '< 0.3', 'error_when_violated': 'radial_flow_ratio', 'generalizes_to': 'yawed_three_dimensional_blade_aero', 'why': 'Spanwise flow in forward flight and dynamic stall couples adjacent stations and delays separation, violating strip-theory independence.'},
        ],
    },
    'rotorcraft_bemt.ground_effect_neglected': {
        'law': 'T = T_infinity (thrust as in free air)',
        'assumptions': [
            {'name': 'out_of_ground_effect', 'regime_variable': 'height_ratio', 'valid_when': '> 2', 'error_when_violated': '1/(16*height_ratio**2)', 'generalizes_to': 'ground_effect_thrust_model', 'why': 'Near the ground the wake cannot contract freely, raising thrust at fixed power (or reducing power at fixed thrust).'},
        ],
    },
    'rotorcraft_bemt.thin_airfoil_lift_slope': {
        'law': 'Lift-curve slope a = 2*pi per radian',
        'assumptions': [
            {'name': 'thin_airfoil', 'regime_variable': 'thickness_ratio', 'valid_when': '< 0.12', 'error_when_violated': 'thickness_ratio', 'generalizes_to': 'thick_airfoil_viscous_lift_slope', 'why': 'Finite thickness and boundary-layer displacement shift the effective slope away from the ideal thin-airfoil value of 2*pi.'},
        ],
    },
    'rotorcraft_bemt.rigid_blade': {
        'law': 'Blade pitch and twist distribution are fixed (no aeroelastic deformation)',
        'assumptions': [
            {'name': 'rigid_blade', 'regime_variable': 'tip_deflection_ratio', 'valid_when': '< 0.05', 'error_when_violated': 'tip_deflection_ratio', 'generalizes_to': 'aeroelastic_bemt', 'why': 'Elastic flap/torsion under airload changes the effective angle of attack distribution, an effect that grows with blade flexibility.'},
        ],
    },
    'thermodynamics.ideal_gas_law': {
        'law': 'P*v = R*T (Z = 1)',
        'assumptions': [
            {'name': 'dilute_gas', 'regime_variable': 'reduced_pressure', 'valid_when': '< 0.3', 'error_when_violated': 'reduced_pressure', 'generalizes_to': 'van_der_waals', 'why': 'At high pressure finite molecular volume and attractive forces push the compressibility factor Z away from 1.'},
            {'name': 'high_temperature', 'regime_variable': 'reduced_temperature', 'valid_when': '>= 1', 'error_when_violated': '1/reduced_temperature', 'generalizes_to': 'van_der_waals', 'why': 'Near and below the critical temperature intermolecular attraction dominates thermal motion, driving condensation-like deviations.'},
        ],
    },
    'thermodynamics.calorically_perfect_gas': {
        'law': 'cp, cv, gamma = constant; h = cp*T, u = cv*T',
        'assumptions': [
            {'name': 'no_vibrational_excitation', 'regime_variable': 'temperature_ratio', 'valid_when': '< 0.3', 'error_when_violated': 'temperature_ratio', 'generalizes_to': 'thermally_perfect_gas', 'why': 'As T approaches the vibrational characteristic temperature, vibrational modes activate and raise cp, so gamma is no longer constant.'},
        ],
    },
    'thermodynamics.joules_law': {
        'law': 'u = u(T) only; (du/dv)_T = 0',
        'assumptions': [
            {'name': 'ideal_gas', 'regime_variable': 'reduced_pressure', 'valid_when': '< 0.3', 'error_when_violated': 'reduced_pressure', 'generalizes_to': 'real_gas_internal_energy', 'why': 'In real gases intermolecular potential makes internal energy depend on volume, producing Joule-Thomson temperature change on expansion.'},
        ],
    },
    'thermodynamics.isentropic_process': {
        'law': 'P*v**gamma = constant',
        'assumptions': [
            {'name': 'adiabatic', 'regime_variable': 'heat_leak_ratio', 'valid_when': '< 0.1', 'error_when_violated': 'heat_leak_ratio', 'generalizes_to': 'polytropic_process', 'why': 'Finite wall area and time let heat cross the boundary, so the polytropic exponent departs from gamma.'},
            {'name': 'reversible', 'regime_variable': 'entropy_generation_number', 'valid_when': '< 0.1', 'error_when_violated': 'entropy_generation_number', 'generalizes_to': 'polytropic_process', 'why': 'Friction and finite-rate gradients generate entropy, so an adiabatic process is no longer isentropic.'},
        ],
    },
    'thermodynamics.quasi_static_process': {
        'law': 'State path passes through equilibrium states; P_system = P_surroundings',
        'assumptions': [
            {'name': 'quasi_static', 'regime_variable': 'deborah', 'valid_when': '< 0.1', 'error_when_violated': 'deborah', 'generalizes_to': 'finite_rate_process', 'why': 'When process time is comparable to internal relaxation time the system lags equilibrium, generating entropy and internal gradients.'},
        ],
    },
    'thermodynamics.clausius_equality': {
        'law': 'dS = dQ / T',
        'assumptions': [
            {'name': 'reversible', 'regime_variable': 'entropy_generation_number', 'valid_when': '< 0.1', 'error_when_violated': 'entropy_generation_number', 'generalizes_to': 'clausius_inequality', 'why': 'Any irreversibility adds generated entropy, so dS exceeds dQ/T and the equality becomes an inequality.'},
        ],
    },
    'thermodynamics.otto_cycle_efficiency': {
        'law': 'eta = 1 - r**(1 - gamma)',
        'assumptions': [
            {'name': 'cold_air_standard', 'regime_variable': 'temperature_ratio', 'valid_when': '< 0.3', 'error_when_violated': 'temperature_ratio', 'generalizes_to': 'fuel_air_cycle', 'why': 'Real gamma falls as combustion raises temperature, so the constant-gamma efficiency overpredicts the actual cycle.'},
        ],
    },
    'thermodynamics.air_standard_cycle': {
        'law': 'Working fluid is a fixed mass of ideal air; combustion modeled as external heat addition',
        'assumptions': [
            {'name': 'no_combustion_mass_change', 'regime_variable': 'fuel_air_ratio', 'valid_when': '< 0.05', 'error_when_violated': 'fuel_air_ratio', 'generalizes_to': 'fuel_air_cycle', 'why': 'Actual combustion changes composition and mole count, so treating the charge as fixed inert air misestimates work and temperature.'},
        ],
    },
    'thermodynamics.daltons_law': {
        'law': 'P_total = sum(P_i); partial pressures add',
        'assumptions': [
            {'name': 'ideal_gas_mixture', 'regime_variable': 'reduced_pressure', 'valid_when': '< 0.3', 'error_when_violated': 'reduced_pressure', 'generalizes_to': 'real_gas_mixture_fugacity', 'why': 'At high pressure cross-species interactions break additivity, requiring fugacities instead of partial pressures.'},
        ],
    },
    'thermodynamics.clausius_clapeyron': {
        'law': 'd(ln P)/dT = L / (R * T**2)',
        'assumptions': [
            {'name': 'ideal_vapor_negligible_liquid_volume', 'regime_variable': 'reduced_pressure', 'valid_when': '< 0.3', 'error_when_violated': 'reduced_pressure', 'generalizes_to': 'clapeyron_equation', 'why': 'Near the critical point vapor is non-ideal and liquid specific volume is no longer negligible against vapor volume.'},
        ],
    },
    'thermodynamics.speed_of_sound_perfect_gas': {
        'law': 'a = sqrt(gamma * R * T)',
        'assumptions': [
            {'name': 'ideal_calorically_perfect', 'regime_variable': 'reduced_pressure', 'valid_when': '< 0.3', 'error_when_violated': 'reduced_pressure', 'generalizes_to': 'real_gas_sound_speed', 'why': 'Real-gas compressibility changes the isentropic (dP/drho)_s, so the perfect-gas closed form no longer holds.'},
        ],
    },
    'airbreathing_propulsion.stagnation_temperature': {
        'law': 'T0 / T = 1 + (gamma - 1)/2 * mach**2',
        'assumptions': [
            {'name': 'calorically_perfect', 'regime_variable': 'mach', 'valid_when': '< 5', 'error_when_violated': '0.02*mach**2', 'generalizes_to': 'high_temperature_gas_dynamics', 'why': 'Hypersonic stagnation heats the gas enough to excite vibration, dissociation, and ionization, so constant-gamma energy balance breaks.'},
        ],
    },
    'thermodynamics.incompressible_process': {
        'law': 'rho = constant; dh = cp*dT (no pressure work on density)',
        'assumptions': [
            {'name': 'incompressible', 'regime_variable': 'mach', 'valid_when': '< 0.3', 'error_when_violated': '0.5*mach**2', 'generalizes_to': 'compressible_flow', 'why': 'Above Mach ~0.3 density varies appreciably with pressure, so constant-density energy accounting fails.'},
        ],
    },
    'thermodynamics.adiabatic_process': {
        'law': 'Q = 0; dU = -W',
        'assumptions': [
            {'name': 'adiabatic', 'regime_variable': 'heat_leak_ratio', 'valid_when': '< 0.1', 'error_when_violated': 'heat_leak_ratio', 'generalizes_to': 'diabatic_process', 'why': 'Finite process time and imperfect insulation allow heat exchange with the surroundings, breaking Q = 0.'},
        ],
    },
    'thermodynamics.isothermal_ideal_gas_work': {
        'law': 'W = R*T*ln(v2/v1)',
        'assumptions': [
            {'name': 'ideal_gas', 'regime_variable': 'reduced_pressure', 'valid_when': '< 0.3', 'error_when_violated': 'reduced_pressure', 'generalizes_to': 'real_gas_work', 'why': 'Real-gas P(v) at fixed T deviates from R*T/v, so the logarithmic work integral no longer applies.'},
        ],
    },
    'statistical_mechanics.maxwell_boltzmann_statistics': {
        'law': 'Occupation number n_i = exp(-(E_i - mu)/kT); classical count of microstates with no quantum indistinguishability factor.',
        'assumptions': [
            {'name': 'non_degenerate', 'regime_variable': 'degeneracy_parameter', 'valid_when': '< 0.1', 'error_when_violated': 'degeneracy_parameter', 'generalizes_to': 'fermi_dirac_bose_einstein_statistics', 'why': 'When phase-space density n*lambda_thermal**3 approaches unity, wavefunctions overlap and exchange (anti)symmetry forces quantum statistics.'},
        ],
    },
    'statistical_mechanics.ideal_gas_law': {
        'law': 'PV = N kT; point particles with no interaction volume and no intermolecular forces.',
        'assumptions': [
            {'name': 'dilute_no_interactions', 'regime_variable': 'reduced_density', 'valid_when': '< 0.1', 'error_when_violated': 'reduced_density', 'generalizes_to': 'van_der_waals_equation', 'why': 'Finite molecular volume (b) and attractive forces (a) make the compressibility factor deviate from 1 once n*b is non-negligible.'},
        ],
    },
    'statistical_mechanics.equipartition_theorem': {
        'law': 'Each quadratic degree of freedom carries (1/2)kT of energy; C_v = (f/2) Nk.',
        'assumptions': [
            {'name': 'classical_high_temperature', 'regime_variable': 'theta_mode_over_T', 'valid_when': '< 0.3', 'error_when_violated': 'theta_mode_over_T', 'generalizes_to': 'quantum_partition_function', 'why': 'When the mode quantum hnu exceeds kT the level is not thermally accessible, so the degree of freedom freezes out and contributes less than (1/2)kT.'},
        ],
    },
    'statistical_mechanics.dulong_petit_law': {
        'law': 'Molar heat capacity of a crystalline solid C_v = 3R (independent of temperature).',
        'assumptions': [
            {'name': 'classical_lattice', 'regime_variable': 'debye_temperature_over_T', 'valid_when': '< 0.3', 'error_when_violated': 'debye_temperature_over_T**2', 'generalizes_to': 'debye_model', 'why': 'Below the Debye temperature high-frequency phonon modes freeze out and C_v drops below 3R toward the T**3 law.'},
        ],
    },
    'statistical_mechanics.rayleigh_jeans_law': {
        'law': 'Spectral energy density u(nu) = (8*pi*nu**2/c**3) kT; classical equipartition over EM modes.',
        'assumptions': [
            {'name': 'low_frequency_classical', 'regime_variable': 'photon_energy_ratio', 'valid_when': '< 0.1', 'error_when_violated': 'photon_energy_ratio', 'generalizes_to': 'planck_law', 'why': 'When hnu approaches kT, mode-energy quantization suppresses high-frequency modes; ignoring it gives the divergent ultraviolet catastrophe.'},
        ],
    },
    'statistical_mechanics.wien_approximation': {
        'law': 'u(nu) proportional to nu**3 exp(-hnu/kT); high-frequency limit of blackbody radiation.',
        'assumptions': [
            {'name': 'high_frequency', 'regime_variable': 'thermal_photon_ratio', 'valid_when': '< 0.1', 'error_when_violated': 'thermal_photon_ratio', 'generalizes_to': 'planck_law', 'why': 'Replacing 1/(exp(x)-1) with exp(-x) drops the low-frequency term; valid only when kT is far below hnu.'},
        ],
    },
    'statistical_mechanics.continuum_flow': {
        'law': 'Navier-Stokes / continuum fields with no-slip boundary conditions treat the gas as a continuous medium.',
        'assumptions': [
            {'name': 'continuum', 'regime_variable': 'knudsen', 'valid_when': '< 0.01', 'error_when_violated': 'knudsen', 'generalizes_to': 'boltzmann_kinetic_transport', 'why': 'When the mean free path is comparable to the length scale, velocity slip and rarefaction break the continuum closure of the moment hierarchy.'},
        ],
    },
    'statistical_mechanics.fourier_heat_conduction': {
        'law': 'q = -k grad(T); diffusive heat flux proportional to local temperature gradient.',
        'assumptions': [
            {'name': 'diffusive_transport', 'regime_variable': 'knudsen', 'valid_when': '< 0.1', 'error_when_violated': 'knudsen', 'generalizes_to': 'ballistic_phonon_transport', 'why': 'When the phonon/molecular mean free path is comparable to the domain, transport becomes ballistic and the local-gradient (diffusive) relation fails.'},
        ],
    },
    'statistical_mechanics.newtonian_viscous_stress': {
        'law': 'Viscous stress linear in velocity gradient (first-order Chapman-Enskog), tau = mu*(grad u).',
        'assumptions': [
            {'name': 'near_equilibrium', 'regime_variable': 'knudsen', 'valid_when': '< 0.1', 'error_when_violated': 'knudsen', 'generalizes_to': 'burnett_equations', 'why': 'Far from equilibrium the distribution has large gradients, so higher-order (Burnett) terms in the Chapman-Enskog expansion become non-negligible.'},
        ],
    },
    'statistical_mechanics.curie_law': {
        'law': 'Paramagnetic magnetization M = C*B/T (susceptibility inversely proportional to T).',
        'assumptions': [
            {'name': 'linear_response', 'regime_variable': 'magnetic_energy_ratio', 'valid_when': '< 0.1', 'error_when_violated': 'magnetic_energy_ratio**2', 'generalizes_to': 'brillouin_function', 'why': 'When mu*B approaches kT the magnetization saturates; the linear (small-argument) expansion of the Brillouin function no longer holds.'},
        ],
    },
    'statistical_mechanics.maxwell_boltzmann_speed_distribution': {
        'law': 'f(v) proportional to v**2 exp(-m*v**2/2kT); non-relativistic kinetic energy in the Boltzmann factor.',
        'assumptions': [
            {'name': 'non_relativistic', 'regime_variable': 'thermal_relativity', 'valid_when': '< 0.01', 'error_when_violated': 'thermal_relativity', 'generalizes_to': 'maxwell_juttner_distribution', 'why': 'When kT approaches mc**2 the energy-momentum relation is relativistic, reshaping the high-speed tail toward the Maxwell-Juttner form.'},
        ],
    },
    'statistical_mechanics.fermi_gas_ground_state': {
        'law': 'Degenerate electron gas at T=0: energy and pressure set by Fermi level (Sommerfeld ground state).',
        'assumptions': [
            {'name': 'fully_degenerate', 'regime_variable': 'temperature_ratio', 'valid_when': '< 0.1', 'error_when_violated': 'temperature_ratio**2', 'generalizes_to': 'sommerfeld_finite_temperature_expansion', 'why': 'Finite temperature smears the Fermi surface over a width kT, adding leading (T/T_F)**2 corrections to energy, C_v, and pressure.'},
        ],
    },
    'statistical_mechanics.debye_t3_law': {
        'law': 'Low-temperature lattice heat capacity C_v proportional to (T/theta_D)**3.',
        'assumptions': [
            {'name': 'low_temperature', 'regime_variable': 'T_over_debye', 'valid_when': '< 0.1', 'error_when_violated': 'T_over_debye**2', 'generalizes_to': 'debye_model_full_integral', 'why': 'The T**3 law assumes only long-wavelength acoustic modes are excited; as T rises, the full Debye integral (approaching Dulong-Petit) is required.'},
        ],
    },
    'statistical_mechanics.molecular_chaos': {
        'law': 'Boltzmann collision term assumes pre-collision velocities are uncorrelated (Stosszahlansatz) in a dilute gas.',
        'assumptions': [
            {'name': 'dilute_gas', 'regime_variable': 'density_parameter', 'valid_when': '< 0.01', 'error_when_violated': 'density_parameter', 'generalizes_to': 'enskog_dense_gas_theory', 'why': 'At high density n*d**3 recollisions and positional correlations invalidate the molecular-chaos closure of the collision integral.'},
        ],
    },
    'statistical_mechanics.raoults_law': {
        'law': 'Ideal solution vapor pressure p_i = x_i * p_i_pure (partial pressure linear in mole fraction).',
        'assumptions': [
            {'name': 'ideal_mixing', 'regime_variable': 'solute_mole_fraction', 'valid_when': '< 0.05', 'error_when_violated': 'solute_mole_fraction', 'generalizes_to': 'activity_coefficient_model', 'why': 'Unlike-molecule interaction energies differ from like-like, so at finite composition activity coefficients deviate from unity.'},
        ],
    },
    'statistical_mechanics.harmonic_lattice_approximation': {
        'law': 'Lattice potential expanded to quadratic order; independent harmonic phonon normal modes with no thermal expansion.',
        'assumptions': [
            {'name': 'harmonic', 'regime_variable': 'temperature_over_melting', 'valid_when': '< 0.3', 'error_when_violated': 'temperature_over_melting', 'generalizes_to': 'anharmonic_lattice_dynamics', 'why': 'Large vibrational amplitude at high T probes cubic/quartic terms of the interatomic potential, producing thermal expansion and phonon-phonon scattering.'},
        ],
    },
    'heat_transfer.lumped_capacitance': {
        'law': 'dT/dt = -(h*A)/(rho*V*c) * (T - T_inf); spatially uniform body temperature',
        'assumptions': [
            {'name': 'lumped_capacitance', 'regime_variable': 'biot', 'valid_when': '< 0.1', 'error_when_violated': 'biot', 'generalizes_to': 'transient_conduction_with_internal_gradients', 'why': 'When internal conduction resistance is not small vs surface convection resistance, the body develops significant internal temperature gradients so a single lumped temperature is wrong.'},
        ],
    },
    'heat_transfer.blackbody_radiation': {
        'law': 'q = sigma * T^4 (ideal emitter/absorber, emissivity = 1)',
        'assumptions': [
            {'name': 'blackbody_surface', 'regime_variable': 'emissivity', 'valid_when': '<= 1.0', 'error_when_violated': '1 - emissivity', 'generalizes_to': 'gray_body_radiation', 'why': 'Real surfaces emit less than a blackbody; treating them as perfect emitters overpredicts emitted flux by the emissivity deficit.'},
        ],
    },
    'heat_transfer.gray_body_radiation': {
        'law': 'q = emissivity * sigma * T^4 with emissivity independent of wavelength',
        'assumptions': [
            {'name': 'gray_surface', 'regime_variable': 'spectral_emissivity_variation', 'valid_when': '< 0.1', 'error_when_violated': 'spectral_emissivity_variation', 'generalizes_to': 'spectral_nongray_radiation', 'why': 'When emissivity varies strongly with wavelength (selective surfaces), a single band-averaged emissivity misrepresents the spectral distribution of source and sink.'},
        ],
    },
    'heat_transfer.linearized_radiation': {
        'law': 'q = h_rad*(T - T_surr) with h_rad = 4*emissivity*sigma*T_mean^3',
        'assumptions': [
            {'name': 'small_temperature_difference', 'regime_variable': 'temperature_difference_ratio', 'valid_when': '< 0.1', 'error_when_violated': '1.5*temperature_difference_ratio', 'generalizes_to': 'fourth_power_radiation_exchange', 'why': 'The T^4 law is only locally linear; when the temperature difference is a large fraction of absolute temperature, neglected higher-order Taylor terms dominate.'},
        ],
    },
    'heat_transfer.constant_properties_conduction': {
        'law': 'Fourier conduction with k, rho, c evaluated as constants',
        'assumptions': [
            {'name': 'constant_properties', 'regime_variable': 'property_variation_ratio', 'valid_when': '< 0.1', 'error_when_violated': 'property_variation_ratio', 'generalizes_to': 'variable_property_conduction', 'why': 'Thermal conductivity and specific heat depend on temperature; over a large temperature span the fractional change in properties directly biases the computed flux.'},
        ],
    },
    'heat_transfer.one_dimensional_conduction': {
        'law': 'q = -k*A*dT/dx; heat flow along one axis only',
        'assumptions': [
            {'name': 'one_dimensional', 'regime_variable': 'transverse_to_axial_aspect_ratio', 'valid_when': '< 0.1', 'error_when_violated': 'transverse_to_axial_aspect_ratio', 'generalizes_to': 'multidimensional_conduction', 'why': 'Transverse gradients become non-negligible when the lateral dimension is comparable to the conduction length, so multidimensional spreading is neglected.'},
        ],
    },
    'heat_transfer.semi_infinite_solid': {
        'law': 'Transient penetration solution T(x,t) using erf, valid before the far boundary is felt',
        'assumptions': [
            {'name': 'semi_infinite', 'regime_variable': 'fourier', 'valid_when': '< 0.05', 'error_when_violated': 'fourier', 'generalizes_to': 'finite_thickness_transient_conduction', 'why': 'Once the thermal penetration depth reaches the opposite boundary (Fourier number grows), the semi-infinite assumption breaks and finite-body boundary conditions apply.'},
        ],
    },
    'heat_transfer.heisler_one_term_approximation': {
        'law': 'Transient temperature = first term of the eigenfunction series (one-term Heisler)',
        'assumptions': [
            {'name': 'one_term_series', 'regime_variable': 'fourier', 'valid_when': '> 0.2', 'error_when_violated': '0.02/fourier', 'generalizes_to': 'full_series_transient_solution', 'why': 'The higher eigenmodes decay quickly; at small Fourier number they are still significant and truncating to one term underpredicts early-time gradients.'},
        ],
    },
    'heat_transfer.steady_state_conduction': {
        'law': 'Laplace/Poisson conduction with dT/dt = 0',
        'assumptions': [
            {'name': 'steady_state', 'regime_variable': 'inverse_fourier_at_observation_time', 'valid_when': '< 0.1', 'error_when_violated': 'inverse_fourier_at_observation_time', 'generalizes_to': 'transient_conduction', 'why': 'If the observation time is not large compared to the thermal diffusion time, stored-energy transients still matter and the steady field is not yet established.'},
        ],
    },
    'heat_transfer.negligible_radiation_convection_only': {
        'law': 'Surface loss modeled as q = h*(T - T_inf), radiation ignored',
        'assumptions': [
            {'name': 'radiation_negligible', 'regime_variable': 'radiative_to_convective_coefficient_ratio', 'valid_when': '< 0.1', 'error_when_violated': 'radiative_to_convective_coefficient_ratio', 'generalizes_to': 'combined_convection_radiation', 'why': 'At high surface temperatures or in low-convection (vacuum, still air) settings, radiative h grows as T^3 and becomes comparable to or larger than convective h.'},
        ],
    },
    'heat_transfer.boussinesq_approximation': {
        'law': 'Natural convection with density variation retained only in the buoyancy term',
        'assumptions': [
            {'name': 'boussinesq', 'regime_variable': 'thermal_expansion_times_delta_T', 'valid_when': '< 0.1', 'error_when_violated': 'thermal_expansion_times_delta_T', 'generalizes_to': 'variable_density_low_mach_convection', 'why': 'The linear density-temperature relation and constant properties fail when beta*deltaT is not small, so density changes in inertia and continuity cannot be dropped.'},
        ],
    },
    'heat_transfer.thermally_fully_developed_flow': {
        'law': 'Constant Nusselt number in internal flow (fully developed thermal profile)',
        'assumptions': [
            {'name': 'thermally_fully_developed', 'regime_variable': 'inverse_graetz_position', 'valid_when': '> 0.05', 'error_when_violated': '0.05/inverse_graetz_position', 'generalizes_to': 'thermal_entry_region_flow', 'why': 'Near the inlet the thermal boundary layer is still growing, so the local Nusselt number is far above its developed value and constant-Nu underpredicts entrance heat transfer.'},
        ],
    },
    'heat_transfer.negligible_viscous_dissipation': {
        'law': 'Energy equation dropping the viscous dissipation source term',
        'assumptions': [
            {'name': 'no_viscous_dissipation', 'regime_variable': 'brinkman', 'valid_when': '< 0.1', 'error_when_violated': 'brinkman', 'generalizes_to': 'convection_with_viscous_heating', 'why': 'In high-speed or high-viscosity flows the frictional heating (Brinkman/Eckert number) becomes a significant internal source that cannot be neglected in the energy balance.'},
        ],
    },
    'heat_transfer.optically_thin_medium': {
        'law': 'Radiating gas treated as non-self-absorbing (emission without reabsorption)',
        'assumptions': [
            {'name': 'optically_thin', 'regime_variable': 'optical_thickness', 'valid_when': '< 0.1', 'error_when_violated': 'optical_thickness', 'generalizes_to': 'radiative_transfer_equation', 'why': 'When optical thickness is not small the medium reabsorbs its own emission and scatters, so the full radiative transfer equation is required rather than simple volumetric emission.'},
        ],
    },
    'heat_transfer.fin_adiabatic_tip': {
        'law': 'Fin temperature solution assuming zero heat loss at the tip',
        'assumptions': [
            {'name': 'adiabatic_tip', 'regime_variable': 'tip_biot', 'valid_when': '< 0.1', 'error_when_violated': 'tip_biot', 'generalizes_to': 'convective_tip_fin', 'why': 'For short or thick fins the convective loss from the exposed tip is not negligible relative to lateral loss, so the insulated-tip boundary condition overpredicts tip temperature.'},
        ],
    },
    'heat_transfer.constant_heat_transfer_coefficient': {
        'law': 'Newton cooling with a single spatially uniform h over the surface',
        'assumptions': [
            {'name': 'uniform_h', 'regime_variable': 'local_h_variation_ratio', 'valid_when': '< 0.1', 'error_when_violated': 'local_h_variation_ratio', 'generalizes_to': 'spatially_varying_convection', 'why': 'The local convection coefficient varies strongly along a surface (leading edge, separation, developing boundary layer), so a single averaged h misplaces local flux and hot spots.'},
        ],
    },
    'combustion.adiabatic_flame_temperature': {
        'law': 'T_ad = T_u + (Y_f * Q_LHV) / c_p  (all chemical enthalpy released goes into sensible heat of products)',
        'assumptions': [
            {'name': 'adiabatic', 'regime_variable': 'heat_loss_ratio', 'valid_when': '< 0.1', 'error_when_violated': 'heat_loss_ratio', 'generalizes_to': 'nonadiabatic_flame_with_losses', 'why': 'Radiative and wall heat loss drains enthalpy from the reaction zone so the real peak temperature falls below T_ad.'},
            {'name': 'no_dissociation', 'regime_variable': 'flame_temperature', 'valid_when': '< 2000', 'error_when_violated': '(flame_temperature - 2000) / flame_temperature', 'generalizes_to': 'equilibrium_flame_temperature', 'why': 'Above ~2000 K product CO2/H2O endothermically dissociate into CO, OH, H, O, absorbing energy and capping the temperature.'},
        ],
    },
    'combustion.complete_combustion': {
        'law': 'Fuel + stoichiometric air -> CO2 + H2O only (100% conversion to fully oxidized products)',
        'assumptions': [
            {'name': 'fuel_lean_or_stoichiometric', 'regime_variable': 'equivalence_ratio', 'valid_when': '<= 1.0', 'error_when_violated': 'equivalence_ratio - 1', 'generalizes_to': 'equilibrium_products_with_CO_H2_soot', 'why': 'In rich mixtures there is insufficient oxygen, so carbon and hydrogen leave as CO, H2 and soot instead of CO2/H2O.'},
        ],
    },
    'combustion.constant_pressure_combustion': {
        'law': 'Deflagration proceeds isobarically: p_products = p_reactants (heat added at constant pressure)',
        'assumptions': [
            {'name': 'low_mach_deflagration', 'regime_variable': 'mach', 'valid_when': '< 0.3', 'error_when_violated': 'mach**2', 'generalizes_to': 'detonation_compressible_combustion', 'why': 'When the flame or flow approaches sonic speed, compressibility and shock/pressure coupling make the process non-isobaric (Rayleigh/detonation).'},
        ],
    },
    'combustion.well_stirred_reactor': {
        'law': 'Perfectly stirred reactor: composition and temperature are spatially uniform, set by residence time vs chemical time',
        'assumptions': [
            {'name': 'perfect_mixing', 'regime_variable': 'damkohler_mixing', 'valid_when': '< 0.1', 'error_when_violated': 'damkohler_mixing', 'generalizes_to': 'partially_stirred_reactor', 'why': 'When mixing is not infinitely fast relative to reaction, unmixed composition pockets form and the single-point rate law breaks down.'},
        ],
    },
    'combustion.high_activation_energy_asymptotics': {
        'law': 'Flame structure splits into a thin reaction zone (thickness ~ 1/Ze) and an inert preheat zone; reaction confined to near T_ad',
        'assumptions': [
            {'name': 'large_zeldovich_number', 'regime_variable': 'zeldovich', 'valid_when': '> 1', 'error_when_violated': '1/zeldovich', 'generalizes_to': 'finite_rate_broad_reaction_zone', 'why': 'For moderate activation energy the reaction is not strongly temperature-selective, so the reaction zone is broad and the thin-flame separation fails.'},
        ],
    },
    'combustion.unity_lewis_number_flame': {
        'law': 'With Le=1 (equal thermal and mass diffusivity) laminar flame speed follows thermal theory, S_L ~ sqrt(alpha * omega)',
        'assumptions': [
            {'name': 'unity_lewis', 'regime_variable': 'lewis_number_deviation', 'valid_when': '< 0.1', 'error_when_violated': 'lewis_number_deviation', 'generalizes_to': 'differential_diffusion_flame', 'why': 'When heat and reactant diffuse at different rates the local enthalpy at the reaction zone shifts, changing flame speed and triggering thermodiffusive (cellular) instability.'},
        ],
    },
    'combustion.flamelet_regime': {
        'law': 'Turbulent premixed flame = ensemble of thin laminar flamelets wrinkled by turbulence; inner structure preserved',
        'assumptions': [
            {'name': 'thin_reaction_zone', 'regime_variable': 'karlovitz', 'valid_when': '< 1', 'error_when_violated': 'karlovitz', 'generalizes_to': 'distributed_reaction_zone', 'why': 'When the smallest (Kolmogorov) eddies are finer than the reaction zone they penetrate and broaden it, destroying the laminar-flamelet picture.'},
        ],
    },
    'combustion.semenov_thermal_explosion': {
        'law': 'Thermal ignition set by balance of volumetric heat release and Newtonian surface loss with a single lumped temperature',
        'assumptions': [
            {'name': 'lumped_temperature', 'regime_variable': 'biot', 'valid_when': '< 0.1', 'error_when_violated': 'biot', 'generalizes_to': 'frank_kamenetskii_theory', 'why': 'When internal conduction is slow relative to surface loss, temperature gradients form inside the charge and the uniform-temperature criterion is wrong.'},
        ],
    },
    'combustion.frank_kamenetskii': {
        'law': 'Steady spatial temperature profile at the ignition limit computed with reaction rate evaluated at initial reactant concentration',
        'assumptions': [
            {'name': 'negligible_reactant_consumption', 'regime_variable': 'consumption_fraction', 'valid_when': '< 0.1', 'error_when_violated': 'consumption_fraction', 'generalizes_to': 'transient_ignition_with_depletion', 'why': 'If a significant fraction of reactant is consumed before criticality, the falling rate delays or prevents the predicted runaway.'},
        ],
    },
    'combustion.laminar_flame_speed': {
        'law': 'Flame propagates at the laminar burning velocity S_L, a property of mixture, pressure and temperature only',
        'assumptions': [
            {'name': 'laminar', 'regime_variable': 'turbulence_intensity', 'valid_when': '< 0.3', 'error_when_violated': 'turbulence_intensity', 'generalizes_to': 'turbulent_flame_speed', 'why': 'Turbulent velocity fluctuations wrinkle and stretch the flame surface, raising the effective burning rate well above S_L.'},
        ],
    },
    'combustion.ideal_gas_products': {
        'law': 'Combustion gases obey p = rho * R * T (ideal-gas equation of state) for reactants and products',
        'assumptions': [
            {'name': 'ideal_gas', 'regime_variable': 'reduced_pressure', 'valid_when': '< 0.3', 'error_when_violated': 'reduced_pressure', 'generalizes_to': 'real_gas_equation_of_state', 'why': 'At high reduced pressure (rockets, diesel, detonation) intermolecular forces and finite molecular volume make density deviate from ideal-gas.'},
        ],
    },
    'combustion.chemical_equilibrium_products': {
        'law': 'Product composition is the local chemical-equilibrium state (fast chemistry limit)',
        'assumptions': [
            {'name': 'fast_chemistry', 'regime_variable': 'damkohler', 'valid_when': '> 1', 'error_when_violated': '1/damkohler', 'generalizes_to': 'finite_rate_chemistry', 'why': 'When residence time is comparable to chemical time, reactions freeze short of equilibrium, leaving non-equilibrium radicals and unburnt species.'},
        ],
    },
    'combustion.plug_flow_reactor': {
        'law': 'Plug-flow reactor: uniform radial profile, convection-only transport, no axial mixing along the flow',
        'assumptions': [
            {'name': 'no_axial_dispersion', 'regime_variable': 'peclet', 'valid_when': '> 1e2', 'error_when_violated': '1/peclet', 'generalizes_to': 'axial_dispersion_reactor', 'why': 'At low Peclet, axial diffusion/back-mixing smears the concentration front so the position-time correspondence of plug flow fails.'},
        ],
    },
    'combustion.constant_density_reacting_flow': {
        'law': 'Reacting flow treated at constant density (velocity field decoupled from heat release)',
        'assumptions': [
            {'name': 'low_heat_release', 'regime_variable': 'heat_release_parameter', 'valid_when': '< 0.3', 'error_when_violated': 'heat_release_parameter', 'generalizes_to': 'variable_density_combustion', 'why': 'Combustion raises temperature severalfold; the resulting thermal expansion drops density and accelerates the gas, feeding back on the flow field.'},
        ],
    },
    'combustion.thin_flame_front': {
        'law': 'Flame modeled as an infinitesimally thin interface (level-set/G-equation) separating reactants and products',
        'assumptions': [
            {'name': 'thin_flame', 'regime_variable': 'flame_thickness_ratio', 'valid_when': '< 0.1', 'error_when_violated': 'flame_thickness_ratio', 'generalizes_to': 'thickened_flame_model', 'why': 'When flame thickness is comparable to the flow/geometry scale, internal structure and curvature/stretch effects can no longer be collapsed to a surface.'},
        ],
    },
    'solid_mechanics.euler_bernoulli_beam': {
        'law': 'M = E*I*(d^2 w/dx^2); beam curvature is proportional to bending moment, plane sections remain plane and normal to the neutral axis.',
        'assumptions': [
            {'name': 'small_deflection', 'regime_variable': 'deflection_ratio', 'valid_when': '< 0.1', 'error_when_violated': 'deflection_ratio**2', 'generalizes_to': 'large_deflection_beam_elastica', 'why': "Linearized curvature w'' drops the (1+w'^2)^(3/2) denominator; at large slope the true curvature and geometric stiffening diverge from the linear estimate."},
            {'name': 'shear_deformation_negligible', 'regime_variable': 'depth_to_span_ratio', 'valid_when': '< 0.1', 'error_when_violated': '10*depth_to_span_ratio**2', 'generalizes_to': 'timoshenko_beam', 'why': 'Euler-Bernoulli forces cross-sections to stay normal to the axis; for stubby beams transverse shear adds compliance the theory ignores, so deflection is underpredicted.'},
        ],
    },
    'solid_mechanics.linear_elasticity_hookes_law': {
        'law': 'sigma = E*epsilon (uniaxial) / sigma_ij = C_ijkl*epsilon_kl; stress is a linear, reversible function of strain.',
        'assumptions': [
            {'name': 'pre_yield_linear_elastic', 'regime_variable': 'stress_ratio', 'valid_when': '< 1.0', 'error_when_violated': 'stress_ratio - 1', 'generalizes_to': 'elastic_plastic_j2_flow', 'why': 'Beyond the yield stress dislocations move irreversibly; the material work-hardens on a nonlinear curve and unloads with permanent set, breaking proportionality.'},
            {'name': 'small_strain', 'regime_variable': 'strain_magnitude', 'valid_when': '< 0.02', 'error_when_violated': 'strain_magnitude', 'generalizes_to': 'finite_strain_hyperelasticity', 'why': 'The infinitesimal strain tensor linearizes the deformation gradient; at finite strain geometric nonlinearity and the distinction between reference and current configuration matter.'},
        ],
    },
    'solid_mechanics.st_venant_torsion': {
        'law': 'T = G*J*(dphi/dx); torque is proportional to the rate of twist through the torsional rigidity G*J.',
        'assumptions': [
            {'name': 'free_warping', 'regime_variable': 'warping_restraint_ratio', 'valid_when': '< 0.1', 'error_when_violated': 'warping_restraint_ratio', 'generalizes_to': 'vlasov_nonuniform_torsion', 'why': 'St-Venant assumes warping is unrestrained and uniform; when ends or supports restrain warping (thin-walled open sections) axial warping stresses arise and stiffness rises.'},
            {'name': 'circular_cross_section_J_equals_polar', 'regime_variable': 'noncircularity_ratio', 'valid_when': '< 0.1', 'error_when_violated': 'noncircularity_ratio', 'generalizes_to': 'prandtl_stress_function_torsion', 'why': 'Only circular shafts have J equal to the polar moment and no warping; noncircular sections warp out of plane, so using the polar moment overestimates torsional stiffness.'},
        ],
    },
    'solid_mechanics.thin_beam_pure_bending_stress': {
        'law': 'sigma = M*y/I; bending stress varies linearly across the depth from the neutral axis.',
        'assumptions': [
            {'name': 'slender_prismatic_beam', 'regime_variable': 'depth_to_span_ratio', 'valid_when': '< 0.2', 'error_when_violated': 'depth_to_span_ratio', 'generalizes_to': 'deep_beam_elasticity_2d', 'why': 'The linear stress distribution assumes the beam is slender; in deep beams the stress becomes nonlinear across depth and normal-stress assumptions of beam theory fail.'},
        ],
    },
    'solid_mechanics.plane_stress': {
        'law': 'sigma_zz = sigma_xz = sigma_yz = 0; the out-of-plane stress components vanish for thin bodies loaded in-plane.',
        'assumptions': [
            {'name': 'thin_body_relative_to_inplane_dimensions', 'regime_variable': 'thickness_to_width_ratio', 'valid_when': '< 0.1', 'error_when_violated': 'thickness_to_width_ratio', 'generalizes_to': 'full_3d_elasticity', 'why': 'Plane stress needs the through-thickness dimension small enough that sigma_zz cannot build up; in thick bodies out-of-plane stress is nonzero and the 2D idealization errs.'},
        ],
    },
    'solid_mechanics.plane_strain': {
        'law': 'epsilon_zz = epsilon_xz = epsilon_yz = 0; out-of-plane strain vanishes for long prismatic bodies with constant cross-section.',
        'assumptions': [
            {'name': 'long_prismatic_constrained_ends', 'regime_variable': 'inplane_to_length_ratio', 'valid_when': '< 0.1', 'error_when_violated': 'inplane_to_length_ratio', 'generalizes_to': 'full_3d_elasticity', 'why': 'Plane strain assumes the body is effectively infinite along z so epsilon_zz is fully suppressed; for short bodies the ends relieve axial strain and the constraint is only partial.'},
        ],
    },
    'solid_mechanics.kirchhoff_love_thin_plate': {
        'law': 'D*grad^4 w = q with D = E*t^3/(12*(1-nu^2)); thin-plate bending with normals staying straight and normal.',
        'assumptions': [
            {'name': 'small_deflection_plate', 'regime_variable': 'deflection_to_thickness_ratio', 'valid_when': '< 0.2', 'error_when_violated': 'deflection_to_thickness_ratio**2', 'generalizes_to': 'von_karman_large_deflection_plate', 'why': 'Kirchhoff plate ignores membrane stretching; once deflection approaches the thickness, in-plane membrane forces stiffen the plate nonlinearly (von Karman coupling).'},
            {'name': 'thin_plate_no_transverse_shear', 'regime_variable': 'thickness_to_span_ratio', 'valid_when': '< 0.1', 'error_when_violated': '10*thickness_to_span_ratio**2', 'generalizes_to': 'mindlin_reissner_plate', 'why': 'Neglecting transverse shear is valid only for thin plates; thick plates deform in shear and Kirchhoff underpredicts deflection much like Euler vs Timoshenko.'},
        ],
    },
    'solid_mechanics.euler_column_buckling': {
        'law': 'P_cr = pi^2*E*I/(K*L)^2; critical elastic buckling load of a slender column.',
        'assumptions': [
            {'name': 'elastic_slender_column', 'regime_variable': 'slenderness_ratio', 'valid_when': '>= 1.0', 'error_when_violated': '1 - slenderness_ratio', 'generalizes_to': 'inelastic_tangent_modulus_buckling', 'why': 'Euler buckling assumes stress stays elastic at the critical load; for stocky columns the critical stress exceeds yield, so inelastic (tangent-modulus) buckling governs and Euler overpredicts capacity.'},
        ],
    },
    'solid_mechanics.isotropic_linear_elasticity': {
        'law': 'Two independent constants (E, nu) fully describe the stiffness tensor; properties are direction-independent.',
        'assumptions': [
            {'name': 'material_isotropy', 'regime_variable': 'anisotropy_ratio', 'valid_when': '< 1.1', 'error_when_violated': 'anisotropy_ratio - 1', 'generalizes_to': 'anisotropic_orthotropic_elasticity', 'why': 'Isotropy collapses the stiffness tensor to two constants; textured, fibrous, or single-crystal materials have direction-dependent moduli requiring the full anisotropic tensor.'},
        ],
    },
    'solid_mechanics.thin_walled_pressure_vessel': {
        'law': 'sigma_hoop = p*r/t, sigma_axial = p*r/(2*t); membrane stresses in a thin shell under internal pressure.',
        'assumptions': [
            {'name': 'thin_wall_membrane', 'regime_variable': 'thickness_to_radius_ratio', 'valid_when': '< 0.1', 'error_when_violated': 'thickness_to_radius_ratio', 'generalizes_to': 'thick_walled_lame_solution', 'why': 'The membrane formula assumes stress is uniform across the wall; in thick walls the radial stress gradient (Lame) makes the inner-surface hoop stress markedly higher.'},
        ],
    },
    'solid_mechanics.linear_elastic_fracture_mechanics': {
        'law': 'sigma_ij = K/sqrt(2*pi*r)*f_ij(theta); crack-tip stress field scales with the stress intensity factor K.',
        'assumptions': [
            {'name': 'small_scale_yielding', 'regime_variable': 'plastic_zone_to_ligament_ratio', 'valid_when': '< 0.1', 'error_when_violated': 'plastic_zone_to_ligament_ratio', 'generalizes_to': 'elastic_plastic_fracture_j_integral', 'why': 'The K-field assumes the crack-tip plastic zone is tiny relative to crack and ligament; when yielding spreads, K no longer characterizes the field and J-integral/CTOD are required.'},
        ],
    },
    'solid_mechanics.torsion_thin_walled_closed_tube': {
        'law': 'tau = T/(2*A_m*t) (Bredt); shear flow is uniform around a thin closed section.',
        'assumptions': [
            {'name': 'thin_wall_uniform_shear_flow', 'regime_variable': 'thickness_to_radius_ratio', 'valid_when': '< 0.1', 'error_when_violated': 'thickness_to_radius_ratio', 'generalizes_to': 'thick_tube_elasticity_torsion', 'why': 'Bredt assumes shear stress is constant through the wall; as the wall thickens the shear varies across it and the uniform shear-flow approximation loses accuracy.'},
        ],
    },
    'solid_mechanics.hertzian_contact': {
        'law': 'p_0 and contact radius follow elastic half-space contact solutions for smooth non-conforming bodies.',
        'assumptions': [
            {'name': 'small_contact_relative_to_body', 'regime_variable': 'contact_to_radius_ratio', 'valid_when': '< 0.1', 'error_when_violated': 'contact_to_radius_ratio', 'generalizes_to': 'conformal_contact_finite_body_elasticity', 'why': 'Hertz treats each body as an elastic half-space, valid only when the contact patch is small versus the curvature radii; for conforming or large contacts the half-space assumption fails.'},
            {'name': 'elastic_contact_no_yield', 'regime_variable': 'mean_pressure_to_yield_ratio', 'valid_when': '< 1.1', 'error_when_violated': 'mean_pressure_to_yield_ratio - 1', 'generalizes_to': 'elastic_plastic_contact', 'why': 'Hertz assumes both bodies stay elastic; once peak subsurface stress reaches yield, plastic flow flattens the pressure distribution and enlarges the true contact.'},
        ],
    },
    'solid_mechanics.saint_venant_principle_uniform_axial': {
        'law': 'sigma = P/A; axial stress is uniform over the cross-section away from load application.',
        'assumptions': [
            {'name': 'away_from_load_application_point', 'regime_variable': 'distance_to_dimension_ratio', 'valid_when': '>= 1.0', 'error_when_violated': '1/distance_to_dimension_ratio', 'generalizes_to': 'local_stress_concentration_analysis', 'why': 'Uniform P/A holds only at distances beyond about one cross-section dimension from the load; near the load or a discontinuity, stresses concentrate and are highly nonuniform.'},
        ],
    },
    'solid_mechanics.linear_viscoelasticity_boltzmann': {
        'law': 'Small-strain viscoelastic response uses linear Boltzmann superposition of the relaxation modulus.',
        'assumptions': [
            {'name': 'linear_strain_regime', 'regime_variable': 'strain_magnitude', 'valid_when': '< 0.05', 'error_when_violated': 'strain_magnitude', 'generalizes_to': 'nonlinear_viscoelasticity', 'why': 'Boltzmann superposition assumes strain-independent relaxation; at larger strains the modulus becomes strain-dependent and superposition of responses no longer holds.'},
        ],
    },
    'structural_dynamics.linear_vibration': {
        'law': "Restoring force is linear in displacement: F = -k*x, giving equation m*x'' + c*x' + k*x = F(t).",
        'assumptions': [
            {'name': 'small_amplitude', 'regime_variable': 'deflection_ratio', 'valid_when': '< 0.3', 'error_when_violated': 'deflection_ratio**2', 'generalizes_to': 'nonlinear_duffing_oscillator', 'why': 'At large displacement the stiffness curve bends (geometric/material nonlinearity), so force is no longer proportional to displacement.'},
        ],
    },
    'structural_dynamics.undamped_natural_frequency': {
        'law': 'omega_n = sqrt(k/m); damped frequency omega_d = omega_n * sqrt(1 - zeta**2).',
        'assumptions': [
            {'name': 'light_damping', 'regime_variable': 'damping_ratio', 'valid_when': '< 0.3', 'error_when_violated': '0.5*damping_ratio**2', 'generalizes_to': 'damped_natural_frequency', 'why': 'The undamped omega_n overestimates the true oscillation frequency; the shift grows with zeta**2 and vanishes past critical damping.'},
        ],
    },
    'structural_dynamics.modal_superposition': {
        'law': 'Response is a linear sum over modes: x(t) = sum_r phi_r * q_r(t).',
        'assumptions': [
            {'name': 'linearity', 'regime_variable': 'deflection_ratio', 'valid_when': '< 0.3', 'error_when_violated': 'deflection_ratio', 'generalizes_to': 'nonlinear_response_analysis', 'why': 'Superposition holds only for linear systems; large deformation or nonlinear material couples modes and forbids simple summation.'},
        ],
    },
    'structural_dynamics.proportional_damping': {
        'law': 'Damping matrix C = alpha*M + beta*K (Rayleigh), so modes of the undamped system diagonalize C.',
        'assumptions': [
            {'name': 'classical_damping', 'regime_variable': 'nonproportionality_index', 'valid_when': '< 0.1', 'error_when_violated': 'nonproportionality_index', 'generalizes_to': 'nonclassical_damping_complex_modes', 'why': 'When damping is not a linear combination of M and K the modal damping matrix has off-diagonal terms, modes become complex and coupled.'},
        ],
    },
    'structural_dynamics.euler_bernoulli_beam': {
        'law': 'EI * d4w/dx4 = q; beam bending neglecting shear and rotary inertia.',
        'assumptions': [
            {'name': 'slender_beam', 'regime_variable': 'depth_to_length_ratio', 'valid_when': '< 0.1', 'error_when_violated': 'depth_to_length_ratio**2', 'generalizes_to': 'timoshenko_beam', 'why': 'For stubby beams transverse shear deformation and rotary inertia become significant, lowering natural frequencies below Euler-Bernoulli predictions.'},
        ],
    },
    'structural_dynamics.rayleigh_damping': {
        'law': 'Modal damping ratio zeta_r = alpha/(2*omega_r) + beta*omega_r/2.',
        'assumptions': [
            {'name': 'two_mode_calibration', 'regime_variable': 'frequency_span_ratio', 'valid_when': '< 10', 'error_when_violated': '0.1*frequency_span_ratio', 'generalizes_to': 'caughey_series_damping', 'why': 'Rayleigh damping is exact at only two frequencies; over a wide modal band intermediate modes are under-damped and extreme modes over-damped.'},
        ],
    },
    'structural_dynamics.viscous_damping': {
        'law': "Damping force is proportional to velocity: F_d = c * x'.",
        'assumptions': [
            {'name': 'velocity_proportional', 'regime_variable': 'loss_factor', 'valid_when': '< 0.2', 'error_when_violated': 'loss_factor', 'generalizes_to': 'hysteretic_structural_damping', 'why': 'Real material damping is largely rate-independent (hysteretic); the viscous model mispredicts energy loss and frequency dependence when losses are large.'},
        ],
    },
    'structural_dynamics.harmonic_response': {
        'law': 'Steady-state amplitude X = F0/k / sqrt((1-r**2)**2 + (2*zeta*r)**2), r = omega/omega_n.',
        'assumptions': [
            {'name': 'steady_state_only', 'regime_variable': 'transient_decay_ratio', 'valid_when': '< 0.1', 'error_when_violated': 'transient_decay_ratio', 'generalizes_to': 'full_transient_plus_steady_response', 'why': 'The formula ignores the decaying transient; early in the response, or for lightly damped systems, the transient dominates and beats against steady state.'},
        ],
    },
    'structural_dynamics.static_condensation': {
        'law': 'Massless (slave) DOFs are statically condensed: quasi-static relation between master and slave DOFs.',
        'assumptions': [
            {'name': 'negligible_slave_inertia', 'regime_variable': 'frequency_ratio_to_condensed_modes', 'valid_when': '< 0.3', 'error_when_violated': 'frequency_ratio_to_condensed_modes**2', 'generalizes_to': 'dynamic_condensation_craig_bampton', 'why': 'Static condensation ignores inertia of condensed DOFs; near their own resonances the quasi-static assumption fails and stiffness must be frequency-corrected.'},
        ],
    },
    'structural_dynamics.linear_buckling_eigenvalue': {
        'law': 'Critical load from linear eigenproblem (K + lambda*K_g)*phi = 0; frequency-load interaction linear.',
        'assumptions': [
            {'name': 'small_prebuckling_deflection', 'regime_variable': 'load_to_critical_ratio', 'valid_when': '< 0.7', 'error_when_violated': 'load_to_critical_ratio**2', 'generalizes_to': 'nonlinear_geometric_buckling', 'why': 'Linear buckling assumes deflections stay small until bifurcation; imperfections and large prebuckling deformation reduce the true critical load.'},
        ],
    },
    'structural_dynamics.string_taut_wave': {
        'law': 'Transverse wave speed c = sqrt(T/rho_L); frequencies f_n = n*c/(2*L).',
        'assumptions': [
            {'name': 'negligible_bending_stiffness', 'regime_variable': 'bending_to_tension_parameter', 'valid_when': '< 0.01', 'error_when_violated': 'bending_to_tension_parameter', 'generalizes_to': 'stiff_string_beam_with_tension', 'why': 'For thick or high-modulus wires bending stiffness raises higher harmonics above ideal-string values (inharmonicity).'},
        ],
    },
    'structural_dynamics.constant_modal_parameters': {
        'law': 'Natural frequencies and mode shapes are constant, independent of excitation amplitude.',
        'assumptions': [
            {'name': 'amplitude_independent_stiffness', 'regime_variable': 'strain_amplitude_ratio', 'valid_when': '< 0.3', 'error_when_violated': 'strain_amplitude_ratio**2', 'generalizes_to': 'amplitude_dependent_nonlinear_modes', 'why': 'With geometric or contact nonlinearity effective stiffness varies with amplitude, so resonant frequencies drift (softening/hardening) with drive level.'},
        ],
    },
    'structural_dynamics.small_rotation_kinematics': {
        'law': 'Rotations treated as vectors; sin(theta) ~ theta, cos(theta) ~ 1 in stiffness assembly.',
        'assumptions': [
            {'name': 'small_rotation', 'regime_variable': 'rotation_angle_rad', 'valid_when': '< 0.1', 'error_when_violated': 'rotation_angle_rad**2/6', 'generalizes_to': 'finite_rotation_corotational_formulation', 'why': 'Large rotations are non-additive and non-vectorial; linearized kinematics introduce spurious strains and stiffness errors.'},
        ],
    },
    'structural_dynamics.linear_material_hooke': {
        'law': 'Stress proportional to strain: sigma = E*epsilon within the structure.',
        'assumptions': [
            {'name': 'elastic_limit', 'regime_variable': 'stress_ratio', 'valid_when': '< 1.0', 'error_when_violated': 'stress_ratio - 1', 'generalizes_to': 'elastoplastic_material_model', 'why': 'Beyond yield the stress-strain curve flattens; linear elasticity overpredicts stiffness and stress and ignores permanent deformation.'},
        ],
    },
    'structural_dynamics.lumped_mass_model': {
        'law': 'Distributed mass replaced by discrete point masses at nodes (diagonal mass matrix).',
        'assumptions': [
            {'name': 'coarse_wavelength', 'regime_variable': 'element_to_wavelength_ratio', 'valid_when': '< 0.1', 'error_when_violated': 'element_to_wavelength_ratio**2', 'generalizes_to': 'consistent_mass_matrix', 'why': 'When mesh elements are not small vs the modal wavelength, lumping misrepresents inertia distribution and biases high-frequency modes.'},
        ],
    },
    'structural_dynamics.base_excitation_transmissibility': {
        'law': 'Transmissibility TR = sqrt((1+(2*zeta*r)**2)/((1-r**2)**2+(2*zeta*r)**2)).',
        'assumptions': [
            {'name': 'rigid_base_single_dof', 'regime_variable': 'mass_ratio', 'valid_when': '< 0.05', 'error_when_violated': 'mass_ratio', 'generalizes_to': 'coupled_two_dof_isolation', 'why': 'Assumes the mounted mass does not react back on an infinite base; a compliant or comparable-mass base couples the two and shifts isolation.'},
        ],
    },
    'structural_dynamics.rayleigh_quotient_frequency': {
        'law': 'omega_n**2 ~ (phi^T K phi)/(phi^T M phi) using an assumed mode shape.',
        'assumptions': [
            {'name': 'accurate_trial_shape', 'regime_variable': 'shape_error_ratio', 'valid_when': '< 0.1', 'error_when_violated': 'shape_error_ratio**2', 'generalizes_to': 'rayleigh_ritz_multimode', 'why': 'The estimate is an upper bound whose error is second order in the shape error; a poor trial function inflates the predicted frequency.'},
        ],
    },
    'structural_dynamics.plane_stress_thin_plate': {
        'law': 'Kirchhoff plate: transverse shear neglected, D*grad4(w) = q.',
        'assumptions': [
            {'name': 'thin_plate', 'regime_variable': 'thickness_to_span_ratio', 'valid_when': '< 0.05', 'error_when_violated': 'thickness_to_span_ratio**2', 'generalizes_to': 'mindlin_reissner_thick_plate', 'why': 'Thick plates carry transverse shear deformation that Kirchhoff theory omits, overestimating stiffness and modal frequencies.'},
        ],
    },
    'materials_science.linear_elasticity_hooke': {
        'law': 'sigma = E * strain (stress linearly proportional to strain via constant modulus)',
        'assumptions': [
            {'name': 'small_strain', 'regime_variable': 'strain', 'valid_when': '< 0.02', 'error_when_violated': 'strain', 'generalizes_to': 'hyperelasticity_finite_strain', 'why': 'At finite strain the stress-strain curve stiffens/softens and geometric nonlinearity makes E no longer constant.'},
        ],
    },
    'materials_science.isotropic_elasticity': {
        'law': 'Stiffness described by two constants (E, nu) identical in all directions',
        'assumptions': [
            {'name': 'isotropy', 'regime_variable': 'anisotropy_index', 'valid_when': '< 0.2', 'error_when_violated': 'anisotropy_index', 'generalizes_to': 'anisotropic_elasticity_tensor', 'why': 'Single crystals and textured/composite materials have direction-dependent stiffness (Zener ratio != 1), so a scalar modulus mispredicts off-axis response.'},
        ],
    },
    'materials_science.temperature_independent_modulus': {
        'law': 'Elastic modulus E treated as constant, independent of temperature',
        'assumptions': [
            {'name': 'constant_modulus', 'regime_variable': 'homologous_temperature', 'valid_when': '< 0.3', 'error_when_violated': 'homologous_temperature', 'generalizes_to': 'temperature_dependent_elasticity', 'why': 'Interatomic bond stiffness weakens as T approaches melting, so modulus drops substantially at high homologous temperature.'},
        ],
    },
    'materials_science.infinitesimal_strain_kinematics': {
        'law': 'strain = 0.5*(grad u + grad u^T) (linearized strain measure)',
        'assumptions': [
            {'name': 'small_rotation', 'regime_variable': 'rotation_angle', 'valid_when': '< 0.1', 'error_when_violated': '0.5*rotation_angle**2', 'generalizes_to': 'finite_strain_green_lagrange', 'why': 'Large rotations inject spurious strain into the linearized measure; only the finite-strain tensor stays objective.'},
        ],
    },
    'materials_science.linear_thermal_expansion': {
        'law': 'thermal_strain = alpha * delta_T with constant alpha',
        'assumptions': [
            {'name': 'constant_cte', 'regime_variable': 'homologous_temperature', 'valid_when': '< 0.4', 'error_when_violated': 'homologous_temperature', 'generalizes_to': 'nonlinear_thermal_expansion', 'why': 'The coefficient of thermal expansion rises with temperature (anharmonic lattice vibrations), so a constant alpha under-predicts expansion at high T.'},
        ],
    },
    'materials_science.linear_elastic_fracture_mechanics': {
        'law': 'Crack driving force set by stress intensity K; K = Kc at fracture',
        'assumptions': [
            {'name': 'small_scale_yielding', 'regime_variable': 'plastic_zone_ratio', 'valid_when': '< 0.1', 'error_when_violated': 'plastic_zone_ratio', 'generalizes_to': 'elastic_plastic_fracture_mechanics_j_integral', 'why': 'When the plastic zone is not tiny relative to crack length, the K-field no longer governs the crack tip and J-integral/CTOD are required.'},
        ],
    },
    'materials_science.rate_independent_plasticity': {
        'law': 'Yield stress independent of strain rate; flow governed by rate-free yield surface',
        'assumptions': [
            {'name': 'quasi_static', 'regime_variable': 'strain_rate_sensitivity', 'valid_when': '< 0.05', 'error_when_violated': 'strain_rate_sensitivity', 'generalizes_to': 'viscoplasticity', 'why': 'At high strain rate or high temperature the flow stress rises with rate (thermally activated dislocation motion), breaking rate independence.'},
        ],
    },
    'materials_science.hall_petch_strengthening': {
        'law': 'yield_stress = sigma0 + k / sqrt(grain_size) (strength rises as grains shrink)',
        'assumptions': [
            {'name': 'dislocation_pileup', 'regime_variable': 'grain_size_nm', 'valid_when': '> 20', 'error_when_violated': '20/grain_size_nm', 'generalizes_to': 'inverse_hall_petch_gb_sliding', 'why': 'Below ~10-20 nm too few dislocations fit to form pileups; grain-boundary sliding takes over and strengthening reverses.'},
        ],
    },
    'materials_science.fickian_diffusion': {
        'law': 'flux = -D * grad(c) with constant diffusivity D',
        'assumptions': [
            {'name': 'constant_diffusivity', 'regime_variable': 'concentration_fraction', 'valid_when': '< 0.1', 'error_when_violated': 'concentration_fraction', 'generalizes_to': 'concentration_dependent_diffusion', 'why': 'At high concentration D varies with c (thermodynamic factor, site blocking), so the linear Fickian form breaks down.'},
        ],
    },
    'materials_science.fourier_heat_conduction': {
        'law': 'heat_flux = -k * grad(T) (diffusive conduction with constant k)',
        'assumptions': [
            {'name': 'diffusive_transport', 'regime_variable': 'knudsen', 'valid_when': '< 0.1', 'error_when_violated': 'knudsen', 'generalizes_to': 'phonon_boltzmann_transport', 'why': "When phonon mean free path approaches the sample size (thin films, nanostructures) transport becomes ballistic and Fourier's law over-predicts conductivity."},
        ],
    },
    'materials_science.dulong_petit_heat_capacity': {
        'law': 'molar heat capacity Cv = 3R (classical constant value)',
        'assumptions': [
            {'name': 'classical_limit', 'regime_variable': 'debye_temperature_ratio', 'valid_when': '> 1', 'error_when_violated': '1/debye_temperature_ratio**2', 'generalizes_to': 'debye_heat_capacity', 'why': 'Below the Debye temperature phonon modes freeze out quantum-mechanically and Cv falls toward zero as T^3, not the constant 3R.'},
        ],
    },
    'materials_science.linear_viscoelasticity': {
        'law': 'Stress = convolution of relaxation modulus with strain rate (Boltzmann superposition)',
        'assumptions': [
            {'name': 'small_strain_superposition', 'regime_variable': 'strain', 'valid_when': '< 0.01', 'error_when_violated': 'strain', 'generalizes_to': 'nonlinear_viscoelasticity', 'why': 'Beyond small strain the relaxation modulus itself becomes strain-dependent, so linear superposition of responses no longer holds.'},
        ],
    },
    'materials_science.diffusional_creep_linear': {
        'law': 'Nabarro-Herring/Coble creep: strain_rate proportional to stress (n=1)',
        'assumptions': [
            {'name': 'linear_viscous_creep', 'regime_variable': 'stress_ratio', 'valid_when': '< 1', 'error_when_violated': 'stress_ratio**3', 'generalizes_to': 'power_law_dislocation_creep', 'why': 'Above a transition stress dislocation-climb creep dominates with stress exponent n~3-5, so the linear diffusional law grossly under-predicts creep rate.'},
        ],
    },
    'materials_science.paris_law_fatigue': {
        'law': 'da/dN = C * (delta_K)^m (power-law fatigue crack growth)',
        'assumptions': [
            {'name': 'stable_growth_regime', 'regime_variable': 'stress_intensity_ratio', 'valid_when': '< 0.7', 'error_when_violated': 'stress_intensity_ratio', 'generalizes_to': 'threshold_and_fast_fracture_regimes', 'why': 'Near Kmax approaching fracture toughness, growth accelerates faster than the Paris power law as static fracture modes intervene.'},
        ],
    },
    'materials_science.griffith_brittle_fracture': {
        'law': 'fracture_stress = sqrt(2*E*gamma_s / (pi*a)) (energy balance with only surface energy)',
        'assumptions': [
            {'name': 'no_plastic_dissipation', 'regime_variable': 'plastic_to_surface_energy_ratio', 'valid_when': '< 0.1', 'error_when_violated': 'plastic_to_surface_energy_ratio', 'generalizes_to': 'orowan_irwin_ductile_fracture', 'why': 'In metals plastic work at the crack tip dwarfs surface energy, so Griffith badly under-predicts the fracture stress unless the plastic term is added.'},
        ],
    },
    'fracture_fatigue.lefm_stress_intensity': {
        'law': 'Crack-tip fields scale as K_I/sqrt(2*pi*r); fracture when K_I = K_IC',
        'assumptions': [
            {'name': 'small_scale_yielding', 'regime_variable': 'plastic_zone_ratio', 'valid_when': '< 0.1', 'error_when_violated': 'plastic_zone_ratio', 'generalizes_to': 'elastic_plastic_fracture_mechanics_J_integral', 'why': 'When the crack-tip plastic zone is not small vs crack/ligament, the elastic K-annulus vanishes and a single elastic parameter no longer sets the tip state.'},
        ],
    },
    'fracture_fatigue.k_dominance_single_parameter': {
        'law': 'Near-tip stresses = (K/sqrt(2*pi*r))*f(theta), one-parameter characterization',
        'assumptions': [
            {'name': 'high_constraint', 'regime_variable': 'biaxiality_ratio', 'valid_when': '< 0.2', 'error_when_violated': 'biaxiality_ratio', 'generalizes_to': 'two_parameter_J_T_or_J_Q', 'why': 'A non-negligible T-stress/Q shifts crack-tip triaxiality, so K (or J) alone no longer fixes the field driving fracture.'},
        ],
    },
    'fracture_fatigue.plane_strain_fracture_toughness': {
        'law': 'K_IC is a material constant; fracture at K_I = K_IC',
        'assumptions': [
            {'name': 'plane_strain_constraint', 'regime_variable': 'constraint_ratio', 'valid_when': '< 1.0', 'error_when_violated': 'constraint_ratio', 'generalizes_to': 'plane_stress_toughness_R_curve', 'why': 'Thin sections (B < 2.5*(K/sigma_y)^2) lose through-thickness constraint, raising apparent toughness and making it thickness-dependent (R-curve).'},
        ],
    },
    'fracture_fatigue.griffith_brittle_fracture': {
        'law': 'sigma_f = sqrt(2*E*gamma_s/(pi*a))',
        'assumptions': [
            {'name': 'ideal_brittle', 'regime_variable': 'plastic_to_surface_energy_ratio', 'valid_when': '< 0.1', 'error_when_violated': 'plastic_to_surface_energy_ratio', 'generalizes_to': 'irwin_orowan_energy_release', 'why': 'Any crack-tip plasticity adds plastic work far exceeding surface energy, so pure surface-energy Griffith drastically underpredicts fracture stress.'},
        ],
    },
    'fracture_fatigue.paris_law': {
        'law': 'da/dN = C*(delta_K)^m',
        'assumptions': [
            {'name': 'above_threshold', 'regime_variable': 'delta_k_over_threshold', 'valid_when': '> 2', 'error_when_violated': '1/delta_k_over_threshold', 'generalizes_to': 'near_threshold_nasgro', 'why': 'As delta_K approaches delta_K_th growth rate drops far below the Paris power law, so extrapolation grossly overpredicts near-threshold life.'},
            {'name': 'below_fast_fracture', 'regime_variable': 'kmax_over_kic', 'valid_when': '< 0.7', 'error_when_violated': 'kmax_over_kic/(1-kmax_over_kic)', 'generalizes_to': 'forman_equation_region_III', 'why': 'As K_max approaches K_IC growth accelerates toward instability, diverging above the Paris trend (Region III).'},
            {'name': 'closure_free_constant_R', 'regime_variable': 'stress_ratio_r', 'valid_when': '>= 0.5', 'error_when_violated': '0.5*(1-stress_ratio_r)', 'generalizes_to': 'walker_or_elber_closure', 'why': 'At low or negative R, crack closure reduces the effective delta_K, so a single C,m calibrated at one R misestimates growth.'},
        ],
    },
    'fracture_fatigue.basquin_high_cycle': {
        'law': 'sigma_a = sigma_f_prime*(2*N_f)^b',
        'assumptions': [
            {'name': 'elastic_dominated', 'regime_variable': 'plastic_strain_ratio', 'valid_when': '< 0.1', 'error_when_violated': 'plastic_strain_ratio', 'generalizes_to': 'coffin_manson_low_cycle', 'why': 'In low-cycle fatigue plastic strain dominates and the stress-life power law underpredicts damage; strain-life is required.'},
            {'name': 'zero_mean_stress', 'regime_variable': 'mean_stress_ratio', 'valid_when': '< 0.1', 'error_when_violated': 'mean_stress_ratio', 'generalizes_to': 'goodman_gerber_walker', 'why': 'A tensile mean stress lowers the endurance limit; ignoring it non-conservatively overpredicts life.'},
        ],
    },
    'fracture_fatigue.long_crack_threshold': {
        'law': 'Fatigue crack grows only when delta_K > delta_K_th (constant threshold)',
        'assumptions': [
            {'name': 'long_crack', 'regime_variable': 'intrinsic_length_over_crack', 'valid_when': '< 0.1', 'error_when_violated': 'intrinsic_length_over_crack', 'generalizes_to': 'el_haddad_kitagawa_short_crack', 'why': 'Short cracks (a ~ a_0) grow below the long-crack threshold because closure is not fully developed; LEFM threshold is non-conservative.'},
        ],
    },
    'fracture_fatigue.isothermal_fatigue': {
        'law': 'Crack growth per cycle is frequency- and hold-time independent',
        'assumptions': [
            {'name': 'no_creep', 'regime_variable': 'homologous_temperature', 'valid_when': '< 0.4', 'error_when_violated': 'homologous_temperature', 'generalizes_to': 'creep_fatigue_interaction', 'why': 'Above ~0.4 T_melt, time-dependent creep and oxidation at holds add damage per cycle beyond the cyclic-plasticity mechanism.'},
        ],
    },
    'fracture_fatigue.elastic_notch_stress': {
        'law': 'Local peak stress = K_t*sigma_nominal (linear elastic)',
        'assumptions': [
            {'name': 'elastic_notch', 'regime_variable': 'net_yield_ratio', 'valid_when': '< 1.0', 'error_when_violated': 'net_yield_ratio', 'generalizes_to': 'neuber_rule_local_plasticity', 'why': 'Once local stress reaches yield, notch-root plasticity redistributes stress and K_t overpredicts true local stress (Neuber/Glinka needed).'},
        ],
    },
    'fracture_fatigue.linear_damage_accumulation': {
        'law': "Failure when sum(n_i/N_i) = 1 (Miner's rule)",
        'assumptions': [
            {'name': 'sequence_independent', 'regime_variable': 'overload_ratio', 'valid_when': '< 1.2', 'error_when_violated': 'overload_ratio-1', 'generalizes_to': 'nonlinear_damage_or_retardation', 'why': 'Overloads induce compressive residual stresses and retardation, so damage accumulates nonlinearly and load order matters, breaking linear summation.'},
        ],
    },
    'fracture_fatigue.j_controlled_growth': {
        'law': 'J-integral characterizes elastic-plastic crack-tip fields (HRR)',
        'assumptions': [
            {'name': 'deformation_plasticity_proportional_loading', 'regime_variable': 'crack_growth_ratio', 'valid_when': '< 0.06', 'error_when_violated': 'crack_growth_ratio', 'generalizes_to': 'j_resistance_curve_with_T_J', 'why': 'J assumes proportional loading (no unloading); significant crack extension causes local elastic unloading that violates deformation-theory plasticity.'},
        ],
    },
    'fracture_fatigue.irwin_plastic_zone_correction': {
        'law': 'Effective crack length a_eff = a + r_p with r_p = (1/(2*pi))*(K/sigma_y)^2',
        'assumptions': [
            {'name': 'contained_yielding', 'regime_variable': 'ligament_yield_ratio', 'valid_when': '< 0.2', 'error_when_violated': 'ligament_yield_ratio', 'generalizes_to': 'dugdale_barenblatt_strip_yield', 'why': 'The first-order Irwin correction assumes the plastic zone is a small local perturbation; with gross-section yielding a strip-yield/EPFM treatment is required.'},
        ],
    },
    'electromagnetism.quasistatic_approximation': {
        'law': 'Neglect displacement current: curl(H) = J, so fields respond instantaneously with no wave propagation.',
        'assumptions': [
            {'name': 'quasistatic', 'regime_variable': 'electrical_size', 'valid_when': '< 0.3', 'error_when_violated': 'electrical_size**2', 'generalizes_to': 'full_maxwell_wave_equations', 'why': 'Once the system size L approaches a wavelength, the displacement current dD/dt rivals conduction current and radiation/retardation appear.'},
        ],
    },
    'electromagnetism.magnetostatics': {
        'law': 'Time-independent magnetic field: curl(B) = mu0*J, div(B) = 0, with no induced EMF.',
        'assumptions': [
            {'name': 'steady_current', 'regime_variable': 'electrical_size', 'valid_when': '< 0.3', 'error_when_violated': 'electrical_size**2', 'generalizes_to': 'electrodynamics_with_faraday_induction', 'why': 'Time-varying currents produce dB/dt and induced electric fields (Faraday) that magnetostatics ignores.'},
        ],
    },
    'electromagnetism.electrostatics_coulomb': {
        'law': 'E = q/(4*pi*eps0*r**2) with curl(E)=0 for charges at rest.',
        'assumptions': [
            {'name': 'static_charges', 'regime_variable': 'beta', 'valid_when': '< 0.1', 'error_when_violated': 'beta**2', 'generalizes_to': 'lienard_wiechert_retarded_potentials', 'why': 'Moving and accelerating charges generate magnetic fields and retarded potentials, negligible only when source speeds are far below c.'},
        ],
    },
    'electromagnetism.ohms_law_linear': {
        'law': 'J = sigma*E with a field-independent conductivity.',
        'assumptions': [
            {'name': 'linear_conduction', 'regime_variable': 'field_ratio', 'valid_when': '< 0.3', 'error_when_violated': 'field_ratio**2', 'generalizes_to': 'nonlinear_hot_carrier_conduction', 'why': 'At high fields carrier drift velocity saturates and mobility becomes field-dependent (hot electrons, breakdown).'},
        ],
    },
    'electromagnetism.dc_conductivity': {
        'law': 'sigma(omega) = sigma0, frequency-independent Ohmic conductor.',
        'assumptions': [
            {'name': 'collision_dominated', 'regime_variable': 'omega_tau', 'valid_when': '< 0.3', 'error_when_violated': 'omega_tau**2', 'generalizes_to': 'drude_ac_conductivity', 'why': 'Above the inverse collision time the carrier inertia makes conductivity complex and frequency dependent.'},
        ],
    },
    'electromagnetism.linear_dielectric': {
        'law': 'D = eps*E with a constant permittivity.',
        'assumptions': [
            {'name': 'linear_polarization', 'regime_variable': 'field_ratio', 'valid_when': '< 0.3', 'error_when_violated': 'field_ratio**2', 'generalizes_to': 'nonlinear_optics', 'why': 'At intense fields the polarization saturates and higher-order susceptibilities (Kerr, harmonic generation) contribute.'},
        ],
    },
    'electromagnetism.linear_magnetization': {
        'law': 'B = mu*H with a constant permeability.',
        'assumptions': [
            {'name': 'unsaturated_linear_media', 'regime_variable': 'h_ratio', 'valid_when': '< 0.3', 'error_when_violated': 'h_ratio', 'generalizes_to': 'ferromagnetic_saturation_hysteresis', 'why': 'Magnetic domains saturate as H rises, so permeability falls and the B-H relation becomes hysteretic and nonlinear.'},
        ],
    },
    'electromagnetism.lossless_dielectric': {
        'law': 'Wave number k = omega*sqrt(mu*eps), real, with no attenuation.',
        'assumptions': [
            {'name': 'lossless_media', 'regime_variable': 'loss_tangent', 'valid_when': '< 0.1', 'error_when_violated': 'loss_tangent', 'generalizes_to': 'lossy_media_complex_permittivity', 'why': 'Finite conductivity adds an imaginary permittivity, attenuating the wave once conduction current rivals displacement current.'},
        ],
    },
    'electromagnetism.uniform_current_conductor': {
        'law': 'Current spreads uniformly over the cross-section: R = rho*L/A (DC resistance).',
        'assumptions': [
            {'name': 'no_skin_effect', 'regime_variable': 'radius_over_skin_depth', 'valid_when': '< 0.3', 'error_when_violated': 'radius_over_skin_depth**2', 'generalizes_to': 'skin_effect_ac_resistance', 'why': 'AC fields are expelled from the conductor interior, crowding current into a surface layer of thickness delta and raising resistance.'},
        ],
    },
    'electromagnetism.perfect_conductor': {
        'law': 'E = 0 inside, fields fully excluded, only surface currents and no Ohmic loss.',
        'assumptions': [
            {'name': 'infinite_conductivity', 'regime_variable': 'skin_depth_over_size', 'valid_when': '< 0.1', 'error_when_violated': 'skin_depth_over_size', 'generalizes_to': 'finite_conductivity_surface_impedance', 'why': 'Finite conductivity lets fields penetrate a depth delta and dissipates power through surface impedance.'},
        ],
    },
    'electromagnetism.lumped_circuit': {
        'law': "Kirchhoff's laws with lumped R, L, C; voltage and current uniform along a wire.",
        'assumptions': [
            {'name': 'lumped_element', 'regime_variable': 'electrical_size', 'valid_when': '< 0.1', 'error_when_violated': 'electrical_size**2', 'generalizes_to': 'transmission_line_distributed_theory', 'why': 'When device size approaches a wavelength, propagation delay makes voltage and current position-dependent along the conductor.'},
        ],
    },
    'electromagnetism.far_field_radiation': {
        'law': 'Radiated fields fall as 1/r and form locally plane, radiating waves.',
        'assumptions': [
            {'name': 'far_field', 'regime_variable': 'inverse_kr', 'valid_when': '< 0.1', 'error_when_violated': 'inverse_kr', 'generalizes_to': 'near_field_reactive_zone', 'why': 'Close to the source the reactive 1/r**2 and 1/r**3 terms dominate over the radiative 1/r term.'},
        ],
    },
    'electromagnetism.electric_dipole_approximation': {
        'law': 'Field of a source captured by its lowest-order (dipole) moment only.',
        'assumptions': [
            {'name': 'point_dipole', 'regime_variable': 'source_size_ratio', 'valid_when': '< 0.3', 'error_when_violated': 'source_size_ratio', 'generalizes_to': 'multipole_expansion', 'why': 'When the source extent is not small versus distance or wavelength, quadrupole and higher moments contribute.'},
        ],
    },
    'electromagnetism.paraxial_approximation': {
        'law': 'Paraxial Helmholtz / ABCD ray transfer with sin(theta) ~ theta.',
        'assumptions': [
            {'name': 'small_angle', 'regime_variable': 'ray_angle', 'valid_when': '< 0.3', 'error_when_violated': 'ray_angle**2', 'generalizes_to': 'nonparaxial_vector_wave_optics', 'why': 'At large angles sin(theta) departs from theta, producing aberration and vector-field coupling the paraxial model omits.'},
        ],
    },
    'electromagnetism.geometric_optics': {
        'law': 'Light travels as rays along the eikonal; diffraction is ignored.',
        'assumptions': [
            {'name': 'short_wavelength', 'regime_variable': 'diffraction_ratio', 'valid_when': '< 0.1', 'error_when_violated': 'diffraction_ratio', 'generalizes_to': 'wave_optics_diffraction', 'why': 'When wavelength is comparable to aperture or feature size, diffraction spreads and interferes with the ray prediction.'},
        ],
    },
    'electromagnetism.local_constitutive_response': {
        'law': 'Response is local: D(r) = eps*E(r) at the same point.',
        'assumptions': [
            {'name': 'no_spatial_dispersion', 'regime_variable': 'em_knudsen', 'valid_when': '< 0.1', 'error_when_violated': 'em_knudsen', 'generalizes_to': 'nonlocal_spatially_dispersive_media', 'why': 'When the carrier mean free path is comparable to the scale of field variation, the response at a point depends on E over a surrounding region.'},
        ],
    },
    'electromagnetism.flux_freezing': {
        'law': 'Magnetic field is frozen into a perfectly conducting fluid, moving with it (ideal MHD).',
        'assumptions': [
            {'name': 'negligible_magnetic_diffusion', 'regime_variable': 'magnetic_reynolds', 'valid_when': '> 1e2', 'error_when_violated': '1/magnetic_reynolds', 'generalizes_to': 'resistive_mhd_diffusion', 'why': 'Finite resistivity lets the magnetic field diffuse through and slip relative to the conducting fluid, breaking flux conservation.'},
        ],
    },
    'circuit_theory.lumped_element_model': {
        'law': 'Circuit elements are described by terminal V-I relations with no internal spatial dependence; voltages and currents are single-valued along a wire at any instant.',
        'assumptions': [
            {'name': 'lumped', 'regime_variable': 'electrical_length', 'valid_when': '< 0.1', 'error_when_violated': '6.28*electrical_length', 'generalizes_to': 'distributed_circuit_transmission_line_theory', 'why': 'When physical size approaches the signal wavelength, phase varies appreciably across the element and propagation delay makes V and I position-dependent.'},
        ],
    },
    'circuit_theory.kvl_quasistatic': {
        'law': "Kirchhoff's voltage law: the sum of branch voltages around any closed loop is zero.",
        'assumptions': [
            {'name': 'negligible_time_varying_flux', 'regime_variable': 'electrical_length', 'valid_when': '< 0.1', 'error_when_violated': '6.28*electrical_length', 'generalizes_to': 'faraday_induction_law', 'why': "KVL is the quasi-static limit of Faraday's law; a time-varying magnetic flux threading the loop adds an induced EMF so the loop sum is no longer zero."},
        ],
    },
    'circuit_theory.small_signal_diode': {
        'law': 'Diode conductance is linearized about its bias point: g = I_Q/V_T, so i_ac = g * v_ac.',
        'assumptions': [
            {'name': 'small_signal', 'regime_variable': 'signal_ratio', 'valid_when': '< 0.1', 'error_when_violated': '0.5*signal_ratio', 'generalizes_to': 'large_signal_shockley_equation', 'why': 'The Shockley exponential is only linear over swings small versus the thermal voltage V_T; larger swings excite quadratic and higher exp terms.'},
        ],
    },
    'circuit_theory.ohms_law_linear': {
        'law': 'Current is proportional to voltage across a resistor: V = I*R with R constant.',
        'assumptions': [
            {'name': 'linear_ohmic', 'regime_variable': 'field_ratio', 'valid_when': '< 1', 'error_when_violated': 'field_ratio', 'generalizes_to': 'nonlinear_conduction', 'why': 'At high fields carrier velocity saturates and resistivity becomes field-dependent, breaking the constant-R proportionality.'},
        ],
    },
    'circuit_theory.ideal_capacitor': {
        'law': 'A capacitor is a pure reactance: impedance Z = 1/(jwC) with no real (dissipative) part.',
        'assumptions': [
            {'name': 'lossless_dielectric', 'regime_variable': 'loss_tangent', 'valid_when': '< 0.01', 'error_when_violated': 'loss_tangent', 'generalizes_to': 'lossy_capacitor_model', 'why': 'Real dielectrics have finite conductivity and polarization loss (tan delta), adding an in-phase resistive current the ideal model omits.'},
        ],
    },
    'circuit_theory.ideal_inductor': {
        'law': 'An inductor is a pure reactance: impedance Z = jwL with no series resistance.',
        'assumptions': [
            {'name': 'lossless_winding', 'regime_variable': 'dissipation_factor', 'valid_when': '< 0.01', 'error_when_violated': 'dissipation_factor', 'generalizes_to': 'lossy_inductor_model', 'why': 'Winding and core losses give finite quality factor Q; the dissipation factor 1/Q is the neglected in-phase resistive term.'},
        ],
    },
    'circuit_theory.ideal_opamp': {
        'law': 'With infinite open-loop gain, the op-amp enforces a virtual short (v+ = v-) and closed-loop gain is set solely by the feedback network.',
        'assumptions': [
            {'name': 'infinite_loop_gain', 'regime_variable': 'inverse_loop_gain', 'valid_when': '< 0.01', 'error_when_violated': 'inverse_loop_gain', 'generalizes_to': 'finite_gain_opamp_model', 'why': 'Finite loop gain A*beta leaves a nonzero differential input; gain error scales as 1/(A*beta), and bandwidth further erodes gain with frequency.'},
        ],
    },
    'circuit_theory.dc_resistance_uniform_current': {
        'law': 'Conductor resistance is R = rho*L/A assuming current density is uniform across the cross-section.',
        'assumptions': [
            {'name': 'no_skin_effect', 'regime_variable': 'skin_ratio', 'valid_when': '< 1', 'error_when_violated': '0.25*skin_ratio', 'generalizes_to': 'skin_effect_resistance', 'why': 'At high frequency current crowds into a surface layer of thickness delta; when the radius exceeds delta the effective area shrinks and AC resistance rises.'},
        ],
    },
    'circuit_theory.ideal_transformer': {
        'law': 'Voltage and current transform by the turns ratio with perfect coupling: V1/V2 = N1/N2 and no leakage.',
        'assumptions': [
            {'name': 'perfect_coupling', 'regime_variable': 'coupling_coefficient', 'valid_when': '>= 1', 'error_when_violated': '1-coupling_coefficient', 'generalizes_to': 'real_transformer_leakage_model', 'why': 'Coupling coefficient k<1 means some flux does not link both windings, introducing leakage inductance and departing from the ideal ratio.'},
        ],
    },
    'circuit_theory.lossless_transmission_line': {
        'law': 'A transmission line has real characteristic impedance Z0 = sqrt(L/C) and undistorted, lossless propagation.',
        'assumptions': [
            {'name': 'lossless_line', 'regime_variable': 'loss_ratio', 'valid_when': '< 0.01', 'error_when_violated': 'loss_ratio', 'generalizes_to': 'lossy_telegrapher_line', 'why': 'Finite series R and shunt G (relative to wL) attenuate and disperse the wave, making Z0 complex and propagation frequency-dependent.'},
        ],
    },
    'circuit_theory.ideal_component_no_parasitics': {
        'law': 'A component behaves as its single nominal element (pure R, L, or C) across frequency.',
        'assumptions': [
            {'name': 'negligible_parasitics', 'regime_variable': 'frequency_ratio', 'valid_when': '< 0.1', 'error_when_violated': 'frequency_ratio**2', 'generalizes_to': 'parasitic_equivalent_circuit', 'why': 'Every real part has parasitic L and C that produce a self-resonance; approaching that frequency the impedance departs sharply from the nominal element.'},
        ],
    },
    'circuit_theory.constant_resistivity': {
        'law': 'Resistance is temperature-independent and equal to its nominal value.',
        'assumptions': [
            {'name': 'isothermal_no_self_heating', 'regime_variable': 'temp_rise_ratio', 'valid_when': '< 0.1', 'error_when_violated': 'temp_rise_ratio', 'generalizes_to': 'temperature_dependent_resistance', 'why': 'Resistivity varies as alpha*deltaT; Joule self-heating at high power shifts R away from its cold nominal value.'},
        ],
    },
    'circuit_theory.parallel_plate_capacitance': {
        'law': 'Capacitance of parallel plates is C = eps*A/d with a uniform field confined between the plates.',
        'assumptions': [
            {'name': 'no_fringing', 'regime_variable': 'gap_ratio', 'valid_when': '< 0.1', 'error_when_violated': 'gap_ratio', 'generalizes_to': 'fringing_field_capacitance', 'why': 'When plate separation is not tiny versus plate size, field lines bulge past the edges and add fringing capacitance beyond eps*A/d.'},
        ],
    },
    'circuit_theory.linear_time_invariant': {
        'law': 'Network response obeys superposition and its parameters do not change in time (LTI transfer function applies).',
        'assumptions': [
            {'name': 'time_invariant', 'regime_variable': 'parameter_modulation_ratio', 'valid_when': '< 0.1', 'error_when_violated': 'parameter_modulation_ratio', 'generalizes_to': 'linear_time_varying_or_nonlinear_network', 'why': 'Switched, mixing, or bias-modulated elements change value within a cycle, generating new frequencies that an LTI transfer function cannot represent.'},
        ],
    },
    'circuit_theory.small_signal_bjt': {
        'law': 'Transistor transconductance is linearized about bias: ic = gm*vbe with gm = IC/V_T.',
        'assumptions': [
            {'name': 'small_signal', 'regime_variable': 'signal_ratio', 'valid_when': '< 0.1', 'error_when_violated': '0.5*signal_ratio', 'generalizes_to': 'large_signal_ebers_moll', 'why': 'The exponential IC-VBE law is only linear for base swings small versus V_T; larger drive introduces harmonic distortion and clipping.'},
        ],
    },
    'circuit_theory.ideal_voltage_source': {
        'law': 'An ideal voltage source holds its terminal voltage fixed regardless of load current.',
        'assumptions': [
            {'name': 'zero_output_impedance', 'regime_variable': 'source_impedance_ratio', 'valid_when': '< 0.01', 'error_when_violated': 'source_impedance_ratio', 'generalizes_to': 'thevenin_source_with_internal_resistance', 'why': 'Real sources have finite internal impedance; when it is not tiny versus the load, terminal voltage droops with drawn current.'},
        ],
    },
    'electric_machines.magnetic_circuit_linear': {
        'law': 'B = mu*H with constant permeability, so flux phi = MMF / reluctance (linear magnetic circuit).',
        'assumptions': [
            {'name': 'no_saturation', 'regime_variable': 'flux_density_ratio', 'valid_when': '< 1.0', 'error_when_violated': 'flux_density_ratio - 1', 'generalizes_to': 'nonlinear_bh_curve', 'why': 'Once B approaches B_sat the aligned magnetic domains run out, mu collapses and flux no longer rises in proportion to MMF.'},
        ],
    },
    'electric_machines.inductance_constant': {
        'law': 'Winding inductance L is constant, independent of current: lambda = L*i.',
        'assumptions': [
            {'name': 'unsaturated_inductance', 'regime_variable': 'current_ratio', 'valid_when': '< 1.0', 'error_when_violated': 'current_ratio - 1', 'generalizes_to': 'saturation_dependent_inductance', 'why': 'High current drives the iron into saturation, lowering incremental permeability so L(i) drops well below its unsaturated value.'},
        ],
    },
    'electric_machines.infinite_iron_permeability': {
        'law': 'Iron reluctance is negligible; all MMF drops across the air gap (mu_iron -> infinity).',
        'assumptions': [
            {'name': 'negligible_core_reluctance', 'regime_variable': 'reluctance_ratio', 'valid_when': '< 0.1', 'error_when_violated': 'reluctance_ratio', 'generalizes_to': 'finite_permeability_circuit', 'why': "Near saturation or with long flux paths the iron's finite reluctance takes a real share of the MMF, so the air-gap-only model overestimates flux."},
        ],
    },
    'electric_machines.core_loss_no_eddy': {
        'law': 'Ideal lossless core: no induced eddy currents in the laminations.',
        'assumptions': [
            {'name': 'thin_lamination', 'regime_variable': 'penetration_ratio', 'valid_when': '< 0.3', 'error_when_violated': 'penetration_ratio**2', 'generalizes_to': 'classical_eddy_current_loss', 'why': 'When lamination thickness approaches the skin depth, induced eddy currents circulate and shield the interior, dissipating power that scales with (thickness/skin_depth)^2.'},
        ],
    },
    'electric_machines.core_no_hysteresis': {
        'law': 'Reversible B-H path with no hysteresis loop area (zero hysteresis loss).',
        'assumptions': [
            {'name': 'reversible_magnetization', 'regime_variable': 'flux_density_ratio', 'valid_when': '< 0.3', 'error_when_violated': 'flux_density_ratio**1.6', 'generalizes_to': 'steinmetz_hysteresis_loss', 'why': 'Real domain-wall motion is irreversible, opening a B-H loop whose area (loss per cycle) grows roughly as B^1.6 (Steinmetz).'},
        ],
    },
    'electric_machines.sinusoidal_back_emf': {
        'law': 'Back-EMF and air-gap MMF are purely sinusoidal in space and time.',
        'assumptions': [
            {'name': 'sinusoidal_winding_distribution', 'regime_variable': 'harmonic_thd', 'valid_when': '< 0.3', 'error_when_violated': 'harmonic_thd', 'generalizes_to': 'space_harmonic_model', 'why': 'Concentrated or non-ideal windings and slotting inject space harmonics, so the EMF waveform departs from a sinusoid by its total harmonic distortion.'},
        ],
    },
    'electric_machines.constant_resistance_temperature': {
        'law': 'Winding resistance R is constant with temperature.',
        'assumptions': [
            {'name': 'isothermal_conductor', 'regime_variable': 'temperature_coefficient_rise', 'valid_when': '< 0.1', 'error_when_violated': 'temperature_coefficient_rise', 'generalizes_to': 'temperature_dependent_resistance', 'why': 'Copper resistivity rises ~0.4%/K; a large temperature rise raises R by alpha*deltaT, invalidating the cold-resistance value.'},
        ],
    },
    'electric_machines.dc_resistance_no_skin': {
        'law': 'Conductor carries current uniformly; AC resistance equals DC resistance.',
        'assumptions': [
            {'name': 'no_skin_effect', 'regime_variable': 'conductor_depth_ratio', 'valid_when': '< 1.0', 'error_when_violated': 'conductor_depth_ratio**2', 'generalizes_to': 'ac_resistance_skin_effect', 'why': 'When conductor size approaches the skin depth, current crowds to the surface, cutting effective area and raising R_ac above R_dc.'},
        ],
    },
    'electric_machines.ideal_transformer': {
        'law': 'Perfect coupling: no leakage flux and infinite magnetizing inductance, V1/V2 = N1/N2.',
        'assumptions': [
            {'name': 'no_leakage_flux', 'regime_variable': 'leakage_ratio', 'valid_when': '< 0.1', 'error_when_violated': 'leakage_ratio', 'generalizes_to': 'real_transformer_leakage_model', 'why': 'Some flux links only one winding; the leakage reactance (fraction of magnetizing inductance) drops voltage and de-tunes the ideal ratio under load.'},
        ],
    },
    'electric_machines.smooth_airgap_nonsalient': {
        'law': 'Uniform air gap so inductance is rotor-position independent (Ld = Lq).',
        'assumptions': [
            {'name': 'magnetic_isotropy', 'regime_variable': 'saliency_ratio', 'valid_when': '< 0.3', 'error_when_violated': 'saliency_ratio', 'generalizes_to': 'salient_pole_dq_model', 'why': 'Salient poles or rotor geometry make reluctance depend on rotor angle, so (Ld-Lq)/Ld introduces reluctance torque and position-varying inductance.'},
        ],
    },
    'electric_machines.neglect_fringing_flux': {
        'law': 'Air-gap flux is confined to the pole projection (no fringing at gap edges).',
        'assumptions': [
            {'name': 'short_gap', 'regime_variable': 'gap_aspect_ratio', 'valid_when': '< 0.3', 'error_when_violated': 'gap_aspect_ratio', 'generalizes_to': 'fringing_flux_model', 'why': 'When gap length is not small versus pole width, flux bulges outward at the edges, increasing effective area and lowering reluctance below the straight-path estimate.'},
        ],
    },
    'electric_machines.constant_flux_neglect_stator_resistance': {
        'law': 'Air-gap flux set by V/f alone; stator resistance voltage drop ignored (V ~ E).',
        'assumptions': [
            {'name': 'negligible_stator_drop', 'regime_variable': 'voltage_drop_ratio', 'valid_when': '< 0.1', 'error_when_violated': 'voltage_drop_ratio', 'generalizes_to': 'full_stator_voltage_equation', 'why': 'At low speed (low frequency) the R*I drop becomes a large fraction of the small terminal voltage, so constant-V/f under-fluxes the machine.'},
        ],
    },
    'electric_machines.induction_approx_equiv_circuit': {
        'law': 'Magnetizing branch moved to terminals; magnetizing current neglected in rotor-current calc.',
        'assumptions': [
            {'name': 'small_magnetizing_current', 'regime_variable': 'magnetizing_current_ratio', 'valid_when': '< 0.3', 'error_when_violated': 'magnetizing_current_ratio', 'generalizes_to': 'exact_equivalent_circuit', 'why': 'In machines with a large air gap the magnetizing current is a big share of stator current, so ignoring its voltage drop across leakage impedance biases torque and current predictions.'},
        ],
    },
    'electric_machines.balanced_park_transform': {
        'law': 'dq model assumes balanced, positive-sequence three-phase quantities.',
        'assumptions': [
            {'name': 'phase_balance', 'regime_variable': 'unbalance_factor', 'valid_when': '< 0.1', 'error_when_violated': 'unbalance_factor', 'generalizes_to': 'symmetrical_components_model', 'why': 'Voltage or winding asymmetry creates a negative-sequence set that appears as 2f ripple in dq, which the single-frame balanced model cannot represent.'},
        ],
    },
    'electric_machines.dc_machine_linear_torque_speed': {
        'law': 'Torque proportional to armature current with constant field flux: T = k*phi*I_a.',
        'assumptions': [
            {'name': 'no_armature_reaction', 'regime_variable': 'armature_reaction_ratio', 'valid_when': '< 0.3', 'error_when_violated': 'armature_reaction_ratio', 'generalizes_to': 'armature_reaction_saturation_model', 'why': 'Heavy armature current sets up a cross MMF that distorts and weakens the field flux, so torque falls below the constant-flux linear prediction.'},
        ],
    },
    'power_electronics.ideal_switch': {
        'law': 'On-state switch behaves as a short (V_sw ≈ 0) and off-state as an open, with instantaneous, lossless transitions.',
        'assumptions': [
            {'name': 'negligible_conduction_drop', 'regime_variable': 'on_drop_ratio', 'valid_when': '< 0.1', 'error_when_violated': 'on_drop_ratio', 'generalizes_to': 'resistive_switch_with_conduction_loss', 'why': 'Finite R_ds_on (or V_CE_sat) drops voltage and dissipates I^2*R, worst at high current / low output voltage.'},
            {'name': 'zero_switching_time', 'regime_variable': 'switching_time_ratio', 'valid_when': '< 0.05', 'error_when_violated': 'switching_time_ratio', 'generalizes_to': 'hard_switching_loss_model', 'why': 'Finite turn-on/off overlap of V and I produces switching loss and duty distortion that scale with t_sw*f_sw.'},
        ],
    },
    'power_electronics.continuous_conduction_mode': {
        'law': 'In CCM the inductor current stays positive over the whole period, so DC voltage gain depends only on duty D (buck M=D, boost M=1/(1-D)).',
        'assumptions': [
            {'name': 'continuous_conduction', 'regime_variable': 'ripple_ratio', 'valid_when': '< 1.0', 'error_when_violated': 'ripple_ratio-1', 'generalizes_to': 'discontinuous_conduction_mode', 'why': 'At light load the peak-to-average ripple exceeds the mean and inductor current hits zero; the diode blocks and the gain becomes load-dependent.'},
        ],
    },
    'power_electronics.small_ripple_approximation': {
        'law': 'State ripple is small enough that averaged (DC) values may replace instantaneous waveforms: v(t) ≈ V.',
        'assumptions': [
            {'name': 'small_ripple', 'regime_variable': 'voltage_ripple_ratio', 'valid_when': '< 0.1', 'error_when_violated': 'voltage_ripple_ratio', 'generalizes_to': 'exact_switched_waveform_model', 'why': 'Large peak-to-DC ripple makes the linear-ripple / constant-value approximation of waveforms inaccurate.'},
        ],
    },
    'power_electronics.state_space_averaging': {
        'law': 'Converter dynamics are governed by duty-cycle-averaged state equations, discarding switching-frequency harmonics.',
        'assumptions': [
            {'name': 'averaging_valid', 'regime_variable': 'frequency_ratio', 'valid_when': '< 0.1', 'error_when_violated': 'frequency_ratio', 'generalizes_to': 'sampled_data_switched_model', 'why': 'As signal frequency approaches half the switching frequency, sampling and aliasing effects break the continuous averaged model.'},
        ],
    },
    'power_electronics.ideal_diode': {
        'law': 'Diode conducts with zero forward drop when on, blocks with zero leakage when off, and recovers instantly.',
        'assumptions': [
            {'name': 'zero_forward_drop', 'regime_variable': 'forward_drop_ratio', 'valid_when': '< 0.1', 'error_when_violated': 'forward_drop_ratio', 'generalizes_to': 'diode_with_forward_voltage_and_reverse_recovery', 'why': 'At low output voltage the fixed junction drop V_f is a large fraction of output; reverse recovery adds loss at high frequency.'},
        ],
    },
    'power_electronics.ideal_transformer': {
        'law': 'Transformer enforces V1/V2 = N1/N2 and I1/I2 = N2/N1 with no energy storage or loss.',
        'assumptions': [
            {'name': 'infinite_magnetizing_inductance', 'regime_variable': 'magnetizing_current_ratio', 'valid_when': '< 0.1', 'error_when_violated': 'magnetizing_current_ratio', 'generalizes_to': 'transformer_with_magnetizing_inductance', 'why': 'Finite Lm draws magnetizing current and requires flux reset, distorting the ideal current ratio.'},
            {'name': 'zero_leakage_inductance', 'regime_variable': 'leakage_ratio', 'valid_when': '< 0.01', 'error_when_violated': 'leakage_ratio', 'generalizes_to': 'leakage_inductance_model', 'why': 'Uncoupled leakage flux causes voltage spikes, duty-cycle loss, and ringing not captured by the ideal ratio.'},
        ],
    },
    'power_electronics.ideal_capacitor': {
        'law': 'Capacitor voltage ripple is set purely by charge balance: ΔV = ΔQ/C (zero ESR/ESL).',
        'assumptions': [
            {'name': 'negligible_esr', 'regime_variable': 'esr_ripple_ratio', 'valid_when': '< 0.1', 'error_when_violated': 'esr_ripple_ratio', 'generalizes_to': 'capacitor_with_esr_esl', 'why': 'At high frequency the resistive ESR term (2*pi*f*C*ESR relative to capacitive impedance) dominates the ripple over the 1/C term.'},
        ],
    },
    'power_electronics.linear_inductor': {
        'law': 'Inductor flux linkage is linear in current, λ = L·i with constant L.',
        'assumptions': [
            {'name': 'no_core_saturation', 'regime_variable': 'flux_ratio', 'valid_when': '< 1.0', 'error_when_violated': 'flux_ratio', 'generalizes_to': 'saturable_nonlinear_inductor', 'why': 'Beyond B_sat the core permeability collapses, inductance drops sharply, and current spikes uncontrollably.'},
        ],
    },
    'power_electronics.ideal_conversion_ratio': {
        'law': 'Lossless CCM DC conversion ratio is a pure function of duty: M(D)=D (buck), 1/(1-D) (boost).',
        'assumptions': [
            {'name': 'lossless', 'regime_variable': 'parasitic_resistance_ratio', 'valid_when': '< 0.05', 'error_when_violated': 'parasitic_resistance_ratio', 'generalizes_to': 'lossy_conversion_ratio_with_parasitics', 'why': 'Winding/switch/ESR resistance drops output voltage and, in boost-type converters, caps the achievable gain near D->1.'},
        ],
    },
    'power_electronics.dc_winding_resistance': {
        'law': 'Winding AC resistance equals its DC resistance (uniform current density in the conductor).',
        'assumptions': [
            {'name': 'no_skin_effect', 'regime_variable': 'penetration_ratio', 'valid_when': '< 1.0', 'error_when_violated': 'penetration_ratio', 'generalizes_to': 'ac_resistance_skin_proximity_model', 'why': 'When conductor thickness exceeds the skin depth, current crowds to the surface, raising R_ac by skin and proximity effects.'},
        ],
    },
    'power_electronics.zero_dead_time': {
        'law': 'Complementary switches commutate instantly, so the averaged output equals D·V_in with no blanking distortion.',
        'assumptions': [
            {'name': 'negligible_dead_time', 'regime_variable': 'dead_time_ratio', 'valid_when': '< 0.02', 'error_when_violated': 'dead_time_ratio', 'generalizes_to': 'dead_time_distortion_model', 'why': 'Blanking (dead) time introduces a current-sign-dependent volt-second error, distorting the effective duty and output.'},
        ],
    },
    'power_electronics.small_signal_linearization': {
        'law': 'Perturbations about the operating point obey linear transfer functions (control-to-output, audio susceptibility).',
        'assumptions': [
            {'name': 'small_perturbation', 'regime_variable': 'duty_perturbation_ratio', 'valid_when': '< 0.1', 'error_when_violated': 'duty_perturbation_ratio', 'generalizes_to': 'large_signal_averaged_model', 'why': 'Large duty excursions hit duty saturation (0<D<1) and slew/current limits, invoking nonlinear large-signal behavior.'},
        ],
    },
    'power_electronics.stiff_input_source': {
        'law': 'Input bus voltage is constant regardless of converter current draw (zero source impedance).',
        'assumptions': [
            {'name': 'stiff_source', 'regime_variable': 'source_impedance_ratio', 'valid_when': '< 0.1', 'error_when_violated': 'source_impedance_ratio', 'generalizes_to': 'finite_source_impedance_model', 'why': "Nonzero source/input-filter impedance interacts with the converter's negative input resistance, causing droop and Middlebrook instability."},
        ],
    },
    'power_electronics.lossless_core': {
        'law': 'Magnetic core stores and returns energy with no hysteresis or eddy-current loss.',
        'assumptions': [
            {'name': 'negligible_core_loss', 'regime_variable': 'core_loss_ratio', 'valid_when': '< 0.05', 'error_when_violated': 'core_loss_ratio', 'generalizes_to': 'steinmetz_core_loss_model', 'why': 'At high flux swing and frequency, hysteresis and eddy losses (Steinmetz P ~ f^a*B^b) become a significant fraction of throughput power.'},
        ],
    },
    'control_theory.small_signal_linearization': {
        'law': 'delta_xdot = A*delta_x + B*delta_u, with A=df/dx and B=df/du evaluated at the operating point',
        'assumptions': [
            {'name': 'small_perturbation', 'regime_variable': 'perturbation_ratio', 'valid_when': '< 0.1', 'error_when_violated': 'perturbation_ratio', 'generalizes_to': 'nonlinear_state_space', 'why': 'The Jacobian drops all second and higher order terms of the Taylor expansion; away from the operating point the neglected curvature dominates the response.'},
        ],
    },
    'control_theory.small_angle_approximation': {
        'law': 'sin(theta) ~= theta and cos(theta) ~= 1 for rotational plant kinematics',
        'assumptions': [
            {'name': 'small_angle', 'regime_variable': 'angle', 'valid_when': '< 0.3', 'error_when_violated': 'angle**2/6', 'generalizes_to': 'large_angle_rigid_body_dynamics', 'why': 'The linear term is only the first Taylor term of sine; the cubic term grows with angle and destroys the linear kinematic map at large deflection.'},
        ],
    },
    'control_theory.ideal_actuator': {
        'law': 'u_actual = u_command (actuator reproduces the command instantly with unit gain)',
        'assumptions': [
            {'name': 'infinite_actuator_bandwidth', 'regime_variable': 'bandwidth_ratio', 'valid_when': '< 0.1', 'error_when_violated': 'bandwidth_ratio', 'generalizes_to': 'first_order_actuator_lag', 'why': "bandwidth_ratio = control_bandwidth/actuator_bandwidth; when the loop is pushed near the actuator's own pole the actuator adds phase lag and rolloff the ideal model ignores."},
        ],
    },
    'control_theory.linear_time_invariant': {
        'law': 'State matrices A,B,C,D are constant so dynamics are described by a fixed transfer function G(s)',
        'assumptions': [
            {'name': 'time_invariance', 'regime_variable': 'parameter_variation_rate', 'valid_when': '< 0.1', 'error_when_violated': 'parameter_variation_rate', 'generalizes_to': 'linear_time_varying_system', 'why': 'parameter_variation_rate = (dp/dt)*tau/p; if plant parameters drift appreciably within one time constant the frozen-model eigenstructure no longer predicts the true trajectory.'},
        ],
    },
    'control_theory.first_order_approximation': {
        'law': 'G(s) ~= K/(tau*s + 1), keeping only the dominant real pole',
        'assumptions': [
            {'name': 'dominant_pole', 'regime_variable': 'pole_ratio', 'valid_when': '< 0.2', 'error_when_violated': 'pole_ratio', 'generalizes_to': 'second_order_system', 'why': 'pole_ratio = dominant_pole/next_pole; when a secondary pole is not far faster it contributes comparable transient dynamics that the single-pole fit omits.'},
        ],
    },
    'control_theory.second_order_dominant_pole': {
        'law': 'G(s) ~= wn^2/(s^2 + 2*zeta*wn*s + wn^2), keeping the dominant complex pole pair',
        'assumptions': [
            {'name': 'dominant_pole_pair', 'regime_variable': 'pole_ratio', 'valid_when': '< 0.2', 'error_when_violated': 'pole_ratio', 'generalizes_to': 'higher_order_system', 'why': 'pole_ratio = real(dominant_pair)/real(nearest_neglected_pole); neglected poles or zeros close to the pair reshape overshoot and settling that the 2nd-order metrics assume.'},
        ],
    },
    'control_theory.light_damping_approximation': {
        'law': 'For a 2nd-order system wd ~= wn, resonant peak Mr ~= 1/(2*zeta), overshoot from zeta alone',
        'assumptions': [
            {'name': 'light_damping', 'regime_variable': 'damping_ratio', 'valid_when': '< 0.3', 'error_when_violated': 'damping_ratio**2/2', 'generalizes_to': 'general_second_order_system', 'why': 'wd = wn*sqrt(1-zeta^2); the sqrt(1-zeta^2) factor and peak formulas are only accurate near zero damping and break as zeta approaches critical.'},
        ],
    },
    'control_theory.rigid_body_assumption': {
        'law': 'Plant modeled as a rigid body, neglecting structural flexible modes',
        'assumptions': [
            {'name': 'rigid_structure', 'regime_variable': 'frequency_ratio', 'valid_when': '< 0.3', 'error_when_violated': 'frequency_ratio**2', 'generalizes_to': 'flexible_body_dynamics', 'why': 'frequency_ratio = control_bandwidth/first_flexible_mode; as the loop bandwidth approaches the first bending mode the flexible resonance couples in and can destabilize the loop.'},
        ],
    },
    'control_theory.continuous_time_approximation': {
        'law': 'A sampled-data loop is designed and analyzed as if the controller were continuous',
        'assumptions': [
            {'name': 'fast_sampling', 'regime_variable': 'sampling_ratio', 'valid_when': '< 0.1', 'error_when_violated': 'sampling_ratio', 'generalizes_to': 'discrete_time_system', 'why': 'sampling_ratio = sample_period*control_bandwidth; sample-and-hold adds phase lag ~ omega*T/2 and aliasing that the continuous model ignores as T grows.'},
        ],
    },
    'control_theory.negligible_time_delay': {
        'law': 'Transport/dead time is dropped: exp(-T_d*s) ~= 1',
        'assumptions': [
            {'name': 'negligible_deadtime', 'regime_variable': 'delay_ratio', 'valid_when': '< 0.1', 'error_when_violated': 'delay_ratio', 'generalizes_to': 'time_delay_system', 'why': 'delay_ratio = dead_time/dominant_time_constant; delay is pure phase lag omega*T_d that erodes phase margin and is not captured by any rational pole model.'},
        ],
    },
    'control_theory.linear_viscous_friction': {
        'law': 'Friction modeled as viscous only: F_f = c*v (linear in velocity)',
        'assumptions': [
            {'name': 'no_coulomb_friction', 'regime_variable': 'friction_ratio', 'valid_when': '< 0.1', 'error_when_violated': 'friction_ratio', 'generalizes_to': 'stribeck_coulomb_friction', 'why': 'friction_ratio = coulomb_force/viscous_force; near zero velocity static/Coulomb friction and stiction dominate, producing limit cycles and hangoff the linear model cannot show.'},
        ],
    },
    'control_theory.unsaturated_actuator': {
        'law': 'Actuator is treated as linear over its full range with no output limit',
        'assumptions': [
            {'name': 'no_saturation', 'regime_variable': 'saturation_ratio', 'valid_when': '<= 1.0', 'error_when_violated': '1 - 1/saturation_ratio', 'generalizes_to': 'saturated_actuator_with_antiwindup', 'why': 'saturation_ratio = commanded_amplitude/actuator_limit; beyond the limit the effective loop gain drops and integrator windup occurs, both invisible to the linear model.'},
        ],
    },
    'control_theory.singular_perturbation_reduction': {
        'law': 'Fast dynamics are set to quasi-steady state, yielding a reduced-order slow model',
        'assumptions': [
            {'name': 'timescale_separation', 'regime_variable': 'timescale_ratio', 'valid_when': '< 0.1', 'error_when_violated': 'timescale_ratio', 'generalizes_to': 'full_order_singularly_perturbed_system', 'why': 'timescale_ratio = tau_fast/tau_slow (epsilon); when the fast subsystem is not much faster, its transients overlap the slow response and the reduced model mispredicts the dynamics.'},
        ],
    },
    'control_theory.describing_function': {
        'law': 'A nonlinearity is replaced by an amplitude-dependent quasi-linear gain N(A) for the fundamental harmonic',
        'assumptions': [
            {'name': 'harmonic_filtering', 'regime_variable': 'harmonic_attenuation', 'valid_when': '< 0.1', 'error_when_violated': 'harmonic_attenuation', 'generalizes_to': 'exact_nonlinear_response', 'why': 'harmonic_attenuation = |G(3*omega)|/|G(omega)|; the method assumes the plant low-passes the harmonics generated by the nonlinearity, which fails if those harmonics are not strongly attenuated.'},
        ],
    },
    'control_theory.ideal_sensor': {
        'law': 'Measurement equals the true state: y = C*x with no noise or dynamics',
        'assumptions': [
            {'name': 'noise_free_measurement', 'regime_variable': 'noise_ratio', 'valid_when': '< 0.1', 'error_when_violated': 'noise_ratio', 'generalizes_to': 'stochastic_estimation_kalman_filter', 'why': 'noise_ratio = sensor_noise_std/signal_amplitude; when noise is non-negligible the deterministic feedback amplifies it and optimal filtering (not direct feedback) is required.'},
        ],
    },
    'control_theory.negligible_quantization': {
        'law': 'Digital signals are treated as continuous-amplitude (quantization ignored)',
        'assumptions': [
            {'name': 'fine_quantization', 'regime_variable': 'quantization_ratio', 'valid_when': '< 0.01', 'error_when_violated': 'quantization_ratio', 'generalizes_to': 'quantized_control_system', 'why': 'quantization_ratio = LSB/signal_amplitude; coarse quantization injects a nonlinear deadband and rounding noise that can cause limit cycles the linear model omits.'},
        ],
    },
    'control_theory.lumped_parameter_approximation': {
        'law': 'A spatially distributed plant is modeled by lumped ODEs, ignoring wave/transport propagation',
        'assumptions': [
            {'name': 'lumped_parameter', 'regime_variable': 'frequency_ratio', 'valid_when': '< 0.3', 'error_when_violated': 'frequency_ratio**2', 'generalizes_to': 'distributed_parameter_system', 'why': 'frequency_ratio = excitation_frequency/(propagation_speed/length); when excitation approaches the first transit/acoustic mode, spatial phase variation makes the single-node lumped model invalid.'},
        ],
    },
    'classical_mechanics.simple_pendulum_small_angle': {
        'law': 'T = 2*pi*sqrt(L/g); restoring torque linear via sin(theta) ~ theta',
        'assumptions': [
            {'name': 'small_angle', 'regime_variable': 'amplitude_angle', 'valid_when': '< 0.3', 'error_when_violated': 'amplitude_angle**2/16', 'generalizes_to': 'large_amplitude_pendulum_elliptic_integral', 'why': 'sin(theta) ~ theta drops the theta^3/6 term, so linear restoring torque and amplitude-independent period both break as swing grows.'},
        ],
    },
    'classical_mechanics.uniform_gravity_near_surface': {
        'law': 'F = m*g with g constant; parabolic projectile motion',
        'assumptions': [
            {'name': 'uniform_field', 'regime_variable': 'altitude_ratio', 'valid_when': '< 0.3', 'error_when_violated': '2*altitude_ratio', 'generalizes_to': 'newtonian_inverse_square_gravitation', 'why': 'g falls as 1/(R+h)^2, so constant-g errs by ~2h/R once altitude is comparable to planetary radius.'},
        ],
    },
    'classical_mechanics.newtonian_kinetic_energy': {
        'law': 'KE = (1/2)*m*v^2',
        'assumptions': [
            {'name': 'non_relativistic', 'regime_variable': 'beta', 'valid_when': '< 0.3', 'error_when_violated': '0.75*beta**2', 'generalizes_to': 'relativistic_kinetic_energy', 'why': 'classical form is leading term of (gamma-1)mc^2; the next term (3/8)m v^4/c^2 grows and energy diverges as v->c.'},
        ],
    },
    'classical_mechanics.newtonian_momentum': {
        'law': 'p = m*v',
        'assumptions': [
            {'name': 'non_relativistic', 'regime_variable': 'beta', 'valid_when': '< 0.3', 'error_when_violated': '0.5*beta**2', 'generalizes_to': 'relativistic_momentum', 'why': 'true momentum is gamma*m*v; gamma ~ 1 + beta^2/2 makes effective inertia grow with speed.'},
        ],
    },
    'classical_mechanics.galilean_velocity_addition': {
        'law': 'v = v1 + v2',
        'assumptions': [
            {'name': 'non_relativistic', 'regime_variable': 'beta', 'valid_when': '< 0.3', 'error_when_violated': '0.5*beta**2', 'generalizes_to': 'relativistic_velocity_addition', 'why': 'simple addition ignores the (1 + v1*v2/c^2) denominator, so combined speeds wrongly exceed c near c.'},
        ],
    },
    'classical_mechanics.stokes_drag': {
        'law': 'F_drag = 6*pi*mu*r*v (linear in velocity)',
        'assumptions': [
            {'name': 'creeping_flow', 'regime_variable': 'reynolds', 'valid_when': '< 1', 'error_when_violated': '0.1875*reynolds', 'generalizes_to': 'quadratic_newton_drag', 'why': 'linear drag neglects inertial momentum transport; the Oseen correction ~3Re/16 and then v^2 scaling take over as Re rises.'},
        ],
    },
    'classical_mechanics.drag_free_projectile': {
        'law': 'range and parabolic path from gravity alone',
        'assumptions': [
            {'name': 'negligible_drag', 'regime_variable': 'drag_ratio', 'valid_when': '< 0.3', 'error_when_violated': 'drag_ratio', 'generalizes_to': 'ballistic_trajectory_with_drag', 'why': 'aerodynamic force ~ rho*Cd*A*v^2/2 grows with speed; when it is a sizable fraction of weight the parabola shortens and steepens.'},
        ],
    },
    'classical_mechanics.undamped_harmonic_oscillator': {
        'law': 'x = A*cos(omega0*t), omega0 = sqrt(k/m), constant amplitude',
        'assumptions': [
            {'name': 'negligible_damping', 'regime_variable': 'damping_ratio', 'valid_when': '< 0.3', 'error_when_violated': '0.5*damping_ratio**2', 'generalizes_to': 'damped_harmonic_oscillator', 'why': 'dissipation shifts frequency to omega0*sqrt(1-zeta^2) and decays amplitude, so the conservative solution drifts as zeta grows.'},
        ],
    },
    'classical_mechanics.hookes_law': {
        'law': 'F = -k*x (stress proportional to strain)',
        'assumptions': [
            {'name': 'small_strain_linear_elastic', 'regime_variable': 'strain', 'valid_when': '< 0.3', 'error_when_violated': 'strain', 'generalizes_to': 'nonlinear_elasticity', 'why': 'linear stress-strain is the first Taylor term of the interatomic potential; large strain brings higher-order and plastic deviations.'},
        ],
    },
    'classical_mechanics.rigid_body': {
        'law': 'interparticle distances fixed; motion = translation + rotation',
        'assumptions': [
            {'name': 'no_deformation', 'regime_variable': 'deflection_ratio', 'valid_when': '< 0.3', 'error_when_violated': 'deflection_ratio', 'generalizes_to': 'deformable_elastic_body', 'why': 'finite stiffness lets loads bend the body; deflection comparable to its size invalidates the fixed-geometry inertia tensor.'},
        ],
    },
    'classical_mechanics.massless_spring_oscillator': {
        'law': "omega = sqrt(k/m), spring's own mass ignored",
        'assumptions': [
            {'name': 'negligible_spring_mass', 'regime_variable': 'spring_mass_ratio', 'valid_when': '< 0.3', 'error_when_violated': 'spring_mass_ratio/6', 'generalizes_to': 'distributed_mass_spring', 'why': 'the coil carries kinetic energy; an effective m_spring/3 adds to the load, lowering frequency when spring mass is not tiny.'},
        ],
    },
    'classical_mechanics.fixed_center_two_body': {
        'law': 'one body treated as a fixed force center (infinite-mass limit)',
        'assumptions': [
            {'name': 'large_mass_ratio', 'regime_variable': 'mass_ratio', 'valid_when': '< 0.3', 'error_when_violated': 'mass_ratio', 'generalizes_to': 'reduced_mass_two_body_problem', 'why': 'the heavy body recoils; replacing m by reduced mass mu = mM/(m+M) matters as m/M grows.'},
        ],
    },
    'classical_mechanics.impulse_approximation': {
        'law': 'collision as instantaneous momentum exchange; positions unchanged during contact',
        'assumptions': [
            {'name': 'short_contact_time', 'regime_variable': 'time_ratio', 'valid_when': '< 0.3', 'error_when_violated': 'time_ratio', 'generalizes_to': 'finite_duration_contact_dynamics', 'why': 'if contact lasts a fraction of the motion timescale, external forces act and bodies move during impact, breaking instantaneous exchange.'},
        ],
    },
    'classical_mechanics.massless_string_tension': {
        'law': 'uniform tension along a light string; straight load path',
        'assumptions': [
            {'name': 'negligible_cable_weight', 'regime_variable': 'cable_mass_ratio', 'valid_when': '< 0.3', 'error_when_violated': 'cable_mass_ratio', 'generalizes_to': 'catenary_heavy_cable', 'why': "a heavy cable's weight varies tension along its length and forces catenary sag rather than a straight massless line."},
        ],
    },
    'classical_mechanics.point_mass': {
        'law': 'body modeled as a point; size and orientation ignored',
        'assumptions': [
            {'name': 'negligible_body_size', 'regime_variable': 'size_ratio', 'valid_when': '< 0.3', 'error_when_violated': 'size_ratio', 'generalizes_to': 'extended_body_tidal_dynamics', 'why': 'when body size approaches the interaction distance, field gradients across it produce tidal and torque effects a point cannot capture.'},
        ],
    },
    'classical_mechanics.gyroscope_steady_precession': {
        'law': 'Omega = torque/(I*omega_spin), steady precession, nutation ignored',
        'assumptions': [
            {'name': 'fast_spin', 'regime_variable': 'precession_ratio', 'valid_when': '< 0.3', 'error_when_violated': 'precession_ratio', 'generalizes_to': 'euler_equations_with_nutation', 'why': 'the formula assumes spin angular momentum dominates; as precession rate nears spin rate, nutation and full Euler dynamics appear.'},
        ],
    },
    'classical_mechanics.non_rotating_frame': {
        'law': "Newton's laws applied directly; Coriolis and centrifugal terms omitted",
        'assumptions': [
            {'name': 'inertial_frame', 'regime_variable': 'rossby', 'valid_when': '>= 1', 'error_when_violated': '1/rossby', 'generalizes_to': 'rotating_frame_dynamics', 'why': 'inertial forces scale as 1/Rossby; for slow large-scale motion (small Rossby) Coriolis deflection becomes first-order.'},
        ],
    },
}