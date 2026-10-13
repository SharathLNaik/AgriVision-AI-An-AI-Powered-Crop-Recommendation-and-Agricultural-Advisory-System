// AgriVision AI - Client Side JS Engine

let currentMode = 'farmer';
let hasSoilReportState = false;
let benchmarkChart = null;
let importanceChart = null;

document.addEventListener('DOMContentLoaded', () => {
    AgriSelect.init();
    loadDistricts();
    initNDVICanvas(0.68);
    fetchModelMetrics();
    loadDatabaseHistory();
    checkDatabaseStatus();
});

// Professional Custom Selection Component
const AgriSelect = {
    instances: new Map(),

    init() {
        document.querySelectorAll('.custom-select-target').forEach(selectEl => {
            this.buildCustomSelect(selectEl);
        });

        document.addEventListener('click', (e) => {
            if (!e.target.closest('.agri-select-container')) {
                this.closeAll();
            }
        });

        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') this.closeAll();
        });
    },

    buildCustomSelect(selectEl) {
        selectEl.style.setProperty('display', 'none', 'important');

        // Remove stale custom select container if present
        if (selectEl.nextElementSibling && selectEl.nextElementSibling.classList.contains('agri-select-container')) {
            selectEl.nextElementSibling.remove();
        }

        const container = document.createElement('div');
        container.className = 'agri-select-container';
        container.dataset.selectId = selectEl.id;

        const trigger = document.createElement('div');
        trigger.className = 'agri-select-trigger';
        trigger.tabIndex = 0;

        const triggerText = document.createElement('span');
        triggerText.className = 'agri-select-trigger-text';

        const arrow = document.createElement('i');
        arrow.className = 'fa-solid fa-chevron-down agri-select-arrow';

        trigger.appendChild(triggerText);
        trigger.appendChild(arrow);

        const menu = document.createElement('div');
        menu.className = 'agri-select-menu';

        let phText = "Search...";
        if (selectEl.id.includes("state")) phText = "Search state...";
        else if (selectEl.id.includes("district")) phText = "Search district...";
        else if (selectEl.id.includes("crop")) phText = "Search crop...";
        else if (selectEl.id.includes("algo")) phText = "Search algorithm...";

        const searchBox = document.createElement('div');
        searchBox.className = 'agri-select-search';
        searchBox.innerHTML = `
            <i class="fa-solid fa-magnifying-glass search-icon"></i>
            <input type="text" class="agri-select-input" placeholder="${phText}" autocomplete="off">
        `;
        const searchInput = searchBox.querySelector('.agri-select-input');

        const optionsList = document.createElement('div');
        optionsList.className = 'agri-select-options';

        menu.appendChild(searchBox);
        menu.appendChild(optionsList);

        container.appendChild(trigger);
        container.appendChild(menu);

        selectEl.parentNode.insertBefore(container, selectEl.nextSibling);

        const instance = {
            selectEl,
            container,
            trigger,
            triggerText,
            menu,
            searchInput,
            optionsList
        };

        this.instances.set(selectEl.id, instance);

        trigger.addEventListener('click', (e) => {
            e.stopPropagation();
            const isOpen = menu.classList.contains('open');
            this.closeAll();
            if (!isOpen) {
                this.openMenu(instance);
            }
        });

        trigger.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                trigger.click();
            }
        });

        searchInput.addEventListener('input', () => {
            this.filterOptions(instance, searchInput.value);
        });

        this.renderOptions(instance);

        selectEl.addEventListener('change', () => {
            this.syncFromNative(instance);
        });
    },

    openMenu(instance) {
        instance.menu.classList.add('open');
        instance.trigger.classList.add('active');
        instance.searchInput.value = '';
        this.filterOptions(instance, '');
        setTimeout(() => instance.searchInput.focus(), 50);
    },

    closeAll() {
        this.instances.forEach(inst => {
            inst.menu.classList.remove('open');
            inst.trigger.classList.remove('active');
        });
    },

    renderOptions(instance) {
        const { selectEl, optionsList } = instance;
        optionsList.innerHTML = '';

        const options = Array.from(selectEl.options);
        if (options.length === 0) {
            optionsList.innerHTML = '<div class="agri-select-empty">No options available</div>';
            this.syncFromNative(instance);
            return;
        }

        options.forEach(opt => {
            const optDiv = document.createElement('div');
            optDiv.className = `agri-select-option ${opt.selected ? 'selected' : ''} ${opt.disabled ? 'disabled' : ''}`;
            optDiv.dataset.value = opt.value;
            
            optDiv.innerHTML = `
                <span>${opt.text}</span>
                ${opt.selected && !opt.disabled ? '<i class="fa-solid fa-check check-icon"></i>' : ''}
            `;

            if (!opt.disabled) {
                optDiv.addEventListener('click', (e) => {
                    e.stopPropagation();
                    selectEl.value = opt.value;
                    selectEl.dispatchEvent(new Event('change', { bubbles: true }));
                    this.closeAll();
                });
            }

            optionsList.appendChild(optDiv);
        });

        this.syncFromNative(instance);
    },

    filterOptions(instance, query) {
        const q = query.toLowerCase().trim();
        const items = instance.optionsList.querySelectorAll('.agri-select-option');
        let matchCount = 0;

        items.forEach(item => {
            if (item.classList.contains('disabled')) {
                item.style.display = 'none';
                return;
            }
            const text = item.innerText.toLowerCase();
            if (!q || text.includes(q)) {
                item.style.display = 'flex';
                matchCount++;
            } else {
                item.style.display = 'none';
            }
        });

        let emptyMsg = instance.optionsList.querySelector('.agri-select-empty');
        if (matchCount === 0) {
            if (!emptyMsg) {
                emptyMsg = document.createElement('div');
                emptyMsg.className = 'agri-select-empty';
                emptyMsg.innerText = 'No matching options found';
                instance.optionsList.appendChild(emptyMsg);
            } else {
                emptyMsg.style.display = 'block';
            }
        } else if (emptyMsg) {
            emptyMsg.style.display = 'none';
        }
    },

    syncFromNative(instance) {
        const { selectEl, triggerText, optionsList } = instance;
        const selectedOpt = selectEl.options[selectEl.selectedIndex];
        
        if (selectedOpt) {
            triggerText.innerText = selectedOpt.text;
            if (selectedOpt.disabled || !selectEl.value) {
                triggerText.classList.add('placeholder-text');
            } else {
                triggerText.classList.remove('placeholder-text');
            }
        } else {
            triggerText.innerText = 'Select...';
            triggerText.classList.add('placeholder-text');
        }

        optionsList.querySelectorAll('.agri-select-option').forEach(optDiv => {
            const isSel = optDiv.dataset.value === selectEl.value;
            optDiv.classList.toggle('selected', isSel);
            let checkIcon = optDiv.querySelector('.check-icon');
            if (isSel && !optDiv.classList.contains('disabled')) {
                if (!checkIcon) {
                    optDiv.insertAdjacentHTML('beforeend', '<i class="fa-solid fa-check check-icon"></i>');
                }
            } else if (checkIcon) {
                checkIcon.remove();
            }
        });
    },

    sync(selectId) {
        const inst = this.instances.get(selectId);
        if (inst) {
            this.renderOptions(inst);
        } else {
            const selectEl = document.getElementById(selectId);
            if (selectEl) this.buildCustomSelect(selectEl);
        }
    }
};

// Mode Switcher
function switchMode(mode) {
    currentMode = mode;
    const farmerBtn = document.getElementById('btn-farmer-mode');
    const expertBtn = document.getElementById('btn-expert-mode');
    const farmerSec = document.getElementById('farmer-mode-section');
    const expertSec = document.getElementById('expert-mode-section');

    if (mode === 'farmer') {
        farmerBtn.classList.add('active');
        expertBtn.classList.remove('active');
        farmerSec.classList.add('active');
        farmerSec.classList.remove('hidden');
        expertSec.classList.remove('active');
        expertSec.classList.add('hidden');
    } else {
        expertBtn.classList.add('active');
        farmerBtn.classList.remove('active');
        expertSec.classList.add('active');
        expertSec.classList.remove('hidden');
        farmerSec.classList.remove('active');
        farmerSec.classList.add('hidden');
    }
}

// Load South Indian Districts based on selected State
async function loadDistricts() {
    const stateSel = document.getElementById('farmer-state').value;
    const distSel = document.getElementById('farmer-district');

    if (!stateSel) {
        distSel.innerHTML = '<option value="" disabled selected>-- Select State First --</option>';
        AgriSelect.sync('farmer-district');
        return;
    }

    distSel.innerHTML = '<option value="" disabled selected>Loading districts...</option>';
    AgriSelect.sync('farmer-district');

    try {
        const res = await fetch(`/api/districts?state=${encodeURIComponent(stateSel)}`);
        const data = await res.json();
        
        if (data.districts) {
            distSel.innerHTML = '<option value="" disabled selected>-- Select District --</option>';
            const addedDistricts = new Set();
            Object.keys(data.districts).forEach(dist => {
                const cleanName = (dist === 'Shimoga') ? 'Shivamogga' : dist;
                if (addedDistricts.has(cleanName)) return;
                addedDistricts.add(cleanName);

                const opt = document.createElement('option');
                opt.value = cleanName;
                opt.innerText = cleanName;
                distSel.appendChild(opt);
            });
            AgriSelect.sync('farmer-district');
        }
    } catch (e) {
        console.error("Error loading districts:", e);
    }
}

// Toggle Soil Report fields
function toggleSoilReport(hasReport) {
    hasSoilReportState = hasReport;
    const btnNo = document.getElementById('btn-soil-no');
    const btnYes = document.getElementById('btn-soil-yes');
    const panel = document.getElementById('custom-soil-panel');

    if (hasReport) {
        btnYes.classList.add('active');
        btnNo.classList.remove('active');
        panel.classList.remove('hidden');
    } else {
        btnNo.classList.add('active');
        btnYes.classList.remove('active');
        panel.classList.add('hidden');
    }
}

// Submit Farmer Mode Prediction
async function submitFarmerPrediction() {
    const stateSel = document.getElementById('farmer-state');
    const distSel = document.getElementById('farmer-district');
    
    if (!stateSel || !stateSel.value) {
        alert("Please select your State before proceeding.");
        return;
    }
    if (!distSel || !distSel.value) {
        alert("Please select your District before proceeding.");
        return;
    }

    const state = stateSel.value;
    const district = distSel.value;

    const landSizeEl = document.getElementById('farmer-land-size');
    const landSize = landSizeEl ? (parseFloat(landSizeEl.value) || 2.0) : 2.0;

    const landUnitEl = document.getElementById('farmer-land-unit');
    const landUnit = landUnitEl ? landUnitEl.value : 'acres';

    const budgetEl = document.getElementById('farmer-budget');
    const farmerBudget = budgetEl ? (parseFloat(budgetEl.value) || 60000) : 60000;
    
    const waterRadio = document.querySelector('input[name="water-avail"]:checked');
    const waterAvail = waterRadio ? waterRadio.value : 'Medium';

    const prevCropEl = document.getElementById('farmer-prev-crop');
    const prevCrop = prevCropEl ? prevCropEl.value : 'none';

    const payload = {
        state: state,
        district: district,
        land_size: landSize,
        land_unit: landUnit,
        farmer_budget: farmerBudget,
        water_availability: waterAvail,
        previous_crop: prevCrop,
        has_soil_report: hasSoilReportState
    };

    if (hasSoilReportState) {
        payload.custom_soil = {
            N: parseFloat(document.getElementById('soil-n')?.value || 90),
            P: parseFloat(document.getElementById('soil-p')?.value || 45),
            K: parseFloat(document.getElementById('soil-k')?.value || 40),
            ph: parseFloat(document.getElementById('soil-ph')?.value || 6.5)
        };
    }

    try {
        const res = await fetch('/api/farmer-recommend', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();

        if (data.success) {
            renderFarmerResults(data);
        } else {
            alert("Prediction error: " + (data.error || "Unknown error"));
        }
    } catch (e) {
        console.error("Farmer submission error:", e);
        alert("Failed to connect to backend server.");
    }
}

let currentFarmerData = null;

// Smooth scroll helper for 10-step stepper
function scrollToStep(stepId) {
    const el = document.getElementById(stepId);
    if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
}

// User Taps a Crop Card in Step 3 -> Recalculates & Updates Steps 5 to 10!
function onSelectCropCard(cropKey, autoScroll = false) {
    if (!currentFarmerData || !currentFarmerData.recommendations) return;

    const selectedRec = currentFarmerData.recommendations.find(r => r.crop_key === cropKey) || currentFarmerData.recommendations[0];

    // 1. Highlight clicked crop card
    const cardNodes = document.querySelectorAll('.crop-card');
    cardNodes.forEach(card => {
        if (card.dataset.cropKey === cropKey) {
            card.classList.add('active-crop-card');
            const badge = card.querySelector('.crop-select-badge');
            if (badge) badge.innerHTML = '<i class="fa-solid fa-circle-check"></i> Active Target Crop';
        } else {
            card.classList.remove('active-crop-card');
            const badge = card.querySelector('.crop-select-badge');
            if (badge) badge.innerHTML = '<i class="fa-solid fa-hand-pointer"></i> Tap to Calculate Steps 5-10';
        }
    });

    // 2. Render Steps 5 to 10 for the selected crop
    renderSteps5To10(selectedRec, currentFarmerData);

    // 3. Smooth scroll down to Step 5 if user explicitly tapped a card
    if (autoScroll) {
        scrollToStep('step-5-cost');
    }
}

// Render Steps 5 to 10 dynamically for selected crop
function renderSteps5To10(rec, data) {
    if (!rec) return;

    // Step 5: Render Cultivation Cost Breakdown Table
    const costWrapper = document.getElementById('cultivation-cost-table-wrapper');
    if (costWrapper && rec.itemized_costs) {
        const costs = rec.itemized_costs;
        costWrapper.innerHTML = `
            <div class="target-crop-banner margin-bottom-sm">
                Target Crop: <strong class="accent-text">${rec.crop_display_name}</strong> (${rec.season} Season)
            </div>
            <table class="agri-table">
                <thead>
                    <tr>
                        <th>Cost Category</th>
                        <th>Per Acre Cost (₹)</th>
                        <th>Total Farm Cost (${data.land_size_formatted})</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td><i class="fa-solid fa-seedling icon-green"></i> Seeds & Saplings</td>
                        <td>₹${costs.seeds ? (costs.seeds / data.land_size).toLocaleString('en-IN') : 0}</td>
                        <td><strong>₹${(costs.seeds || 0).toLocaleString('en-IN')}</strong></td>
                        <td><span class="pill-sm pill-emerald">Essential</span></td>
                    </tr>
                    <tr>
                        <td><i class="fa-solid fa-flask icon-cyan"></i> Fertilizers & Soil Nutrients</td>
                        <td>₹${costs.fertilizer ? (costs.fertilizer / data.land_size).toLocaleString('en-IN') : 0}</td>
                        <td><strong>₹${(costs.fertilizer || 0).toLocaleString('en-IN')}</strong></td>
                        <td><span class="pill-sm pill-emerald">Recommended</span></td>
                    </tr>
                    <tr>
                        <td><i class="fa-solid fa-shield-halved icon-gold"></i> Crop Protection & Pesticides</td>
                        <td>₹${costs.pesticides ? (costs.pesticides / data.land_size).toLocaleString('en-IN') : 0}</td>
                        <td><strong>₹${(costs.pesticides || 0).toLocaleString('en-IN')}</strong></td>
                        <td><span class="pill-sm pill-cyan">Preventative</span></td>
                    </tr>
                    <tr>
                        <td><i class="fa-solid fa-tractor"></i> Machinery, Tillage & Fuel</td>
                        <td>₹${costs.machinery ? (costs.machinery / data.land_size).toLocaleString('en-IN') : 0}</td>
                        <td><strong>₹${(costs.machinery || 0).toLocaleString('en-IN')}</strong></td>
                        <td><span class="pill-sm">Standard</span></td>
                    </tr>
                    <tr>
                        <td><i class="fa-solid fa-users"></i> Labor & Drip Irrigation</td>
                        <td>₹${costs.labor_irrigation ? (costs.labor_irrigation / data.land_size).toLocaleString('en-IN') : 0}</td>
                        <td><strong>₹${(costs.labor_irrigation || 0).toLocaleString('en-IN')}</strong></td>
                        <td><span class="pill-sm">Operational</span></td>
                    </tr>
                    <tr class="highlight-row">
                        <td><strong>Total Estimated Cost (${rec.crop_display_name})</strong></td>
                        <td><strong>₹${costs.cost_per_acre ? costs.cost_per_acre.toLocaleString('en-IN') : 0} / Acre</strong></td>
                        <td><strong class="accent-text text-large">₹${(costs.total_cost || 0).toLocaleString('en-IN')}</strong></td>
                        <td><span class="pill-sm pill-emerald">Final Budget</span></td>
                    </tr>
                </tbody>
            </table>
        `;
    }

    // Step 6: Render Required Agricultural Products
    const prodsGrid = document.getElementById('required-products-grid');
    if (prodsGrid && rec.required_products) {
        prodsGrid.innerHTML = '';
        const p = rec.required_products;
        
        // Extract values supporting both dictionary and array structures
        let seedsName = p.seeds;
        let fertName = p.fertilizer;
        let bioName = p.bio_boost || p.bio_booster;
        let protName = p.crop_protection || p.protection || p.pesticide;

        // If p is an array or contains an items list, extract product names by category
        const pList = Array.isArray(p) ? p : (Array.isArray(p.items) ? p.items : []);
        if (pList.length > 0) {
            pList.forEach(item => {
                const cat = (item.category || '').toLowerCase();
                const nm = item.name || '';
                if (!seedsName && cat.includes('seed')) seedsName = nm;
                if (!fertName && cat.includes('fertilizer')) fertName = nm;
                if (!bioName && (cat.includes('bio') || cat.includes('booster'))) bioName = nm;
                if (!protName && (cat.includes('pesticide') || cat.includes('herbicide') || cat.includes('protection') || cat.includes('fungicide') || cat.includes('insecticide'))) protName = nm;
            });
        }

        // Bulletproof defaults tailored to the crop to ensure no 'undefined' ever shows
        seedsName = seedsName || `High-Yield Hybrid ${rec.crop_display_name} Seeds`;
        fertName = fertName || 'IFFCO Nano Urea & DAP (18-46-0) Balanced Complex';
        bioName = bioName || 'Trichoderma Viride & Bio-NPK Growth Inoculant';
        protName = protName || 'Neem Shield Bio-Pesticide & Broad Protection';

        const items = [
            { icon: 'fa-seedling', cat: 'Seeds & Variety', name: seedsName, dosage: `High-Yield Certified Hybrid Seed for ${rec.crop_display_name}` },
            { icon: 'fa-vial', cat: 'Fertilizers & Nutrients', name: fertName, dosage: 'Split Dose: 50% Basal + 50% Top Dressing' },
            { icon: 'fa-microchip', cat: 'Bio-Boosters', name: bioName, dosage: 'Soil Application at Rooting Stage' },
            { icon: 'fa-bug-slash', cat: 'Crop Protection', name: protName, dosage: 'Foliar Spray at 30 & 60 Days After Sowing' }
        ];

        items.forEach(item => {
            const div = document.createElement('div');
            div.className = 'product-card';
            div.innerHTML = `
                <div class="product-icon"><i class="fa-solid ${item.icon}"></i></div>
                <div class="product-meta">
                    <span class="product-cat">${item.cat}</span>
                    <h4 class="product-title">${item.name}</h4>
                    <p class="product-dosage">${item.dosage}</p>
                </div>
            `;
            prodsGrid.appendChild(div);
        });
    }

    // Step 7: Render Store Comparison Matrix
    const storeWrapper = document.getElementById('store-comparison-wrapper');
    if (storeWrapper && rec.store_price_matrix) {
        let storeHtml = `
            <div class="target-crop-banner margin-bottom-sm">
                Product Package Prices for <strong class="accent-text">${rec.crop_display_name}</strong> Inputs:
            </div>
            <table class="agri-table">
                <thead>
                    <tr>
                        <th>Agri Store Marketplace</th>
                        <th>Store Badge</th>
                        <th>Delivery Estimate</th>
                        <th>Stock Status</th>
                        <th>Complete Package Cost</th>
                        <th>Action</th>
                    </tr>
                </thead>
                <tbody>
        `;
        rec.store_price_matrix.forEach(st => {
            storeHtml += `
                <tr>
                    <td><strong>${st.store_name}</strong></td>
                    <td><span class="pill-sm pill-gold">${st.badge}</span></td>
                    <td><i class="fa-solid fa-truck-fast"></i> ${st.delivery_time}</td>
                    <td><span class="pill-sm pill-emerald">${st.stock_status}</span></td>
                    <td><strong class="accent-text">${st.estimated_package_cost}</strong> <small class="text-muted">(${st.discount_label})</small></td>
                    <td><button class="btn-sm-emerald" onclick="alert('Redirecting to ${st.store_name} online store checkout for ${rec.crop_display_name} package...')">Order Online</button></td>
                </tr>
            `;
        });
        storeHtml += '</tbody></table>';
        storeWrapper.innerHTML = storeHtml;
    }

    // Step 8: Render Budget Check Status
    const budgetContainer = document.getElementById('budget-assessment-container');
    if (budgetContainer && rec.budget_check) {
        const b = rec.budget_check;
        budgetContainer.innerHTML = `
            <div class="budget-card ${b.status_class}">
                <div class="budget-header-row">
                    <div>
                        <div class="budget-title">Farmer Budget Assessment</div>
                        <div class="budget-subtitle">Selected Target Crop: <strong>${rec.crop_display_name}</strong> (${data.land_size_formatted})</div>
                    </div>
                    <span class="budget-badge ${b.status_class}">${b.status_label}</span>
                </div>
                
                <div class="budget-metrics-row margin-top-md">
                    <div class="budget-metric">
                        <span class="b-label">Farmer Available Budget</span>
                        <span class="b-val">${b.farmer_budget_inr}</span>
                    </div>
                    <div class="budget-metric">
                        <span class="b-label">Estimated Cultivation Cost</span>
                        <span class="b-val accent-gold">${b.total_cost_inr}</span>
                    </div>
                    <div class="budget-metric">
                        <span class="b-label">${b.is_within_budget ? 'Budget Surplus' : 'Budget Deficit'}</span>
                        <span class="b-val ${b.is_within_budget ? 'accent-text' : 'text-red'}">${b.difference_inr}</span>
                    </div>
                </div>

                <div class="budget-advice-box margin-top-md">
                    <i class="fa-solid fa-shield-cat icon-emerald"></i>
                    <span><strong>Financial Guidance:</strong> ${b.summary_text}</span>
                </div>
            </div>
        `;
    }

    // Step 9: Render Financial Revenue & Margins
    const marginGrid = document.getElementById('revenue-margin-grid');
    if (marginGrid && rec.financial_margins) {
        const fm = rec.financial_margins;
        marginGrid.innerHTML = `
            <div class="financial-card">
                <span class="f-label">Estimated Gross Revenue (${rec.crop_display_name})</span>
                <span class="f-val gold">${fm.gross_revenue}</span>
                <span class="f-sub">Based on mandi prices</span>
            </div>
            <div class="financial-card">
                <span class="f-label">Total Cultivation Cost</span>
                <span class="f-val">${fm.cultivation_cost}</span>
                <span class="f-sub">Seeds, nutrients, labor & machinery</span>
            </div>
            <div class="financial-card highlight">
                <span class="f-label">Estimated Net Profit</span>
                <span class="f-val emerald">${fm.net_profit_range}</span>
                <span class="f-sub">Profit margin: ${fm.profit_margin_percent}</span>
            </div>
            <div class="financial-card">
                <span class="f-label">Return on Investment</span>
                <span class="f-val cyan">${fm.roi_multiplier}</span>
                <span class="f-sub">ROI index for ${rec.crop_display_name}</span>
            </div>
        `;
    }

    // Step 10: Render 5-Day Weather Forecast & Agronomic Advisory
    const weatherGrid = document.getElementById('weather-forecast-grid');
    const liveInd = document.getElementById('weather-live-indicator');
    const weatherUpdated = document.getElementById('weather-updated-time');
    const weatherLicensing = document.getElementById('weather-licensing');

    if (liveInd && data.weather_meta) {
        liveInd.innerHTML = data.weather_meta.is_live
            ? '<i class="fa-solid fa-satellite-dish"></i> Live Open-Meteo NWP'
            : '<i class="fa-solid fa-cloud"></i> Regional Model (Offline)';
    }

    if (weatherUpdated && data.weather_meta && data.weather_meta.last_updated) {
        weatherUpdated.innerHTML = `<i class="fa-solid fa-clock"></i> Updated: ${data.weather_meta.last_updated}`;
    }

    if (weatherLicensing && data.weather_meta && data.weather_meta.licensing) {
        weatherLicensing.innerHTML = `<i class="fa-solid fa-scale-balanced"></i> Source: ${data.weather_meta.licensing}`;
    }

    if (weatherGrid && data.weather_forecast) {
        weatherGrid.innerHTML = '';
        data.weather_forecast.forEach(w => {
            const card = document.createElement('div');
            card.className = 'weather-card';
            const tempVal = w.temp_c !== undefined ? `${w.temp_c}°C` : (w.temp || '28°C');
            const humVal = typeof w.humidity === 'string' && w.humidity.includes('%') ? w.humidity : `${w.humidity || 70}%`;
            const rainProb = w.rainfall_prob !== undefined ? `${w.rainfall_prob}%` : (w.rain_prob || '15%');
            const rainQty = w.rainfall_quantity || (w.rainfall_amount_mm !== undefined ? `${w.rainfall_amount_mm} mm` : '0.0 mm');
            const advisoryText = w.advisory || 'Optimal window for routine agricultural field management';

            card.innerHTML = `
                <div class="w-day">${w.day || 'Day'}</div>
                <div class="w-temp">${tempVal}</div>
                ${w.temp_range ? `<div style="font-size:11px; color:#9ca3af; margin-bottom:4px;">${w.temp_range}</div>` : ''}
                <div class="w-cond">${w.condition || 'Partly Cloudy'}</div>
                <div class="w-meta" title="Relative Humidity | Rain Chance | Expected Rain Volume"><i class="fa-solid fa-droplet"></i> ${humVal} | <i class="fa-solid fa-cloud-rain"></i> ${rainProb} (${rainQty})</div>
                <div class="w-adv">${advisoryText}</div>
            `;
            weatherGrid.appendChild(card);
        });
    }

    // Render 3-Season Rotation Plan
    if (data.crop_rotation) {
        const rKharif = document.getElementById('rot-kharif');
        const rRabi = document.getElementById('rot-rabi');
        const rRabiDesc = document.getElementById('rot-rabi-desc');
        const rZaid = document.getElementById('rot-zaid');
        const rZaidDesc = document.getElementById('rot-zaid-desc');

        if (rKharif) rKharif.innerText = rec.crop_display_name;
        if (rRabi) rRabi.innerText = data.crop_rotation.rabi_season;
        if (rRabiDesc) rRabiDesc.innerText = data.crop_rotation.rabi_reason;
        if (rZaid) rZaid.innerText = data.crop_rotation.zaid_season;
        if (rZaidDesc) rZaidDesc.innerText = data.crop_rotation.zaid_reason;
    }
}

// Render Farmer Mode Results for all 10 distinct steps
function renderFarmerResults(data) {
    const container = document.getElementById('farmer-results-container');
    if (!container) return;
    container.classList.remove('hidden');

    // Refresh enterprise database transaction log
    loadDatabaseHistory();
    checkDatabaseStatus();

    currentFarmerData = data;
    const topRec = data.recommendations && data.recommendations.length > 0 ? data.recommendations[0] : null;

    // 0. Render Alerts Banner
    const alertsWrapper = document.getElementById('farm-alerts-wrapper');
    if (alertsWrapper) {
        alertsWrapper.innerHTML = '';
        if (data.alerts && data.alerts.length > 0) {
            data.alerts.forEach(al => {
                const div = document.createElement('div');
                div.className = `alert-box alert-${al.type || 'info'}`;
                div.innerHTML = `<strong>${al.title}:</strong> ${al.text}`;
                alertsWrapper.appendChild(div);
            });
        }
    }

    // Step 1: Render Farm Details
    const farmGrid = document.getElementById('farm-details-grid');
    if (farmGrid) {
        const locDisplay = data.location || `${data.district || 'Thanjavur'}, ${data.state || 'Tamil Nadu'}`;
        const waterDisplay = data.water_availability ? `${data.water_availability} Source` : 'Medium Source';
        const budgetVal = data.budget || data.farmer_budget || 60000;

        farmGrid.innerHTML = `
            <div class="metric-card">
                <span class="metric-label">Location</span>
                <span class="metric-val">${locDisplay}</span>
            </div>
            <div class="metric-card">
                <span class="metric-label">Farm Size</span>
                <span class="metric-val">${data.land_size_formatted || '2.0 Acres'}</span>
            </div>
            <div class="metric-card">
                <span class="metric-label">Water Availability</span>
                <span class="metric-val">${waterDisplay}</span>
            </div>
            <div class="metric-card">
                <span class="metric-label">Previous Season Crop</span>
                <span class="metric-val text-capitalize">${data.previous_crop || 'None'}</span>
            </div>
            <div class="metric-card">
                <span class="metric-label">Farmer Available Budget</span>
                <span class="metric-val highlight-gold">₹${Number(budgetVal).toLocaleString('en-IN')}</span>
            </div>
        `;
    }

    // Step 2: Render AI Land & Soil Analysis
    const landGrid = document.getElementById('land-analysis-grid');
    const soil = data.soil_profile || data.input_soil_climate;
    if (landGrid && soil) {
        landGrid.innerHTML = `
            <div class="metric-card">
                <span class="metric-label">Nitrogen (N) Content</span>
                <span class="metric-val">${soil.N} kg/ha</span>
            </div>
            <div class="metric-card">
                <span class="metric-label">Phosphorus (P) Content</span>
                <span class="metric-val">${soil.P} kg/ha</span>
            </div>
            <div class="metric-card">
                <span class="metric-label">Potassium (K) Content</span>
                <span class="metric-val">${soil.K} kg/ha</span>
            </div>
            <div class="metric-card">
                <span class="metric-label">Soil Reaction (pH)</span>
                <span class="metric-val">pH ${soil.ph}</span>
            </div>
            <div class="metric-card">
                <span class="metric-label">Annual Rainfall</span>
                <span class="metric-val">${soil.rainfall ? Math.round(soil.rainfall) : 1200} mm</span>
            </div>
        `;
    }

    // Step 3: Render Recommended Crops with Tap to Select Feature
    const cardsGrid = document.getElementById('crop-cards-grid');
    if (cardsGrid) {
        cardsGrid.innerHTML = '';
        data.recommendations.forEach((rec, idx) => {
            const card = document.createElement('div');
            const isDefaultTop = (idx === 0);
            card.className = `crop-card ${isDefaultTop ? 'active-crop-card' : ''}`;
            card.dataset.cropKey = rec.crop_key;
            card.onclick = () => onSelectCropCard(rec.crop_key, true);
            
            let reasonsHtml = '';
            if (rec.why_reasons && rec.why_reasons.length > 0) {
                reasonsHtml = `
                    <div class="why-box">
                        <div class="why-title"><i class="fa-solid fa-circle-question"></i> Agronomic Suitability Analysis:</div>
                        <ul class="why-list">
                            ${rec.why_reasons.map(r => `<li><i class="fa-solid fa-check icon-green"></i> <strong>${r.factor}:</strong> ${r.text}</li>`).join('')}
                        </ul>
                    </div>
                `;
            }

            card.innerHTML = `
                <div>
                    <div class="crop-card-header">
                        <div>
                            <div class="crop-name">${rec.crop_display_name}</div>
                            <div class="crop-season">Season: ${rec.season}</div>
                        </div>
                        <span class="suitability-badge ${rec.badge_class}">${rec.badge}</span>
                    </div>

                    <div class="stat-row">
                        <span class="stat-label">Yield per Hectare</span>
                        <span class="stat-value">${rec.yield_per_ha_range}</span>
                    </div>
                    <div class="stat-row">
                        <span class="stat-label">Total Harvest (${data.land_size_formatted})</span>
                        <span class="stat-value">${rec.total_harvest_range}</span>
                    </div>
                    <div class="stat-row">
                        <span class="stat-label">Estimated Gross Revenue</span>
                        <span class="stat-value highlight-gold">${rec.revenue_range_inr}</span>
                    </div>
                    <div class="stat-row">
                        <span class="stat-label">Total Cultivation Cost</span>
                        <span class="stat-value">${rec.total_cultivation_cost_inr}</span>
                    </div>

                    ${reasonsHtml}

                    <div class="crop-select-badge">
                        ${isDefaultTop ? '<i class="fa-solid fa-circle-check"></i> Active Target Crop' : '<i class="fa-solid fa-hand-pointer"></i> Tap to Calculate Steps 5-10'}
                    </div>
                </div>
            `;
            cardsGrid.appendChild(card);
        });
    }

    // Step 4: Render Estimated Harvest Yield Table
    const yieldWrapper = document.getElementById('yield-estimation-table-wrapper');
    if (yieldWrapper && data.recommendations) {
        let yieldHtml = `
            <table class="agri-table">
                <thead>
                    <tr>
                        <th>Crop Name</th>
                        <th>Growing Season</th>
                        <th>Yield / Hectare</th>
                        <th>Total Harvest Production (${data.land_size_formatted})</th>
                        <th>Est. Gross Income</th>
                        <th>Action</th>
                    </tr>
                </thead>
                <tbody>
        `;
        data.recommendations.forEach(rec => {
            yieldHtml += `
                <tr>
                    <td><strong>${rec.crop_display_name}</strong></td>
                    <td><span class="pill-sm pill-emerald">${rec.season}</span></td>
                    <td>${rec.yield_per_ha_range}</td>
                    <td><strong class="accent-text">${rec.total_harvest_range}</strong></td>
                    <td><strong class="accent-gold">${rec.revenue_range_inr}</strong></td>
                    <td><button class="btn-sm-emerald" onclick="onSelectCropCard('${rec.crop_key}', true)"><i class="fa-solid fa-calculator"></i> Select Crop</button></td>
                </tr>
            `;
        });
        yieldHtml += '</tbody></table>';
        yieldWrapper.innerHTML = yieldHtml;
    }

    // Render Steps 5 to 10 for the top crop by default
    if (topRec) {
        onSelectCropCard(topRec.crop_key, false);
    }

    container.scrollIntoView({ behavior: 'smooth' });
}

// Satellite Canvas Field Renderer
function initNDVICanvas(ndviVal) {
    const canvas = document.getElementById('ndviCanvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const w = canvas.width;
    const h = canvas.height;

    ctx.clearRect(0, 0, w, h);
    const cols = 20;
    const rows = 10;
    const cellW = w / cols;
    const cellH = h / rows;

    for (let r = 0; r < rows; r++) {
        for (let c = 0; c < cols; c++) {
            const noise = (Math.sin(c * 0.5) + Math.cos(r * 0.5)) * 0.1;
            const cellNdvi = ndviVal + noise;
            
            if (cellNdvi >= 0.60) {
                ctx.fillStyle = `rgb(${20 + Math.floor(Math.random() * 20)}, ${160 + Math.floor(Math.random() * 40)}, ${80 + Math.floor(Math.random() * 20)})`;
            } else if (cellNdvi >= 0.45) {
                ctx.fillStyle = `rgb(${210 + Math.floor(Math.random() * 30)}, ${160 + Math.floor(Math.random() * 30)}, ${20 + Math.floor(Math.random() * 20)})`;
            } else {
                ctx.fillStyle = `rgb(${200 + Math.floor(Math.random() * 40)}, ${50 + Math.floor(Math.random() * 20)}, ${40 + Math.floor(Math.random() * 20)})`;
            }
            ctx.fillRect(c * cellW, r * cellH, cellW - 1, cellH - 1);
        }
    }
}

// Expert Slider Value Updater
function updateVal(param) {
    const val = document.getElementById(`exp-${param}`).value;
    document.getElementById(`val-${param}`).innerText = val;
}

// Expert Prediction Submission
async function submitExpertPrediction() {
    const payload = {
        N: parseFloat(document.getElementById('exp-n').value),
        P: parseFloat(document.getElementById('exp-p').value),
        K: parseFloat(document.getElementById('exp-k').value),
        ph: parseFloat(document.getElementById('exp-ph').value),
        temperature: parseFloat(document.getElementById('exp-temp').value),
        rainfall: parseFloat(document.getElementById('exp-rain').value),
        algorithm: document.getElementById('exp-algo').value
    };

    try {
        const res = await fetch('/api/predict-crop', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();

        if (data.success) {
            document.getElementById('expert-output').classList.remove('hidden');
            document.getElementById('exp-model-used').innerText = data.model_used;
            document.getElementById('exp-model-acc').innerText = data.model_accuracy;

            const wrapper = document.getElementById('expert-table-wrapper');
            let tableHtml = `
                <table class="form-control" style="border-collapse: collapse;">
                    <thead>
                        <tr style="text-align: left; border-bottom: 1px solid var(--border-glass);">
                            <th style="padding: 8px;">Rank</th>
                            <th style="padding: 8px;">Crop Species</th>
                            <th style="padding: 8px;">Model Probability</th>
                            <th style="padding: 8px;">Yield Projection</th>
                        </tr>
                    </thead>
                    <tbody>
            `;
            data.predictions.forEach((item, idx) => {
                tableHtml += `
                    <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
                        <td style="padding: 8px;">#${idx + 1}</td>
                        <td style="padding: 8px; font-weight:700;">${item.crop_name}</td>
                        <td style="padding: 8px; color: var(--primary-emerald); font-weight:700;">${item.confidence_percent}%</td>
                        <td style="padding: 8px;">${item.estimated_yield_ha}</td>
                    </tr>
                `;
            });
            tableHtml += '</tbody></table>';
            wrapper.innerHTML = tableHtml;
        }
    } catch (e) {
        console.error("Expert prediction error:", e);
    }
}

// Fetch and render model metrics benchmark
async function fetchModelMetrics() {
    try {
        const res = await fetch('/api/metrics');
        const data = await res.json();
        
        if (data.crop_classification) {
            renderBenchmarkChart(data.crop_classification);
        }
        if (data.feature_importances) {
            renderImportanceChart(data.feature_importances);
        }
    } catch (e) {
        console.error("Metrics fetch error:", e);
    }
}

function renderBenchmarkChart(clfData) {
    const ctx = document.getElementById('modelBenchmarkChart').getContext('2d');
    if (benchmarkChart) benchmarkChart.destroy();

    const labels = ['Random Forest', 'Support Vector Machine (SVM)', 'Deep Neural Network (DNN)'];
    const accs = [
        clfData.random_forest.accuracy * 100,
        clfData.svm.accuracy * 100,
        clfData.deep_neural_network.accuracy * 100
    ];

    benchmarkChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Accuracy (%)',
                data: accs,
                backgroundColor: ['rgba(16, 185, 129, 0.7)', 'rgba(245, 158, 11, 0.7)', 'rgba(6, 182, 212, 0.7)'],
                borderColor: ['#10b981', '#f59e0b', '#06b6d4'],
                borderWidth: 1.5,
                borderRadius: 8
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: { min: 90, max: 100, grid: { color: 'rgba(255,255,255,0.05)' } },
                x: { grid: { display: false } }
            },
            plugins: { legend: { display: false } }
        }
    });
}

function renderImportanceChart(impData) {
    const ctx = document.getElementById('featureImportanceChart').getContext('2d');
    if (importanceChart) importanceChart.destroy();

    const keys = Object.keys(impData);
    const vals = Object.values(impData);

    importanceChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: keys,
            datasets: [{
                data: vals,
                backgroundColor: [
                    '#10b981', '#f59e0b', '#06b6d4', '#ec4899', '#8b5cf6', '#3b82f6', '#14b8a6'
                ]
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { position: 'right', labels: { color: '#9ca3af', font: { size: 11 } } }
            }
        }
    });
}

// Enterprise Database Audit & Transaction History
async function checkDatabaseStatus() {
    try {
        const res = await fetch('/api/database-status');
        const data = await res.json();
        const badge = document.getElementById('db-status-badge');
        if (badge && data.status === 'connected') {
            badge.innerHTML = `<i class="fa-solid fa-server"></i> ${data.dialect} DB: Connected (${data.tables.recommendation_history} Records)`;
            badge.className = 'pill-sm pill-emerald';
        }
    } catch (e) {
        console.warn('Database status check error:', e);
    }
}

async function loadDatabaseHistory() {
    const tbody = document.getElementById('db-history-tbody');
    if (!tbody) return;

    try {
        const res = await fetch('/api/history?limit=8');
        const data = await res.json();
        if (data.success && data.history && data.history.length > 0) {
            tbody.innerHTML = '';
            data.history.forEach(item => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td style="color:#9ca3af; font-size:12px;"><i class="fa-regular fa-clock"></i> ${item.created_at || 'Just now'}</td>
                    <td><strong>${item.district}</strong>, ${item.state}</td>
                    <td>${item.land_size} ${item.land_unit}</td>
                    <td><span class="pill-sm pill-emerald">${item.crop_display_name}</span></td>
                    <td class="cyan font-bold">${item.confidence_score}%</td>
                    <td>${item.estimated_yield_range || `${item.estimated_yield_tons} Tons`}</td>
                    <td class="emerald font-bold">${item.net_profit_inr}</td>
                `;
                tbody.appendChild(tr);
            });
        } else {
            tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: #9ca3af;">No prior database transactions found. Generate your first recommendation above!</td></tr>`;
        }
    } catch (e) {
        console.warn('Failed to load database history:', e);
        tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: #ef4444;">Unable to load database records.</td></tr>`;
    }
}

