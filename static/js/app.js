document.addEventListener("DOMContentLoaded", function () {
    // -------------------------------------------------------------
    // UI Elements
    // -------------------------------------------------------------
    const dropZone = document.getElementById("drop-zone");
    const fileInput = document.getElementById("policy-file-input");
    const browseBtn = document.getElementById("browse-btn");
    const fileListQueue = document.getElementById("file-list-queue");
    const fileCountBadge = document.getElementById("file-count-badge");
    const queueEmptyText = document.getElementById("queue-empty-text");
    const analyzeBtn = document.getElementById("analyze-btn");
    const analyzeIcon = document.getElementById("analyze-icon");
    const analyzeSpinner = document.getElementById("analyze-spinner");
    
    const loadSamplesBtn = document.getElementById("load-samples-btn");
    const loadSamplesEmptyBtn = document.getElementById("load-samples-empty-btn");
    
    const obligationsFilter = document.getElementById("obligations-filter");
    const obligationsRows = document.querySelectorAll(".obligation-row");

    let queuedFiles = [];

    // -------------------------------------------------------------
    // Drag & Drop Handlers
    // -------------------------------------------------------------
    if (dropZone) {
        // Prevent default behaviors
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, preventDefaults, false);
        });

        function preventDefaults(e) {
            e.preventDefault();
            e.stopPropagation();
        }

        // Highlight drop zone
        ['dragenter', 'dragover'].forEach(eventName => {
            dropZone.addEventListener(eventName, () => dropZone.classList.add('dragover'), false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, () => dropZone.classList.remove('dragover'), false);
        });

        // Handle dropped files
        dropZone.addEventListener('drop', (e) => {
            const dt = e.dataTransfer;
            const files = dt.files;
            handleFiles(files);
        });
        
        // Handle browse button click
        browseBtn.addEventListener('click', () => fileInput.click());
        dropZone.addEventListener('click', (e) => {
            if (e.target !== browseBtn && !browseBtn.contains(e.target)) {
                fileInput.click();
            }
        });
        
        fileInput.addEventListener('change', (e) => {
            handleFiles(e.target.files);
        });
    }

    function handleFiles(files) {
        for (let i = 0; i < files.length; i++) {
            const file = files[i];
            const ext = file.name.split('.').pop().toLowerCase();
            
            // Check file type (.txt or .md)
            if (ext === 'txt' || ext === 'md') {
                // Prevent duplicate files in the queue
                if (!queuedFiles.some(f => f.name === file.name && f.size === file.size)) {
                    queuedFiles.push(file);
                }
            } else {
                alert(`File "${file.name}" rejected. Only .txt and .md files are supported.`);
            }
        }
        updateQueueUI();
    }

    function updateQueueUI() {
        if (queuedFiles.length === 0) {
            fileListQueue.innerHTML = '';
            fileListQueue.appendChild(queueEmptyText);
            fileCountBadge.textContent = '0 Files';
            fileCountBadge.className = 'badge bg-cyber-cyan-muted text-cyber-cyan font-mono';
            analyzeBtn.disabled = true;
        } else {
            fileListQueue.innerHTML = '';
            queuedFiles.forEach((file, index) => {
                const fileRow = document.createElement('div');
                fileRow.className = 'd-flex justify-content-between align-items-center mb-1.5 p-2 rounded bg-cyber-card-dark border border-cyber-dark-border small';
                
                const fileInfo = document.createElement('div');
                fileInfo.className = 'd-flex align-items-center overflow-hidden me-2';
                
                const icon = document.createElement('i');
                icon.className = file.name.endsWith('.md') ? 'bi bi-markdown text-cyber-cyan me-2 fs-5' : 'bi bi-filetype-txt text-cyber-cyan me-2 fs-5';
                
                const name = document.createElement('span');
                name.className = 'text-truncate text-cyber-light font-mono';
                name.textContent = file.name;
                
                fileInfo.appendChild(icon);
                fileInfo.appendChild(name);
                
                const deleteBtn = document.createElement('button');
                deleteBtn.className = 'btn btn-link text-cyber-red p-0 border-0 fs-6 line-height-1';
                deleteBtn.innerHTML = '<i class="bi bi-x-circle-fill"></i>';
                deleteBtn.type = 'button';
                deleteBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    queuedFiles.splice(index, 1);
                    updateQueueUI();
                });
                
                fileRow.appendChild(fileInfo);
                fileRow.appendChild(deleteBtn);
                fileListQueue.appendChild(fileRow);
            });
            
            fileCountBadge.textContent = `${queuedFiles.length} File(s)`;
            fileCountBadge.className = 'badge bg-cyber-cyan text-dark font-mono';
            analyzeBtn.disabled = false;
        }
    }

    // -------------------------------------------------------------
    // Upload & Analysis Action
    // -------------------------------------------------------------
    if (analyzeBtn) {
        analyzeBtn.addEventListener('click', () => {
            if (queuedFiles.length === 0) return;
            
            // Set Loading state
            analyzeBtn.disabled = true;
            analyzeIcon.classList.add('d-none');
            analyzeSpinner.classList.remove('d-none');
            
            const formData = new FormData();
            queuedFiles.forEach(file => {
                formData.append('policies', file);
            });
            
            fetch('/upload', {
                method: 'POST',
                body: formData
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    window.location.reload();
                } else {
                    alert(data.error || 'Failed to complete analysis.');
                    resetAnalyzeBtn();
                }
            })
            .catch(err => {
                console.error(err);
                alert('Analysis failed. Check backend console logs.');
                resetAnalyzeBtn();
            });
        });
    }

    function resetAnalyzeBtn() {
        analyzeBtn.disabled = false;
        analyzeIcon.classList.remove('d-none');
        analyzeSpinner.classList.add('d-none');
    }

    // -------------------------------------------------------------
    // Load Sample Suite Action
    // -------------------------------------------------------------
    const sampleLoadHandler = () => {
        const btn = loadSamplesBtn || loadSamplesEmptyBtn;
        if (!btn) return;
        
        btn.disabled = true;
        const origContent = btn.innerHTML;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span> Loading...';
        
        fetch('/load-samples', {
            method: 'POST'
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                window.location.reload();
            } else {
                alert(data.error || 'Failed to load samples.');
                btn.disabled = false;
                btn.innerHTML = origContent;
            }
        })
        .catch(err => {
            console.error(err);
            alert('Failed to load sample suite.');
            btn.disabled = false;
            btn.innerHTML = origContent;
        });
    };

    if (loadSamplesBtn) loadSamplesBtn.addEventListener('click', sampleLoadHandler);
    if (loadSamplesEmptyBtn) loadSamplesEmptyBtn.addEventListener('click', sampleLoadHandler);

    // -------------------------------------------------------------
    // Obligations search filter
    // -------------------------------------------------------------
    if (obligationsFilter) {
        obligationsFilter.addEventListener('input', function (e) {
            const query = e.target.value.toLowerCase().trim();
            obligationsRows.forEach(row => {
                const text = row.getAttribute('data-sentence') || '';
                if (text.includes(query)) {
                    row.classList.remove('d-none');
                } else {
                    row.classList.add('d-none');
                }
            });
        });
    }

    // -------------------------------------------------------------
    // Chart.js Visualizations Setup
    // -------------------------------------------------------------
    if (window.categoryChartLabels && window.categoryChartData) {
        const pieCtx = document.getElementById('categoriesPieChart');
        if (pieCtx) {
            new Chart(pieCtx.getContext('2d'), {
                type: 'pie',
                data: {
                    labels: window.categoryChartLabels,
                    datasets: [{
                        data: window.categoryChartData,
                        backgroundColor: [
                            'rgba(0, 240, 255, 0.7)',  // Password (Cyan)
                            'rgba(182, 106, 251, 0.7)', // Encryption (Purple)
                            'rgba(38, 128, 235, 0.7)',  // Access Control (Blue)
                            'rgba(255, 189, 0, 0.7)',   // Data Retention (Amber)
                            'rgba(255, 106, 193, 0.7)', // Logging (Pink)
                            'rgba(79, 90, 107, 0.7)',   // Network (Gray)
                            'rgba(5, 255, 196, 0.7)',   // Backup (Green)
                            'rgba(255, 0, 85, 0.7)',    // MFA (Red)
                            'rgba(142, 142, 147, 0.7)'  // Others
                        ],
                        borderColor: '#121520',
                        borderWidth: 2
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'right',
                            labels: {
                                color: '#7d8ea7',
                                font: {
                                    family: 'Share Tech Mono',
                                    size: 10
                                }
                            }
                        }
                    }
                }
            });
        }
    }

    if (window.flawsLabels && window.flawsData) {
        const barCtx = document.getElementById('issuesBarChart');
        if (barCtx) {
            new Chart(barCtx.getContext('2d'), {
                type: 'bar',
                data: {
                    labels: window.flawsLabels,
                    datasets: [{
                        label: 'Count',
                        data: window.flawsData,
                        backgroundColor: [
                            'rgba(255, 0, 85, 0.75)',    // Direct Conflicts
                            'rgba(255, 189, 0, 0.75)',   // Retention Mismatches
                            'rgba(255, 159, 64, 0.75)',  // Redundant Sentences
                            'rgba(182, 106, 251, 0.75)', // Stale Files
                            'rgba(0, 240, 255, 0.75)'    // Deprecated Terms
                        ],
                        borderColor: '#121520',
                        borderWidth: 1.5
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: {
                                precision: 0,
                                color: '#7d8ea7',
                                font: {
                                    family: 'Share Tech Mono'
                                }
                            },
                            grid: {
                                color: 'rgba(29, 35, 54, 0.5)'
                            }
                        },
                        x: {
                            ticks: {
                                color: '#7d8ea7',
                                font: {
                                    family: 'Share Tech Mono',
                                    size: 9
                                }
                            },
                            grid: {
                                display: false
                            }
                        }
                    },
                    plugins: {
                        legend: {
                            display: false
                        }
                    }
                }
            });
        }
    }
});
