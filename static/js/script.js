let reviews = [];
let editingReviewId = null;

const $ = (id) => document.getElementById(id);

function escapeHTML(value) {
    return String(value ?? "").replace(/[&<>"']/g, (character) => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#039;"
    })[character]);
}

function showMessage(elementId, message, isError = false) {
    const element = $(elementId);
    if (!element) return;

    element.textContent = message;
    element.className = isError ? "message error" : "message success";
}

function formatDate(value) {
    if (!value) return "—";

    const date = new Date(value.replace(" ", "T"));
    if (Number.isNaN(date.getTime())) return value;

    return date.toLocaleString();
}

function getIssueText(issue) {
    if (typeof issue === "string") return issue;

    return issue.description ||
        issue.issue ||
        issue.explanation ||
        "Issue detected";
}

function getSuggestionText(suggestion) {
    if (typeof suggestion === "string") return suggestion;

    return suggestion.suggestion ||
        suggestion.description ||
        "Review this content.";
}

function showPage(pageId) {
    document.querySelectorAll(".page").forEach((page) => {
        page.classList.toggle("active", page.id === pageId);
    });

    document.querySelectorAll(".sidebar-menu a").forEach((link) => {
        link.classList.toggle(
            "active",
            link.dataset.page === pageId
        );
    });
}

document.querySelectorAll(".sidebar-menu a").forEach((link) => {
    link.addEventListener("click", (event) => {
        event.preventDefault();
        showPage(link.dataset.page);
    });
});

function updateDashboard() {
    const total = reviews.length;
    const pending = reviews.filter(r => r.status === "Pending").length;
    const approved = reviews.filter(r => r.status === "Approved").length;
    const issueCount = reviews.reduce(
        (sum, review) => sum + (review.issues || []).length,
        0
    );
    const averageScore = total ? Math.round(reviews.reduce((sum, r) => sum + Number(r.compliance_score ?? 100), 0) / total) : 0;

    $("totalReviews").textContent = total;
    $("pendingReviews").textContent = pending;
    $("approvedReviews").textContent = approved;
    $("totalIssues").textContent = issueCount;

    $("reportReviews").textContent = total;
    $("reportApproved").textContent = approved;
    $("reportIssues").textContent = issueCount;
    $("reportSummary").textContent = total
        ? `${total} reviews recorded · ${approved} approved · ${pending} pending · ${issueCount} findings · Average compliance score: ${averageScore}%.`
        : "No report data available yet.";

    renderRecentReviews();
    renderHistory();
    renderApprovals();
}

function renderRecentReviews() {
    const body = $("recentReviews");

    if (!reviews.length) {
        body.innerHTML = '<tr><td colspan="4">No reviews yet.</td></tr>';
        return;
    }

    body.innerHTML = reviews.slice(0, 5).map(review => `
        <tr>
            <td>${escapeHTML(review.title)}</td>
            <td>${escapeHTML(review.content_type)}</td>
            <td>${escapeHTML(formatDate(review.created_at))}</td>
            <td><span class="status ${review.status === "Approved" ? "approved" : "pending"}">${escapeHTML(review.status)}</span></td>
        </tr>
    `).join("");
}

function renderHistory() {
    const body = $("historyList");

    if (!reviews.length) {
        body.innerHTML = '<tr><td colspan="6">No reviews yet.</td></tr>';
        return;
    }

    body.innerHTML = reviews.map(review => `
        <tr>
            <td>${escapeHTML(review.title)}</td>
            <td>${escapeHTML(review.content_type)}</td>
            <td>${escapeHTML(formatDate(review.created_at))}</td>
            <td><span class="status ${review.status === "Approved" ? "approved" : "pending"}">${escapeHTML(review.status)}</span></td>
            <td>${Number(review.compliance_score ?? 100)}%</td>
            <td class="action-cell">
                <button class="action-btn" data-action="report" data-id="${review.id}">Report</button>
                <button class="action-btn edit-btn" data-action="edit" data-id="${review.id}">Edit</button>
                <button class="action-btn delete-btn" data-action="delete" data-id="${review.id}">Delete</button>
            </td>
        </tr>
    `).join("");
}

function renderApprovals() {
    const container = $("approvalList");
    const pending = reviews.filter(review => review.status === "Pending");

    if (!pending.length) {
        container.innerHTML = "<p>No pending reviews.</p>";
        return;
    }

    container.innerHTML = pending.map(review => `
        <div class="review-item">
            <div>
                <h3>${escapeHTML(review.title)}</h3>
                <p>${escapeHTML(review.content_type)} · ${escapeHTML(formatDate(review.created_at))}</p>
                <p>${(review.issues || []).length} issue(s) detected</p>
            </div>
            <button class="action-btn approve-btn" data-action="approve" data-id="${review.id}">
                Approve
            </button>
        </div>
    `).join("");
}

function displayAnalysis(review) {
    const container = $("analysisResult");

    if (!review) {
        container.innerHTML = "<p>No analysis available yet.</p>";
        $("issuesList").innerHTML = "<p>No issues to display.</p>";
        $("suggestionsList").innerHTML = "<p>No suggestions to display.</p>";
        return;
    }

    container.innerHTML = `
        <div class="analysis-header">
            <h3>${escapeHTML(review.title)}</h3>
            <span class="status ${review.status === "Approved" ? "approved" : "pending"}">${escapeHTML(review.status)}</span>
        </div>
        <p><strong>Content Type:</strong> ${escapeHTML(review.content_type)}</p>
        <p><strong>Review ID:</strong> ${review.id}</p>
        <div class="score-panel"><span>Compliance Score</span><strong>${Number(review.compliance_score ?? 100)}%</strong><small>${escapeHTML((review.report || {}).grade || "Assessment")}</small></div>
        <p><strong>AI Status:</strong> ${review.gemini_success ? "Gemini AI + rules review completed" : "Rules-based fallback (AI connection unavailable)"}</p>
        <p>${escapeHTML(review.analysis || "No additional AI summary available.")}</p>
        <p class="muted">${escapeHTML(review.gemini_message || "")}</p>
        <div class="submitted-content">
            <h4>Visual Brand Analysis</h4>
            <p>${escapeHTML((review.visual_analysis || {}).message || "No visual analysis was saved.")}</p>
            ${((review.visual_analysis || {}).palette || []).length ? `<div class="palette-row">${review.visual_analysis.palette.map(c => `<span title="${escapeHTML(c.hex)}" style="background:${escapeHTML(c.hex)}"></span><small>${escapeHTML(c.hex)} · ${escapeHTML(c.share)}%</small>`).join("")}</div>` : ""}
            ${((review.visual_analysis || {}).checks || []).map(c => `<p><strong>${escapeHTML(c.name)}:</strong> ${escapeHTML(c.status)} — ${escapeHTML(c.details)}</p>`).join("")}
        </div>
        <div class="submitted-content">
            <h4>Submitted Content</h4>
            <p>${escapeHTML(review.content)}</p>
        </div>
    `;

    const issues = review.issues || [];
    $("issuesList").innerHTML = issues.length
        ? issues.map((issue, index) => `
            <div class="result-item issue-item">
                <strong>Issue ${index + 1}</strong>
                ${typeof issue === "object" ? `<span class="severity-label severity-${escapeHTML(String(issue.severity || "Medium").toLowerCase())}">${escapeHTML(issue.severity || "Medium")}</span><small>${escapeHTML(issue.category || "Brand review")} · ${escapeHTML(issue.source || "Review")}</small>` : ""}
                <p>${escapeHTML(getIssueText(issue))}</p>
                ${issue && typeof issue === "object" && issue.explanation ? `<p>${escapeHTML(issue.explanation)}</p>` : ""}
            </div>
        `).join("")
        : "<p>No issues detected.</p>";

    const report = review.report || {};
    $("reportDetails").innerHTML = `<p><strong>Review #${review.id}</strong> · ${escapeHTML(report.generated_at || review.created_at || "")}</p><p><strong>Score:</strong> ${Number(review.compliance_score ?? 100)}% · <strong>Grade:</strong> ${escapeHTML(report.grade || "—")}</p><p><strong>Findings:</strong> ${Number(report.issue_count ?? issues.length)} · <strong>High severity:</strong> ${Number(report.high_severity ?? 0)}</p>${(report.sections || []).map(section => `<p><strong>${escapeHTML(section.name)}:</strong> ${escapeHTML(section.result)}</p>`).join("")}<h4>Review activity</h4><div id="reviewEventList">Loading activity...</div>`;
    loadReviewEvents(review.id);

    const suggestions = review.suggestions || [];
    $("suggestionsList").innerHTML = suggestions.length
        ? suggestions.map((suggestion, index) => `
            <div class="result-item suggestion-item">
                <strong>Suggestion ${index + 1}</strong>
                <p>${escapeHTML(getSuggestionText(suggestion))}</p>
            </div>
        `).join("")
        : "<p>No correction suggestions available.</p>";
}

async function readFileAsDataURL(file) {
    if (!file) return "";
    if (file.size > 5 * 1024 * 1024) throw new Error("Each image must be smaller than 5 MB.");
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(String(reader.result || ""));
        reader.onerror = () => reject(new Error("Could not read the selected image."));
        reader.readAsDataURL(file);
    });
}

async function loadReviewEvents(reviewId) {
    const target = $("reviewEventList");
    if (!target) return;
    try {
        const response = await fetch(`/review/${reviewId}/events`);
        const events = await response.json();
        target.innerHTML = events.length ? events.map(item => `<p><strong>${escapeHTML(item.event)}</strong> · ${escapeHTML(formatDate(item.created_at))}<br>${escapeHTML(item.details || "")}</p>`).join("") : "<p>No activity recorded.</p>";
    } catch (_) { target.textContent = "Activity history could not be loaded."; }
}

async function loadReviews() {
    try {
        const response = await fetch("/reviews");

        if (!response.ok) {
            throw new Error("Could not load reviews.");
        }

        reviews = await response.json();

        updateDashboard();

        if (reviews.length) {
            displayAnalysis(reviews[0]);
        } else {
            displayAnalysis(null);
        }
    } catch (error) {
        console.error(error);
        $("historyList").innerHTML =
            '<tr><td colspan="6">Could not load review history. Refresh the page.</td></tr>';
    }
}

$("contentForm").addEventListener("submit", async (event) => {
    event.preventDefault();

    const title = $("contentTitle").value.trim();
    const content = $("contentText").value.trim();
    const content_type = $("contentType").value;

    if (!title || !content) {
        showMessage("formMessage", "Please enter both title and content.", true);
        return;
    }

    const button = $("submitContentBtn");
    button.disabled = true;
    button.textContent = editingReviewId ? "Updating..." : "Analyzing...";

    showMessage("formMessage", "Review is being processed. Please wait.");

    try {
        const url = editingReviewId
            ? `/review/${editingReviewId}`
            : "/analyze";

        const method = editingReviewId ? "PUT" : "POST";

        const imageData = await readFileAsDataURL($("creativeImage").files[0]);
        const savedGuidelines = (() => { try { return JSON.parse(localStorage.getItem("brandGuardGuidelines") || "{}"); } catch (_) { return {}; } })();
        const response = await fetch(url, {
            method,
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                title,
                content,
                content_type,
                image_data: imageData,
                logo_reference_data: savedGuidelines.logoReferenceData || "",
                guidelines: savedGuidelines
            })
        });

        const result = await response.json();

        if (!response.ok || !result.success) {
            throw new Error(result.message || "Review could not be completed.");
        }

        const savedReview = result.review;

        resetEditMode();
        $("contentForm").reset();

        showMessage("formMessage", result.message || "Review completed.");

        await loadReviews();
        displayAnalysis(savedReview);
        showPage("analysis");

    } catch (error) {
        showMessage("formMessage", error.message, true);
    } finally {
        button.disabled = false;
        button.textContent = "Analyze Content";
    }
});

function startEdit(reviewId) {
    const review = reviews.find(item => item.id === reviewId);

    if (!review) {
        alert("Review not found.");
        return;
    }

    editingReviewId = reviewId;

    $("contentTitle").value = review.title;
    $("contentType").value = review.content_type;
    $("contentText").value = review.content;

    $("submissionHeading").textContent = "Edit & Re-analyze Content";
    $("submitContentBtn").textContent = "Update & Re-analyze";
    $("cancelEditBtn").hidden = false;

    showMessage("formMessage", `Editing review #${reviewId}.`);

    showPage("submission");
}

function resetEditMode() {
    editingReviewId = null;

    $("submissionHeading").textContent = "Content Submission";
    $("submitContentBtn").textContent = "Analyze Content";
    $("cancelEditBtn").hidden = true;
}

$("cancelEditBtn").addEventListener("click", () => {
    $("contentForm").reset();
    resetEditMode();
    showMessage("formMessage", "Edit cancelled.");
});

async function deleteReview(reviewId) {
    const review = reviews.find(item => item.id === reviewId);

    if (!review) {
        alert("Review not found.");
        return;
    }

    const confirmed = confirm(
        `Delete "${review.title}" (Review #${reviewId}) permanently?`
    );

    if (!confirmed) return;

    try {
        const response = await fetch(`/review/${reviewId}`, {
            method: "DELETE"
        });

        const result = await response.json();

        if (!response.ok || !result.success) {
            throw new Error(result.message || "Delete failed.");
        }

        if (editingReviewId === reviewId) {
            $("contentForm").reset();
            resetEditMode();
        }

        await loadReviews();
        alert(result.message);

    } catch (error) {
        alert(error.message);
    }
}

async function approveReview(reviewId) {
    try {
        const response = await fetch(`/approve/${reviewId}`, {
            method: "POST"
        });

        const result = await response.json();

        if (!response.ok || !result.success) {
            throw new Error(result.message || "Approval failed.");
        }

        await loadReviews();
        alert(result.message);

    } catch (error) {
        alert(error.message);
    }
}

document.addEventListener("click", (event) => {
    const button = event.target.closest("[data-action]");
    if (!button) return;

    const action = button.dataset.action;
    const reviewId = Number(button.dataset.id);

    if (!Number.isInteger(reviewId)) return;

    if (action === "edit") startEdit(reviewId);
    if (action === "delete") deleteReview(reviewId);
    if (action === "approve") approveReview(reviewId);
    if (action === "report") { const selected = reviews.find(item => item.id === reviewId); if (selected) { displayAnalysis(selected); showPage("analysis"); } }
});

$("guidelinesForm").addEventListener("submit", (event) => {
    event.preventDefault();

    const guidelines = {
        brandName: $("brandName").value,
        brandTone: $("brandTone").value,
        approvedKeywords: $("approvedKeywords").value,
        restrictedWords: $("restrictedWords").value,
        brandRules: $("brandRules").value,
        requiredDisclaimer: $("requiredDisclaimer").value,
        brandColors: $("brandColors").value,
        logoReferenceData: JSON.parse(localStorage.getItem("brandGuardGuidelines") || "{}").logoReferenceData || ""
    };

    const logoFile = $("brandLogoFile").files[0];
    if (logoFile) {
        if (logoFile.size > 2 * 1024 * 1024) { showMessage("guidelinesMessage", "Please choose a logo image smaller than 2 MB.", true); return; }
        readFileAsDataURL(logoFile).then(data => {
            guidelines.logoReferenceData = data;
            localStorage.setItem("brandGuardGuidelines", JSON.stringify(guidelines));
            showMessage("guidelinesMessage", "Brand guidelines and logo reference saved in this browser.");
        }).catch(error => showMessage("guidelinesMessage", error.message, true));
    } else {
        localStorage.setItem("brandGuardGuidelines", JSON.stringify(guidelines));
        showMessage("guidelinesMessage", "Brand guidelines saved in this browser.");
    }

    /* message is set after optional logo processing */
    /* keep this form local so existing browser-based settings remain compatible */
});

function loadGuidelines() {
    const saved = localStorage.getItem("brandGuardGuidelines");
    if (!saved) return;

    try {
        const data = JSON.parse(saved);

        $("brandName").value = data.brandName || "";
        $("brandTone").value = data.brandTone || "";
        $("approvedKeywords").value = data.approvedKeywords || "";
        $("restrictedWords").value = data.restrictedWords || "";
        $("brandRules").value = data.brandRules || "";
        $("requiredDisclaimer").value = data.requiredDisclaimer || "";
        $("brandColors").value = data.brandColors || "";

    } catch (error) {
        console.error("Could not load saved guidelines.", error);
    }
}

document.addEventListener("DOMContentLoaded", () => {
    loadGuidelines();
    loadReviews();
});