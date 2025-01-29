document.getElementById('downloadForm').addEventListener('submit', async (event) => {
    event.preventDefault();
    const url = document.getElementById('urlInput').value.trim();
    const downloadBtn = document.getElementById('downloadBtn');
    const messageDiv = document.getElementById('message');

    if (!url) {
        alert('Please enter a URL');
        return;
    }

    downloadBtn.textContent = 'Processing...';
    downloadBtn.disabled = true;

    try {
        const response = await fetch('/fetch_media', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ url }),
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Failed to fetch media URLs');
        }

        const result = await response.json();

        if (result.video_url) {
            // Create a link to download the merged file
            const downloadLink = document.createElement('a');
            downloadLink.href = result.video_url;
            downloadLink.download = 'merged_video.mp4';
            downloadLink.click();
        } else {
            throw new Error('Merged video URL missing');
        }
    } catch (error) {
        console.error('Error fetching media:', error);
        messageDiv.textContent = `Error: ${error.message}`;
    } finally {
        downloadBtn.textContent = 'Download Video';
        downloadBtn.disabled = false;          
    }
});
