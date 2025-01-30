document
  .getElementById("downloadForm")
  .addEventListener("submit", async (event) => {
    event.preventDefault();
    const url = document.getElementById("urlInput").value.trim();
    const downloadBtn = document.getElementById("downloadBtn");
    const messageDiv = document.getElementById("message");
    const progressContainer = document.createElement("div");
    const progressBar = document.createElement("div");

    // Create loader element
    const loader = document.createElement("div");
    loader.className = "loader";

    // Reset UI
    messageDiv.textContent = "";
    messageDiv.style.color = ""; // Reset color
    document.querySelector(".video-preview")?.remove();
    progressContainer.className = "progress-container";
    progressBar.className = "progress-bar";
    progressContainer.appendChild(progressBar);
    event.target.parentNode.insertBefore(progressContainer, messageDiv);

    // Set loading state
    downloadBtn.innerHTML = "";
    downloadBtn.appendChild(loader.cloneNode(true));
    downloadBtn.appendChild(document.createTextNode(""));
    downloadBtn.classList.add("button-loading");
    downloadBtn.disabled = true;

    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => {
        controller.abort();
        throw new Error("Request timed out after 5 minutes");
      }, 300000);

      const response = await fetch("/fetch_media", {
        method: "POST",
        signal: controller.signal,
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": document.querySelector('[name="csrf_token"]').value,
        },
        body: JSON.stringify({ url }),
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || "Failed to process video");
      }

      const { video_url, preview_url, task_id } = await response.json();
      const eventSource = new EventSource(`/progress/${task_id}`);

      eventSource.onmessage = (e) => {
        const data = JSON.parse(e.data);
        // Immediately update DOM elements
        requestAnimationFrame(() => {
          if (data.error) {
            messageDiv.textContent = `Error: ${data.error}`;
            messageDiv.style.color = "red";
            eventSource.close();
            return;
          }

          const progressText = `${data.status} ${data.progress.toFixed(
            1
          )}% | Speed: ${data.speed} | ETA: ${data.eta}`;

          // Update button text
          downloadBtn.innerHTML = "";
          const newLoader = loader.cloneNode(true);
          downloadBtn.appendChild(newLoader);
          downloadBtn.appendChild(document.createTextNode(` ${progressText}`));

          // Force immediate DOM update
          progressBar.style.width = `${data.progress}%`;
          messageDiv.textContent = progressText;
          messageDiv.style.color = "#6366f1";

          if (data.progress >= 100) {
            eventSource.close();
            setTimeout(() => {
              progressContainer.remove();
              showVideoPreview(preview_url);
              triggerDownload(video_url);
              messageDiv.textContent =
                "✅ Download complete! Video ready below ↓";
              messageDiv.style.color = "green";
            }, 1500);
          }
        });
      };

      eventSource.onerror = () => {
        eventSource.close();
        messageDiv.textContent = "Progress updates disconnected";
        messageDiv.style.color = "orange";
      };
    } catch (error) {
      console.error("Error:", error);
      const friendlyError = handleError(error.message);
      messageDiv.textContent = `Error: ${friendlyError}`;
      messageDiv.style.color = "red";
      progressContainer.remove();
    } finally {
      // Reset button state
      downloadBtn.classList.remove("button-loading");
      downloadBtn.innerHTML = "Download Video";
      downloadBtn.disabled = false;
    }
  });

function showVideoPreview(url) {
  const video = document.createElement("video");
  video.className = "video-preview";
  video.controls = true;
  video.src = url;
  video.style.width = "100%";
  video.style.marginTop = "20px";
  document.querySelector(".container").appendChild(video);
}

function triggerDownload(url) {
  const link = document.createElement("a");
  link.href = url;
  link.download = decodeURIComponent(url.split("/").pop());
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

function handleError(message) {
  const errorMap = {
    "HTTP Error 403": "Video is age-restricted or unavailable",
    unavailable: "Video not available in your country",
    FFmpeg: "Server processing error (FFmpeg required)",
    private: "Private video - login required",
    "timed out": "Request timed out - try again",
    copyright: "Video unavailable due to copyright",
    removed: "Video has been removed",
  };

  return (
    Object.entries(errorMap).find(([key]) => message.includes(key))?.[1] ||
    `Processing failed: ${message.split(":")[0]}`
  );
}
