/* 短视频搬运工作流 v2 — 逐步骤工作流 */

// === 全局状态 ===
const state = {
    extract: { videoPath: "", text: "", segments: [], title: "", duration: 0 },
    rewrite: { text: "", originalText: "" },
    tts: { audioPath: "", duration: 0 },
    video: { outputPath: "", duration: 0 },
    subtitle: { srtPath: "", segments: [], fullText: "" },
    cover: { coverPath: "" },
    faceImagePath: null,
    voices: [],
    autoPollTimer: null,
};

// === 初始化 ===
document.addEventListener("DOMContentLoaded", () => {
    loadVoices();
    setupFaceUpload();
});

async function loadVoices() {
    try {
        const resp = await fetch("/api/steps/voices");
        const data = await resp.json();
        state.voices = data.voices || [];
        const sel = document.getElementById("tts-voice");
        sel.innerHTML = "";
        const groups = { male: "男声", female: "女声" };
        for (const [gender, label] of Object.entries(groups)) {
            const optgroup = document.createElement("optgroup");
            optgroup.label = label;
            state.voices.filter(v => v.gender === gender).forEach(v => {
                const opt = document.createElement("option");
                opt.value = v.id;
                opt.textContent = `${v.name} — ${v.style}`;
                optgroup.appendChild(opt);
            });
            sel.appendChild(optgroup);
        }
    } catch (e) {
        console.error("加载音色失败:", e);
    }
}

function setupFaceUpload() {
    const area = document.getElementById("face-upload");
    const file = document.getElementById("face-file");
    const preview = document.getElementById("face-preview");
    const text = document.getElementById("face-text");

    area.addEventListener("click", () => file.click());
    file.addEventListener("change", async (e) => {
        const f = e.target.files[0];
        if (!f) return;
        const reader = new FileReader();
        reader.onload = (ev) => {
            preview.src = ev.target.result;
            preview.style.display = "block";
            text.style.display = "none";
        };
        reader.readAsDataURL(f);

        const form = new FormData();
        form.append("file", f);
        try {
            const resp = await fetch("/api/steps/upload-face", { method: "POST", body: form });
            const data = await resp.json();
            state.faceImagePath = data.path;
        } catch (err) {
            alert("上传失败: " + err.message);
        }
    });
}


// === 工具函数 ===
function setLoading(btnId, loading) {
    const btn = document.querySelector(`[onclick="${btnId}"]`) || document.getElementById(btnId);
    if (!btn) return;
    if (loading) {
        btn.classList.add("loading");
        btn.disabled = true;
    } else {
        btn.classList.remove("loading");
        btn.disabled = false;
    }
}

function setGlobalStatus(text, busy = false) {
    const dot = document.getElementById("global-status");
    const label = document.getElementById("global-status-text");
    dot.className = busy ? "status-dot busy" : "status-dot";
    label.textContent = text;
}

function updateSummary() {
    const s = state;
    document.getElementById("sum-text").textContent = s.rewrite.text ? "✅ 已改写" : (s.extract.text ? "📝 已提取" : "-");
    document.getElementById("sum-audio").textContent = s.tts.audioPath ? `✅ ${s.tts.duration}秒` : "-";
    document.getElementById("sum-video").textContent = s.video.outputPath ? `✅ ${s.video.duration}秒` : "-";
    document.getElementById("sum-subtitle").textContent = s.subtitle.srtPath ? `✅ ${s.subtitle.segments.length}条` : "-";
    document.getElementById("sum-cover").textContent = s.cover.coverPath ? "✅ 已生成" : "-");

    // 标记就绪项
    ["sum-text", "sum-audio", "sum-video", "sum-subtitle", "sum-cover"].forEach(id => {
        const el = document.getElementById(id);
        el.classList.toggle("ready", el.textContent.startsWith("✅"));
    });
}


// === 步骤1: 提取文案 ===
async function runExtract() {
    const url = document.getElementById("extract-url").value.trim();
    if (!url) { alert("请输入视频链接"); return; }

    const platform = document.getElementById("extract-platform").value;
    setLoading("runExtract", true);
    setGlobalStatus("正在提取文案...", true);

    try {
        const resp = await fetch("/api/steps/extract", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ url, platform }),
        });
        const data = await resp.json();
        if (data.success) {
            state.extract = {
                videoPath: data.video_path,
                text: data.full_text,
                segments: data.segments || [],
                title: data.title,
                duration: data.duration,
            };
            document.getElementById("extract-meta").textContent =
                `📌 ${data.title || "无标题"} | ⏱ ${data.duration}秒`;
            document.getElementById("extract-text").value = data.full_text;
            const wordCount = data.full_text.length;
            document.getElementById("extract-stats").textContent =
                `字数: ${wordCount} | 段落: ${(data.segments || []).length}`;

            // 自动填充到下一步
            document.getElementById("rewrite-input").value =
                "保持原意，换个角度重新表述，更换人物和细节";

            updateSummary();
        } else {
            alert("提取失败: " + (data.error || "未知错误"));
        }
    } catch (e) {
        alert("请求失败: " + e.message);
    } finally {
        setLoading("runExtract", false);
        setGlobalStatus("就绪");
    }
}


// === 步骤2: 改写文案 ===
async function runRewrite() {
    const text = state.extract.text || document.getElementById("extract-text").value;
    if (!text) { alert("请先提取文案或手动输入文案"); return; }

    const style = document.getElementById("rewrite-input").value;
    setLoading("runRewrite", true);
    setGlobalStatus("正在改写文案...", true);

    try {
        const resp = await fetch("/api/steps/rewrite", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text, style }),
        });
        const data = await resp.json();
        if (data.success) {
            state.rewrite = { text: data.rewritten_text, originalText: data.original_text };
            document.getElementById("rewrite-text").value = data.rewritten_text;
            const origLen = data.original_text.length;
            const newLen = data.rewritten_text.length;
            const diff = ((newLen - origLen) / origLen * 100).toFixed(1);
            document.getElementById("rewrite-stats").textContent =
                `原: ${origLen}字 → 新: ${newLen}字 (${diff > 0 ? "+" : ""}${diff}%)`;
            updateSummary();
        } else {
            alert("改写失败: " + (data.error || "未知错误"));
        }
    } catch (e) {
        alert("请求失败: " + e.message);
    } finally {
        setLoading("runRewrite", false);
        setGlobalStatus("就绪");
    }
}


// === 步骤3: TTS配音 ===
async function runTTS() {
    const text = state.rewrite.text || document.getElementById("rewrite-text").value;
    if (!text) { alert("请先改写文案或手动输入文案"); return; }

    const voice = document.getElementById("tts-voice").value;
    const rateVal = document.getElementById("tts-rate").value;
    const rate = (rateVal >= 0 ? "+" : "") + rateVal + "%";

    setLoading("runTTS", true);
    setGlobalStatus("正在生成配音...", true);

    try {
        const resp = await fetch("/api/steps/tts", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text, voice, rate }),
        });
        const data = await resp.json();
        if (data.success) {
            state.tts = { audioPath: data.audio_path, duration: data.duration };
            const audio = document.getElementById("tts-audio");
            audio.src = `/data/outputs/${data.audio_path.split("/").pop()}`;
            audio.style.display = "block";
            document.getElementById("tts-stats").textContent =
                `⏱ 时长: ${data.duration}秒 | 音色: ${voice.split("-").pop().replace("Neural", "")}`;
            updateSummary();
        } else {
            alert("配音失败: " + (data.error || "未知错误"));
        }
    } catch (e) {
        alert("请求失败: " + e.message);
    } finally {
        setLoading("runTTS", false);
        setGlobalStatus("就绪");
    }
}


// === 步骤4: 视频生成 ===
async function runVideo() {
    const videoPath = state.extract.videoPath;
    const audioPath = state.tts.audioPath;
    if (!videoPath) { alert("请先提取视频"); return; }
    if (!audioPath) { alert("请先生成配音"); return; }

    setLoading("runVideo", true);
    setGlobalStatus("正在生成视频...", true);

    try {
        const resp = await fetch("/api/steps/video", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                video_path: videoPath,
                audio_path: audioPath,
                face_image: state.faceImagePath,
            }),
        });
        const data = await resp.json();
        if (data.success) {
            state.video = { outputPath: data.output_path, duration: data.duration };
            const video = document.getElementById("video-preview");
            video.src = `/data/outputs/${data.output_path.split("/").pop()}`;
            video.style.display = "block";
            document.getElementById("video-stats").textContent =
                `✅ 视频生成完成 | ⏱ ${data.duration}秒`;
            updateSummary();
        } else {
            alert("视频生成失败: " + (data.error || "未知错误"));
        }
    } catch (e) {
        alert("请求失败: " + e.message);
    } finally {
        setLoading("runVideo", false);
        setGlobalStatus("就绪");
    }
}


// === 步骤5: 字幕识别 ===
async function runSubtitle() {
    const videoPath = state.video.outputPath || state.extract.videoPath;
    if (!videoPath) { alert("请先生成视频或提取视频"); return; }

    setLoading("runSubtitle", true);
    setGlobalStatus("正在识别字幕...", true);

    try {
        const style = {
            font_name: document.getElementById("sub-font").value,
            font_size: parseInt(document.getElementById("sub-size").value),
            font_color: document.getElementById("sub-color").value,
            margin_v: parseFloat(document.getElementById("sub-margin").value),
        };
        const resp = await fetch("/api/steps/subtitle", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ video_path: videoPath, style }),
        });
        const data = await resp.json();
        if (data.success) {
            state.subtitle = {
                srtPath: data.srt_path,
                segments: data.segments || [],
                fullText: data.full_text,
            };

            // 渲染字幕时间轴
            const timeline = document.getElementById("subtitle-timeline");
            timeline.innerHTML = "";
            (data.segments || []).forEach(seg => {
                const div = document.createElement("div");
                div.className = "sub-item";
                div.innerHTML = `
                    <span class="sub-time">${seg.start} → ${seg.end}</span>
                    <span class="sub-text">${seg.text}</span>
                `;
                timeline.appendChild(div);
            });

            document.getElementById("subtitle-stats").textContent =
                `📝 ${data.segments.length}条字幕 | ⏱ ${data.duration}秒`;
            updateSummary();
        } else {
            alert("字幕识别失败: " + (data.error || "未知错误"));
        }
    } catch (e) {
        alert("请求失败: " + e.message);
    } finally {
        setLoading("runSubtitle", false);
        setGlobalStatus("就绪");
    }
}


// === 步骤6: 封面设计 ===
async function runCover() {
    const videoPath = state.video.outputPath || state.extract.videoPath;
    if (!videoPath) { alert("请先生成视频或提取视频"); return; }

    const title = document.getElementById("cover-title").value ||
                  state.rewrite.text?.slice(0, 20) ||
                  state.extract.title || "";

    setLoading("runCover", true);
    setGlobalStatus("正在生成封面...", true);

    try {
        const style = {
            ratio: document.getElementById("cover-ratio").value,
            font_size: parseInt(document.getElementById("cover-fontsize").value),
        };
        const resp = await fetch("/api/steps/cover", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ video_path: videoPath, title, style }),
        });
        const data = await resp.json();
        if (data.success) {
            state.cover = { coverPath: data.cover_path };
            const img = document.getElementById("cover-preview");
            img.src = `/data/covers/${data.cover_path.split("/").pop()}`;
            img.style.display = "block";
            document.getElementById("cover-stats").textContent = "✅ 封面生成完成";
            updateSummary();
        } else {
            alert("封面生成失败: " + (data.error || "未知错误"));
        }
    } catch (e) {
        alert("请求失败: " + e.message);
    } finally {
        setLoading("runCover", false);
        setGlobalStatus("就绪");
    }
}


// === 步骤7: 导出 ===
async function runExport() {
    const videoPath = state.video.outputPath || state.extract.videoPath;
    if (!videoPath) { alert("请先生成视频"); return; }

    const burnSub = document.getElementById("export-burn-sub").checked;
    setLoading("runExport", true);
    setGlobalStatus("正在导出...", true);

    document.getElementById("export-progress").style.display = "block";
    document.getElementById("export-bar").style.width = "30%";
    document.getElementById("export-bar").textContent = "30%";
    document.getElementById("export-status").textContent = "正在处理...";

    try {
        const resp = await fetch("/api/steps/export", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                video_path: videoPath,
                audio_path: state.tts.audioPath || "",
                subtitle_path: state.subtitle.srtPath || null,
                cover_path: state.cover.coverPath || null,
                burn_subtitles: burnSub,
            }),
        });
        const data = await resp.json();

        document.getElementById("export-bar").style.width = "100%";
        document.getElementById("export-bar").textContent = "100%";

        if (data.success) {
            document.getElementById("export-status").textContent = "✅ 导出完成！";
            const video = document.getElementById("export-video");
            video.src = `/data/outputs/${data.output_path.split("/").pop()}`;
            document.getElementById("export-result").style.display = "block";
            const link = document.getElementById("export-download");
            link.href = video.src;
        } else {
            document.getElementById("export-status").textContent = "❌ " + (data.error || "导出失败");
        }
    } catch (e) {
        document.getElementById("export-status").textContent = "❌ " + e.message;
    } finally {
        setLoading("runExport", false);
        setGlobalStatus("就绪");
    }
}


// === 导出中稿 ===
function exportDraft(step) {
    let content = "";
    let filename = "";
    switch (step) {
        case "extract":
            content = state.extract.text;
            filename = "文案素材.txt";
            break;
        case "rewrite":
            content = state.rewrite.text;
            filename = "改写文案.txt";
            break;
        case "tts":
            if (state.tts.audioPath) {
                const a = document.createElement("a");
                a.href = `/data/outputs/${state.tts.audioPath.split("/").pop()}`;
                a.download = "配音.mp3";
                a.click();
                return;
            }
            alert("请先生成配音");
            return;
        case "video":
        case "subtitle":
        case "cover":
            alert("该步骤的中稿导出功能开发中");
            return;
    }
    if (!content) { alert("暂无内容可导出"); return; }
    const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    a.click();
}


// === 模型配置 ===
function showModelConfig(step) {
    const overlay = document.getElementById("modal-overlay");
    const title = document.getElementById("modal-title");
    const body = document.getElementById("modal-body");

    const configs = {
        extract: {
            title: "模型配置 — 文案提取",
            html: `
                <div class="form-group">
                    <label>ASR 模型</label>
                    <select id="cfg-asr-model">
                        <option value="large-v3">large-v3（推荐）</option>
                        <option value="medium">medium</option>
                        <option value="small">small（快速）</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>设备</label>
                    <select id="cfg-asr-device">
                        <option value="cpu">CPU</option>
                        <option value="cuda">GPU (CUDA)</option>
                    </select>
                </div>
            `,
        },
        rewrite: {
            title: "模型配置 — AI改写",
            html: `
                <div class="form-group">
                    <label>改写模型</label>
                    <select id="cfg-rewrite-model">
                        <option value="openai/gpt-4o-mini">GPT-4o Mini</option>
                        <option value="openai/gpt-4o">GPT-4o</option>
                        <option value="deepseek/deepseek-chat">DeepSeek Chat</option>
                        <option value="anthropic/claude-sonnet-4">Claude Sonnet</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Temperature (0-1)</label>
                    <input type="number" id="cfg-temperature" value="0.8" min="0" max="1" step="0.1">
                </div>
            `,
        },
        tts: {
            title: "模型配置 — 语音合成",
            html: `
                <div class="form-group">
                    <label>TTS 引擎</label>
                    <select id="cfg-tts-engine">
                        <option value="edge-tts">Edge TTS（免费）</option>
                        <option value="azure">Azure TTS</option>
                    </select>
                </div>
            `,
        },
        video: { title: "模型配置 — 视频生成", html: "<p style='color:#888'>视频合成使用 FFmpeg，暂无可配置模型。</p>" },
        subtitle: { title: "模型配置 — 字幕识别", html: "<p style='color:#888'>字幕识别复用 ASR 模型，请在步骤1中配置。</p>" },
        cover: { title: "模型配置 — 封面设计", html: "<p style='color:#888'>封面生成使用 Pillow + FFmpeg，暂无可配置模型。</p>" },
    };

    const cfg = configs[step] || { title: "模型配置", html: "<p>暂无配置项</p>" };
    title.textContent = cfg.title;
    body.innerHTML = cfg.html;
    overlay.style.display = "flex";
}

function closeModal() {
    document.getElementById("modal-overlay").style.display = "none";
}


// === 一键模式（旧版 pipeline） ===
async function startAutoPipeline() {
    const url = document.getElementById("auto-url").value.trim();
    if (!url) { alert("请输入视频链接"); return; }

    const btn = document.querySelector('[onclick="startAutoPipeline()"]');
    btn.disabled = true;
    btn.textContent = "⏳ 处理中...";
    setGlobalStatus("一键模式处理中...", true);

    const progressDiv = document.getElementById("auto-progress");
    progressDiv.style.display = "block";

    try {
        const resp = await fetch("/api/pipeline/start", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                url: url,
                platform: "douyin",
                rewrite_style: "保持原意，换个角度重新表述",
                voice_gender: "male",
            }),
        });
        const data = await resp.json();
        if (data.task_id) {
            pollAutoStatus(data.task_id);
        } else {
            alert("启动失败: " + (data.detail || JSON.stringify(data)));
            resetAutoBtn();
        }
    } catch (e) {
        alert("请求失败: " + e.message);
        resetAutoBtn();
    }
}

function pollAutoStatus(taskId) {
    if (state.autoPollTimer) clearInterval(state.autoPollTimer);
    const steps = ["下载", "语音识别", "AI改写", "TTS配音", "换脸", "合成"];

    state.autoPollTimer = setInterval(async () => {
        try {
            const resp = await fetch(`/api/pipeline/status/${taskId}`);
            const data = await resp.json();

            document.getElementById("auto-bar").style.width = data.progress + "%";
            document.getElementById("auto-bar").textContent = data.progress + "%";

            // 步骤指示器
            const indicator = document.getElementById("auto-steps");
            const statusOrder = ["downloading", "transcribing", "rewriting", "generating_tts", "faceswapping", "compositing"];
            const currentIdx = statusOrder.indexOf(data.status);
            indicator.innerHTML = steps.map((name, i) => {
                let cls = "step-dot";
                if (i < currentIdx) cls += " done";
                else if (i === currentIdx) cls += " active";
                return `<span class="${cls}">${name}</span>`;
            }).join("");

            if (data.status === "done" || data.status === "failed") {
                clearInterval(state.autoPollTimer);
                state.autoPollTimer = null;
                resetAutoBtn();
                if (data.status === "done") {
                    setGlobalStatus("一键处理完成！");
                    // 回填结果到各步骤
                    if (data.original_text) {
                        state.extract.text = data.original_text;
                        document.getElementById("extract-text").value = data.original_text;
                    }
                    if (data.rewritten_text) {
                        state.rewrite.text = data.rewritten_text;
                        document.getElementById("rewrite-text").value = data.rewritten_text;
                    }
                    updateSummary();
                } else {
                    setGlobalStatus("处理失败");
                }
            }
        } catch (e) {
            console.error("轮询失败:", e);
        }
    }, 1500);
}

function resetAutoBtn() {
    const btn = document.querySelector('[onclick="startAutoPipeline()"]');
    btn.disabled = false;
    btn.textContent = "🚀 开始处理";
    setGlobalStatus("就绪");
}
