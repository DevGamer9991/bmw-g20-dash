let tapCount = 0;
let timer = null;

document.addEventListener('click', () => {
    tapCount++;

    console.log(`Tap count: ${tapCount}`); // Log the current tap count for debugging

    // If this is the very first tap, start the 5-second countdown
    if (tapCount === 1) {
        timer = setTimeout(() => {
            // This runs if 5 seconds pass without reaching 5 taps
            tapCount = 0;
        }, 5000); // 5000 milliseconds = 5 seconds
    }

    // Check if they successfully reached 5 taps before the timer reset
    if (tapCount === 5) {
        clearTimeout(timer); // Stop the timer so it doesn't reset in the background
        
        // Redirect to the new location
        window.location.href = "/menu"; 
    }
});