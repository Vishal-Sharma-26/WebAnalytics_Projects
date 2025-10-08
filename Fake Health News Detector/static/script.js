document.getElementById('detectBtn').addEventListener('click', function() {
    const newsText = document.getElementById('newsText').value;
    if(newsText.trim() === "") {
        alert("Please enter news text!");
        return;
    }

    fetch('/predict', {
        method: 'POST',
        headers: {'Content-Type': 'application/x-www-form-urlencoded'},
        body: `news_text=${encodeURIComponent(newsText)}`
    })
    .then(response => response.json())
    .then(data => {
        if(data.prediction) {
            document.getElementById('result').innerText = "Prediction: " + data.prediction;
        } else {
            document.getElementById('result').innerText = "Error: " + data.error;
        }
    });
});
