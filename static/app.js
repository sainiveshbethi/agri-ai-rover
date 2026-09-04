/**
 * AGRI AI ROVER - Frontend JavaScript Controller
 */

document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const toggleSettingsBtn = document.getElementById('toggleSettingsBtn');
    const settingsPanel = document.getElementById('settingsPanel');
    const geminiApiKeyInput = document.getElementById('geminiApiKeyInput');
    const saveKeyBtn = document.getElementById('saveKeyBtn');
    const clearKeyBtn = document.getElementById('clearKeyBtn');
    const testConnBtn = document.getElementById('testConnBtn');
    const testOutputBox = document.getElementById('testOutputBox');

    const badgeDot = document.getElementById('badgeDot');
    const badgeModeText = document.getElementById('badgeModeText');

    const diagEngine = document.getElementById('diagEngine');
    const diagConn = document.getElementById('diagConn');
    const diagModel = document.getElementById('diagModel');
    const diagKeyStatus = document.getElementById('diagKeyStatus');

    const dropzone = document.getElementById('dropzone');
    const imageInput = document.getElementById('imageInput');
    const uploadPlaceholder = document.getElementById('uploadPlaceholder');
    const previewContainer = document.getElementById('previewContainer');
    const imagePreview = document.getElementById('imagePreview');
    const fileNameDisplay = document.getElementById('fileName');
    const fileSizeDisplay = document.getElementById('fileSize');
    const removeImgBtn = document.getElementById('removeImgBtn');
    const analyzeBtn = document.getElementById('analyzeBtn');
    const btnText = document.getElementById('btnText');
    const btnSpinner = document.getElementById('btnSpinner');
    const syncTelemetryBtn = document.getElementById('syncTelemetryBtn');
    const clearSensorsBtn = document.getElementById('clearSensorsBtn');
    
    // Progress / Loading Elements
    const analysisProgress = document.getElementById('analysisProgress');
    const progressStepText = document.getElementById('progressStepText');

    // Alert Bar Elements
    const errorAlert = document.getElementById('errorAlert');
    const errorMessage = document.getElementById('errorMessage');

    // Sensor Inputs
    const soilMoistureInput = document.getElementById('soilMoisture');
    const temperatureInput = document.getElementById('temperature');
    const humidityInput = document.getElementById('humidity');
    const soilPhInput = document.getElementById('soilPh');

    // State Variables
    let selectedFile = null;

    // Check API status on startup
    checkApiConnection();
    fetchTelemetry();

    toggleSettingsBtn.addEventListener('click', () => {
        settingsPanel.classList.toggle('hidden');
    });

    testConnBtn.addEventListener('click', async () => {
        testOutputBox.classList.remove('hidden');
        testOutputBox.innerHTML = '<span style="color:#2563eb;">🧪 Testing Gemini API connection...</span>';
        await checkApiConnection(true);
    });

    saveKeyBtn.addEventListener('click', () => {
        const val = geminiApiKeyInput.value.trim();
        if (val) {
            localStorage.setItem('AGRI_ROVER_GEMINI_KEY', val);
            alert('API Key saved in local browser memory!');
            checkApiConnection(true);
        } else {
            localStorage.removeItem('AGRI_ROVER_GEMINI_KEY');
            checkApiConnection(true);
        }
    });

    clearKeyBtn.addEventListener('click', () => {
        geminiApiKeyInput.value = '';
        localStorage.removeItem('AGRI_ROVER_GEMINI_KEY');
        alert('Override API key cleared.');
        checkApiConnection(true);
    });

    async function checkApiConnection(verbose = false) {
        try {
            const res = await fetch('/api/test-gemini');
            const data = await res.json();
            if (res.ok && data.status === 'connected') {
                setBadgeState('connected', 'Gemini Vision Connected');
                diagConn.textContent = 'Connected (.env Key)';
                diagConn.style.color = '#15803d';
                diagKeyStatus.textContent = 'Configured (.env)';
                diagModel.textContent = data.model || 'gemini-3.5-flash-lite';
                if (verbose) testOutputBox.innerHTML = `<span style="color:#15803d;">✅ ${data.message}</span>`;
            } else {
                setBadgeState('error', 'Gemini API Error');
                diagConn.textContent = data.message || 'API Test Failed';
                diagConn.style.color = '#b91c1c';
                diagKeyStatus.textContent = data.configured ? 'Configured (.env)' : 'Not Configured';
                if (verbose) testOutputBox.innerHTML = `<span style="color:#b91c1c;">❌ ${data.message}</span>`;
            }
        } catch (err) {
            setBadgeState('error', 'Gemini API Error');
            diagConn.textContent = 'Server Offline / Error';
            diagConn.style.color = '#b91c1c';
            diagKeyStatus.textContent = 'Unknown';
            if (verbose) testOutputBox.innerHTML = `<span style="color:#b91c1c;">❌ Cannot connect to AgriAI server.</span>`;
        }
    }

    function setBadgeState(state, textStr) {
        badgeModeText.textContent = textStr;
        badgeDot.className = 'status-dot';
        if (state === 'connected') {
            badgeDot.style.backgroundColor = '#22c55e';
            badgeDot.style.boxShadow = '0 0 8px #22c55e';
        } else if (state === 'demo') {
            badgeDot.style.backgroundColor = '#f59e0b';
            badgeDot.style.boxShadow = '0 0 8px #f59e0b';
        } else {
            badgeDot.style.backgroundColor = '#ef4444';
            badgeDot.style.boxShadow = '0 0 8px #ef4444';
        }
    }

    // Drag-and-Drop & File Select
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropzone.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    ['dragenter', 'dragover'].forEach(eventName => {
        dropzone.addEventListener(eventName, () => dropzone.classList.add('drag-over'), false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropzone.addEventListener(eventName, () => dropzone.classList.remove('drag-over'), false);
    });

    dropzone.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        const files = dt.files;
        if (files && files.length > 0) handleFileSelect(files[0]);
    });

    imageInput.addEventListener('change', (e) => {
        if (e.target.files && e.target.files.length > 0) handleFileSelect(e.target.files[0]);
    });

    function handleFileSelect(file) {
        if (!file.type.startsWith('image/')) {
            showError("Selected file is not an image. Please select a PNG, JPG, JPEG, or WEBP photo.");
            return;
        }

        hideError();
        selectedFile = file;

        const reader = new FileReader();
        reader.onload = (e) => {
            imagePreview.src = e.target.result;
            fileNameDisplay.textContent = file.name;
            fileSizeDisplay.textContent = formatBytes(file.size);

            uploadPlaceholder.classList.add('hidden');
            previewContainer.classList.remove('hidden');
            analyzeBtn.disabled = false;
        };
        reader.readAsDataURL(file);
    }

    removeImgBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        resetImageSelection();
    });

    function resetImageSelection() {
        selectedFile = null;
        imageInput.value = '';
        imagePreview.src = '';
        uploadPlaceholder.classList.remove('hidden');
        previewContainer.classList.add('hidden');
        analyzeBtn.disabled = true;
    }

    function formatBytes(bytes, decimals = 1) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const dm = decimals < 0 ? 0 : decimals;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
    }

    syncTelemetryBtn.addEventListener('click', fetchTelemetry);
    if (clearSensorsBtn) {
        clearSensorsBtn.addEventListener('click', () => {
            soilMoistureInput.value = '';
            temperatureInput.value = '';
            humidityInput.value = '';
            soilPhInput.value = '';
        });
    }

    async function fetchTelemetry() {
        try {
            const res = await fetch('/api/telemetry');
            if (!res.ok) throw new Error("Telemetry fetch failed");
            const data = await res.json();
            
            if (data.soil_moisture !== undefined && data.soil_moisture !== null) soilMoistureInput.value = data.soil_moisture;
            if (data.temperature !== undefined && data.temperature !== null) temperatureInput.value = data.temperature;
            if (data.humidity !== undefined && data.humidity !== null) humidityInput.value = data.humidity;
            if (data.ph !== undefined && data.ph !== null) soilPhInput.value = data.ph;
        } catch (err) {
            console.warn("Telemetry offline or failed:", err.message);
        }
    }

    analyzeBtn.addEventListener('click', startAnalysis);

    async function startAnalysis() {
        if (!selectedFile) {
            showError("Please upload an image of a seed, crop, or leaf first.");
            return;
        }

        hideError();
        setLoadingState(true);

        const formData = new FormData();
        formData.append('image', selectedFile);
        if (soilMoistureInput.value !== '') formData.append('soil_moisture', soilMoistureInput.value);
        if (temperatureInput.value !== '') formData.append('temperature', temperatureInput.value);
        if (humidityInput.value !== '') formData.append('humidity', humidityInput.value);
        if (soilPhInput.value !== '') formData.append('ph', soilPhInput.value);

        try {
            const response = await fetch('/api/analyze', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (!response.ok) {
                const errDetail = result.error || "AI analysis failed. Please try again.";
                showError(errDetail);
                setLoadingState(false);
                return;
            }

            renderAnalysisResults(result);
            setLoadingState(false);

        } catch (err) {
            setLoadingState(false);
            showError("Cannot connect to AgriAI backend. Please ensure server is running.");
            console.error("API error:", err);
        }
    }

    function setLoadingState(isLoading) {
        if (isLoading) {
            analyzeBtn.disabled = true;
            btnText.textContent = "ANALYSING...";
            btnSpinner.classList.remove('hidden');
            analysisProgress.classList.remove('hidden');
            progressStepText.textContent = "Analyzing image with Gemini Vision...";
        } else {
            analyzeBtn.disabled = false;
            btnText.textContent = "ANALYSE IMAGE";
            btnSpinner.classList.add('hidden');
            analysisProgress.classList.add('hidden');
        }
    }

    function renderAnalysisResults(data) {
        const identifiedItem = data.identified_item || data.crop_name || "Unknown";
        document.getElementById('resCropName').textContent = identifiedItem;
        document.getElementById('resScientificName').textContent = data.scientific_name ? `${data.scientific_name} (${data.category || 'crop'})` : (data.category ? `Category: ${data.category}` : '');

        const confBadge = document.getElementById('resConfidenceBadge');
        confBadge.classList.remove('placeholder-badge');
        const confPct = Math.round((data.confidence || 0) * 100);
        confBadge.textContent = `Confidence: ${confPct}%`;
        
        if (confPct >= 80) {
            confBadge.style.backgroundColor = 'var(--status-success-bg)';
            confBadge.style.color = 'var(--status-success-text)';
        } else if (confPct >= 50) {
            confBadge.style.backgroundColor = 'var(--status-warning-bg)';
            confBadge.style.color = 'var(--status-warning-text)';
        } else {
            confBadge.style.backgroundColor = 'var(--status-danger-bg)';
            confBadge.style.color = 'var(--status-danger-text)';
        }

        const candList = document.getElementById('resCandidatesList');
        candList.innerHTML = '';
        if (data.candidates && data.candidates.length > 0) {
            data.candidates.forEach((cand, idx) => {
                const li = document.createElement('li');
                const cConfPct = Math.round((cand.confidence || 0) * 100);
                li.innerHTML = `<span>${idx + 1}. ${cand.name}</span><strong>${cConfPct}%</strong>`;
                candList.appendChild(li);
            });
        } else {
            candList.innerHTML = `<li class="empty-candidate">Single candidate classification.</li>`;
        }

        const condStatus = data.visible_condition || data.visible_condition_status || "Unknown";
        const condPill = document.getElementById('resConditionPill');
        condPill.textContent = condStatus;
        condPill.className = `pill ${getPillClass(condStatus)}`;

        document.getElementById('resVisibleIssue').textContent = data.visible_damage_or_symptoms || data.visible_abnormalities || "None detected";
        document.getElementById('resExplanation').textContent = data.explanation || "No visual detail provided.";

        const envData = data.environment || {};
        updateEnvItem('resTempPill', 'resTempMeta', envData.temperature, '°C');
        updateEnvItem('resHumidityPill', 'resHumidityMeta', envData.humidity, '%');
        updateEnvItem('resMoisturePill', 'resMoistureMeta', envData.soil_moisture, '%');
        updateEnvItem('resPhPill', 'resPhMeta', envData.ph, '');

        const cropDetails = data.crop_details || {};
        document.getElementById('resSuitableSoil').textContent = cropDetails.soil_suitability || "—";
        document.getElementById('resPreferredPh').textContent = cropDetails.preferred_ph || "—";
        document.getElementById('resWaterNeed').textContent = cropDetails.water_need || "—";
        document.getElementById('resUsefulness').textContent = cropDetails.usefulness || "—";

        const growthBlock = document.getElementById('growthStagesBlock');
        const stagesContainer = document.getElementById('resGrowthStages');
        stagesContainer.innerHTML = '';

        if (data.growth_guidance && data.growth_guidance.length > 0) {
            growthBlock.classList.remove('hidden');
            data.growth_guidance.forEach(stage => {
                const span = document.createElement('span');
                span.className = 'stage-tag';
                span.textContent = stage;
                stagesContainer.appendChild(span);
            });
        } else {
            growthBlock.classList.add('hidden');
        }

        const irrData = data.irrigation || {};
        const curMoisture = envData.soil_moisture?.current;
        document.getElementById('resCurrentMoistureVal').textContent = (curMoisture !== undefined && curMoisture !== "No live sensor data") ? `${curMoisture}%` : "No live sensor data";
        document.getElementById('resIrrigationRecommendation').textContent = irrData.recommendation || "—";

        document.getElementById('resAiRecommendation').textContent = data.recommendation || "—";
    }

    function updateEnvItem(pillId, metaId, envObj, unit) {
        const pill = document.getElementById(pillId);
        const meta = document.getElementById(metaId);

        if (!envObj) return;

        const rating = envObj.rating || "UNKNOWN";
        pill.textContent = rating;
        pill.className = `pill ${getPillClass(rating)}`;

        const curVal = envObj.current;
        const curText = (curVal !== undefined && curVal !== "No live sensor data") ? `${curVal}${unit}` : "No live sensor data";
        const idealVal = envObj.ideal || "—";
        meta.textContent = `Current: ${curText} | Ideal: ${idealVal}`;
    }

    function getPillClass(statusStr) {
        const s = statusStr.toUpperCase();
        if (s.includes('OPTIMAL') || s.includes('GOOD') || s.includes('HEALTHY')) return 'pill-success';
        if (s.includes('MODERATE') || s.includes('FAIR')) return 'pill-warning';
        if (s.includes('NEEDS ATTENTION') || s.includes('UNSUITABLE') || s.includes('POOR') || s.includes('DAMAGED') || s.includes('EXCESS') || s.includes('REQUIRED')) return 'pill-danger';
        return 'pill-neutral';
    }

    function showError(msg) {
        errorMessage.textContent = msg;
        errorAlert.classList.remove('hidden');
        errorAlert.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    window.hideError = function() {
        errorAlert.classList.add('hidden');
    };
});
