document.getElementById('uploadForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    let formData = new FormData(this);

    try {
        const response = await fetch('/upload', {
            method: 'POST',
            body: formData
        });

        const result = await response.json();
        const resultDiv = document.getElementById('result');

        if(result.status === 'success') {
            resultDiv.innerHTML = `<p>Invoice Uploaded Successfully!<br>
                                   Number: ${result.data.invoice_number} <br>
                                   Date: ${result.data.invoice_date} <br>
                                   Total: ${result.data.total_amount}</p>`;
        } else {
            resultDiv.innerHTML = `<p>Upload Failed!</p>`;
        }
    } catch (err) {
        console.error(err);
        document.getElementById('result').innerHTML = "<p>Error uploading file.</p>";
    }
});
