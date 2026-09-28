// TRACEFUSION - Forensic Workstation Interactive Engine

document.addEventListener("DOMContentLoaded", () => {
    initKeyboardShortcuts();
    initCommandPalette();
    initVerificationHandlers();
});

// Keyboard Shortcuts System
function initKeyboardShortcuts() {
    document.addEventListener("keydown", (e) => {
        // Ctrl+K: Command Palette
        if ((e.ctrlKey || e.metaKey) && e.key === "k") {
            e.preventDefault();
            toggleCommandPalette();
        }

        // Ctrl+Shift+T: Timeline
        if ((e.ctrlKey || e.metaKey) && e.shiftKey && (e.key === "T" || e.key === "t")) {
            e.preventDefault();
            const activeCaseLink = document.querySelector("#nav-timeline");
            if (activeCaseLink) window.location.href = activeCaseLink.href;
        }

        // Ctrl+Shift+E: Evidence
        if ((e.ctrlKey || e.metaKey) && e.shiftKey && (e.key === "E" || e.key === "e")) {
            e.preventDefault();
            const activeCaseLink = document.querySelector("#nav-evidence");
            if (activeCaseLink) window.location.href = activeCaseLink.href;
        }

        // Ctrl+Shift+R: Reports
        if ((e.ctrlKey || e.metaKey) && e.shiftKey && (e.key === "R" || e.key === "r")) {
            e.preventDefault();
            const activeCaseLink = document.querySelector("#nav-reports");
            if (activeCaseLink) window.location.href = activeCaseLink.href;
        }

        // Ctrl+Shift+N: New Case Modal
        if ((e.ctrlKey || e.metaKey) && e.shiftKey && (e.key === "N" || e.key === "n")) {
            e.preventDefault();
            openNewCaseModal();
        }

        // Escape: Close all modals & drawers
        if (e.key === "Escape") {
            closeAllDrawers();
            closeCommandPalette();
            closeNewCaseModal();
            document.querySelectorAll(".modal-backdrop").forEach(m => m.classList.remove("show"));
        }
    });
}

// Case Switching & New Case Modal Handling
function handleCaseSelection(selectElem) {
    const val = selectElem.value;
    if (!val) return;
    if (val === "__NEW_CASE__") {
        selectElem.value = "";
        openNewCaseModal();
    } else {
        window.location.href = "/cases/" + val + "/select";
    }
}

function openNewCaseModal() {
    const modal = document.getElementById("global-new-case-modal");
    if (modal) {
        modal.classList.add("show");
        const input = modal.querySelector('input[name="case_number"]');
        if (input) input.focus();
    }
}

function closeNewCaseModal() {
    const modal = document.getElementById("global-new-case-modal");
    if (modal) modal.classList.remove("show");
}

// Command Palette (Ctrl+K)
function toggleCommandPalette() {
    const palette = document.getElementById("cmd-palette-backdrop");
    if (!palette) return;
    if (palette.classList.contains("show")) {
        closeCommandPalette();
    } else {
        palette.classList.add("show");
        const input = document.getElementById("cmd-palette-input");
        if (input) {
            input.value = "";
            input.focus();
            filterCommands("");
        }
    }
}

function closeCommandPalette() {
    const palette = document.getElementById("cmd-palette-backdrop");
    if (palette) palette.classList.remove("show");
}

function filterCommands(query) {
    const items = document.querySelectorAll(".cmd-item");
    const q = (query || "").toLowerCase();
    items.forEach(item => {
        const text = item.innerText.toLowerCase();
        if (text.includes(q)) {
            item.style.display = "flex";
        } else {
            item.style.display = "none";
        }
    });
}

// Evidence Detail Drawer
function openEventDrawer(eventId) {
    const drawer = document.getElementById("detail-drawer");
    if (!drawer) return;

    // Show loading skeleton
    const titleElem = document.getElementById("drawer-title");
    const bodyElem = document.getElementById("drawer-content");
    titleElem.innerText = `Forensic Event #TL-${eventId}`;
    bodyElem.innerHTML = `<div style="text-align:center; padding: 40px; color: var(--text-dim);"><p>Reading forensic evidence record from case database...</p></div>`;

    drawer.classList.add("open");

    fetch(`/timeline/event/${eventId}`)
        .then(r => r.json())
        .then(res => {
            if (res.success && res.data) {
                renderEventDetails(res.data);
            } else {
                bodyElem.innerHTML = `<p style="color: var(--accent-red)">Failed to load event details.</p>`;
            }
        })
        .catch(err => {
            bodyElem.innerHTML = `<p style="color: var(--accent-red)">Error: ${err.message}</p>`;
        });
}

function renderEventDetails(ev) {
    const titleElem = document.getElementById("drawer-title");
    const bodyElem = document.getElementById("drawer-content");

    titleElem.innerText = `${ev.browser} ${ev.event_type}`;

    let metaRows = "";
    if (ev.metadata && Object.keys(ev.metadata).length > 0) {
        for (const [k, v] of Object.entries(ev.metadata)) {
            metaRows += `<div class="meta-row"><span class="meta-key">${k}:</span><span class="meta-val">${v}</span></div>`;
        }
    } else {
        metaRows = `<div class="meta-row"><span class="meta-key">Metadata:</span><span class="meta-val">None</span></div>`;
    }

    bodyElem.innerHTML = `
        <div class="meta-group">
            <div class="meta-group-title">Primary Forensic Coordinates</div>
            <div class="meta-row"><span class="meta-key">Event ID:</span><span class="meta-val">TL-${ev.id}</span></div>
            <div class="meta-row"><span class="meta-key">Browser Platform:</span><span class="meta-val"><b>${ev.browser}</b> (${ev.profile})</span></div>
            <div class="meta-row"><span class="meta-key">Artifact Category:</span><span class="meta-val">${ev.artifact_type}</span></div>
            <div class="meta-row"><span class="meta-key">Event Action:</span><span class="meta-val">${ev.event_type}</span></div>
            <div class="meta-row"><span class="meta-key">Normalized Timestamp:</span><span class="meta-val" style="color:var(--accent-cyan); font-weight:600;">${ev.timestamp_utc || "N/A"}</span></div>
            <div class="meta-row"><span class="meta-key">Raw Source Timestamp:</span><span class="meta-val">${ev.timestamp_raw || "N/A"}</span></div>
            <div class="meta-row"><span class="meta-key">Confidence Level:</span><span class="meta-val"><span class="status-pill pill-info">${ev.confidence}</span></span></div>
        </div>

        <div class="meta-group">
            <div class="meta-group-title">Observed Resource & Content</div>
            <div class="meta-row"><span class="meta-key">Title / Identifier:</span><span class="meta-val">${ev.title || "Untitled"}</span></div>
            <div class="meta-row"><span class="meta-key">Target Domain:</span><span class="meta-val" style="color:var(--accent-blue)">${ev.domain || "N/A"}</span></div>
            <div style="margin-top:6px;">
                <span class="meta-key" style="display:block; margin-bottom:4px;">Full Target URL:</span>
                <div style="background:var(--bg-surface); padding:8px; border-radius:4px; font-family:var(--font-mono); font-size:11px; word-break:break-all; color:#e2e8f0;">
                    ${ev.url || "N/A"}
                </div>
            </div>
        </div>

        <div class="meta-group">
            <div class="meta-group-title">Evidence Provenance & Integrity</div>
            <div class="meta-row"><span class="meta-key">Source Database:</span><span class="meta-val">${ev.source_file || "Unknown"}</span></div>
            <div class="meta-row"><span class="meta-key">Baseline SHA-256:</span><span class="meta-val" style="font-size:10px;">${ev.source_hash || "N/A"}</span></div>
        </div>

        <div class="meta-group">
            <div class="meta-group-title">Parser Raw Metadata Extract</div>
            ${metaRows}
        </div>
    `;
}

function closeAllDrawers() {
    const drawer = document.getElementById("detail-drawer");
    if (drawer) drawer.classList.remove("open");
}

// Single-file Hash Verification AJAX
function initVerificationHandlers() {
    document.querySelectorAll(".btn-verify-hash").forEach(btn => {
        btn.addEventListener("click", function (e) {
            e.preventDefault();
            const fileId = this.dataset.fileId;
            const statusCell = document.getElementById(`status-cell-${fileId}`);

            if (statusCell) {
                statusCell.innerHTML = `<span class="status-pill pill-warning">VERIFYING...</span>`;
            }

            fetch(`/evidence/file/${fileId}/verify`, { method: "POST" })
                .then(r => r.json())
                .then(res => {
                    if (res.success && res.data) {
                        const isValid = res.data.is_valid;
                        if (statusCell) {
                            if (isValid) {
                                statusCell.innerHTML = `<span class="status-pill pill-success">✓ INTEGRITY VERIFIED</span>`;
                            } else {
                                statusCell.innerHTML = `<span class="status-pill pill-danger">⚠ INTEGRITY MISMATCH</span>`;
                            }
                        }
                    }
                })
                .catch(() => {
                    if (statusCell) {
                        statusCell.innerHTML = `<span class="status-pill pill-danger">ERROR</span>`;
                    }
                });
        });
    });
}
