/**
 * BGP Playground - Main JavaScript
 * Handles UI interactions, API calls, and visualizations
 */

let currentResults = null;
let network = null;
let playbackInterval = null;
let currentStep = 0;
let examples = {};
let eventsChart = null;
let pathLengthChart = null;
let bestPathStabilityChart = null;
let asCentralityChart = null;
let stepData = [];
let playbackSpeed = 800;
let isPlaying = false;
let networkNodes = null;  // Add this
let networkEdges = null;  // Add this

/**
 * Initialize application
 */
async function initApp() {
    // Load examples
    await loadExamples();
    
    // Setup event listeners
    setupEventListeners();
    setupThemeToggle();
    setupSpeedControl();
    setupConfigEditor();
    
    // Initialize default example
    loadExample('simple_line');
}

/**
 * Setup JSON config editor: allow brackets, tabs, and auto-pairing
 */
function setupConfigEditor() {
    const ta = document.getElementById('configInput');
    if (!ta) return;

    // Editor-friendly attributes
    ta.setAttribute('spellcheck', 'false');
    ta.setAttribute('autocomplete', 'off');
    ta.setAttribute('autocorrect', 'off');
    ta.setAttribute('autocapitalize', 'off');
    ta.style.fontFamily = 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace';
    ta.style.fontSize = '13px';
    ta.style.lineHeight = '1.5';

    // Helper to insert text at cursor
    function insertAtCursor(el, text) {
        const start = el.selectionStart;
        const end = el.selectionEnd;
        const value = el.value;
        el.value = value.slice(0, start) + text + value.slice(end);
        const newPos = start + text.length;
        el.selectionStart = el.selectionEnd = newPos;
    }

    // Helper to wrap selection with pair
    function wrapSelection(el, left, right) {
        const start = el.selectionStart;
        const end = el.selectionEnd;
        const value = el.value;
        const selected = value.slice(start, end);
        el.value = value.slice(0, start) + left + selected + right + value.slice(end);
        const newPosStart = start + left.length;
        const newPosEnd = newPosStart + selected.length;
        el.selectionStart = newPosStart;
        el.selectionEnd = newPosEnd;
    }

    // Keydown enhancements
    ta.addEventListener('keydown', (e) => {
        // Allow braces/brackets explicitly
        if (e.key === '{' || e.key === '}' || e.key === '[' || e.key === ']') {
            // Do not prevent default – just let it type normally
            return;
        }

        // Tab -> insert 2 spaces
        if (e.key === 'Tab') {
            e.preventDefault();
            insertAtCursor(ta, '  ');
            return;
        }

        // Enter inside braces/brackets: add newline and indent
        if (e.key === 'Enter') {
            const before = ta.value.slice(0, ta.selectionStart);
            const after = ta.value.slice(ta.selectionEnd);
            const prevChar = before.slice(-1);
            const nextChar = after.slice(0, 1);
            if ((prevChar === '{' && nextChar === '}') || (prevChar === '[' && nextChar === ']')) {
                e.preventDefault();
                const indent = '  ';
                const insert = `\n${indent}\n`;
                const start = ta.selectionStart;
                ta.value = before + insert + after;
                ta.selectionStart = ta.selectionEnd = start + 1 + indent.length;
                return;
            }
        }

        // Auto-pair quotes/brackets
        const pairs = { '"': '"', "'": "'", '{': '}', '[': ']' };
        if (pairs[e.key]) {
            // Only autopair when no selection and next char isn't already the closer
            if (ta.selectionStart === ta.selectionEnd) {
                const nextChar = ta.value.slice(ta.selectionStart, ta.selectionStart + 1);
                if (nextChar !== pairs[e.key]) {
                    e.preventDefault();
                    const left = e.key;
                    const right = pairs[e.key];
                    insertAtCursor(ta, left + right);
                    // Move cursor between the pair
                    ta.selectionStart = ta.selectionEnd = ta.selectionStart - 1;
                    return;
                }
            } else {
                // Wrap selection
                e.preventDefault();
                wrapSelection(ta, e.key, pairs[e.key]);
                return;
            }
        }
    });

    // Toolbar buttons if present
    const bracketButtons = document.querySelectorAll('[data-insert-to="configInput"]');
    bracketButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const text = btn.getAttribute('data-text') || '';
            const pair = btn.getAttribute('data-pair') || '';
            ta.focus();
            if (pair) {
                wrapSelection(ta, text, pair);
            } else {
                insertAtCursor(ta, text);
            }
        });
    });

    // Validate JSON button
    const validateBtn = document.getElementById('validateJsonBtn');
    if (validateBtn) {
        validateBtn.addEventListener('click', () => {
            try {
                const obj = JSON.parse(ta.value);
                // Pretty print
                ta.value = JSON.stringify(obj, null, 2);
                showStatus('JSON is valid.', 'success');
            } catch (err) {
                showStatus('Invalid JSON: ' + err.message, 'error');
            }
        });
    }
}

/**
 * Load example scenarios from API
 */
async function loadExamples() {
    try {
        const response = await fetch('/api/examples');
        examples = await response.json();
        
        const select = document.getElementById('exampleSelect');
        select.innerHTML = '<option value="">-- Select Example --</option>';
        
        Object.keys(examples).forEach(key => {
            const option = document.createElement('option');
            option.value = key;
            option.textContent = examples[key].name;
            select.appendChild(option);
        });
    } catch (error) {
        console.error('Error loading examples:', error);
        showStatus('Failed to load examples', 'error');
    }
}

/**
 * Load specific example into config
 */
function loadExample(key) {
    if (examples[key]) {
        const config = JSON.stringify(examples[key].config, null, 2);
        document.getElementById('configInput').value = config;
        document.getElementById('exampleSelect').value = key;
    }
}

/**
 * Setup all event listeners
 */
function setupEventListeners() {
    // Example selector
    document.getElementById('exampleSelect').addEventListener('change', (e) => {
        if (e.target.value) {
            loadExample(e.target.value);
        }
    });
    
    // Run button
    document.getElementById('runBtn').addEventListener('click', runSimulation);
    
    // Clear button
    document.getElementById('clearBtn').addEventListener('click', () => {
        document.getElementById('configInput').value = '';
        document.getElementById('exampleSelect').value = '';
        clearResults();
    });
    
    // Tab buttons
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const tabName = e.target.id.replace('Tab', '');
            switchTab(tabName);
        });
    });
    
    // Playback controls
    document.getElementById('playBtn').addEventListener('click', startPlayback);
    document.getElementById('pauseBtn').addEventListener('click', pausePlayback);
    document.getElementById('resetBtn').addEventListener('click', resetPlayback);
}

/**
 * Theme toggle setup and persistence
 */
/**
 * Theme toggle setup and persistence
 */
function setupThemeToggle() {
    const btn = document.getElementById('themeToggle');
    if (!btn) {
        console.error('Theme toggle button not found!');
        return;
    }
    
    console.log('Setting up theme toggle...');
    
    // Set initial button text based on current theme
    const updateButtonText = () => {
        const isDark = document.documentElement.classList.contains('dark');
        btn.textContent = isDark ? '☀️ Light' : '🌙 Dark';
        console.log('Theme updated:', isDark ? 'dark' : 'light');
    };
    
    // Initialize button text
    updateButtonText();
    
    // Add click handler
    btn.addEventListener('click', (e) => {
        console.log('Theme toggle clicked!');
        e.preventDefault();
        e.stopPropagation();
        
        // Toggle dark class on root element
        document.documentElement.classList.toggle('dark');
        const isDark = document.documentElement.classList.contains('dark');
        
        // Save preference to localStorage
        try {
            localStorage.setItem('bgp_theme', isDark ? 'dark' : 'light');
            console.log('Theme saved to localStorage:', isDark ? 'dark' : 'light');
        } catch (e) {
            console.warn('Could not save theme preference:', e);
        }
        
        // Update button text
        updateButtonText();
        
        // Re-render visualizations with new theme colors
        if (currentResults) {
            displayCharts(currentResults);
            if (stepData[currentStep]) {
                displayTopology(currentResults.topology, stepData[currentStep].ribs);
            } else {
                displayTopology(currentResults.topology, currentResults.final_ribs);
            }
        }
    });
    
    console.log('Theme toggle setup complete');
}

/**
 * Setup speed control
 */
function setupSpeedControl() {
    const speedControl = document.getElementById('speedControl');
    const speedValue = document.getElementById('speedValue');
    
    if (speedControl && speedValue) {
        speedControl.addEventListener('input', (e) => {
            playbackSpeed = parseInt(e.target.value);
            speedValue.textContent = `${(playbackSpeed / 1000).toFixed(1)}s`;
        });
    }
}

/**
 * Run simulation
 */
async function runSimulation() {
    const configText = document.getElementById('configInput').value;
    
    if (!configText.trim()) {
        showStatus('Please enter a configuration', 'error');
        return;
    }
    
    try {
        const config = JSON.parse(configText);
        
        showStatus('Running simulation...', 'info');
        document.getElementById('runBtn').disabled = true;
        
        const response = await fetch('/api/simulate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(config)
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Simulation failed');
        }
        
        currentResults = await response.json();
        
        showStatus('Simulation completed successfully!', 'success');
        prepareStepByStepData(currentResults);
        displayInitialResults();
        
    } catch (error) {
        showStatus(`Error: ${error.message}`, 'error');
        console.error('Simulation error:', error);
    } finally {
        document.getElementById('runBtn').disabled = false;
    }
}

/**
 * Prepare step-by-step data for dynamic visualization
 * COMPLETELY REWRITTEN to fix all issues
 */
function prepareStepByStepData(results) {
    console.log('=== PREPARING STEP-BY-STEP DATA ===');
    console.log('Timeline events:', results.timeline.length);
    
    stepData = [];
    
    if (!results || !results.timeline || !results.topology) {
        console.error('Invalid results object:', results);
        return;
    }
    
    const timeline = results.timeline;
    const topology = results.topology;
    
    if (timeline.length === 0) {
        console.warn('Timeline is empty');
        return;
    }
    
    // Find max step
    const maxStep = Math.max(...timeline.map(e => e.timestamp), 0);
    console.log(`Processing ${maxStep + 1} steps (0 to ${maxStep})`);
    
    // Initialize RIB evolution tracker - maintains state across all steps
    // Each AS starts with an empty RIB
    const ribEvolution = {};
    topology.nodes.forEach(node => {
        ribEvolution[node.id] = {};
    });
    
    // Process each step chronologically from 0 to maxStep
    for (let step = 0; step <= maxStep; step++) {
        // Get only events for THIS specific step
        const stepEvents = timeline.filter(e => e.timestamp === step);
        
        console.log(`\n--- Step ${step}: ${stepEvents.length} events ---`);
        
        // Process each event in this step
        stepEvents.forEach((event, idx) => {
            console.log(`  Event ${idx + 1}:`, event.event_type, event.from_as, '→', event.to_as, event.prefix);
            
            // Ensure ASes exist in RIB tracker
            if (event.from_as && !ribEvolution[event.from_as]) {
                ribEvolution[event.from_as] = {};
            }
            if (event.to_as && !ribEvolution[event.to_as]) {
                ribEvolution[event.to_as] = {};
            }
            
            if (event.event_type === 'update' && event.prefix) {
                // Case 1: Origin announcement (from_as originates the route, no to_as)
                // This should NOT happen in timeline - origin routes are pre-installed
                // But if it does, handle it
                if (event.from_as && !event.to_as) {
                    console.log(`    → Origin announcement: ${event.from_as} originates ${event.prefix}`);
                    ribEvolution[event.from_as][event.prefix] = {
                        prefix: event.prefix,
                        as_path: [event.from_as],
                        local_pref: 100,
                        origin: 'IGP',
                        med: 0,
                        next_hop: event.from_as
                    };
                }
                
                // Case 2: Normal BGP update (from_as sends route to to_as)
                else if (event.from_as && event.to_as) {
                    // Get the route that from_as has for this prefix
                    const sourceRoute = ribEvolution[event.from_as][event.prefix];
                    
                    if (!sourceRoute) {
                        console.warn(`    ⚠ ${event.from_as} doesn't have route for ${event.prefix}!`);
                        // Create a basic route anyway (shouldn't happen in correct simulation)
                        ribEvolution[event.to_as][event.prefix] = {
                            prefix: event.prefix,
                            as_path: [event.to_as, event.from_as],
                            local_pref: 100,
                            origin: 'IGP',
                            med: 0,
                            next_hop: event.from_as
                        };
                    } else {
                        // Construct the AS_PATH for the received route.
                        // Rule:
                        //  - If the sender's stored path already begins with sender ASN (typical for origin), don't double-prepend.
                        //  - If it was learned from elsewhere (path starts with a different ASN), prepend sender ASN.
                        const srcPath = Array.isArray(sourceRoute.as_path) ? sourceRoute.as_path : [];
                        const newAsPath = (srcPath[0] === event.from_as) ? srcPath.slice() : [event.from_as, ...srcPath];
                        
                        console.log(`    → Path: ${newAsPath.join(' → ')}`);
                        
                        // Create the new route for to_as
                        const newRoute = {
                            prefix: event.prefix,
                            as_path: newAsPath,
                            local_pref: 100,  // Default
                            origin: sourceRoute.origin || 'IGP',
                            med: sourceRoute.med || 0,
                            next_hop: event.from_as  // Next hop is the peer that sent the route
                        };
                        
                        // Apply local policies if they exist
                        if (results.config && results.config.policies) {
                            const nodePolicy = results.config.policies[event.to_as];
                            if (nodePolicy && nodePolicy.local_pref && nodePolicy.local_pref[event.from_as]) {
                                newRoute.local_pref = nodePolicy.local_pref[event.from_as];
                                console.log(`    → Applied policy: local_pref = ${newRoute.local_pref}`);
                            }
                        }
                        
                        // Install the route in to_as's RIB
                        ribEvolution[event.to_as][event.prefix] = newRoute;
                    }
                }
            }
            
            // Case 3: Withdrawal
            else if (event.event_type === 'withdraw' && event.prefix && event.to_as) {
                console.log(`    → Withdraw: ${event.to_as} removes ${event.prefix}`);
                if (ribEvolution[event.to_as] && ribEvolution[event.to_as][event.prefix]) {
                    delete ribEvolution[event.to_as][event.prefix];
                }
            }
        });
        
        // Create deep copy snapshot of current RIB state for this step
        // This preserves the state at this moment in time
        const stepRibs = JSON.parse(JSON.stringify(ribEvolution));
        
        // Calculate metrics for this step
        const totalRoutes = Object.values(stepRibs).reduce((sum, rib) => sum + Object.keys(rib).length, 0);
        const updates = stepEvents.filter(e => e.event_type === 'update').length;
        const withdraws = stepEvents.filter(e => e.event_type === 'withdraw').length;
        
        const metrics = {
            totalRoutes,
            updates,
            withdraws,
            events: stepEvents.length
        };
        
        // Store step data with correct step number
        stepData.push({
            step: step,  // IMPORTANT: Use actual step number
            events: stepEvents,
            ribs: stepRibs,
            metrics: metrics
        });
        
        console.log(`  Total routes after step ${step}: ${totalRoutes}`);
    }
    
    console.log(`\n=== STEP DATA PREPARED: ${stepData.length} steps ===\n`);
}

/**
 * Calculate metrics for a specific step
 */
function calculateStepMetrics(events, ribs) {
    const totalRoutes = Object.values(ribs).reduce((sum, rib) => sum + Object.keys(rib).length, 0);
    const updates = events.filter(e => e.event_type === 'update').length;
    const withdraws = events.filter(e => e.event_type === 'withdraw').length;
    
    return {
        totalRoutes,
        updates,
        withdraws,
        events: events.length
    };
}

/**
 * Display initial results (without charts)
 */
/**
 * Display initial results (without charts)
 */
function displayInitialResults() {
    console.log('Displaying initial results...');
    
    if (!currentResults) {
        console.error('No current results');
        return;
    }
    
    // Show metrics
    displayMetrics(currentResults.metrics);
    
    // Display topology with NO RIBs initially (empty state)
    displayTopology(currentResults.topology, {});
    
    // Clear timeline and RIBs - show placeholder messages
    document.getElementById('timelineContainer').innerHTML = '<p class="text-sm" style="color: var(--muted); padding: 2rem; text-align: center;">Click Play to start step-by-step visualization...</p>';
    document.getElementById('ribsContainer').innerHTML = '<p class="text-sm" style="color: var(--muted); padding: 2rem; text-align: center;">Click Play to start step-by-step visualization...</p>';
    
    // Show playback controls
    document.getElementById('playbackControls').classList.remove('hidden');
    
    // Reset playback to step 0 but DON'T display it yet
    currentStep = 0;
    updatePlaybackDisplay();
    
    // DO NOT call updateStepVisualization() here!
    // User must click Play to see step 0
    console.log('Initial state ready. Click Play to begin.');
}
/**
 * Display metrics
 */
function displayMetrics(metrics) {
    console.log('displayMetrics called with:', metrics);
    
    const metricsCard = document.getElementById('metricsCard');
    if (!metricsCard) {
        console.error('metricsCard element not found!');
        return;
    }
    
    console.log('Removing hidden class from metricsCard');
    metricsCard.classList.remove('hidden');
    
    // Force display with inline style as fallback
    metricsCard.style.display = 'block';
    
    document.getElementById('metricSteps').textContent = metrics.convergence_steps || 0;
    document.getElementById('metricUpdates').textContent = metrics.total_updates || 0;
    document.getElementById('metricEvents').textContent = metrics.total_events || 0;
    
    console.log('Metrics displayed:', {
        steps: metrics.convergence_steps,
        updates: metrics.total_updates,
        events: metrics.total_events
    });
    
    if (metrics.hijack_coverage_pct !== undefined) {
        document.getElementById('hijackMetric').classList.remove('hidden');
        document.getElementById('metricHijack').textContent = 
            `${metrics.hijack_coverage_pct.toFixed(1)}%`;
    } else {
        document.getElementById('hijackMetric').classList.add('hidden');
    }
}

/**
 * Get current RIBs based on playback state
 */
function getCurrentRIBs() {
    // If we have step data and a valid current step, use that
    if (stepData && stepData.length > 0 && stepData[currentStep]) {
        return stepData[currentStep].ribs;
    }
    
    // Otherwise, fall back to final RIBs
    if (currentResults && currentResults.final_ribs) {
        return currentResults.final_ribs;
    }
    
    // No data available
    return {};
}

/**
 * Display network topology using vis.js
 */
function displayTopology(topology, ribs) {
    const container = document.getElementById('networkVis');
    const isDark = document.documentElement.classList.contains('dark');
    
    const nodes = topology.nodes.map(node => {
        const hasRoutes = ribs[node.id] && Object.keys(ribs[node.id]).length > 0;
        return {
            id: node.id,
            label: `AS${node.id}`,
            color: hasRoutes ? (isDark ? '#60a5fa' : '#3b82f6') : (isDark ? '#475569' : '#9ca3af'),
            font: { color: isDark ? '#e5e7eb' : '#ffffff', size: 14, face: 'Inter', bold: '600' },
            shape: 'circle',
            size: hasRoutes ? 40 : 35,
            borderWidth: 2,
            borderWidthSelected: 4,
            chosen: { node: function(values) { values.borderWidth = 4; values.size = 45; } }
        };
    });
    
    const edges = topology.edges.map(edge => ({
        from: edge.from,
        to: edge.to,
        color: { color: isDark ? '#334155' : '#cbd5e1', highlight: isDark ? '#60a5fa' : '#3b82f6' },
        width: 2,
        smooth: false
    }));
    
    // Create or update DataSets
    if (!networkNodes) {
        networkNodes = new vis.DataSet(nodes);
    } else {
        networkNodes.clear();
        networkNodes.add(nodes);
    }
    
    if (!networkEdges) {
        networkEdges = new vis.DataSet(edges);
    } else {
        networkEdges.clear();
        networkEdges.add(edges);
    }
    
    const data = { nodes: networkNodes, edges: networkEdges };
    
    const options = {
        physics: {
            enabled: true,
            solver: 'forceAtlas2Based',
            stabilization: { iterations: 300, updateInterval: 20 },
            forceAtlas2Based: {
                gravitationalConstant: -50,
                centralGravity: 0.015,
                springLength: 180,
                springConstant: 0.08,
                damping: 0.45,
                avoidOverlap: 0.7
            }
        },
        interaction: { hover: true, tooltipDelay: 100, navigationButtons: true, keyboard: true },
        nodes: { borderWidth: 2, borderWidthSelected: 4, shadow: { enabled: true, color: isDark ? 'rgba(0,0,0,0.5)' : 'rgba(0,0,0,0.15)', size: 10, x: 2, y: 2 } },
        edges: { shadow: { enabled: true, color: isDark ? 'rgba(0,0,0,0.4)' : 'rgba(0,0,0,0.1)', size: 5, x: 1, y: 1 } }
    };

    if (network) { 
        network.destroy(); 
        network = null;
    }
    
    network = new vis.Network(container, data, options);
    
    // FIXED: Get current RIBs dynamically instead of using closure
    network.on('click', function(params) {
        if (params.nodes.length > 0) {
            const asn = params.nodes[0];
            const currentRibs = getCurrentRIBs();
            showNodeRIB(asn, currentRibs[asn] || {}); 
        }
    });
    
    // FIXED: Get current RIBs dynamically for hover
    network.on('hoverNode', function(params) {
        const asn = params.node;
        const currentRibs = getCurrentRIBs();
        const rib = currentRibs[asn] || {}; 
        const routeCount = Object.keys(rib).length; 
        container.title = `AS${asn}: ${routeCount} route(s)`;
    });
}


/**
 * Show RIB for a specific node in a modal
 */
function showNodeRIB(asn, rib) {
    const modal = document.getElementById('ribModal');
    const title = document.getElementById('ribModalTitle');
    const content = document.getElementById('ribModalContent');
    
    title.textContent = `Routing Table for AS${asn} (Step ${currentStep})`;
    
    if (!rib || Object.keys(rib).length === 0) {
        content.innerHTML = '<p class="text-gray-500 dark:text-gray-400">No routes in RIB</p>';
    } else {
        let html = '<div class="space-y-3">';
        
        for (const [prefix, route] of Object.entries(rib)) {
            html += `
                <div class="border border-gray-200 dark:border-gray-700 rounded-lg p-3 bg-gray-50 dark:bg-gray-900">
                    <div class="font-semibold text-blue-600 dark:text-blue-400 mb-2">${prefix}</div>
                    <div class="space-y-1 text-sm">
                        <div class="flex">
                            <span class="w-32 text-gray-600 dark:text-gray-400">AS Path:</span>
                            <span class="font-mono text-gray-900 dark:text-white">${route.as_path.join(' → ')}</span>
                        </div>
                        <div class="flex">
                            <span class="w-32 text-gray-600 dark:text-gray-400">Local Pref:</span>
                            <span class="text-gray-900 dark:text-white">${route.local_pref}</span>
                        </div>
                        <div class="flex">
                            <span class="w-32 text-gray-600 dark:text-gray-400">Origin:</span>
                            <span class="text-gray-900 dark:text-white">${route.origin}</span>
                        </div>
                        <div class="flex">
                            <span class="w-32 text-gray-600 dark:text-gray-400">MED:</span>
                            <span class="text-gray-900 dark:text-white">${route.med}</span>
                        </div>
                        ${route.next_hop ? `
                        <div class="flex">
                            <span class="w-32 text-gray-600 dark:text-gray-400">Next Hop:</span>
                            <span class="text-gray-900 dark:text-white">${route.next_hop}</span>
                        </div>
                        ` : ''}
                    </div>
                </div>
            `;
        }
        
        html += '</div>';
        content.innerHTML = html;
    }
    
    modal.classList.remove('hidden');
}

/**
 * Close RIB modal
 */
function closeRIBModal() {
    document.getElementById('ribModal').classList.add('hidden');
}

/**
 * Display timeline events for current step
 */
function displayTimelineForStep(step) {
    const container = document.getElementById('timelineContainer');
    container.innerHTML = '';

    if (!stepData || stepData.length === 0) {
        container.innerHTML = '<p class="text-sm" style="color: var(--muted);">No events</p>';
        return;
    }

    // Show cumulative events from step 0 up to current step
    for (let s = 0; s <= step && s < stepData.length; s++) {
        const events = stepData[s].events || [];

        if (!events.length) continue;

        events.forEach(event => {
            const eventDiv = document.createElement('div');
            eventDiv.className = 'timeline-event animate-fade-in';

            let badgeClass = 'event-badge event-badge-open';
            if (event.event_type === 'update') badgeClass = 'event-badge event-badge-update';
            if (event.event_type === 'withdraw') badgeClass = 'event-badge event-badge-withdraw';
            if (event.event_type === 'keepalive') badgeClass = 'event-badge event-badge-keepalive';

            eventDiv.innerHTML = `
                <div class="flex items-start space-x-3">
                    <span class="${badgeClass}">
                        ${event.event_type.toUpperCase()}
                    </span>
                    <div class="flex-1">
                        <div class="text-sm font-medium">
                            Step ${s + 1}: AS${event.from_as}
                            ${event.to_as ? `→ AS${event.to_as}` : ''}
                        </div>
                        ${event.prefix ? `<div class="text-xs mt-1" style="color: var(--muted);">Prefix: ${event.prefix}</div>` : ''}
                        ${event.details ? `<div class="text-xs mt-1" style="color: var(--muted);">${event.details}</div>` : ''}
                    </div>
                </div>
            `;

            container.appendChild(eventDiv);
        });
    }

    // If still empty (no events at any step), show placeholder
    if (!container.children.length) {
        container.innerHTML = '<p class="text-sm" style="color: var(--muted);">No events</p>';
    }
}

/**
 * Display RIBs for current step
 */
function displayRIBsForStep(step) {
    const container = document.getElementById('ribsContainer');
    container.innerHTML = '';
    
    // Check if step data exists
    if (!stepData || !stepData[step]) {
        container.innerHTML = '<p class="text-sm" style="color: var(--muted);">No RIBs for this step</p>';
        return;
    }
    
    const ribs = stepData[step].ribs;
    
    // Check if RIBs exist
    if (!ribs || Object.keys(ribs).length === 0) {
        container.innerHTML = '<p class="text-sm" style="color: var(--muted);">No RIBs for this step</p>';
        return;
    }
    
    // Sort ASNs numerically
    const sortedASNs = Object.keys(ribs).sort((a, b) => parseInt(a) - parseInt(b));
    
    // Display each AS's RIB
    for (const asn of sortedASNs) {
        const rib = ribs[asn];
        const ribDiv = document.createElement('div');
        ribDiv.className = 'rib-card animate-fade-in';
        
        let ribContent = `<div class="rib-header">
            <span class="as-badge">AS${asn}</span>
            <span class="route-count">${Object.keys(rib).length} route(s)</span>
        </div>`;
        
        if (Object.keys(rib).length === 0) {
            ribContent += '<p class="text-sm" style="color: var(--muted);">No routes</p>';
        } else {
            ribContent += '<div class="space-y-2">';
            for (const [prefix, route] of Object.entries(rib)) {
                // Ensure route has all required fields
                const asPath = route.as_path || [];
                const localPref = route.local_pref !== undefined ? route.local_pref : 100;
                const origin = route.origin || 'IGP';
                const med = route.med !== undefined ? route.med : 0;
                const nextHopRaw = route.next_hop || 'N/A';
                const nextHop = (nextHopRaw === 'N/A') ? 'N/A' : `AS${nextHopRaw}`;
                
                ribContent += `
                    <div class="route-item">
                        <div class="route-prefix">${prefix}</div>
                        <div class="route-details">
                            <div class="route-path">Path: ${asPath.join(' → ')}</div>
                            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem; margin-top: 0.5rem;">
                                <div>Local Pref: <span class="font-semibold">${localPref}</span></div>
                                <div>Origin: <span class="font-semibold">${origin}</span></div>
                                <div>MED: <span class="font-semibold">${med}</span></div>
                                <div>Next Hop: <span class="font-semibold">${nextHop}</span></div>
                            </div>
                        </div>
                    </div>
                `;
            }
            ribContent += '</div>';
        }
        
        ribDiv.innerHTML = ribContent;
        container.appendChild(ribDiv);
    }
}

/**
 * Display charts (only when on charts tab)
 */
function displayCharts(results) {
    // Only display charts if we're on the charts tab
    if (document.getElementById('chartsView').classList.contains('hidden')) {
        return;
    }
    
    displayEventsChart(results.timeline);
    displayPathLengthChart(results.final_ribs);
    displayBestPathStabilityChart(results.timeline);
    displayASCentralityChart(results.topology, results.final_ribs);
}

/**
 * Display events over time chart
 */
function displayEventsChart(timeline) {
    const ctx = document.getElementById('eventsChart');
    if (!ctx) return;
    
    if (eventsChart) { eventsChart.destroy(); eventsChart = null; }
    
    const eventsByStep = {};
    timeline.forEach(event => {
        if (!eventsByStep[event.timestamp]) {
            eventsByStep[event.timestamp] = { open: 0, update: 0, keepalive: 0, withdraw: 0 };
        }
        eventsByStep[event.timestamp][event.event_type] = (eventsByStep[event.timestamp][event.event_type] || 0) + 1;
    });
    
    const steps = Object.keys(eventsByStep).sort((a, b) => parseInt(a) - parseInt(b));
    const updates = steps.map(s => eventsByStep[s].update || 0);
    const opens = steps.map(s => eventsByStep[s].open || 0);
    const withdraws = steps.map(s => eventsByStep[s].withdraw || 0);
    const isDark = document.documentElement.classList.contains('dark');
    
    eventsChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: steps,
            datasets: [
                { label: 'Updates', data: updates, borderColor: isDark ? '#34d399' : '#10b981', backgroundColor: isDark ? 'rgba(52,211,153,0.08)' : 'rgba(16,185,129,0.1)', tension: 0.3, fill: true },
                { label: 'Opens', data: opens, borderColor: isDark ? '#60a5fa' : '#3b82f6', backgroundColor: isDark ? 'rgba(96,165,250,0.08)' : 'rgba(59,130,246,0.1)', tension: 0.3, fill: true },
                { label: 'Withdrawals', data: withdraws, borderColor: isDark ? '#f87171' : '#ef4444', backgroundColor: isDark ? 'rgba(248,113,113,0.08)' : 'rgba(239,68,68,0.1)', tension: 0.3, fill: true }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                title: { display: true, text: 'BGP Events Over Time', color: isDark ? '#e5e7eb' : '#111827' }, 
                legend: { position: 'top', labels: { usePointStyle: true, padding: 15, color: isDark ? '#e5e7eb' : '#111827' } } 
            },
            scales: {
                x: { title: { display: true, text: 'Simulation Step', color: isDark ? '#e5e7eb' : '#111827' }, grid: { display: false }, ticks: { color: isDark ? '#94a3b8' : '#6b7280' } }, 
                y: { title: { display: true, text: 'Event Count', color: isDark ? '#e5e7eb' : '#111827' }, beginAtZero: true, ticks: { stepSize: 1, color: isDark ? '#94a3b8' : '#6b7280' }, grid: { color: isDark ? 'rgba(148,163,184,0.15)' : 'rgba(17,24,39,0.06)' } } 
            }
        }
    });
}

/**
 * Display AS path length distribution
 */
function displayPathLengthChart(ribs) {
    const ctx = document.getElementById('pathLengthChart');
    if (!ctx) return;
    
    if (pathLengthChart) { pathLengthChart.destroy(); }
    
    const pathLengths = {};
    for (const rib of Object.values(ribs)) {
        for (const route of Object.values(rib)) {
            const len = route.as_path.length;
            pathLengths[len] = (pathLengths[len] || 0) + 1;
        }
    }
    
    const lengths = Object.keys(pathLengths).sort((a, b) => parseInt(a) - parseInt(b));
    const counts = lengths.map(l => pathLengths[l]);
    const isDark = document.documentElement.classList.contains('dark');
    
    pathLengthChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: lengths.map(l => `${l} hop${l > 1 ? 's' : ''}`),
            datasets: [{
                label: 'Number of Routes',
                data: counts,
                backgroundColor: isDark ? '#60a5fa' : '#3b82f6', 
                borderColor: isDark ? '#3b82f6' : '#2563eb', 
                borderWidth: 2,
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                title: { display: true, text: 'AS Path Length Distribution', color: isDark ? '#e5e7eb' : '#111827' }, 
                legend: { display: false } 
            }, 
            scales: { 
                x: { title: { display: true, text: 'Path Length', color: isDark ? '#e5e7eb' : '#111827' }, grid: { display: false }, ticks: { color: isDark ? '#94a3b8' : '#6b7280' } }, 
                y: { title: { display: true, text: 'Count', color: isDark ? '#e5e7eb' : '#111827' }, beginAtZero: true, ticks: { stepSize: 1, color: isDark ? '#94a3b8' : '#6b7280' }, grid: { color: isDark ? 'rgba(148,163,184,0.15)' : 'rgba(17,24,39,0.06)' } } 
            } 
        } 
    });
}

/**
 * Display best path stability chart
 */
function displayBestPathStabilityChart(timeline) {
    const el = document.getElementById('bestPathStabilityChart');
    if (!el) return;
    
    if (bestPathStabilityChart) { bestPathStabilityChart.destroy(); bestPathStabilityChart = null; }
    
    const changesByStep = {};
    timeline.forEach(ev => { 
        if (ev.event_type === 'update') { 
            changesByStep[ev.timestamp] = (changesByStep[ev.timestamp] || 0) + 1; 
        } 
    });
    
    const steps = Object.keys(changesByStep).sort((a,b)=>parseInt(a)-parseInt(b));
    const vals = steps.map(s => changesByStep[s]);
    const isDark = document.documentElement.classList.contains('dark');
    
    bestPathStabilityChart = new Chart(el, { 
        type: 'bar', 
        data: { 
            labels: steps, 
            datasets: [{ 
                label: 'Best-Route Changes', 
                data: vals, 
                backgroundColor: isDark ? '#f59e0b' : '#f59e0b', 
                borderColor: isDark ? '#d97706' : '#d97706', 
                borderWidth: 1, 
                borderRadius: 3 
            }] 
        }, 
        options: { 
            plugins: { 
                legend: { display: false }, 
                title: { display: true, text: 'Best Path Changes per Step', color: isDark ? '#e5e7eb' : '#111827' } 
            },
            scales: {
                x: { ticks: { color: isDark ? '#94a3b8' : '#6b7280' }, grid: { display: false } }, 
                y: { beginAtZero: true, ticks: { color: isDark ? '#94a3b8' : '#6b7280' }, grid: { color: isDark ? 'rgba(148,163,184,0.15)' : 'rgba(17,24,39,0.06)' } } 
            } 
        } 
    });
}

/**
 * Display AS centrality chart
 */
function displayASCentralityChart(topology, ribs) {
    const el = document.getElementById('asCentralityChart');
    if (!el) return;
    
    if (asCentralityChart) { asCentralityChart.destroy(); asCentralityChart = null; }
    
    const degree = {}; 
    topology.nodes.forEach(n => degree[n.id] = 0);
    topology.edges.forEach(e => { degree[e.from]++; degree[e.to]++; });
    
    const learnedRoutes = {}; 
    Object.entries(ribs).forEach(([asn, rib]) => learnedRoutes[asn] = Object.keys(rib).length);
    
    const labels = Object.keys(degree).sort((a,b)=>parseInt(a)-parseInt(b));
    const degVals = labels.map(l => degree[l] || 0);
    const learnVals = labels.map(l => learnedRoutes[l] || 0);
    const isDark = document.documentElement.classList.contains('dark');
    
    asCentralityChart = new Chart(el, { 
        type: 'bar', 
        data: { 
            labels, 
            datasets: [ 
                { label: 'Degree', data: degVals, backgroundColor: isDark ? 'rgba(96,165,250,0.6)' : 'rgba(59,130,246,0.6)' }, 
                { label: 'Routes Learned', data: learnVals, backgroundColor: isDark ? 'rgba(52,211,153,0.6)' : 'rgba(16,185,129,0.6)' } 
            ] 
        }, 
        options: { 
            responsive: true, 
            plugins: { 
                legend: { labels: { color: isDark ? '#e5e7eb' : '#111827' } }, 
                title: { display: true, text: 'AS Centrality and Learned Routes', color: isDark ? '#e5e7eb' : '#111827' } 
            }, 
            scales: { 
                x: { ticks: { color: isDark ? '#94a3b8' : '#6b7280' }, grid: { display: false } }, 
                y: { beginAtZero: true, ticks: { color: isDark ? '#94a3b8' : '#6b7280' }, grid: { color: isDark ? 'rgba(148,163,184,0.15)' : 'rgba(17,24,39,0.06)' } } 
            }
        }
    });
}

/**
 * Timeline playback with dynamic visualization
 */
/**
 * Timeline playback with dynamic visualization
 */
function startPlayback() {
    console.log('Starting playback...');
    
    if (!currentResults) {
        console.error('No results to play');
        showStatus('No simulation results available', 'error');
        return;
    }
    
    if (!stepData || stepData.length === 0) {
        console.error('No step data available');
        showStatus('No step data available. Try running the simulation again.', 'error');
        return;
    }
    
    isPlaying = true;
    document.getElementById('playBtn').classList.add('hidden');
    document.getElementById('pauseBtn').classList.remove('hidden');
    
    // Start from current step
    updateStepVisualization();
    
    playbackInterval = setInterval(() => {
        if (currentStep >= stepData.length - 1) {
            pausePlayback();
            showStatus('Playback complete!', 'success');
            return;
        }
        
        currentStep++;
        updatePlaybackDisplay();
        updateStepVisualization();
    }, playbackSpeed);
}

function pausePlayback() {
    isPlaying = false;
    document.getElementById('playBtn').classList.remove('hidden');
    document.getElementById('pauseBtn').classList.add('hidden');
    
    if (playbackInterval) {
        clearInterval(playbackInterval);
        playbackInterval = null;
    }
}

function resetPlayback() {
    console.log('Resetting playback...');
    pausePlayback();
    currentStep = 0;
    updatePlaybackDisplay();
    
    // Clear displays - require user to click Play again
    document.getElementById('timelineContainer').innerHTML = '<p class="text-sm" style="color: var(--muted); padding: 2rem; text-align: center;">Click Play to start step-by-step visualization...</p>';
    document.getElementById('ribsContainer').innerHTML = '<p class="text-sm" style="color: var(--muted); padding: 2rem; text-align: center;">Click Play to start step-by-step visualization...</p>';
    
    // Reset network to empty state
    if (currentResults && currentResults.topology) {
        displayTopology(currentResults.topology, {});
    }
    
    console.log('Reset to step 0. Click Play to begin.');
}

function updatePlaybackDisplay() {
    const totalSteps = stepData.length;
    const shownStep = Math.min(currentStep + 1, Math.max(totalSteps, 1));
    document.getElementById('stepCounter').textContent = `Step: ${shownStep}/${totalSteps}`;
    
    // Show completion message
    if (currentStep >= totalSteps - 1 && isPlaying) {
        setTimeout(() => {
            showStatus('Playback complete!', 'success');
        }, 100);
    }
}

/**
 * Update visualization for current step
 */
function updateStepVisualization() {
    console.log('Updating visualization for step:', currentStep);
    
    if (!stepData || stepData.length === 0) {
        console.warn('No step data available');
        return;
    }
    
    if (!stepData[currentStep]) {
        console.warn('No data for step:', currentStep);
        return;
    }
    
    const stepInfo = stepData[currentStep];
    console.log('Step info:', stepInfo);
    
    // Update network visualization
    if (network && stepInfo.ribs) {
        updateNetworkForStep(stepInfo.ribs);
    }
    
    // Update timeline tab
    displayTimelineForStep(currentStep);
    
    // Update RIBs tab
    displayRIBsForStep(currentStep);
    
    // Update charts if on charts tab
    if (!document.getElementById('chartsView').classList.contains('hidden')) {
        displayCharts(currentResults);
    }
}

/**
 * Update network visualization for current step
 */
function updateNetworkForStep(ribs) {
    if (!network || !networkNodes) {
        console.warn('Network or nodes not initialized');
        return;
    }
    
    const isDark = document.documentElement.classList.contains('dark');
    
    // Update each node's appearance based on whether it has routes
    networkNodes.forEach(node => {
        const nodeId = node.id;
        const hasRoutes = ribs[nodeId] && Object.keys(ribs[nodeId]).length > 0;
        
        networkNodes.update({
            id: nodeId,
            color: hasRoutes ? (isDark ? '#60a5fa' : '#3b82f6') : (isDark ? '#475569' : '#9ca3af'),
            size: hasRoutes ? 40 : 35
        });
    });
}

/**
 * Switch tabs
 */
function switchTab(tabName) {
    // Update tab buttons
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    
    const activeTab = document.getElementById(`${tabName}Tab`);
    activeTab.classList.add('active');
    
    // Update tab content
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.add('hidden');
    });
    
    document.getElementById(`${tabName}View`).classList.remove('hidden');
    
    // If switching to charts tab, display charts
    if (tabName === 'charts' && currentResults) {
        displayCharts(currentResults);
    }
}

/**
 * Show status message
 */
function showStatus(message, type) {
    const status = document.getElementById('status');
    const statusText = document.getElementById('statusText');
    
    status.classList.remove('hidden', 'status-success', 'status-error', 'status-info');
    
    if (type === 'success') {
        status.classList.add('status-success');
    } else if (type === 'error') {
        status.classList.add('status-error');
    } else {
        status.classList.add('status-info');
    }
    
    statusText.textContent = message;
    
    if (type === 'success' || type === 'error') {
        setTimeout(() => {
            status.classList.add('hidden');
        }, 5000);
    }
}

/**
 * Clear all results
 */
function clearResults() {
    currentResults = null;
    currentStep = 0;
    stepData = [];
    isPlaying = false;
    
    if (playbackInterval) {
        clearInterval(playbackInterval);
        playbackInterval = null;
    }
    
    document.getElementById('metricsCard').classList.add('hidden');
    document.getElementById('playbackControls').classList.add('hidden');
    document.getElementById('timelineContainer').innerHTML = 
        '<p class="text-sm" style="color: var(--muted);">Run a simulation to see events...</p>';
    document.getElementById('ribsContainer').innerHTML = 
        '<p class="text-sm" style="color: var(--muted);">Run a simulation to see RIBs...</p>';
    
    // Destroy network and clear DataSets
    if (network) {
        network.destroy();
        network = null;
    }
    
    if (networkNodes) {
        networkNodes.clear();
        networkNodes = null;
    }
    
    if (networkEdges) {
        networkEdges.clear();
        networkEdges = null;
    }
    
    // Destroy charts
    if (eventsChart) {
        eventsChart.destroy();
        eventsChart = null;
    }
    
    if (pathLengthChart) {
        pathLengthChart.destroy();
        pathLengthChart = null;
    }
    
    if (bestPathStabilityChart) {
        bestPathStabilityChart.destroy();
        bestPathStabilityChart = null;
    }
    
    if (asCentralityChart) {
        asCentralityChart.destroy();
        asCentralityChart = null;
    }
    
    // Clear network visualization
    document.getElementById('networkVis').innerHTML = '';
    
    showStatus('Results cleared', 'info');
    setTimeout(() => {
        document.getElementById('status').classList.add('hidden');
    }, 2000);
}

/**
 * Debug function to inspect step data
 */
function debugStepData() {
    console.log('=== STEP DATA DEBUG ===');
    console.log('Total steps:', stepData.length);
    console.log('Current step:', currentStep);
    
    if (stepData.length > 0) {
        console.log('Step 0 data:', stepData[0]);
        console.log('Step 0 events:', stepData[0].events.length);
        console.log('Step 0 RIBs:', Object.keys(stepData[0].ribs));
    }
    
    if (currentResults) {
        console.log('Timeline length:', currentResults.timeline.length);
        console.log('First timeline event:', currentResults.timeline[0]);
    }
}

// Initialize the application when page loads
document.addEventListener('DOMContentLoaded', function() {
    initApp();
});